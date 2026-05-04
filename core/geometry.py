from __future__ import annotations

from math import isclose, sqrt

from core.models import Point2D, Polygon2D

EPSILON = 1e-9
_NORMALIZED_WIZARD_OUTLINES = {
    "trojkat": ((0.5, 0.0), (1.0, 1.0), (0.0, 1.0)),
    "pieciokat": ((0.5, 0.0), (1.0, 0.4), (1.0, 1.0), (0.0, 1.0), (0.0, 0.4)),
    "pieciokat2": ((0.5, 0.0), (1.0, 0.4), (0.85, 1.0), (0.15, 1.0), (0.0, 0.4)),
}
_WIZARD_TRAPEZOID_ANCHORS = {
    "trapez_row": "center",
    "trapez_prl": "right",
    "trapez_l": "left",
    "trapez6": "left",
    "trapez7": "center",
}


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


def build_add_polac_outline(shape_key: str, values: dict) -> Polygon2D:
    if shape_key == "prostokat":
        return make_rectangle(values["A"], values["B"])

    if shape_key in _NORMALIZED_WIZARD_OUTLINES:
        return _scale_normalized_outline(_NORMALIZED_WIZARD_OUTLINES[shape_key], values["A"], values["B"])

    if shape_key in _WIZARD_TRAPEZOID_ANCHORS:
        return _build_wizard_trapezoid(
            _WIZARD_TRAPEZOID_ANCHORS[shape_key],
            bottom_base_cm=values["A"],
            top_base_cm=values["C"],
            height_cm=values["B"],
        )

    raise ValueError(f"Nieobsługiwany kształt połaci: {shape_key}")


def build_add_polac_cutout(cutout_kind: str, values: dict, outline: Polygon2D) -> Polygon2D | None:
    if cutout_kind == "none":
        return None

    bounds = outline.bounds()
    center_x = bounds.min_x + bounds.width / 2.0
    center_y = bounds.min_y + bounds.height / 2.0

    if cutout_kind == "lukarna1":
        width_cm = values["A"]
        height_cm = values["H1"]
        return Polygon2D.rectangle(
            width_cm,
            height_cm,
            origin_x=center_x - width_cm / 2.0,
            origin_y=center_y - height_cm / 2.0,
        )

    if cutout_kind == "lukarna2":
        return _scale_normalized_outline(
            ((0.5, 0.0), (1.0, 1.0), (0.0, 1.0)),
            values["A"],
            values["H"],
            origin_x=center_x - values["A"] / 2.0,
            origin_y=center_y - values["H"] / 2.0,
        )

    if cutout_kind == "lukarna3":
        width_cm = values["A"]
        height_cm = values["H"]
        top_y = center_y - height_cm / 2.0
        bottom_y = top_y + height_cm
        left_x = center_x - width_cm / 2.0
        right_x = center_x + width_cm / 2.0
        break_y = top_y + values["H1"]
        return Polygon2D(
            [
                Point2D(center_x, top_y),
                Point2D(right_x, break_y),
                Point2D(right_x, bottom_y),
                Point2D(left_x, bottom_y),
                Point2D(left_x, break_y),
            ]
        )

    raise ValueError(f"Nieobsługiwany wycinek połaci: {cutout_kind}")


def flip_polygon_in_bounds(
    polygon: Polygon2D,
    *,
    horizontal: bool = False,
    vertical: bool = False,
) -> Polygon2D:
    if not horizontal and not vertical:
        return polygon.copy()

    bounds = polygon.bounds()

    def _map_point(point: Point2D) -> Point2D:
        next_x = bounds.max_x - (point.x - bounds.min_x) if horizontal else point.x
        next_y = bounds.max_y - (point.y - bounds.min_y) if vertical else point.y
        return Point2D(next_x, next_y)

    return Polygon2D([_map_point(point) for point in polygon.points])


def _scale_normalized_outline(
    normalized_points: tuple[tuple[float, float], ...],
    width_cm: float,
    height_cm: float,
    *,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
) -> Polygon2D:
    _require_positive(width_cm, "Szerokość")
    _require_positive(height_cm, "Wysokość")
    return Polygon2D(
        [
            Point2D(origin_x + x * width_cm, origin_y + y * height_cm)
            for x, y in normalized_points
        ]
    )


def _build_wizard_trapezoid(
    anchor: str,
    *,
    bottom_base_cm: float,
    top_base_cm: float,
    height_cm: float,
) -> Polygon2D:
    _require_positive(bottom_base_cm, "Podstawa dolna")
    _require_positive(top_base_cm, "Podstawa górna")
    _require_positive(height_cm, "Wysokość")

    if anchor == "left":
        top_left_x = 0.0
    elif anchor == "right":
        top_left_x = bottom_base_cm - top_base_cm
    elif anchor == "center":
        top_left_x = (bottom_base_cm - top_base_cm) / 2.0
    else:
        raise ValueError(f"Nieobsługiwane zakotwiczenie trapezu: {anchor}")

    return Polygon2D(
        [
            Point2D(top_left_x, 0.0),
            Point2D(top_left_x + top_base_cm, 0.0),
            Point2D(bottom_base_cm, height_cm),
            Point2D(0.0, height_cm),
        ]
    )


def segment_length(start: Point2D, end: Point2D) -> float:
    return sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2)


