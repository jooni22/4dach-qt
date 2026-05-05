from __future__ import annotations

import logging
from dataclasses import dataclass, field

from core.app_settings import AppSettings
from core.rounding import ceil_cm
from core.geometry import (
    canonicalize_polygon,
    polygon_edges,
    polygon_is_inside_polygon,
    validate_hole_polygon,
    validate_polygon,
    vertical_segments_for_band,
)
from core.models import Material, Point2D, Polygon2D, RoofPlane, SheetPlacement

EPSILON = 1e-6
logger = logging.getLogger(__name__)


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
    partial_cut_reference_y_cm: float | None = None
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
            "partial_cut_reference_y_cm": self.partial_cut_reference_y_cm,
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


@dataclass(frozen=True, slots=True)
class _RowGeometry:
    y_top_cm: float
    y_bottom_cm: float
    raw_length_cm: float


@dataclass(frozen=True, slots=True)
class _RowPhase:
    start_y_cm: float
    limit_y_cm: float
    terminal_split_reason: str | None = None
    terminal_extra_cm: float = 0.0


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

    layout_plane = _prepare_plane_for_layout(plane, result)
    if layout_plane is None:
        return result

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

    band_ranges = _iter_band_ranges(layout_plane, width)
    partial_cut_references_by_hole = _partial_cut_references_by_hole(layout_plane, band_ranges)

    for band_index, (x_left, x_right) in enumerate(band_ranges):
        band_segments = _build_band_segments(layout_plane, band_index, x_left, x_right)
        layout_band = LayoutBand(band_index=band_index, x_left_cm=x_left, x_right_cm=x_right)

        for band_segment in band_segments:
            _detect_cutout_interaction(
                layout_plane,
                band_segment,
                _settings,
                partial_cut_references_by_hole=partial_cut_references_by_hole,
            )

        for segment_index, band_segment in enumerate(band_segments):
            max_len = material.max_sheet_length_cm
            min_len = material.min_sheet_length_cm
            segment_is_renderable = _append_segment_rows(
                result,
                plane.id,
                material.id,
                band_index,
                segment_index,
                band_segment,
                min_length_cm=min_len,
                max_length_cm=max_len,
            )
            if not segment_is_renderable:
                continue

            band_segment.segment_index = segment_index
            if band_segment.placement_id is None:
                band_segment.placement_id = f"{plane.id}-b{band_index}-s{segment_index}-r0"
            layout_band.segments.append(band_segment)

        result.bands.append(layout_band)

    return result


def _row_geometry(y_cursor: float, limit_y: float, max_len: float) -> _RowGeometry:
    raw_length_cm = min(max_len, y_cursor - limit_y)
    return _RowGeometry(
        y_top_cm=y_cursor - raw_length_cm,
        y_bottom_cm=y_cursor,
        raw_length_cm=raw_length_cm,
    )


def _append_zero_sheet_height_warning(
    result: LayoutResult,
    band_index: int,
    segment_index: int,
) -> None:
    result.warnings.append(
        LayoutWarning(
            code="zero_sheet_height",
            message="Wysokość arkusza wynosi zero - przerwano generowanie",
            data={"band_index": band_index, "segment_index": segment_index},
        )
    )


def _append_invalid_max_sheet_length_warning(
    result: LayoutResult,
    material_id: str,
    max_length_cm: float,
) -> None:
    result.warnings.append(
        LayoutWarning(
            code="invalid_max_sheet_length",
            message="Maksymalna długość arkusza musi być dodatnia",
            data={"material_id": material_id, "max_sheet_length_cm": max_length_cm},
        )
    )


def _make_placement_id(plane_id: str, band_index: int, segment_index: int, row_index: int) -> str:
    return f"{plane_id}-b{band_index}-s{segment_index}-r{row_index}"


