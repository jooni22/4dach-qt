from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil

from core.app_settings import AppSettings
from core.geometry import validate_polygon, vertical_segments_for_band
from core.models import Material, Point2D, Polygon2D, RoofPlane, SheetPlacement


EPSILON = 1e-6


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
class LayoutBandSegment:
    segment_index: int
    x_left_cm: float
    x_right_cm: float
    y_top_cm: float
    y_bottom_cm: float
    raw_length_cm: float
    coverage_polygons: list[Polygon2D] = field(default_factory=list)
    placement_id: str | None = None
    split_reason: str | None = None
    cutout_interaction: str | None = None
    partial_cut_line_y_cm: float | None = None
    top_extra_cm: float = 0.0

    def to_dict(self) -> dict:
        return {
            "segment_index": self.segment_index,
            "x_left_cm": self.x_left_cm,
            "x_right_cm": self.x_right_cm,
            "y_top_cm": self.y_top_cm,
            "y_bottom_cm": self.y_bottom_cm,
            "raw_length_cm": self.raw_length_cm,
            "coverage_polygons": [_polygon_to_dict(polygon) for polygon in self.coverage_polygons],
            "placement_id": self.placement_id,
            "split_reason": self.split_reason,
            "cutout_interaction": self.cutout_interaction,
            "partial_cut_line_y_cm": self.partial_cut_line_y_cm,
            "top_extra_cm": self.top_extra_cm,
        }


@dataclass(slots=True)
class LayoutBand:
    band_index: int
    x_left_cm: float
    x_right_cm: float
    segments: list[LayoutBandSegment] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "band_index": self.band_index,
            "x_left_cm": self.x_left_cm,
            "x_right_cm": self.x_right_cm,
            "segments": [segment.to_dict() for segment in self.segments],
        }


@dataclass(slots=True)
class LayoutResult:
    placements: list[SheetPlacement] = field(default_factory=list)
    bands: list[LayoutBand] = field(default_factory=list)
    warnings: list[LayoutWarning] = field(default_factory=list)
    rejected_segments: list[RejectedSegment] = field(default_factory=list)
    requires_transverse_split: bool = False

    def to_dict(self) -> dict:
        return {
            "placements": [placement.to_dict() for placement in self.placements],
            "bands": [band.to_dict() for band in self.bands],
            "warnings": [
                {
                    "code": warning.code,
                    "message": warning.message,
                    "data": dict(warning.data),
                }
                for warning in self.warnings
            ],
            "rejected_segments": [
                {
                    "band_index": segment.band_index,
                    "x_left_cm": segment.x_left_cm,
                    "x_right_cm": segment.x_right_cm,
                    "y_top_cm": segment.y_top_cm,
                    "y_bottom_cm": segment.y_bottom_cm,
                    "raw_length_cm": segment.raw_length_cm,
                    "reason": segment.reason,
                }
                for segment in self.rejected_segments
            ],
            "requires_transverse_split": self.requires_transverse_split,
        }


@dataclass(slots=True)
class _BandPiece:
    piece_index: int
    slab_index: int
    x_left_cm: float
    x_right_cm: float
    y_top_cm: float
    y_bottom_cm: float
    left_interval: tuple[float, float]
    right_interval: tuple[float, float]
    polygon: Polygon2D

    @property
    def raw_length_cm(self) -> float:
        return self.y_bottom_cm - self.y_top_cm


class _UnionFind:
    def __init__(self, size: int) -> None:
        self._parent = list(range(size))

    def find(self, item: int) -> int:
        parent = self._parent[item]
        if parent != item:
            self._parent[item] = self.find(parent)
        return self._parent[item]

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self._parent[right_root] = left_root


