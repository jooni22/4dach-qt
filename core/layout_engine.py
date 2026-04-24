from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil

from core.geometry import validate_polygon, vertical_segments_for_band
from core.models import Material, RoofPlane, SheetPlacement


@dataclass(slots=True)
class LayoutWarning:
    code: str
    message: str
    data: dict = field(default_factory=dict)


@dataclass(slots=True)
class RejectedSegment:
    band_index: int
    x_left_cm: float
    x_right_cm: float
    y_top_cm: float
    y_bottom_cm: float
    raw_length_cm: float
    reason: str


@dataclass(slots=True)
class LayoutResult:
    placements: list[SheetPlacement] = field(default_factory=list)
    warnings: list[LayoutWarning] = field(default_factory=list)
    rejected_segments: list[RejectedSegment] = field(default_factory=list)
    requires_transverse_split: bool = False


def normalize_sheet_length(raw_length_cm: float, material: Material, *, y_top_cm: float = 0.0, y_bottom_cm: float = 0.0, base_line_y_cm: float | None = None) -> float:
    base_length = raw_length_cm + material.bottom_margin_cm + material.top_margin_cm
    if material.type == "dachówkowa" and material.module_length_cm > 0:
        if base_line_y_cm is not None:
            span_from_base = max(base_line_y_cm - y_top_cm, 0.0)
            trimmed_bottom = max(base_line_y_cm - y_bottom_cm, 0.0)
            modules = ceil((span_from_base + material.bottom_margin_cm + material.top_margin_cm) / material.module_length_cm)
            return max(modules * material.module_length_cm - trimmed_bottom, raw_length_cm)
        modules = ceil(base_length / material.module_length_cm)
        return modules * material.module_length_cm
    return base_length


def generate_layout(plane: RoofPlane, material: Material) -> LayoutResult:
    result = LayoutResult()
    if plane.outline is None:
        result.warnings.append(
            LayoutWarning(code="missing_outline", message="Połać nie ma jeszcze obrysu", data={"plane_id": plane.id})
        )
        return result
    result.warnings.extend(
        LayoutWarning(code="invalid_outline", message=issue, data={"plane_id": plane.id})
        for issue in validate_polygon(plane.outline)
    )
    for hole_index, hole in enumerate(plane.holes):
        result.warnings.extend(
            LayoutWarning(code="invalid_hole", message=issue, data={"plane_id": plane.id, "hole_index": hole_index})
            for issue in validate_polygon(hole)
        )

    width = material.effective_width_cm
    if width <= 0:
        result.warnings.append(
            LayoutWarning(code="invalid_material_width", message="Szerokość efektywna materiału musi być dodatnia", data={"material_id": material.id})
        )
        return result

    bounds = plane.outline.bounds()
    if plane.generation_settings.layout_origin == "right":
        x_cursor = bounds.max_x
        band_index = 0
        while x_cursor > bounds.min_x:
            x_left = max(bounds.min_x, x_cursor - width)
            x_right = x_cursor
            _collect_band_segments(result, plane, material, band_index, x_left, x_right)
            x_cursor -= width
            band_index += 1
        return result

    x_cursor = bounds.min_x
    band_index = 0
    while x_cursor < bounds.max_x:
        x_left = x_cursor
        x_right = min(bounds.max_x, x_cursor + width)
        _collect_band_segments(result, plane, material, band_index, x_left, x_right)
        x_cursor += width
        band_index += 1
    return result


def _collect_band_segments(
    result: LayoutResult,
    plane: RoofPlane,
    material: Material,
    band_index: int,
    x_left: float,
    x_right: float,
) -> None:
    for segment_index, (y_top, y_bottom) in enumerate(vertical_segments_for_band(plane.outline, plane.holes, x_left, x_right)):
        raw_length = y_bottom - y_top
        final_length = normalize_sheet_length(
            raw_length,
            material,
            y_top_cm=y_top,
            y_bottom_cm=y_bottom,
            base_line_y_cm=plane.generation_settings.base_line_y_cm,
        )

        if final_length < material.min_sheet_length_cm:
            result.rejected_segments.append(
                RejectedSegment(
                    band_index=band_index,
                    x_left_cm=x_left,
                    x_right_cm=x_right,
                    y_top_cm=y_top,
                    y_bottom_cm=y_bottom,
                    raw_length_cm=raw_length,
                    reason="below_min_length",
                )
            )
            continue

        split_reason = None
        if final_length > material.max_sheet_length_cm:
            result.requires_transverse_split = True
            split_reason = "exceeds_max_length"
            result.warnings.append(
                LayoutWarning(
                    code="requires_transverse_split",
                    message="Arkusz przekracza maksymalną długość i wymaga podziału poprzecznego",
                    data={"band_index": band_index, "material_id": material.id, "final_length_cm": final_length},
                )
            )

        result.placements.append(
            SheetPlacement(
                id=f"{plane.id}-b{band_index}-s{segment_index}",
                band_index=band_index,
                x_left_cm=x_left,
                x_right_cm=x_right,
                y_top_cm=y_top,
                y_bottom_cm=y_bottom,
                raw_length_cm=raw_length,
                final_length_cm=final_length,
                split_reason=split_reason,
            )
        )
