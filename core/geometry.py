from __future__ import annotations

from math import isclose
from math import sqrt

from core.models import Point2D, Polygon2D


EPSILON = 1e-9


def _require_positive(value: float, label: str) -> None:
    if value <= 0:
        raise ValueError(f"{label} musi być dodatnia")


def make_rectangle(width_cm: float, height_cm: float) -> Polygon2D:
    _require_positive(width_cm, "Szerokość")
    _require_positive(height_cm, "Wysokość")
    return Polygon2D.rectangle(width_cm, height_cm)


def make_triangle(triangle_type: str, base_cm: float, height_cm: float, side_length_cm: float | None = None) -> Polygon2D:
    _require_positive(base_cm, "Podstawa")
    _require_positive(height_cm, "Wysokość")

    if triangle_type == "prostokątny":
        return Polygon2D(
            [
                Point2D(0.0, 0.0),
                Point2D(base_cm, 0.0),
                Point2D(0.0, height_cm),
            ]
        )

    if triangle_type == "dowolny":
        apex_x = base_cm * 0.66
        if side_length_cm is not None:
            _require_positive(side_length_cm, "Ramię")
            if side_length_cm <= height_cm:
                raise ValueError("Ramię musi być większe od wysokości dla trójkąta dowolnego")
            horizontal = sqrt(max(side_length_cm**2 - height_cm**2, 0.0))
            if horizontal >= base_cm:
                raise ValueError("Ramię jest zbyt długie dla podanej podstawy i wysokości")
            apex_x = horizontal
        return Polygon2D(
            [
                Point2D(0.0, height_cm),
                Point2D(apex_x, 0.0),
                Point2D(base_cm, height_cm),
            ]
        )

    return Polygon2D(
        [
            Point2D(0.0, height_cm),
            Point2D(base_cm / 2.0, 0.0),
            Point2D(base_cm, height_cm),
        ]
    )


def make_trapezoid(trapezoid_type: str, bottom_base_cm: float, top_base_cm: float, height_cm: float) -> Polygon2D:
    _require_positive(bottom_base_cm, "Podstawa dolna")
    _require_positive(top_base_cm, "Podstawa górna")
    _require_positive(height_cm, "Wysokość")

    if trapezoid_type == "prostokątny":
        return Polygon2D(
            [
                Point2D(0.0, height_cm),
                Point2D(0.0, 0.0),
                Point2D(top_base_cm, 0.0),
                Point2D(bottom_base_cm, height_cm),
            ]
        )

    offset = (bottom_base_cm - top_base_cm) / 2.0
    return Polygon2D(
        [
            Point2D(0.0, height_cm),
            Point2D(offset, 0.0),
            Point2D(offset + top_base_cm, 0.0),
            Point2D(bottom_base_cm, height_cm),
        ]
    )


def build_rectangle_outline(width_cm: float, height_cm: float) -> Polygon2D:
    return make_rectangle(width_cm, height_cm)


def build_triangle_outline(triangle_type: str, base_cm: float, height_cm: float, side_length_cm: float | None = None) -> Polygon2D:
    return make_triangle(triangle_type, base_cm, height_cm, side_length_cm)


def build_trapezoid_outline(trapezoid_type: str, bottom_base_cm: float, top_base_cm: float, height_cm: float) -> Polygon2D:
    return make_trapezoid(trapezoid_type, bottom_base_cm, top_base_cm, height_cm)


def segment_length(start: Point2D, end: Point2D) -> float:
    return sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2)


def _orientation(a: Point2D, b: Point2D, c: Point2D) -> float:
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def _point_on_segment(point: Point2D, start: Point2D, end: Point2D) -> bool:
    return (
        min(start.x, end.x) - EPSILON <= point.x <= max(start.x, end.x) + EPSILON
        and min(start.y, end.y) - EPSILON <= point.y <= max(start.y, end.y) + EPSILON
        and isclose(_orientation(start, end, point), 0.0, abs_tol=EPSILON)
    )


def segments_intersect(start_a: Point2D, end_a: Point2D, start_b: Point2D, end_b: Point2D) -> bool:
    orientation_1 = _orientation(start_a, end_a, start_b)
    orientation_2 = _orientation(start_a, end_a, end_b)
    orientation_3 = _orientation(start_b, end_b, start_a)
    orientation_4 = _orientation(start_b, end_b, end_a)

    if orientation_1 * orientation_2 < -EPSILON and orientation_3 * orientation_4 < -EPSILON:
        return True

    return (
        (isclose(orientation_1, 0.0, abs_tol=EPSILON) and _point_on_segment(start_b, start_a, end_a))
        or (isclose(orientation_2, 0.0, abs_tol=EPSILON) and _point_on_segment(end_b, start_a, end_a))
        or (isclose(orientation_3, 0.0, abs_tol=EPSILON) and _point_on_segment(start_a, start_b, end_b))
        or (isclose(orientation_4, 0.0, abs_tol=EPSILON) and _point_on_segment(end_a, start_b, end_b))
    )


def polygon_edges(polygon: Polygon2D) -> list[tuple[Point2D, Point2D]]:
    return [
        (polygon.points[index], polygon.points[(index + 1) % len(polygon.points)])
        for index in range(len(polygon.points))
    ]


def polygon_has_self_intersections(polygon: Polygon2D) -> bool:
    edges = polygon_edges(polygon)
    edge_count = len(edges)
    for index, (start_a, end_a) in enumerate(edges):
        for other_index in range(index + 1, edge_count):
            if other_index in {index, (index - 1) % edge_count, (index + 1) % edge_count}:
                continue
            if index == 0 and other_index == edge_count - 1:
                continue
            start_b, end_b = edges[other_index]
            if segments_intersect(start_a, end_a, start_b, end_b):
                return True
    return False