def generate_layout(
    plane: RoofPlane,
    material: Material,
    settings: AppSettings | None = None,
) -> LayoutResult:
    _settings = settings if settings is not None else AppSettings()

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
            LayoutWarning(
                code="invalid_material_width",
                message="Szerokość efektywna materiału musi być dodatnia",
                data={"material_id": material.id},
            )
        )
        return result

    for band_index, (x_left, x_right) in enumerate(_iter_band_ranges(plane, width)):
        band_segments = _build_band_segments(plane, band_index, x_left, x_right)
        layout_band = LayoutBand(band_index=band_index, x_left_cm=x_left, x_right_cm=x_right)

        for band_segment in band_segments:
            _detect_cutout_interaction(plane, band_segment, _settings)

        for segment_index, band_segment in enumerate(band_segments):
            y_bottom = band_segment.y_bottom_cm
            y_top = band_segment.y_top_cm
            max_len = material.max_sheet_length_cm
            row_index = 0

            if (
                band_segment.cutout_interaction == "partial"
                and band_segment.partial_cut_line_y_cm is not None
            ):
                cut_y = band_segment.partial_cut_line_y_cm
                extra = band_segment.top_extra_cm

                # Phase A — BOTTOM: from y_bottom down to cut_y (below the cutout)
                y_cursor = y_bottom
                while y_cursor > cut_y + EPSILON:
                    sheet_height = min(max_len, y_cursor - cut_y)
                    sheet_top = y_cursor - sheet_height
                    sheet_bottom = y_cursor
                    if sheet_height >= material.min_sheet_length_cm - EPSILON:
                        placement_id = f"{plane.id}-b{band_index}-s{segment_index}-r{row_index}"
                        result.placements.append(
                            SheetPlacement(
                                id=placement_id,
                                band_index=band_index,
                                x_left_cm=band_segment.x_left_cm,
                                x_right_cm=band_segment.x_right_cm,
                                y_top_cm=sheet_top,
                                y_bottom_cm=sheet_bottom,
                                raw_length_cm=sheet_height,
                                final_length_cm=sheet_height,
                                split_reason=None,
                            )
                        )
                    else:
                        result.rejected_segments.append(
                            RejectedSegment(
                                band_index=band_index,
                                x_left_cm=band_segment.x_left_cm,
                                x_right_cm=band_segment.x_right_cm,
                                y_top_cm=sheet_top,
                                y_bottom_cm=sheet_bottom,
                                raw_length_cm=sheet_height,
                                reason=f"Arkusz za krótki: {sheet_height:.1f} cm (min. {material.min_sheet_length_cm:.1f} cm)",
                            )
                        )
                    y_cursor -= sheet_height
                    row_index += 1

                # Phase B — TOP: from cut_y down to y_top (above the cutout)
                y_cursor = cut_y
                while y_cursor > y_top + EPSILON:
                    sheet_height = min(max_len, y_cursor - y_top)
                    sheet_top = y_cursor - sheet_height
                    sheet_bottom = y_cursor
                    is_top_sheet = sheet_top <= y_top + EPSILON
                    actual_length = sheet_height + (extra if is_top_sheet else 0.0)
                    placement_split = "partial_cutout_top" if is_top_sheet else None
                    if sheet_height >= material.min_sheet_length_cm - EPSILON:
                        placement_id = f"{plane.id}-b{band_index}-s{segment_index}-r{row_index}"
                        result.placements.append(
                            SheetPlacement(
                                id=placement_id,
                                band_index=band_index,
                                x_left_cm=band_segment.x_left_cm,
                                x_right_cm=band_segment.x_right_cm,
                                y_top_cm=sheet_top,
                                y_bottom_cm=sheet_bottom,
                                raw_length_cm=sheet_height,
                                final_length_cm=actual_length,
                                split_reason=placement_split,
                            )
                        )
                    else:
                        result.rejected_segments.append(
                            RejectedSegment(
                                band_index=band_index,
                                x_left_cm=band_segment.x_left_cm,
                                x_right_cm=band_segment.x_right_cm,
                                y_top_cm=sheet_top,
                                y_bottom_cm=sheet_bottom,
                                raw_length_cm=sheet_height,
                                reason=f"Arkusz za krótki: {sheet_height:.1f} cm (min. {material.min_sheet_length_cm:.1f} cm)",
                            )
                        )
                    y_cursor -= sheet_height
                    row_index += 1

            else:
                # Standard single-phase loop (no partial cutout)
                y_cursor = y_bottom
                while y_cursor > y_top + EPSILON:
                    sheet_height = min(max_len, y_cursor - y_top)
                    sheet_top = y_cursor - sheet_height
                    sheet_bottom = y_cursor
                    if sheet_height >= material.min_sheet_length_cm - EPSILON:
                        placement_id = f"{plane.id}-b{band_index}-s{segment_index}-r{row_index}"
                        result.placements.append(
                            SheetPlacement(
                                id=placement_id,
                                band_index=band_index,
                                x_left_cm=band_segment.x_left_cm,
                                x_right_cm=band_segment.x_right_cm,
                                y_top_cm=sheet_top,
                                y_bottom_cm=sheet_bottom,
                                raw_length_cm=sheet_height,
                                final_length_cm=sheet_height,
                                split_reason=None,
                            )
                        )
                    else:
                        result.rejected_segments.append(
                            RejectedSegment(
                                band_index=band_index,
                                x_left_cm=band_segment.x_left_cm,
                                x_right_cm=band_segment.x_right_cm,
                                y_top_cm=sheet_top,
                                y_bottom_cm=sheet_bottom,
                                raw_length_cm=sheet_height,
                                reason=f"Arkusz za krótki: {sheet_height:.1f} cm (min. {material.min_sheet_length_cm:.1f} cm)",
                            )
                        )
                    y_cursor -= sheet_height
                    row_index += 1

            band_segment.segment_index = segment_index
            band_segment.placement_id = f"{plane.id}-b{band_index}-s{segment_index}-r0"
            layout_band.segments.append(band_segment)

        result.bands.append(layout_band)

    return result



