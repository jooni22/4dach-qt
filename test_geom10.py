import sys
from core.models import Material, RoofPlane
from core.geometry import build_trapezoid_outline, vertical_intersections

plane = RoofPlane(
    id="plane-1",
    name="Trap",
    outline=build_trapezoid_outline("równoramienny", 200, 100, 120),
)
print("x=200", vertical_intersections(plane.outline, 200))
