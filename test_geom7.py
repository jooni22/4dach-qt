import sys
from core.models import Material, RoofPlane
from core.geometry import build_trapezoid_outline
from core.layout_engine import generate_layout

plane = RoofPlane(
    id="plane-1",
    name="Trap",
    outline=build_trapezoid_outline("równoramienny", 200, 100, 120),
)
result = generate_layout(plane, Material(
        id="PD510",
        nazwa="PD510",
        type="dachówkowa",
        effective_width_cm=50,
        min_sheet_length_cm=10,
        max_sheet_length_cm=500,
        top_margin_cm=0,
        bottom_margin_cm=0,
        module_length_cm=25,
    ))

for p in result.placements:
    print(p)
