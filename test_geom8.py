import sys
from core.models import Material, RoofPlane
from core.geometry import build_trapezoid_outline
from core.layout_engine import generate_layout, _band_pieces_for_range

plane = RoofPlane(
    id="plane-1",
    name="Trap",
    outline=build_trapezoid_outline("równoramienny", 200, 100, 120),
)
pieces = _band_pieces_for_range(plane, 150, 200)
for p in pieces:
    print(p.y_top_cm, p.y_bottom_cm)
