import sys
from core.models import Material, RoofPlane
from core.geometry import build_trapezoid_outline, vertical_segments_for_band

plane = RoofPlane(
    id="plane-1",
    name="Trap",
    outline=build_trapezoid_outline("równoramienny", 200, 100, 120),
)
print("x=175", vertical_segments_for_band(plane.outline, plane.holes, 175, 175))
print("x=150", vertical_segments_for_band(plane.outline, plane.holes, 150, 150))
print("x=200", vertical_segments_for_band(plane.outline, plane.holes, 200, 200))
