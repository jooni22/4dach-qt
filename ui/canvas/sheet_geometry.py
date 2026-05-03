from __future__ import annotations

import re
from dataclasses import dataclass

from PySide6.QtGui import QPainterPath, QPolygonF

from core.canvas_mapper import CanvasMapper
from core.geometry import segment_length
from core.models import Point2D, Polygon2D, SheetPlacement

SHEET_PLACEMENT_ID_PATTERN = re.compile(r"-b(?P<band>\d+)-s(?P<segment>\d+)-r\d+$")


@dataclass(slots=True)
class SheetRenderItem:
    placement_id: str
    source: str
    band_index: int
    polygons: list[Polygon2D]
    raw_length_cm: float
    final_length_cm: float
    split_reason: str | None = None


def build_sheet_render_items(layout_bands: list[dict], visible_placements: list[SheetPlacement]) -> list[SheetRenderItem]:
    placements_by_id = {placement.id: placement for placement in visible_placements}
    render_items: list[SheetRenderItem] = []
    seen_ids: set[str] = set()

    for band in layout_bands:
        for segment in band.get("segments", []):
            placement_id = segment.get("placement_id")
            if not placement_id:
                continue
            placement = placements_by_id.get(placement_id)
            if placement is None:
                continue
            render_items.append(_sheet_render_item_for_placement(placement))
            seen_ids.add(placement.id)

    for placement in visible_placements:
        if placement.id in seen_ids:
            continue
        render_items.append(_sheet_render_item_for_placement(placement))

    return sorted(render_items, key=lambda item: (item.source != "auto", item.band_index, item.placement_id))


def build_layout_segment_map(layout_bands: list[dict]) -> dict[tuple[int, int], dict]:
    segment_map: dict[tuple[int, int], dict] = {}
    for band in layout_bands:
        band_index = band.get("band_index")
        if band_index is None:
            continue
        for segment in band.get("segments", []):
            segment_index = segment.get("segment_index")
            if segment_index is None:
                continue
            segment_map[(int(band_index), int(segment_index))] = segment
    return segment_map


def segment_key_for_placement(placement_id: str) -> tuple[int, int] | None:
    match = SHEET_PLACEMENT_ID_PATTERN.search(placement_id)
    if match is None:
        return None
    return int(match.group("band")), int(match.group("segment"))


def segment_coverage_polygons(segment: dict) -> list[Polygon2D]:
    polygons: list[Polygon2D] = []
    for polygon_payload in segment.get("coverage_polygons", []):
        if not isinstance(polygon_payload, list) or len(polygon_payload) < 3:
            continue
        points = [
            Point2D(float(point[0]), float(point[1]))
            for point in polygon_payload
            if isinstance(point, (list, tuple)) and len(point) == 2
        ]
        if len(points) >= 3:
            polygons.append(Polygon2D(points))
    return polygons


def placement_render_polygons(placement: SheetPlacement, segment_map: dict[tuple[int, int], dict]) -> list[Polygon2D]:
    segment_key = segment_key_for_placement(placement.id)
    if segment_key is None:
        return []
    segment = segment_map.get(segment_key)
    if segment is None:
        return []
    coverage_polygons = segment_coverage_polygons(segment)
    if not coverage_polygons:
        return []
    return clip_segment_polygons_for_placement(coverage_polygons, placement)


def clip_segment_polygons_for_placement(polygons: list[Polygon2D], placement: SheetPlacement) -> list[Polygon2D]:
    clipped_polygons: list[Polygon2D] = []
    top_extension = max(0.0, placement.final_length_cm - placement.raw_length_cm)
    for polygon in polygons:
        clipped = clip_polygon_to_vertical_span(
            polygon,
            placement.y_top_cm,
            placement.y_bottom_cm,
        )
        if clipped is None:
            continue
        if placement.split_reason == "partial_cutout_top" and top_extension > 0.0:
            clipped = extend_polygon_top(clipped, placement.y_top_cm, top_extension)
        clipped_polygons.append(clipped)
    return clipped_polygons


