from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, sin

from core.geometry import polygon_edges, segment_length, validate_polygon
from core.models import Point2D, Polygon2D


@dataclass(slots=True, frozen=True)
class ImportDraft:
    points: list[Point2D]
    reference_edge_index: int
    reference_length_cm: float


def cleanup_import_points(
    points: list[Point2D],
    *,
    duplicate_tolerance: float = 1.0,
    collinear_tolerance: float = 0.01,
) -> list[Point2D]:
    deduped: list[Point2D] = []
    for point in points:
        if deduped and segment_length(deduped[-1], point) <= duplicate_tolerance:
            continue
        deduped.append(point)

    if len(deduped) >= 2 and segment_length(deduped[0], deduped[-1]) <= duplicate_tolerance:
        deduped.pop()

    if len(deduped) < 3:
        return deduped

    changed = True
    cleaned = deduped
    while changed and len(cleaned) >= 3:
        changed = False
        filtered: list[Point2D] = []
        count = len(cleaned)
        for index, point in enumerate(cleaned):
            previous = cleaned[index - 1]
            next_point = cleaned[(index + 1) % count]
            if _is_nearly_collinear(
                previous,
                point,
                next_point,
                tolerance=collinear_tolerance,
            ):
                changed = True
                continue
            filtered.append(point)
        cleaned = filtered

    return cleaned


def validate_import_polygon(points: list[Point2D], *, cleanup: bool = True) -> list[str]:
    normalized_points = cleanup_import_points(points) if cleanup else list(points)
    if len(normalized_points) < 3:
        return ["Połać musi mieć co najmniej 3 punkty"]

    try:
        polygon = Polygon2D(normalized_points)
    except ValueError:
        return ["Połać musi mieć co najmniej 3 punkty"]
    return validate_polygon(polygon)


def longest_edge_index(points: list[Point2D]) -> int:
    polygon = Polygon2D(cleanup_import_points(points))
    lengths = [segment_length(start, end) for start, end in polygon_edges(polygon)]
    return max(range(len(lengths)), key=lengths.__getitem__)


def normalize_polygon_to_reference_edge(
    points: list[Point2D],
    *,
    reference_edge_index: int,
    reference_length_cm: float,
    duplicate_tolerance: float = 1.0,
    collinear_tolerance: float = 0.01,
    rounding_digits: int = 2,
    axis_snap_tolerance: float = 0.5,
) -> Polygon2D:
    if reference_length_cm <= 0:
        raise ValueError("Długość referencyjna musi być dodatnia")

    cleaned_points = cleanup_import_points(
        points,
        duplicate_tolerance=duplicate_tolerance,
        collinear_tolerance=collinear_tolerance,
    )
    issues = validate_import_polygon(cleaned_points, cleanup=False)
    if issues:
        raise ValueError("; ".join(issues))

    polygon = Polygon2D(cleaned_points)
    if reference_edge_index < 0 or reference_edge_index >= len(polygon.points):
        raise ValueError("Nieprawidłowa krawędź referencyjna")

    edge_start, edge_end = polygon_edges(polygon)[reference_edge_index]
    edge_length = segment_length(edge_start, edge_end)
    if edge_length <= 0:
        raise ValueError("Krawędź referencyjna ma zerową długość")

    scale = reference_length_cm / edge_length
    scaled = [Point2D(point.x * scale, point.y * scale) for point in polygon.points]
    scaled_edge_start = Point2D(edge_start.x * scale, edge_start.y * scale)
    scaled_edge_end = Point2D(edge_end.x * scale, edge_end.y * scale)
    edge_center = Point2D(
        (scaled_edge_start.x + scaled_edge_end.x) / 2.0,
        (scaled_edge_start.y + scaled_edge_end.y) / 2.0,
    )
    angle = atan2(
        scaled_edge_end.y - scaled_edge_start.y,
        scaled_edge_end.x - scaled_edge_start.x,
    )
    cos_angle = cos(-angle)
    sin_angle = sin(-angle)
    rotated = [
        _snap_point_to_axis(
            _rotate_point_around_center(point, edge_center, cos_angle, sin_angle),
            tolerance=axis_snap_tolerance,
        )
        for point in scaled
    ]
    min_x = min(point.x for point in rotated)
    min_y = min(point.y for point in rotated)
    normalized = [
        Point2D(
            round(point.x - min_x, rounding_digits),
            round(point.y - min_y, rounding_digits),
        )
        for point in rotated
    ]
    return Polygon2D(normalized)


def _rotate_point_around_center(
    point: Point2D,
    center: Point2D,
    cos_angle: float,
    sin_angle: float,
) -> Point2D:
    relative_x = point.x - center.x
    relative_y = point.y - center.y
    return Point2D(
        center.x + relative_x * cos_angle - relative_y * sin_angle,
        center.y + relative_x * sin_angle + relative_y * cos_angle,
    )


def _snap_point_to_axis(point: Point2D, *, tolerance: float) -> Point2D:
    x = 0.0 if abs(point.x) < tolerance else point.x
    y = 0.0 if abs(point.y) < tolerance else point.y
    return Point2D(x, y)


def _is_nearly_collinear(
    previous: Point2D,
    point: Point2D,
    next_point: Point2D,
    *,
    tolerance: float,
) -> bool:
    previous_to_point = segment_length(previous, point)
    point_to_next = segment_length(point, next_point)
    previous_to_next = segment_length(previous, next_point)
    if min(previous_to_point, point_to_next, previous_to_next) <= tolerance:
        return True
    area2 = abs(
        (point.x - previous.x) * (next_point.y - previous.y)
        - (point.y - previous.y) * (next_point.x - previous.x)
    )
    distance = area2 / previous_to_next
    return distance <= tolerance
