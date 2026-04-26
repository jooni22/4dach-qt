import sys
from core.models import Point2D, Polygon2D
from test_geom3 import vertical_intersections
from core.geometry import segments_from_intersections

poly4 = Polygon2D([Point2D(0,100), Point2D(100,100), Point2D(50,50)])
print("tri down x=50 ys:", vertical_intersections(poly4, 50))
print("tri down x=50 segs:", segments_from_intersections(vertical_intersections(poly4, 50)))