def clip_polygon_to_vertical_span(
    polygon: Polygon2D,
    y_top_cm: float,
    y_bottom_cm: float,
) -> Polygon2D | None:
    points = list(polygon.points)
    if len(points) < 3:
        return None
    clipped_to_top = clip_polygon_to_half_plane(points, y_value=y_top_cm, keep_below=False)
    clipped_to_span = clip_polygon_to_half_plane(clipped_to_top, y_value=y_bottom_cm, keep_below=True)
    cleaned = clean_polygon_points(clipped_to_span)
    if len(cleaned) < 3:
        return None
    clipped_polygon = Polygon2D(cleaned)
    if abs(clipped_polygon.area()) <= 1e-6:
        return None
    return clipped_polygon


def clip_polygon_to_half_plane(
    points: list[Point2D],
    *,
    y_value: float,
    keep_below: bool,
) -> list[Point2D]:
    if not points:
        return []

    def inside(point: Point2D) -> bool:
        if keep_below:
            return point.y <= y_value + 1e-6
        return point.y >= y_value - 1e-6

    clipped: list[Point2D] = []
    previous = points[-1]
    previous_inside = inside(previous)
    for current in points:
        current_inside = inside(current)
        if current_inside:
            if not previous_inside:
                clipped.append(interpolate_point_at_y(previous, current, y_value))
            clipped.append(current)
        elif previous_inside:
            clipped.append(interpolate_point_at_y(previous, current, y_value))
        previous = current
        previous_inside = current_inside
    return clipped


def interpolate_point_at_y(start: Point2D, end: Point2D, y_value: float) -> Point2D:
    dy = end.y - start.y
    if abs(dy) <= 1e-9:
        return Point2D(end.x, y_value)
    ratio = (y_value - start.y) / dy
    x_value = start.x + ratio * (end.x - start.x)
    return Point2D(x_value, y_value)


def clean_polygon_points(points: list[Point2D]) -> list[Point2D]:
    cleaned: list[Point2D] = []
    for point in points:
        if cleaned and segment_length(cleaned[-1], point) <= 1e-6:
            continue
        cleaned.append(point)
    if len(cleaned) >= 2 and segment_length(cleaned[0], cleaned[-1]) <= 1e-6:
        cleaned.pop()
    return cleaned


def extend_polygon_top(polygon: Polygon2D, top_y_cm: float, extra_cm: float) -> Polygon2D:
    return Polygon2D(
        [
            Point2D(point.x, point.y - extra_cm) if abs(point.y - top_y_cm) <= 1e-6 else point
            for point in polygon.points
        ]
    )


def sheet_item_path(mapper: CanvasMapper, polygons: list[Polygon2D]) -> tuple[list[QPolygonF], QPainterPath]:
    mapped_polygons = [QPolygonF([mapper.map_point(point) for point in polygon.points]) for polygon in polygons]
    union_path = QPainterPath()
    for mapped_polygon in mapped_polygons:
        polygon_path = QPainterPath()
        polygon_path.addPolygon(mapped_polygon)
        union_path = polygon_path if union_path.isEmpty() else union_path.united(polygon_path)
    return mapped_polygons, union_path.simplified()


def placement_polygon(placement: SheetPlacement) -> Polygon2D:
    visual_top = placement.y_top_cm
    if placement.split_reason == "partial_cutout_top":
        visual_top -= max(0.0, placement.final_length_cm - placement.raw_length_cm)
    return Polygon2D(
        [
            Point2D(placement.x_left_cm, visual_top),
            Point2D(placement.x_right_cm, visual_top),
            Point2D(placement.x_right_cm, placement.y_bottom_cm),
            Point2D(placement.x_left_cm, placement.y_bottom_cm),
        ]
    )


def _sheet_render_item_for_placement(placement: SheetPlacement) -> SheetRenderItem:
    return SheetRenderItem(
        placement_id=placement.id,
        source=placement.source,
        band_index=placement.band_index,
        polygons=[placement_polygon(placement)],
        raw_length_cm=placement.raw_length_cm,
        final_length_cm=placement.final_length_cm,
        split_reason=placement.split_reason,
    )
