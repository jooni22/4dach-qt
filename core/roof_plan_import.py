from __future__ import annotations

from dataclasses import dataclass

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
    min_x = min(point.x for point in scaled)
    min_y = min(point.y for point in scaled)
    normalized = [
        Point2D(
            round(point.x - min_x, rounding_digits),
            round(point.y - min_y, rounding_digits),
        )
        for point in scaled
    ]
    return Polygon2D(normalized)


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
