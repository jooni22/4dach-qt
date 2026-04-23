from __future__ import annotations

from dataclasses import dataclass, field

from core.layout_engine import LayoutResult
from core.models import cm2_to_m2
from core.project_state import ProjectState


@dataclass(slots=True)
class BomRow:
    material_id: str
    quantity: int
    total_area_m2: float


@dataclass(slots=True)
class LayoutReport:
    net_roof_area_m2: float
    gross_sheet_area_m2: float
    waste_percent: float
    total_cost: float
    bom_rows: list[BomRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def build_report(project_state: ProjectState, layout_result: LayoutResult, material_id: str) -> LayoutReport:
    net_area_cm2 = sum(plane.net_area_cm2 for plane in project_state.roof_planes)
    gross_area_cm2 = sum(placement.area_cm2 for placement in layout_result.placements)
    waste_percent = 0.0
    if gross_area_cm2 > 0:
        waste_percent = max(0.0, ((gross_area_cm2 - net_area_cm2) / gross_area_cm2) * 100.0)

    material = project_state.material_by_id(material_id)
    total_cost = 0.0
    gross_area_m2 = cm2_to_m2(gross_area_cm2)
    if material is not None and material.price_unit == "m2":
        total_cost = gross_area_m2 * material.price_value

    return LayoutReport(
        net_roof_area_m2=cm2_to_m2(net_area_cm2),
        gross_sheet_area_m2=gross_area_m2,
        waste_percent=waste_percent,
        total_cost=total_cost,
        bom_rows=[
            BomRow(
                material_id=material_id,
                quantity=len(layout_result.placements),
                total_area_m2=gross_area_m2,
            )
        ]
        if layout_result.placements
        else [],
        warnings=[warning.message for warning in layout_result.warnings],
    )