def _iter_band_ranges(plane: RoofPlane, band_width_cm: float) -> list[tuple[float, float]]:
    outline = plane.outline
    if outline is None:
        return []

    bounds = outline.bounds()
    bands: list[tuple[float, float]] = []
    if plane.generation_settings.layout_origin == "right":
        x_cursor = bounds.max_x
        while x_cursor > bounds.min_x + EPSILON:
            x_left = max(bounds.min_x, x_cursor - band_width_cm)
            bands.append((x_left, x_cursor))
            x_cursor -= band_width_cm
        return bands

    x_cursor = bounds.min_x
    while x_cursor < bounds.max_x - EPSILON:
        x_right = min(bounds.max_x, x_cursor + band_width_cm)
        bands.append((x_cursor, x_right))
        x_cursor += band_width_cm
    return bands


def _build_band_segments(plane: RoofPlane, band_index: int, x_left: float, x_right: float) -> list[LayoutBandSegment]:
    pieces = _band_pieces_for_range(plane, x_left, x_right)
    if not pieces:
        return []

    union_find = _UnionFind(len(pieces))
    pieces_by_slab: dict[int, list[_BandPiece]] = {}
    for piece in pieces:
        pieces_by_slab.setdefault(piece.slab_index, []).append(piece)

    for slab_index in sorted(pieces_by_slab):
        current_pieces = pieces_by_slab[slab_index]
        next_pieces = pieces_by_slab.get(slab_index + 1)
        if not next_pieces:
            continue
        for current_piece in current_pieces:
            for next_piece in next_pieces:
                if _intervals_touch_or_overlap(current_piece.right_interval, next_piece.left_interval):
                    union_find.union(current_piece.piece_index, next_piece.piece_index)

    groups: dict[int, list[_BandPiece]] = {}
    for piece in pieces:
        groups.setdefault(union_find.find(piece.piece_index), []).append(piece)

    band_segments: list[LayoutBandSegment] = []
    for segment_index, component in enumerate(
        sorted(
            groups.values(),
            key=lambda group: (
                min(piece.x_left_cm for piece in group),
                min(piece.y_top_cm for piece in group),
                max(piece.y_bottom_cm for piece in group),
            ),
        )
    ):
        coverage_polygons = [
            piece.polygon
            for piece in sorted(component, key=lambda item: (item.x_left_cm, item.y_top_cm, item.piece_index))
        ]
        y_top_cm = min(piece.y_top_cm for piece in component)
        y_bottom_cm = max(piece.y_bottom_cm for piece in component)
        band_segments.append(
            LayoutBandSegment(
                segment_index=segment_index,
                x_left_cm=min(piece.x_left_cm for piece in component),
                x_right_cm=max(piece.x_right_cm for piece in component),
                y_top_cm=y_top_cm,
                y_bottom_cm=y_bottom_cm,
                raw_length_cm=y_bottom_cm - y_top_cm,
                coverage_polygons=coverage_polygons,
            )
        )

    return band_segments