def validate_polygon(polygon: Polygon2D) -> list[str]:
    issues: list[str] = []
    if polygon.area() <= EPSILON:
        issues.append("Polygon ma zerowe lub ujemne pole")

    unique_points = {(point.x, point.y) for point in polygon.points}
    if len(unique_points) != len(polygon.points):
        issues.append("Polygon zawiera zduplikowane punkty")

    if any(segment_length(start, end) <= EPSILON for start, end in polygon_edges(polygon)):
        issues.append("Polygon zawiera krawędź o zerowej długości")

    if polygon_has_self_intersections(polygon):
        issues.append("Polygon zawiera samoprzecięcia")

    return issues


def validate_hole_polygon(outline: Polygon2D, hole: Polygon2D, sibling_holes: list[Polygon2D] | None = None) -> list[str]:
    issues = [f"Wycinek: {issue.lower()}" for issue in validate_polygon(hole)]
    if hole.area() >= outline.area() - EPSILON:
        issues.append("Wycinek musi być mniejszy od obrysu połaci")

    for sibling_hole in sibling_holes or []:
        if polygons_overlap(hole, sibling_hole):
            issues.append("Wycinki nie mogą na siebie nachodzić")
            break

    return issues


def translate_polygon(polygon: Polygon2D, dx: float, dy: float) -> Polygon2D:
    return polygon.translated(dx, dy)


def replace_polygon_point(polygon: Polygon2D, point_index: int, point: Point2D) -> Polygon2D:
    points = list(polygon.points)
    points[point_index] = point
    return Polygon2D(points)


def insert_polygon_point(polygon: Polygon2D, edge_index: int, point: Point2D) -> Polygon2D:
    points = list(polygon.points)
    points.insert(edge_index + 1, point)
    return Polygon2D(points)


def delete_polygon_point(polygon: Polygon2D, point_index: int) -> Polygon2D:
    if len(polygon.points) <= 3:
        raise ValueError("Polygon po usunięciu punktu musi mieć co najmniej 3 wierzchołki")
    points = list(polygon.points)
    del points[point_index]
    return Polygon2D(points)


def point_in_polygon(point: Point2D, polygon: Polygon2D) -> bool:
    inside = False
    points = polygon.points
    for index, current in enumerate(points):
        previous = points[index - 1]
        intersects = ((current.y > point.y) != (previous.y > point.y)) and (
            point.x < (previous.x - current.x) * (point.y - current.y) / ((previous.y - current.y) or EPSILON) + current.x
        )
        if intersects:
            inside = not inside
    return inside


def vertical_intersections(polygon: Polygon2D, x: float) -> list[float]:
    ys: list[float] = []
    points = polygon.points
    if not points:
        return []
    
    poly_max_x = max(p.x for p in points)
    is_max = isclose(x, poly_max_x, abs_tol=EPSILON)

    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        min_x = min(start.x, end.x)
        max_x = max(start.x, end.x)

        if isclose(start.x, end.x, abs_tol=EPSILON):
            if is_max and isclose(x, start.x, abs_tol=EPSILON):
                ys.extend([start.y, end.y])
            continue

        if x < min_x - EPSILON:
            continue

        if x >= max_x - EPSILON:
            if not (is_max and isclose(max_x, poly_max_x, abs_tol=EPSILON)):
                continue

        ratio = (x - start.x) / (end.x - start.x)
        y = start.y + ratio * (end.y - start.y)
        ys.append(y)

    ys.sort()
    
    if is_max:
        unique_ys = []
        for y in ys:
            if not unique_ys or not isclose(y, unique_ys[-1], abs_tol=EPSILON):
                unique_ys.append(y)
        return unique_ys
        
    return ys


def segments_from_intersections(intersections: list[float]) -> list[tuple[float, float]]:
    if len(intersections) < 2:
        return []

    segments: list[tuple[float, float]] = []
    iterator = iter(intersections)
    for start in iterator:
        end = next(iterator, None)
        if end is None:
            break
        top = min(start, end)
        bottom = max(start, end)
        if bottom - top > EPSILON:
            segments.append((top, bottom))
    return segments


def polygons_overlap(left: Polygon2D, right: Polygon2D) -> bool:
    for point in left.points:
        if point_in_polygon(point, right):
            return True
    for point in right.points:
        if point_in_polygon(point, left):
            return True

    for left_start, left_end in polygon_edges(left):
        for right_start, right_end in polygon_edges(right):
            if segments_intersect(left_start, left_end, right_start, right_end):
                return True

    return False


def subtract_segments(base_segments: list[tuple[float, float]], cut_segments: list[tuple[float, float]]) -> list[tuple[float, float]]:
    result = list(base_segments)
    for cut_top, cut_bottom in cut_segments:
        next_result: list[tuple[float, float]] = []
        for base_top, base_bottom in result:
            if cut_bottom <= base_top + EPSILON or cut_top >= base_bottom - EPSILON:
                next_result.append((base_top, base_bottom))
                continue

            if cut_top > base_top + EPSILON:
                next_result.append((base_top, cut_top))
            if cut_bottom < base_bottom - EPSILON:
                next_result.append((cut_bottom, base_bottom))
        result = next_result
    return result


def vertical_segments_for_band(outline: Polygon2D, holes: list[Polygon2D], x_left: float, x_right: float) -> list[tuple[float, float]]:
    x_sample = x_left + (x_right - x_left) / 2.0
    outline_segments = segments_from_intersections(vertical_intersections(outline, x_sample))
    if not outline_segments:
        return []

    result = outline_segments
    for hole in holes:
        hole_segments = segments_from_intersections(vertical_intersections(hole, x_sample))
        if hole_segments:
            result = subtract_segments(result, hole_segments)
    return result
