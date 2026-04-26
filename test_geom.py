import sys
from core.models import Point2D, Polygon2D
from core.geometry import vertical_intersections

poly = Polygon2D([Point2D(0,0), Point2D(100,0), Point2D(100,100), Point2D(0,100)])
print("x=50:", vertical_intersections(poly, 50))
print("x=100:", vertical_intersections(poly, 100))