def _band_pieces_for_range(plane: RoofPlane, x_left: float, x_right: float) -> list[_BandPiece]:
    x_positions = _critical_x_positions(plane, x_left, x_right)
    pieces: list[_BandPiece] = []
    piece_index = 0

    for slab_index, (slab_left, slab_right) in enumerate(zip(x_positions, x_positions[1:])):
        slab_width = slab_right - slab_left
        if slab_width <= EPSILON:
            continue

        x_mid = slab_left + slab_width / 2.0
        mid_segments = vertical_segments_for_band(plane.outline, plane.holes, x_mid, x_mid)
        if not mid_segments:
            continue

        left_segments = vertical_segments_for_band(plane.outline, plane.holes, slab_left, slab_left)
        right_segments = vertical_segments_for_band(plane.outline, plane.holes, slab_right, slab_right)

        if len(left_segments) != len(mid_segments):
            left_segments = mid_segments
        if len(right_segments) != len(mid_segments):
            right_segments = mid_segments

        for segment_index, (mid_top, mid_bottom) in enumerate(mid_segments):
            left_top, left_bottom = left_segments[segment_index]
            right_top, right_bottom = right_segments[segment_index]
            y_top_cm = min(left_top, mid_top, right_top)
            y_bottom_cm = max(left_bottom, mid_bottom, right_bottom)
            polygon = Polygon2D(
                [
                    Point2D(slab_left, left_top),
                    Point2D(slab_right, right_top),
                    Point2D(slab_right, right_bottom),
                    Point2D(slab_left, left_bottom),
                ]
            )
            pieces.append(
                _BandPiece(
                    piece_index=piece_index,
                    slab_index=slab_index,
                    x_left_cm=slab_left,
                    x_right_cm=slab_right,
                    y_top_cm=y_top_cm,
                    y_bottom_cm=y_bottom_cm,
                    left_interval=(left_top, left_bottom),
                    right_interval=(right_top, right_bottom),
                    polygon=polygon,
                )
            )
            piece_index += 1

    return pieces


def _critical_x_positions(plane: RoofPlane, x_left: float, x_right: float) -> list[float]:
    xs = [x_left, x_right]
    polygons = [plane.outline, *plane.holes] if plane.outline is not None else []
    for polygon in polygons:
        if polygon is None:
            continue
        for point in polygon.points:
            if x_left + EPSILON < point.x < x_right - EPSILON:
                xs.append(point.x)
    return _unique_sorted(xs)


def _unique_sorted(values: list[float]) -> list[float]:
    ordered = sorted(values)
    unique: list[float] = []
    for value in ordered:
        if not unique or abs(value - unique[-1]) > EPSILON:
            unique.append(value)
    return unique


def _intervals_touch_or_overlap(left: tuple[float, float], right: tuple[float, float]) -> bool:
    left_top, left_bottom = left
    right_top, right_bottom = right
    return min(left_bottom, right_bottom) >= max(left_top, right_top) - EPSILON


def _detect_cutout_interaction(
    plane: RoofPlane,
    segment: LayoutBandSegment,
    settings,
) -> None:
    """Inspect holes of *plane* against the segment x/y range and annotate
    *segment* in-place with ``cutout_interaction``, ``partial_cut_line_y_cm``,
    and ``top_extra_cm``.
    """
    for hole in plane.holes:
        bounds = hole.bounds()

        # Skip holes that don't touch this segment's y-range
        if bounds.max_y <= segment.y_top_cm or bounds.min_y >= segment.y_bottom_cm:
            continue

        # Skip holes that don't touch this segment's x-range
        if bounds.max_x <= segment.x_left_cm or bounds.min_x >= segment.x_right_cm:
            continue

        # FULL: hole covers the entire band width
        if bounds.min_x <= segment.x_left_cm and bounds.max_x >= segment.x_right_cm:
            segment.cutout_interaction = "full"
            continue  # keep inspecting — another hole might be partial

        # PARTIAL: hole partially overlaps this segment in x
        cut_y = bounds.min_y  # top edge of the hole = where the cut must happen
        extra_raw = getattr(settings, "partial_cutout_top_extra_cm", 15.0)
        max_possible_extra = cut_y - segment.y_top_cm
        extra_clamped = max(0.0, min(extra_raw, max_possible_extra))

        segment.cutout_interaction = "partial"
        segment.partial_cut_line_y_cm = cut_y
        segment.top_extra_cm = extra_clamped
        break  # first valid partial hole is sufficient


def _polygon_to_dict(polygon: Polygon2D) -> list[dict[str, float]]:
    return [{"x": point.x, "y": point.y} for point in polygon.points]
