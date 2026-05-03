from __future__ import annotations

import math
from dataclasses import dataclass

from core.geometry import project_point_to_segment_inside, segment_length
from core.models import Bounds2D, Point2D

GRID_SNAP_THRESHOLD_PX = 8.0
SNAP_3060_THRESHOLD_DEG = 2.0


@dataclass(slots=True, frozen=True)
class DrawSnapState:
    kind: str
    point: Point2D
    label: str = ""


@dataclass(slots=True, frozen=True)
class InferenceLine:
    kind: str
    start: Point2D
    end: Point2D


def snap_domain_point(point: Point2D, *, should_snap: bool, step_cm: float, anchor: Point2D) -> Point2D:
    if not should_snap:
        return point
    snapped_x = anchor.x + round((point.x - anchor.x) / step_cm) * step_cm
    snapped_y = anchor.y - round((anchor.y - point.y) / step_cm) * step_cm
    return Point2D(snapped_x, snapped_y)


def angle_difference_degrees(first: float, second: float) -> float:
    return abs((first - second + 180.0) % 360.0 - 180.0)


def point_from_angle_and_radius(start: Point2D, angle_deg: float, radius: float) -> Point2D:
    radians = math.radians(angle_deg)
    return Point2D(start.x + math.cos(radians) * radius, start.y - math.sin(radians) * radius)


def snap_radius_cm(*, snap_radius_px: float, ui_scale: float, mapper_scale: float) -> float:
    return max(float(snap_radius_px) * ui_scale, 1.0) / max(mapper_scale, 1e-9)


def grid_snap_radius_cm(mapper_scale: float) -> float:
    return GRID_SNAP_THRESHOLD_PX / max(mapper_scale, 1e-9)


def ray_segment_intersection(ray_start: Point2D, ray_end: Point2D, seg_start: Point2D, seg_end: Point2D) -> Point2D | None:
    rx = ray_end.x - ray_start.x
    ry = ray_end.y - ray_start.y
    sx = seg_end.x - seg_start.x
    sy = seg_end.y - seg_start.y
    denominator = rx * sy - ry * sx
    if abs(denominator) <= 1e-9:
        return None
    qpx = seg_start.x - ray_start.x
    qpy = seg_start.y - ray_start.y
    t = (qpx * sy - qpy * sx) / denominator
    u = (qpx * ry - qpy * rx) / denominator
    if t < 0.0 or u < 0.0 or u > 1.0:
        return None
    return Point2D(ray_start.x + t * rx, ray_start.y + t * ry)


def distance_to_infinite_line(point: Point2D, anchor: Point2D, direction: Point2D) -> float:
    return abs((point.x - anchor.x) * direction.y - (point.y - anchor.y) * direction.x)


def points_close(left: Point2D, right: Point2D, tolerance: float = 1e-6) -> bool:
    return abs(left.x - right.x) <= tolerance and abs(left.y - right.y) <= tolerance


def clip_infinite_line_to_bounds(
    anchor: Point2D,
    direction: Point2D,
    bounds: Bounds2D,
) -> tuple[Point2D, Point2D] | None:
    intersections: list[tuple[float, Point2D]] = []
    tolerance = 1e-6
    if abs(direction.x) > tolerance:
        for x in (bounds.min_x, bounds.max_x):
            t = (x - anchor.x) / direction.x
            y = anchor.y + t * direction.y
            if bounds.min_y - tolerance <= y <= bounds.max_y + tolerance:
                intersections.append((t, Point2D(x, y)))
    if abs(direction.y) > tolerance:
        for y in (bounds.min_y, bounds.max_y):
            t = (y - anchor.y) / direction.y
            x = anchor.x + t * direction.x
            if bounds.min_x - tolerance <= x <= bounds.max_x + tolerance:
                intersections.append((t, Point2D(x, y)))
    deduped: list[tuple[float, Point2D]] = []
    for t, point in intersections:
        if any(points_close(point, existing_point) for _, existing_point in deduped):
            continue
        deduped.append((t, point))
    if len(deduped) < 2:
        return None
    deduped.sort(key=lambda item: item[0])
    start_point = deduped[0][1]
    end_point = deduped[-1][1]
    if points_close(start_point, end_point):
        return None
    return start_point, end_point


