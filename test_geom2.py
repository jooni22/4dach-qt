import sys
from core.models import Point2D, Polygon2D
from core.geometry import vertical_intersections

poly = Polygon2D([Point2D(0,0), Point2D(100,0), Point2D(100,100), Point2D(0,100)])
print("x=100-1e-5:", vertical_intersections(poly, 100 - 1e-5))