def _row_phases_for_segment(segment: LayoutBandSegment) -> list[_RowPhase]:
    cut_reference_y_cm = _segment_partial_cut_reference_y(segment)
    if segment.cutout_interaction == "partial" and cut_reference_y_cm is not None:
        return [
            _RowPhase(start_y_cm=segment.y_bottom_cm, limit_y_cm=cut_reference_y_cm),
            _RowPhase(
                start_y_cm=cut_reference_y_cm,
                limit_y_cm=segment.y_top_cm,
                terminal_split_reason="partial_cutout_top",
                terminal_extra_cm=segment.top_extra_cm,
            ),
        ]
    return [_RowPhase(start_y_cm=segment.y_bottom_cm, limit_y_cm=segment.y_top_cm)]


def _terminal_row_extra(
    phase: _RowPhase,
    row: _RowGeometry,
    max_length_cm: float,
    *,
    is_terminal_row: bool,
) -> float:
    if not is_terminal_row or phase.terminal_extra_cm <= 0:
        return 0.0
    return min(phase.terminal_extra_cm, max(0.0, max_length_cm - row.raw_length_cm))


def _append_phase_rows(
    result: LayoutResult,
    plane_id: str,
    band_index: int,
    segment_index: int,
    band_segment: LayoutBandSegment,
    phase: _RowPhase,
    *,
    min_length_cm: float,
    max_length_cm: float,
    row_index_start: int,
) -> int:
    row_index = row_index_start
    y_cursor = phase.start_y_cm

    while y_cursor > phase.limit_y_cm + EPSILON:
        row = _row_geometry(y_cursor, phase.limit_y_cm, max_length_cm)
        if row.raw_length_cm <= EPSILON:
            _append_zero_sheet_height_warning(result, band_index, segment_index)
            break

        is_terminal_row = row.y_top_cm <= phase.limit_y_cm + EPSILON
        extra_cm = _terminal_row_extra(
            phase,
            row,
            max_length_cm,
            is_terminal_row=is_terminal_row,
        )
        final_length_cm = float(ceil_cm(row.raw_length_cm + extra_cm))
        split_reason = phase.terminal_split_reason if is_terminal_row else None
        placement_id = _record_sheet_outcome(
            result,
            plane_id,
            band_index,
            segment_index,
            row_index,
            band_segment,
            row,
            min_length_cm=min_length_cm,
            final_length_cm=final_length_cm,
            split_reason=split_reason,
            displayed_length_cm=final_length_cm if split_reason is not None else None,
        )

        if placement_id is not None and split_reason == "partial_cutout_top" and extra_cm > 0:
            _extend_segment_coverage_for_top_extra(band_segment, extra_cm)
            band_segment.placement_id = placement_id

        y_cursor -= row.raw_length_cm
        row_index += 1

    return row_index


def _append_segment_rows(
    result: LayoutResult,
    plane_id: str,
    material_id: str,
    band_index: int,
    segment_index: int,
    band_segment: LayoutBandSegment,
    *,
    min_length_cm: float,
    max_length_cm: float,
) -> bool:
    if max_length_cm <= 0:
        _append_invalid_max_sheet_length_warning(result, material_id, max_length_cm)
        return False

    row_index = 0
    for phase in _row_phases_for_segment(band_segment):
        row_index = _append_phase_rows(
            result,
            plane_id,
            band_index,
            segment_index,
            band_segment,
            phase,
            min_length_cm=min_length_cm,
            max_length_cm=max_length_cm,
            row_index_start=row_index,
        )
    return True


def _append_placement(
    result: LayoutResult,
    plane_id: str,
    band_index: int,
    segment_index: int,
    row_index: int,
    band_segment: LayoutBandSegment,
    row: _RowGeometry,
    *,
    final_length_cm: float,
    split_reason: str | None,
) -> str:
    placement_id = _make_placement_id(plane_id, band_index, segment_index, row_index)
    result.placements.append(
        SheetPlacement(
            id=placement_id,
            band_index=band_index,
            x_left_cm=band_segment.x_left_cm,
            x_right_cm=band_segment.x_right_cm,
            y_top_cm=row.y_top_cm,
            y_bottom_cm=row.y_bottom_cm,
            raw_length_cm=row.raw_length_cm,
            final_length_cm=final_length_cm,
            split_reason=split_reason,
        )
    )
    return placement_id