def best_near_point(candidates: list[tuple[str, Point2D]], raw_point: Point2D, radius: float) -> DrawSnapState | None:
    best: tuple[float, DrawSnapState] | None = None
    for kind, point in candidates:
        distance = segment_length(point, raw_point)
        if distance <= radius and (best is None or distance < best[0]):
            best = (distance, DrawSnapState(kind, point))
    return None if best is None else best[1]


def line_intersection(first: InferenceLine, second: InferenceLine) -> Point2D | None:
    horizontal: InferenceLine | None = None
    vertical: InferenceLine | None = None
    if first.kind == "horizontal" and second.kind == "vertical":
        horizontal = first
        vertical = second
    elif first.kind == "vertical" and second.kind == "horizontal":
        horizontal = second
        vertical = first
    if horizontal is None or vertical is None:
        return None
    return Point2D(vertical.start.x, horizontal.start.y)


def resolve_inference_snap(raw_point: Point2D, inference_lines: list[InferenceLine], radius: float) -> DrawSnapState | None:
    if not inference_lines:
        return None
    line_candidates: list[tuple[str, Point2D]] = []
    intersection_candidates: list[tuple[str, Point2D]] = []
    for line in inference_lines:
        if line.kind == "horizontal":
            line_candidates.append(("horizontal", Point2D(raw_point.x, line.start.y)))
        elif line.kind == "vertical":
            line_candidates.append(("vertical", Point2D(line.start.x, raw_point.y)))
    for index, first in enumerate(inference_lines):
        for second in inference_lines[index + 1 :]:
            intersection = line_intersection(first, second)
            if intersection is not None:
                intersection_candidates.append(("intersection", intersection))
    intersection_state = best_near_point(intersection_candidates, raw_point, radius)
    if intersection_state is not None:
        return intersection_state
    return best_near_point(line_candidates, raw_point, radius)


def resolve_axis_snap(raw_point: Point2D, start: Point2D, *, threshold_deg: float) -> DrawSnapState | None:
    dx = raw_point.x - start.x
    dy = raw_point.y - start.y
    radius = math.hypot(dx, dy)
    if radius <= 1e-6:
        return None
    angle = absolute_angle_degrees_from_delta(dx, dy)
    for target in (0.0, 90.0, 180.0, 270.0):
        if angle_difference_degrees(angle, target) <= threshold_deg:
            return DrawSnapState("axis", point_from_angle_and_radius(start, target, radius), f"{int(target)}°")
    return None


def resolve_angular_snap(
    raw_point: Point2D,
    start: Point2D,
    *,
    snap_to_45deg: bool,
    threshold_45_deg: float,
    snap_to_3060deg: bool,
    threshold_3060_deg: float = SNAP_3060_THRESHOLD_DEG,
) -> DrawSnapState | None:
    dx = raw_point.x - start.x
    dy = raw_point.y - start.y
    radius = math.hypot(dx, dy)
    if radius <= 1e-6:
        return None
    angle = absolute_angle_degrees_from_delta(dx, dy)
    candidates: list[tuple[float, float]] = []
    if snap_to_45deg:
        candidates.extend((target, threshold_45_deg) for target in (45.0, 135.0, 225.0, 315.0))
    if snap_to_3060deg:
        candidates.extend(
            (target, threshold_3060_deg)
            for target in (30.0, 60.0, 120.0, 150.0, 210.0, 240.0, 300.0, 330.0)
        )
    best: tuple[float, float] | None = None
    for target, threshold in candidates:
        delta = angle_difference_degrees(angle, target)
        if delta <= threshold and (best is None or delta < best[0]):
            best = (delta, target)
    if best is None:
        return None
    target = best[1]
    return DrawSnapState("angle", point_from_angle_and_radius(start, target, radius), f"{int(target)}°")