def project_point_to_segment_inside(point: Point2D, start: Point2D, end: Point2D) -> Point2D | None:
    dx = end.x - start.x
    dy = end.y - start.y
    length_sq = dx * dx + dy * dy
    if length_sq <= EPSILON:
        return None
    ratio = ((point.x - start.x) * dx + (point.y - start.y) * dy) / length_sq
    if ratio < 0.0 or ratio > 1.0:
        return None
    return Point2D(start.x + ratio * dx, start.y + ratio * dy)


def project_point_to_segment_clamped(point: Point2D, start: Point2D, end: Point2D) -> Point2D:
    dx = end.x - start.x
    dy = end.y - start.y
    length_sq = dx * dx + dy * dy
    if length_sq <= EPSILON:
        return start
    projection = ((point.x - start.x) * dx + (point.y - start.y) * dy) / length_sq
    ratio = min(1.0, max(0.0, projection))
    return Point2D(start.x + dx * ratio, start.y + dy * ratio)


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
    """Validate that *hole* is a valid cutout inside *outline*.

    CRITICAL CONTRACT — do not remove any of the three checks below:

    1. Basic polygon geometry (self-intersections, duplicate points, etc.).
    2. hole must lie ENTIRELY inside outline — enforced by polygon_is_inside_polygon().
       This check was accidentally removed during refactor (2025) and caused
       corrupted sheet-cutting results. It is guarded by:
           tests/test_geometry.py::test_validate_hole_polygon_outside_outline
       Removing this call will make that test fail immediately.
    3. Sibling holes must not overlap each other.
    """
    issues = [f"Wycinek: {issue.lower()}" for issue in validate_polygon(hole)]

    if hole.area() >= outline.area() - EPSILON:
        issues.append("Wycinek musi być mniejszy od obrysu połaci")

    # GUARD — DO NOT REMOVE: ensures every vertex AND every edge midpoint of the
    # hole lies within (or on the boundary of) the outline.  Uses the stronger
    # polygon_is_inside_polygon() instead of a vertex-only point_in_polygon loop
    # so that a hole whose edge crosses the outline boundary is also rejected.
    # Regression test: test_validate_hole_polygon_outside_outline
    if not polygon_is_inside_polygon(hole, outline):
        issues.append("Wycinek musi leżeć w całości wewnątrz obrysu")

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


def canonicalize_polygon(polygon: Polygon2D, *, clockwise: bool | None = None) -> Polygon2D:
    points = list(polygon.points)
    changed = True
    while changed:
        changed = False
        deduped: list[Point2D] = []
        for point in points:
            if deduped and segment_length(deduped[-1], point) <= EPSILON:
                changed = True
                continue
            deduped.append(point)

        if len(deduped) >= 2 and segment_length(deduped[0], deduped[-1]) <= EPSILON:
            deduped.pop()
            changed = True

        if len(deduped) < 3:
            raise ValueError("Polygon po normalizacji musi mieć co najmniej 3 unikalne wierzchołki")

        filtered: list[Point2D] = []
        count = len(deduped)
        for index, point in enumerate(deduped):
            previous = deduped[index - 1]
            next_point = deduped[(index + 1) % count]
            if _point_is_redundant_collinear(point, previous, next_point):
                changed = True
                continue
            filtered.append(point)

        if len(filtered) < 3:
            raise ValueError("Polygon po normalizacji musi mieć co najmniej 3 wierzchołki")
        points = filtered

    normalized = Polygon2D(points)
    if clockwise is None or abs(normalized.signed_area()) <= EPSILON:
        return normalized
    wants_negative_area = clockwise
    has_negative_area = normalized.signed_area() < 0.0
    if has_negative_area == wants_negative_area:
        return normalized
    return Polygon2D(list(reversed(normalized.points)))


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


def point_on_polygon_boundary(point: Point2D, polygon: Polygon2D) -> bool:
    return any(_point_on_segment(point, start, end) for start, end in polygon_edges(polygon))


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


def polygon_is_inside_polygon(inner: Polygon2D, outer: Polygon2D) -> bool:
    """Return True if *inner* lies entirely within (or on the boundary of) *outer*.

    Checks both vertices and edge midpoints to catch the case where all
    vertices are inside but an edge still crosses the boundary.
    """
    if any(not _point_in_polygon_or_on_boundary(point, outer) for point in inner.points):
        return False

    for inner_start, inner_end in polygon_edges(inner):
        midpoint = Point2D((inner_start.x + inner_end.x) / 2.0, (inner_start.y + inner_end.y) / 2.0)
        if not _point_in_polygon_or_on_boundary(midpoint, outer):
            return False
        for outer_start, outer_end in polygon_edges(outer):
            if not segments_intersect(inner_start, inner_end, outer_start, outer_end):
                continue
            if _point_on_segment(inner_start, outer_start, outer_end) or _point_on_segment(inner_end, outer_start, outer_end):
                continue
            return False

    return True


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


def _point_is_redundant_collinear(point: Point2D, previous: Point2D, next_point: Point2D) -> bool:
    if segment_length(previous, next_point) <= EPSILON:
        return True
    if not isclose(_orientation(previous, point, next_point), 0.0, abs_tol=EPSILON):
        return False
    return _point_on_segment(point, previous, next_point)


def _point_in_polygon_or_on_boundary(point: Point2D, polygon: Polygon2D) -> bool:
    if point_in_polygon(point, polygon):
        return True
    return point_on_polygon_boundary(point, polygon)