def _append_rejected_segment(
    result: LayoutResult,
    band_index: int,
    band_segment: LayoutBandSegment,
    row: _RowGeometry,
    *,
    displayed_length_cm: float,
    min_length_cm: float,
) -> None:
    result.rejected_segments.append(
        RejectedSegment(
            band_index=band_index,
            x_left_cm=band_segment.x_left_cm,
            x_right_cm=band_segment.x_right_cm,
            y_top_cm=row.y_top_cm,
            y_bottom_cm=row.y_bottom_cm,
            raw_length_cm=row.raw_length_cm,
            reason=f"Arkusz za krótki: {ceil_cm(displayed_length_cm)} cm (min. {ceil_cm(min_length_cm)} cm)",
        )
    )


def _record_sheet_outcome(
    result: LayoutResult,
    plane_id: str,
    band_index: int,
    segment_index: int,
    row_index: int,
    band_segment: LayoutBandSegment,
    row: _RowGeometry,
    *,
    min_length_cm: float,
    final_length_cm: float,
    split_reason: str | None = None,
    displayed_length_cm: float | None = None,
) -> str | None:
    if final_length_cm >= min_length_cm - EPSILON:
        return _append_placement(
            result,
            plane_id,
            band_index,
            segment_index,
            row_index,
            band_segment,
            row,
            final_length_cm=final_length_cm,
            split_reason=split_reason,
        )

    _append_rejected_segment(
        result,
        band_index,
        band_segment,
        row,
        displayed_length_cm=final_length_cm if displayed_length_cm is None else displayed_length_cm,
        min_length_cm=min_length_cm,
    )
    return None


def _extend_segment_coverage_for_top_extra(segment: LayoutBandSegment, extra_cm: float) -> None:
    extended_coverage_polygons: list[Polygon2D] = []
    for polygon in segment.coverage_polygons:
        extended_points: list[Point2D] = []
        for point in polygon.points:
            # Only shift top edge points upward, keep bottom edge in place.
            if abs(point.y - segment.y_top_cm) < EPSILON:
                extended_points.append(Point2D(point.x, point.y - extra_cm))
            else:
                extended_points.append(point)
        extended_coverage_polygons.append(Polygon2D(extended_points))
    segment.coverage_polygons = extended_coverage_polygons


