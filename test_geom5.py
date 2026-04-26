import sys
from core.models import Point2D, Polygon2D

EPSILON = 1e-9
from math import isclose

def vertical_intersections(polygon: Polygon2D, x: float) -> list[float]:
    ys: list[float] = []
    points = polygon.points
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
            
        if x >= max_x - EPSILON and not is_max:
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

poly = Polygon2D([Point2D(0,0), Point2D(100,0), Point2D(100,100), Point2D(0,100)])
print("rect x=100:", vertical_intersections(poly, 100))