def resolve_point_snap(
    raw_point: Point2D,
    start: Point2D | None,
    *,
    radius: float,
    vertices: list[Point2D],
    edges: list[tuple[Point2D, Point2D]],
) -> DrawSnapState | None:
    vertex = best_near_point([("vertex", point) for point in vertices], raw_point, radius)
    if vertex is not None:
        return vertex
    midpoint_candidates = [
        ("midpoint", Point2D((edge_start.x + edge_end.x) / 2.0, (edge_start.y + edge_end.y) / 2.0))
        for edge_start, edge_end in edges
    ]
    midpoint = best_near_point(midpoint_candidates, raw_point, radius)
    if midpoint is not None:
        return midpoint
    intersection_candidates: list[tuple[str, Point2D]] = []
    projection_candidates: list[tuple[str, Point2D]] = []
    for edge_start, edge_end in edges:
        projection = project_point_to_segment_inside(raw_point, edge_start, edge_end)
        if projection is not None:
            projection_candidates.append(("perpendicular", projection))
        if start is not None:
            intersection = ray_segment_intersection(start, raw_point, edge_start, edge_end)
            if intersection is not None:
                intersection_candidates.append(("intersection", intersection))
    intersection = best_near_point(intersection_candidates, raw_point, radius)
    if intersection is not None:
        return intersection
    return best_near_point(projection_candidates, raw_point, radius)


def build_draw_inferences(
    raw_point: Point2D,
    *,
    start: Point2D | None,
    previous_point: Point2D | None,
    target_vertices: list[Point2D],
    target_edges: list[tuple[Point2D, Point2D]],
    bounds: Bounds2D,
    radius: float,
) -> list[InferenceLine]:
    lines: list[InferenceLine] = []
    for vertex in target_vertices:
        if abs(raw_point.y - vertex.y) <= radius:
            lines.append(InferenceLine("horizontal", Point2D(bounds.min_x, vertex.y), Point2D(bounds.max_x, vertex.y)))
            break
    for vertex in target_vertices:
        if abs(raw_point.x - vertex.x) <= radius:
            lines.append(InferenceLine("vertical", Point2D(vertex.x, bounds.min_y), Point2D(vertex.x, bounds.max_y)))
            break
    if start is not None and previous_point is not None:
        dx = start.x - previous_point.x
        dy = start.y - previous_point.y
        length = math.hypot(dx, dy)
        if length > 1e-6:
            ux = dx / length
            uy = dy / length
            span = max(bounds.width, bounds.height) * 2.0
            lines.append(
                InferenceLine(
                    "continuation",
                    Point2D(start.x - ux * span, start.y - uy * span),
                    Point2D(start.x + ux * span, start.y + uy * span),
                )
            )
    for edge_start, edge_end in target_edges:
        dx = edge_end.x - edge_start.x
        dy = edge_end.y - edge_start.y
        length = math.hypot(dx, dy)
        if length <= 1e-6:
            continue
        direction = Point2D(dx / length, dy / length)
        if distance_to_infinite_line(raw_point, edge_start, direction) > radius:
            continue
        clipped = clip_infinite_line_to_bounds(edge_start, direction, bounds)
        if clipped is None:
            continue
        if any(
            line.kind == "edge_extension"
            and points_close(line.start, clipped[0])
            and points_close(line.end, clipped[1])
            for line in lines
        ):
            continue
        lines.append(InferenceLine("edge_extension", clipped[0], clipped[1]))
    return lines


def absolute_angle_degrees_from_delta(dx: float, dy: float) -> float:
    return (math.degrees(math.atan2(-dy, dx)) + 360.0) % 360.0