def _prepare_plane_for_layout(plane: RoofPlane, result: LayoutResult) -> RoofPlane | None:
    raw_outline = plane.outline
    if raw_outline is None:
        return None

    _log_split_geometry("raw", plane.id, raw_outline, plane.holes)
    try:
        outline = canonicalize_polygon(raw_outline, clockwise=False)
    except ValueError as exc:
        result.warnings.append(
            LayoutWarning(code="invalid_outline", message=str(exc), data={"plane_id": plane.id})
        )
        return None

    outline_issues = validate_polygon(outline)
    if outline_issues:
        result.warnings.extend(
            LayoutWarning(code="invalid_outline", message=issue, data={"plane_id": plane.id})
            for issue in outline_issues
        )
        return None

    normalized_holes: list[Polygon2D] = []
    for hole_index, raw_hole in enumerate(plane.holes):
        try:
            hole = canonicalize_polygon(raw_hole, clockwise=True)
        except ValueError as exc:
            result.warnings.append(
                LayoutWarning(code="invalid_hole", message=str(exc), data={"plane_id": plane.id, "hole_index": hole_index})
            )
            continue

        hole_issues = validate_polygon(hole)
        if hole_issues:
            result.warnings.extend(
                LayoutWarning(code="invalid_hole", message=issue, data={"plane_id": plane.id, "hole_index": hole_index})
                for issue in hole_issues
            )
            continue
        if not polygon_is_inside_polygon(hole, outline):
            result.warnings.append(
                LayoutWarning(
                    code="hole_outside_outline",
                    message="Wycinek pominięto przy podziale arkuszy, bo po edycji wychodzi poza obrys połaci",
                    data={"plane_id": plane.id, "hole_index": hole_index},
                )
            )
            continue
        overlap_issues = validate_hole_polygon(outline, hole, normalized_holes)
        if overlap_issues:
            result.warnings.extend(
                LayoutWarning(code="invalid_hole", message=issue, data={"plane_id": plane.id, "hole_index": hole_index})
                for issue in overlap_issues
            )
            continue
        normalized_holes.append(hole)

    _log_split_geometry("normalized", plane.id, outline, normalized_holes)
    return RoofPlane(
        id=plane.id,
        name=plane.name,
        outline=outline,
        holes=normalized_holes,
        selected_material_id=plane.selected_material_id,
        generation_settings=plane.generation_settings,
    )



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
    *,
    partial_cut_references_by_hole: list[float | None] | None = None,
) -> None:
    """Inspect holes of *plane* against the segment x/y range and annotate
    *segment* in-place with ``cutout_interaction``, ``partial_cut_line_y_cm``,
    and ``top_extra_cm``.
    """
    full_overlap_detected = False
    partial_cut_reference_y_cm: float | None = None

    for hole_index, hole in enumerate(plane.holes):
        bounds = hole.bounds()

        # Skip holes that don't touch this segment's y-range
        if bounds.max_y <= segment.y_top_cm or bounds.min_y >= segment.y_bottom_cm:
            continue

        # Skip holes that don't touch this segment's x-range
        if bounds.max_x <= segment.x_left_cm or bounds.min_x >= segment.x_right_cm:
            continue

        # FULL: hole covers the entire band width
        if bounds.min_x <= segment.x_left_cm and bounds.max_x >= segment.x_right_cm:
            full_overlap_detected = True
            continue  # keep inspecting — another hole might be partial

        cut_reference_y = None
        if partial_cut_references_by_hole is not None and hole_index < len(partial_cut_references_by_hole):
            cut_reference_y = partial_cut_references_by_hole[hole_index]
        if cut_reference_y is None:
            cut_reference_y = _partial_cut_reference_y_for_hole(hole)
        if partial_cut_reference_y_cm is None or cut_reference_y < partial_cut_reference_y_cm:
            partial_cut_reference_y_cm = cut_reference_y

    if partial_cut_reference_y_cm is not None:
        cut_y = min(max(partial_cut_reference_y_cm, segment.y_top_cm), segment.y_bottom_cm)
        extra_raw = getattr(settings, "partial_cutout_top_extra_cm", 15.0)
        max_possible_extra = cut_y - segment.y_top_cm
        extra_clamped = max(0.0, min(extra_raw, max_possible_extra))

        segment.cutout_interaction = "partial"
        segment.partial_cut_line_y_cm = cut_y
        segment.partial_cut_reference_y_cm = cut_y
        segment.top_extra_cm = extra_clamped
        return

    if full_overlap_detected:
        segment.cutout_interaction = "full"


def _highest_cutout_edge_y_in_range(hole: Polygon2D, x_left: float, x_right: float) -> float | None:
    highest_y: float | None = None
    for start, end in polygon_edges(hole):
        clipped = _clip_edge_to_x_range(start, end, x_left, x_right)
        if clipped is None:
            continue
        clipped_start, clipped_end = clipped
        edge_highest_y = min(clipped_start.y, clipped_end.y)
        if highest_y is None or edge_highest_y < highest_y:
            highest_y = edge_highest_y
    return highest_y


def _segment_partial_cut_reference_y(segment: LayoutBandSegment) -> float | None:
    if segment.partial_cut_reference_y_cm is not None:
        return segment.partial_cut_reference_y_cm
    return segment.partial_cut_line_y_cm


def _partial_cut_reference_y_for_hole(hole: Polygon2D) -> float:
    vertical_side_reference = _vertical_side_reference_y(hole)
    if vertical_side_reference is not None:
        return vertical_side_reference

    plateau_reference = _max_width_plateau_reference_y(hole)
    if plateau_reference is not None:
        return plateau_reference

    return hole.bounds().min_y


