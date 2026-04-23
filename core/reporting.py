from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from html import escape

from core.layout_engine import LayoutResult
from core.models import cm2_to_m2
from core.project_state import ProjectState


@dataclass(slots=True)
class BomRow:
    material_id: str
    sheet_length_cm: float
    quantity: int
    total_area_m2: float


@dataclass(slots=True)
class LayoutReport:
    net_roof_area_m2: float
    gross_sheet_area_m2: float
    waste_area_m2: float
    waste_percent: float
    total_cost: float
    bom_rows: list[BomRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def build_report(
    project_state: ProjectState,
    layout_result: LayoutResult,
    material_id: str,
    plane_id: str | None = None,
) -> LayoutReport:
    plane = project_state.roof_plane_by_id(plane_id) if plane_id else project_state.active_roof_plane()
    net_area_cm2 = plane.net_area_cm2 if plane is not None else sum(item.net_area_cm2 for item in project_state.roof_planes)
    gross_area_cm2 = sum(placement.area_cm2 for placement in layout_result.placements)
    waste_area_cm2 = max(0.0, gross_area_cm2 - net_area_cm2)
    waste_percent = 0.0
    if gross_area_cm2 > 0:
        waste_percent = (waste_area_cm2 / gross_area_cm2) * 100.0

    material = project_state.material_by_id(material_id)
    total_cost = 0.0
    gross_area_m2 = cm2_to_m2(gross_area_cm2)
    if material is not None and material.price_unit == "m2":
        total_cost = gross_area_m2 * material.price_value
    elif material is not None and material.price_unit in {"szt", "arkusz"}:
        total_cost = len(layout_result.placements) * material.price_value

    bom_area_by_length: dict[float, float] = {}
    bom_quantity_by_length: Counter[float] = Counter()
    for placement in layout_result.placements:
        length_key = round(placement.final_length_cm, 6)
        bom_quantity_by_length[length_key] += 1
        bom_area_by_length[length_key] = bom_area_by_length.get(length_key, 0.0) + placement.area_cm2

    warnings = [warning.message for warning in layout_result.warnings]
    rejected_by_reason = Counter(segment.reason for segment in layout_result.rejected_segments)
    for reason, quantity in sorted(rejected_by_reason.items()):
        warnings.append(_rejected_segment_warning(reason, quantity))

    if layout_result.requires_transverse_split and not any("podziału poprzecznego" in warning for warning in warnings):
        warnings.append("Arkusze wymagają podziału poprzecznego")

    return LayoutReport(
        net_roof_area_m2=cm2_to_m2(net_area_cm2),
        gross_sheet_area_m2=gross_area_m2,
        waste_area_m2=cm2_to_m2(waste_area_cm2),
        waste_percent=waste_percent,
        total_cost=total_cost,
        bom_rows=[
            BomRow(
                material_id=material_id,
                sheet_length_cm=sheet_length_cm,
                quantity=quantity,
                total_area_m2=cm2_to_m2(bom_area_by_length[sheet_length_cm]),
            )
            for sheet_length_cm, quantity in sorted(bom_quantity_by_length.items())
        ],
        warnings=warnings,
    )


def _rejected_segment_warning(reason: str, quantity: int) -> str:
    if reason == "below_min_length":
        return f"Pominięto {quantity} segment(y) krótsze niż minimalna długość arkusza"
    return f"Pominięto {quantity} segment(y) z powodu: {reason}"


def build_report_html(
    project_state: ProjectState,
    report: LayoutReport,
    material_id: str,
    plane_id: str | None = None,
    *,
    include_bom: bool = True,
    title_suffix: str | None = None,
) -> str:
    plane = project_state.roof_plane_by_id(plane_id) if plane_id else project_state.active_roof_plane()
    material = project_state.material_by_id(material_id)
    title = f"Raport 4Dach - {plane.name}" if plane is not None else "Raport 4Dach"
    if title_suffix:
        title = f"{title} ({title_suffix})"
    company_lines = [line.strip() for line in project_state.company_data.address.splitlines() if line.strip()]
    company_html = "<br>".join(escape(line) for line in company_lines) or "-"
    warnings_html = "".join(f"<li>{escape(warning)}</li>" for warning in report.warnings) or "<li>Brak ostrzeżeń</li>"
    bom_rows_html = "".join(
        (
            "<tr>"
            f"<td>{escape(row.material_id)}</td>"
            f"<td>{row.sheet_length_cm:.2f}</td>"
            f"<td>{row.quantity}</td>"
            f"<td>{row.total_area_m2:.3f}</td>"
            "</tr>"
        )
        for row in report.bom_rows
    ) or '<tr><td colspan="4">Brak arkuszy</td></tr>'
    bom_section_html = ""
    if include_bom:
        bom_section_html = "".join(
            [
                "<section>",
                "<h2>BOM</h2>",
                "<table>",
                "<thead><tr><th>Materiał</th><th>Długość arkusza [cm]</th><th>Ilość</th><th>Powierzchnia [m2]</th></tr></thead>",
                f"<tbody>{bom_rows_html}</tbody>",
                "</table>",
                "</section>",
            ]
        )

    return "".join(
        [
            "<!DOCTYPE html>",
            '<html lang="pl">',
            "<head>",
            '<meta charset="utf-8">',
            f"<title>{escape(title)}</title>",
            "</head>",
            "<body>",
            f"<h1>{escape(title)}</h1>",
            "<section>",
            "<h2>Dane firmy</h2>",
            f"<p><strong>{escape(project_state.company_data.name or '-')}</strong><br>{company_html}<br>{escape(project_state.company_data.website or '-')}</p>",
            "</section>",
            "<section>",
            "<h2>Zakres raportu</h2>",
            f"<p>Połać: <strong>{escape(plane.name if plane is not None else '-')}</strong><br>Materiał: <strong>{escape(material.nazwa if material is not None else material_id)}</strong></p>",
            "</section>",
            "<section>",
            "<h2>Podsumowanie</h2>",
            "<table>",
            f"<tr><th>Powierzchnia netto [m2]</th><td>{report.net_roof_area_m2:.3f}</td></tr>",
            f"<tr><th>Powierzchnia brutto [m2]</th><td>{report.gross_sheet_area_m2:.3f}</td></tr>",
            f"<tr><th>Odpad [m2]</th><td>{report.waste_area_m2:.3f}</td></tr>",
            f"<tr><th>Odpad [%]</th><td>{report.waste_percent:.2f}</td></tr>",
            f"<tr><th>Koszt całkowity [zł]</th><td>{report.total_cost:.2f}</td></tr>",
            "</table>",
            "</section>",
            bom_section_html,
            "<section>",
            "<h2>Ostrzeżenia</h2>",
            f"<ul>{warnings_html}</ul>",
            "</section>",
            "</body>",
            "</html>",
        ]
    )
