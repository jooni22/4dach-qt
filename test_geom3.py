import sys
from core.models import Point2D, Polygon2D

EPSILON = 1e-9
from math import isclose

def vertical_intersections(polygon: Polygon2D, x: float) -> list[float]:
    ys: list[float] = []
    points = polygon.points

    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        min_x = min(start.x, end.x)
        max_x = max(start.x, end.x)

        if isclose(start.x, end.x, abs_tol=EPSILON):
            continue

        if x < min_x - EPSILON or x > max_x + EPSILON:
            continue

        ratio = (x - start.x) / (end.x - start.x)
        y = start.y + ratio * (end.y - start.y)
        ys.append(y)

    ys.sort()
    return ys

poly = Polygon2D([Point2D(0,0), Point2D(100,0), Point2D(100,100), Point2D(0,100)])
print("rect x=100:", vertical_intersections(poly, 100))

poly2 = Polygon2D([Point2D(0,0), Point2D(100,0), Point2D(50,50)])
print("tri x=50:", vertical_intersections(poly2, 50))
print("tri x=0:", vertical_intersections(poly2, 0))

poly3 = Polygon2D([Point2D(0,0), Point2D(100,0), Point2D(100,100), Point2D(0,100), Point2D(0,75), Point2D(50,50), Point2D(0,25)])
print("concave x=50:", vertical_intersections(poly3, 50))