def _partial_cut_references_by_hole(
    plane: RoofPlane,
    band_ranges: list[tuple[float, float]],
) -> list[float | None]:
    references: list[float | None] = []
    for hole in plane.holes:
        vertical_side_reference = _vertical_side_reference_y(hole)
        if vertical_side_reference is not None:
            references.append(vertical_side_reference)
            continue

        plateau_reference = _max_width_plateau_reference_y(hole)
        if plateau_reference is not None:
            references.append(plateau_reference)
            continue

        simple_base_reference = _simple_sloped_cutout_base_reference_y(hole)
        if simple_base_reference is not None:
            references.append(simple_base_reference)
            continue

        band_shoulder_reference = _band_shoulder_reference_y(hole, band_ranges)
        if band_shoulder_reference is not None:
            references.append(band_shoulder_reference)
            continue

        references.append(hole.bounds().min_y)
    return references


def _vertical_side_reference_y(hole: Polygon2D) -> float | None:
    bounds = hole.bounds()
    left_top = _outer_vertical_side_top_y(hole, bounds.min_x)
    right_top = _outer_vertical_side_top_y(hole, bounds.max_x)
    if left_top is None or right_top is None:
        return None
    return max(left_top, right_top)


def _outer_vertical_side_top_y(hole: Polygon2D, target_x: float) -> float | None:
    candidates: list[tuple[float, float]] = []
    for start, end in polygon_edges(hole):
        if abs(start.x - end.x) > EPSILON:
            continue
        if abs(start.x - target_x) > EPSILON:
            continue
        top_y = min(start.y, end.y)
        bottom_y = max(start.y, end.y)
        if bottom_y - top_y <= EPSILON:
            continue
        candidates.append((top_y, bottom_y))
    if not candidates:
        return None
    top_y, _ = max(candidates, key=lambda span: (span[1] - span[0], -span[0]))
    return top_y


def _max_width_plateau_reference_y(hole: Polygon2D) -> float | None:
    slabs = _hole_width_slabs(hole)
    if not slabs:
        return None
    if len(slabs) == 1:
        return None

    max_width = max(width_cm for _, _, width_cm in slabs)
    tolerance_cm = max(1e-3, min(1.0, max_width * 0.01))
    plateau_start = _plateau_suffix_start_y(slabs, max_width=max_width, tolerance_cm=tolerance_cm)
    if plateau_start is not None:
        return plateau_start

    stable_run_start = _longest_plateau_run_start_y(slabs, max_width=max_width, tolerance_cm=tolerance_cm)
    if stable_run_start is not None:
        return stable_run_start

    for top_y, _, width_cm in slabs:
        if width_cm >= max_width - tolerance_cm:
            return top_y
    return None


def _hole_width_slabs(hole: Polygon2D) -> list[tuple[float, float, float]]:
    y_levels = _unique_sorted([point.y for point in hole.points])
    slabs: list[tuple[float, float, float]] = []
    for top_y, bottom_y in zip(y_levels, y_levels[1:], strict=False):
        if bottom_y - top_y <= EPSILON:
            continue
        sample_y = (top_y + bottom_y) / 2.0
        span = _horizontal_span_at_y(hole, sample_y)
        if span is None:
            continue
        slabs.append((top_y, bottom_y, span[1] - span[0]))
    return slabs


def _plateau_suffix_start_y(
    slabs: list[tuple[float, float, float]],
    *,
    max_width: float,
    tolerance_cm: float,
) -> float | None:
    suffix_start_y: float | None = None
    for top_y, _, width_cm in reversed(slabs):
        if width_cm < max_width - tolerance_cm:
            break
        suffix_start_y = top_y
    return suffix_start_y


def _longest_plateau_run_start_y(
    slabs: list[tuple[float, float, float]],
    *,
    max_width: float,
    tolerance_cm: float,
) -> float | None:
    best_run: tuple[float, float] | None = None
    current_top_y: float | None = None
    current_height = 0.0

    for top_y, bottom_y, width_cm in slabs:
        if width_cm >= max_width - tolerance_cm:
            if current_top_y is None:
                current_top_y = top_y
                current_height = 0.0
            current_height += bottom_y - top_y
            continue

        if current_top_y is not None:
            if best_run is None or current_height > best_run[1]:
                best_run = (current_top_y, current_height)
            current_top_y = None
            current_height = 0.0

    if current_top_y is not None and (best_run is None or current_height > best_run[1]):
        best_run = (current_top_y, current_height)

    return None if best_run is None else best_run[0]


def _horizontal_span_at_y(hole: Polygon2D, y_value: float) -> tuple[float, float] | None:
    intersections: list[float] = []
    for start, end in polygon_edges(hole):
        if abs(start.y - end.y) <= EPSILON:
            continue
        edge_min_y = min(start.y, end.y)
        edge_max_y = max(start.y, end.y)
        if y_value < edge_min_y - EPSILON or y_value >= edge_max_y - EPSILON:
            continue
        ratio = (y_value - start.y) / (end.y - start.y)
        intersections.append(start.x + ratio * (end.x - start.x))

    if len(intersections) < 2:
        return None

    intersections.sort()
    return intersections[0], intersections[-1]


def _simple_sloped_cutout_base_reference_y(hole: Polygon2D) -> float | None:
    if len(hole.points) not in {3, 4}:
        return None
    if _vertical_side_reference_y(hole) is not None:
        return None
    return hole.bounds().max_y


def _band_shoulder_reference_y(
    hole: Polygon2D,
    band_ranges: list[tuple[float, float]],
) -> float | None:
    touched_bands: list[tuple[int, float, str]] = []
    bounds = hole.bounds()

    for band_index, (x_left, x_right) in enumerate(band_ranges):
        if bounds.max_x <= x_left or bounds.min_x >= x_right:
            continue
        local_top = _highest_cutout_edge_y_in_range(hole, x_left, x_right)
        if local_top is None:
            continue
        interaction = "full" if bounds.min_x <= x_left and bounds.max_x >= x_right else "partial"
        touched_bands.append((band_index, local_top, interaction))

    if len(touched_bands) < 3:
        return None

    tolerance_cm = 1e-6
    full_band_indices = [band_index for band_index, _, interaction in touched_bands if interaction == "full"]
    if not full_band_indices:
        return None

    core_start = min(full_band_indices)
    core_end = max(full_band_indices)
    local_tops_by_band = {band_index: local_top for band_index, local_top, _ in touched_bands}

    left_shoulder = local_tops_by_band.get(core_start - 1)
    right_shoulder = local_tops_by_band.get(core_end + 1)
    shoulder_candidates = [value for value in (left_shoulder, right_shoulder) if value is not None]
    if shoulder_candidates:
        return max(shoulder_candidates)

    partial_band_tops = [local_top for _, local_top, interaction in touched_bands if interaction == "partial"]
    if partial_band_tops:
        return max(partial_band_tops)

    return None


def _clip_edge_to_x_range(
    start: Point2D,
    end: Point2D,
    x_left: float,
    x_right: float,
) -> tuple[Point2D, Point2D] | None:
    edge_min_x = min(start.x, end.x)
    edge_max_x = max(start.x, end.x)
    if edge_max_x < x_left - EPSILON or edge_min_x > x_right + EPSILON:
        return None

    if abs(start.x - end.x) <= EPSILON:
        if x_left - EPSILON <= start.x <= x_right + EPSILON:
            return start, end
        return None

    clipped_left = max(x_left, edge_min_x)
    clipped_right = min(x_right, edge_max_x)
    if clipped_right < clipped_left - EPSILON:
        return None
    return _point_on_edge_at_x(start, end, clipped_left), _point_on_edge_at_x(start, end, clipped_right)


def _point_on_edge_at_x(start: Point2D, end: Point2D, x_value: float) -> Point2D:
    ratio = (x_value - start.x) / (end.x - start.x)
    y_value = start.y + ratio * (end.y - start.y)
    return Point2D(x_value, y_value)


def _polygon_to_dict(polygon: Polygon2D) -> list[list[float]]:
    return [[point.x, point.y] for point in polygon.points]


def _log_split_geometry(label: str, plane_id: str, outline: Polygon2D, holes: list[Polygon2D]) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return
    logger.debug(
        "sheet_split_geometry[%s] plane=%s outline=%s holes=%s",
        label,
        plane_id,
        _polygon_points(outline),
        [_polygon_points(hole) for hole in holes],
    )


def _polygon_points(polygon: Polygon2D) -> list[tuple[float, float]]:
    return [(point.x, point.y) for point in polygon.points]
