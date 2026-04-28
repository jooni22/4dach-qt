from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from html import escape

from core.layout_engine import LayoutResult
from core.models import SheetPlacement, cm2_to_m2
from core.project_state import ProjectState


@dataclass(slots=True)
class BomRow:
    material_id: str
    sheet_length_cm: float
    quantity: int
    total_area_m2: float
    material_name: str = ""


@dataclass(slots=True)
class LayoutReport:
    net_roof_area_m2: float
    gross_sheet_area_m2: float
    waste_area_m2: float
    waste_percent: float
    total_cost: float
    bom_rows: list[BomRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class PreviewPlacement:
    x_left_cm: float
    x_right_cm: float
    y_top_cm: float
    y_bottom_cm: float
    final_length_cm: float
    source: str


@dataclass(slots=True, frozen=True)
class PlanePreview:
    outline_points: tuple[tuple[float, float], ...]
    hole_points: tuple[tuple[tuple[float, float], ...], ...]
    placements: tuple[PreviewPlacement, ...]


@dataclass(slots=True)
class RoofPlaneSection:
    plane_id: str
    plane_name: str
    material_id: str
    material_name: str
    effective_area_m2: float
    material_usage_area_m2: float
    waste_area_m2: float
    waste_percent: float
    total_cost: float
    sheet_rows: list[BomRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    preview: PlanePreview | None = None


@dataclass(slots=True)
class ProjectTotals:
    total_effective_area_m2: float
    total_material_usage_area_m2: float
    total_waste_area_m2: float
    total_waste_percent: float
    total_cost: float
    total_sheet_count: int


@dataclass(slots=True)
class ProjectReport:
    title: str
    company_name: str
    company_address_lines: list[str]
    company_website: str
    plane_sections: list[RoofPlaneSection] = field(default_factory=list)
    aggregated_bom_rows: list[BomRow] = field(default_factory=list)
    totals: ProjectTotals = field(
        default_factory=lambda: ProjectTotals(
            total_effective_area_m2=0.0,
            total_material_usage_area_m2=0.0,
            total_waste_area_m2=0.0,
            total_waste_percent=0.0,
            total_cost=0.0,
            total_sheet_count=0,
        )
    )


def build_report(
    project_state: ProjectState,
    layout_result: LayoutResult,
    material_id: str,
    plane_id: str | None = None,
) -> LayoutReport:
    plane = project_state.roof_plane_by_id(plane_id) if plane_id else project_state.active_roof_plane()
    material = project_state.material_by_id(material_id)
    placements = project_state.active_sheet_placements_for_plane(plane_id)
    if not placements:
        placements = list(layout_result.placements)
    warnings = _warnings_for_layout_result(layout_result)
    section = _build_roof_plane_section(
        plane=plane,
        placements=placements,
        material_id=material_id,
        material_name=_material_name(material, material_id),
        warnings=warnings,
        price_unit=(material.price_unit if material is not None else None),
        price_value=(material.price_value if material is not None else 0.0),
    )
    return LayoutReport(
        net_roof_area_m2=section.effective_area_m2,
        gross_sheet_area_m2=section.material_usage_area_m2,
        waste_area_m2=section.waste_area_m2,
        waste_percent=section.waste_percent,
        total_cost=section.total_cost,
        bom_rows=section.sheet_rows,
        warnings=section.warnings,
    )


def build_project_report(project_state: ProjectState) -> ProjectReport:
    plane_sections: list[RoofPlaneSection] = []
    aggregated_rows: dict[tuple[str, float], BomRow] = {}

    total_effective_area_cm2 = 0.0
    total_material_usage_area_cm2 = 0.0
    total_cost = 0.0
    total_sheet_count = 0

    for plane in project_state.roof_planes:
        material_id = plane.selected_material_id or project_state.active_material_id() or "-"
        material = project_state.material_by_id(material_id)
        layout_warnings: list[str] = []
        if (
            plane.outline is not None
            and material is not None
            and (plane.layout_dirty_reason or (not plane.auto_sheet_placements and not plane.manual_sheet_placements))
        ):
            try:
                layout_result = project_state.generate_layout_for_plane(plane.id)
            except ValueError:
                layout_result = None
            if layout_result is not None:
                layout_warnings = _warnings_for_layout_result(layout_result)
        placements = project_state.active_sheet_placements_for_plane(plane.id)
        warnings = _warnings_for_plane(project_state, plane, material) + layout_warnings
        section = _build_roof_plane_section(
            plane=plane,
            placements=placements,
            material_id=material_id,
            material_name=_material_name(material, material_id),
            warnings=warnings,
            price_unit=(material.price_unit if material is not None else None),
            price_value=(material.price_value if material is not None else 0.0),
        )
        plane_sections.append(section)

        total_effective_area_cm2 += plane.net_area_cm2
        total_material_usage_area_cm2 += sum(placement.area_cm2 for placement in placements)
        total_cost += section.total_cost
        total_sheet_count += sum(row.quantity for row in section.sheet_rows)

        for row in section.sheet_rows:
            key = (row.material_id, round(row.sheet_length_cm, 6))
            existing = aggregated_rows.get(key)
            if existing is None:
                aggregated_rows[key] = BomRow(
                    material_id=row.material_id,
                    material_name=row.material_name,
                    sheet_length_cm=row.sheet_length_cm,
                    quantity=row.quantity,
                    total_area_m2=row.total_area_m2,
                )
            else:
                existing.quantity += row.quantity
                existing.total_area_m2 += row.total_area_m2

    total_waste_area_cm2 = max(0.0, total_material_usage_area_cm2 - total_effective_area_cm2)
    total_waste_percent = 0.0
    if total_material_usage_area_cm2 > 0:
        total_waste_percent = (total_waste_area_cm2 / total_material_usage_area_cm2) * 100.0

    return ProjectReport(
        title="Raport projektu 4Dach",
        company_name=project_state.company_data.name,
        company_address_lines=[
            line.strip()
            for line in project_state.company_data.address.splitlines()
            if line.strip()
        ],
        company_website=project_state.company_data.website,
        plane_sections=plane_sections,
        aggregated_bom_rows=sorted(
            aggregated_rows.values(),
            key=lambda row: (row.material_name, row.material_id, row.sheet_length_cm),
        ),
        totals=ProjectTotals(
            total_effective_area_m2=cm2_to_m2(total_effective_area_cm2),
            total_material_usage_area_m2=cm2_to_m2(total_material_usage_area_cm2),
            total_waste_area_m2=cm2_to_m2(total_waste_area_cm2),
            total_waste_percent=total_waste_percent,
            total_cost=total_cost,
            total_sheet_count=total_sheet_count,
        ),
    )


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
    preview_placements = project_state.active_sheet_placements_for_plane(plane.id if plane is not None else None)
    section = _build_roof_plane_section(
        plane=plane,
        placements=preview_placements,
        material_id=material_id,
        material_name=_material_name(material, material_id),
        warnings=list(report.warnings),
        price_unit=(material.price_unit if material is not None else None),
        price_value=(material.price_value if material is not None else 0.0),
    )
    section.effective_area_m2 = report.net_roof_area_m2
    section.material_usage_area_m2 = report.gross_sheet_area_m2
    section.waste_area_m2 = report.waste_area_m2
    section.waste_percent = report.waste_percent
    section.total_cost = report.total_cost
    section.sheet_rows = list(report.bom_rows)
    section.warnings = list(report.warnings)
    title = f"Raport 4Dach - {plane.name}" if plane is not None else "Raport 4Dach"
    if title_suffix:
        title = f"{title} ({title_suffix})"
    project_report = ProjectReport(
        title=title,
        company_name=project_state.company_data.name,
        company_address_lines=[
            line.strip()
            for line in project_state.company_data.address.splitlines()
            if line.strip()
        ],
        company_website=project_state.company_data.website,
        plane_sections=[section],
        aggregated_bom_rows=list(report.bom_rows),
        totals=ProjectTotals(
            total_effective_area_m2=report.net_roof_area_m2,
            total_material_usage_area_m2=report.gross_sheet_area_m2,
            total_waste_area_m2=report.waste_area_m2,
            total_waste_percent=report.waste_percent,
            total_cost=report.total_cost,
            total_sheet_count=sum(row.quantity for row in report.bom_rows),
        ),
    )
    return build_project_report_html(
        project_report,
        include_aggregated_bom=include_bom,
        title_override=title,
    )


def build_project_report_html(
    report: ProjectReport,
    *,
    title_suffix: str | None = None,
    include_aggregated_bom: bool = True,
    include_plane_sheet_tables: bool = True,
    page_break_between_planes: bool = True,
    title_override: str | None = None,
) -> str:
    title = title_override or report.title
    if title_suffix:
        title = f"{title} ({title_suffix})"
    company_address_html = "<br>".join(escape(line) for line in report.company_address_lines) or "-"
    company_name = escape(report.company_name or "-")
    company_website = escape(report.company_website or "-")
    plane_sections_html = "".join(
        _render_plane_section_html(
            section,
            include_sheet_table=include_plane_sheet_tables,
            page_break=(page_break_between_planes and index < len(report.plane_sections) - 1),
        )
        for index, section in enumerate(report.plane_sections)
    ) or '<section class="plane-section"><h2>Połacie</h2><p>Brak połaci w projekcie.</p></section>'

    aggregated_bom_html = ""
    if include_aggregated_bom:
        aggregated_bom_html = "".join(
            [
                '<section class="summary-section">',
                "<h2>Zbiorcze zestawienie materiałów</h2>",
                _render_bom_table(report.aggregated_bom_rows, empty_label="Brak arkuszy w projekcie"),
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
            "<style>",
            _REPORT_CSS,
            "</style>",
            "</head>",
            "<body>",
            '<main class="report">',
            '<header class="report-header">',
            f"<h1>{escape(title)}</h1>",
            "<div class=\"company-card\">",
            "<h2>Dane firmy</h2>",
            f"<p><strong>{company_name}</strong><br>{company_address_html}<br>{company_website}</p>",
            "</div>",
            "<div class=\"totals-card\">",
            "<h2>Podsumowanie projektu</h2>",
            "<table>",
            f"<tr><th>Łączna powierzchnia efektywna [m2]</th><td>{report.totals.total_effective_area_m2:.3f}</td></tr>",
            f"<tr><th>Łączne zużycie materiału [m2]</th><td>{report.totals.total_material_usage_area_m2:.3f}</td></tr>",
            f"<tr><th>Łączny odpad [m2]</th><td>{report.totals.total_waste_area_m2:.3f}</td></tr>",
            f"<tr><th>Łączny odpad [%]</th><td>{report.totals.total_waste_percent:.2f}</td></tr>",
            f"<tr><th>Łączna liczba arkuszy</th><td>{report.totals.total_sheet_count}</td></tr>",
            f"<tr><th>Łączny koszt [zł]</th><td>{report.totals.total_cost:.2f}</td></tr>",
            "</table>",
            "</div>",
            "</header>",
            aggregated_bom_html,
            plane_sections_html,
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _build_roof_plane_section(
    *,
    plane,
    placements: list[SheetPlacement],
    material_id: str,
    material_name: str,
    warnings: list[str],
    price_unit: str | None,
    price_value: float,
) -> RoofPlaneSection:
    net_area_cm2 = 0.0 if plane is None else plane.net_area_cm2
    material_usage_area_cm2 = sum(placement.area_cm2 for placement in placements)
    waste_area_cm2 = max(0.0, material_usage_area_cm2 - net_area_cm2)
    waste_percent = 0.0
    if material_usage_area_cm2 > 0:
        waste_percent = (waste_area_cm2 / material_usage_area_cm2) * 100.0

    total_cost = 0.0
    if price_unit == "m2":
        total_cost = cm2_to_m2(material_usage_area_cm2) * price_value
    elif price_unit in {"szt", "arkusz"}:
        total_cost = len(placements) * price_value

    return RoofPlaneSection(
        plane_id=plane.id if plane is not None else "-",
        plane_name=plane.name if plane is not None else "-",
        material_id=material_id,
        material_name=material_name,
        effective_area_m2=cm2_to_m2(net_area_cm2),
        material_usage_area_m2=cm2_to_m2(material_usage_area_cm2),
        waste_area_m2=cm2_to_m2(waste_area_cm2),
        waste_percent=waste_percent,
        total_cost=total_cost,
        sheet_rows=_group_sheet_rows(placements, material_id, material_name),
        warnings=warnings,
        preview=_build_plane_preview(plane, placements),
    )


def _group_sheet_rows(
    placements: list[SheetPlacement],
    material_id: str,
    material_name: str,
) -> list[BomRow]:
    area_by_length_cm: dict[float, float] = {}
    quantity_by_length_cm: Counter[float] = Counter()
    for placement in placements:
        length_key = round(placement.final_length_cm, 6)
        quantity_by_length_cm[length_key] += 1
        area_by_length_cm[length_key] = area_by_length_cm.get(length_key, 0.0) + placement.area_cm2

    return [
        BomRow(
            material_id=material_id,
            material_name=material_name,
            sheet_length_cm=sheet_length_cm,
            quantity=quantity,
            total_area_m2=cm2_to_m2(area_by_length_cm[sheet_length_cm]),
        )
        for sheet_length_cm, quantity in sorted(quantity_by_length_cm.items())
    ]


def _build_plane_preview(plane, placements: list[SheetPlacement]) -> PlanePreview | None:
    if plane is None or plane.outline is None:
        return None
    outline_points = tuple((point.x, point.y) for point in plane.outline.points)
    hole_points = tuple(
        tuple((point.x, point.y) for point in hole.points)
        for hole in plane.holes
    )
    preview_placements = tuple(
        PreviewPlacement(
            x_left_cm=placement.x_left_cm,
            x_right_cm=placement.x_right_cm,
            y_top_cm=placement.y_top_cm,
            y_bottom_cm=placement.y_bottom_cm,
            final_length_cm=placement.final_length_cm,
            source=placement.source,
        )
        for placement in placements
    )
    return PlanePreview(
        outline_points=outline_points,
        hole_points=hole_points,
        placements=preview_placements,
    )


def _warnings_for_layout_result(layout_result: LayoutResult) -> list[str]:
    warnings = [warning.message for warning in layout_result.warnings]
    rejected_by_reason = Counter(segment.reason for segment in layout_result.rejected_segments)
    for reason, quantity in sorted(rejected_by_reason.items()):
        warnings.append(_rejected_segment_warning(reason, quantity))
    if layout_result.requires_transverse_split and not any("podziału poprzecznego" in warning for warning in warnings):
        warnings.append("Arkusze wymagają podziału poprzecznego")
    return warnings


def _warnings_for_plane(project_state: ProjectState, plane, material) -> list[str]:
    warnings: list[str] = []
    if plane.outline is None:
        warnings.append("Połać nie ma jeszcze obrysu")
    if material is None:
        warnings.append("Połać nie ma przypisanego materiału")
    if plane.layout_dirty_reason:
        warnings.append(
            f"Zapisany layout wymaga odświeżenia: {_dirty_reason_label(plane.layout_dirty_reason)}"
        )
    if not plane.auto_sheet_placements and not plane.manual_sheet_placements and plane.outline is not None and material is not None:
        warnings.append("Brak zapisanych arkuszy dla połaci")
    return warnings


def _dirty_reason_label(reason: str) -> str:
    return {
        "geometry_changed": "zmieniono geometrię",
        "material_changed": "zmieniono materiał",
        "manual_override": "wprowadzono ręczne korekty",
    }.get(reason, reason)


def _rejected_segment_warning(reason: str, quantity: int) -> str:
    if reason == "below_min_length":
        return f"Pominięto {quantity} segment(y) krótsze niż minimalna długość arkusza"
    return f"Pominięto {quantity} segment(y) z powodu: {reason}"


def _material_name(material, material_id: str) -> str:
    if material is None:
        return material_id
    return material.nazwa


def _render_plane_section_html(
    section: RoofPlaneSection,
    *,
    include_sheet_table: bool,
    page_break: bool,
) -> str:
    preview_html = "<p>Brak podglądu geometrii.</p>"
    if section.preview is not None:
        preview_html = _build_preview_svg(section.preview)
    warning_items = "".join(f"<li>{escape(warning)}</li>" for warning in section.warnings) or "<li>Brak ostrzeżeń</li>"
    sheet_table_html = ""
    if include_sheet_table:
        sheet_table_html = "".join(
            [
                '<section class="plane-subsection">',
                "<h3>Lista arkuszy</h3>",
                _render_bom_table(section.sheet_rows, empty_label="Brak arkuszy dla połaci"),
                "</section>",
            ]
        )
    css_class = "plane-section page-break" if page_break else "plane-section"
    return "".join(
        [
            f'<section class="{css_class}">',
            f"<h2>Połać: {escape(section.plane_name)}</h2>",
            '<div class="plane-meta">',
            f"<p><strong>Materiał:</strong> {escape(section.material_name)} ({escape(section.material_id)})</p>",
            "</div>",
            '<div class="plane-grid">',
            '<section class="plane-subsection">',
            "<h3>Podsumowanie połaci</h3>",
            "<table>",
            f"<tr><th>Powierzchnia efektywna [m2]</th><td>{section.effective_area_m2:.3f}</td></tr>",
            f"<tr><th>Zużycie materiału [m2]</th><td>{section.material_usage_area_m2:.3f}</td></tr>",
            f"<tr><th>Odpad [m2]</th><td>{section.waste_area_m2:.3f}</td></tr>",
            f"<tr><th>Odpad [%]</th><td>{section.waste_percent:.2f}</td></tr>",
            f"<tr><th>Koszt [zł]</th><td>{section.total_cost:.2f}</td></tr>",
            "</table>",
            "</section>",
            '<section class="plane-subsection">',
            "<h3>Podgląd geometrii</h3>",
            preview_html,
            "</section>",
            "</div>",
            sheet_table_html,
            '<section class="plane-subsection">',
            "<h3>Ostrzeżenia</h3>",
            f"<ul>{warning_items}</ul>",
            "</section>",
            "</section>",
        ]
    )


def _render_bom_table(rows: list[BomRow], *, empty_label: str) -> str:
    body_html = "".join(
        (
            "<tr>"
            f"<td>{escape(row.material_name or row.material_id)}</td>"
            f"<td>{escape(row.material_id)}</td>"
            f"<td>{row.sheet_length_cm:.2f}</td>"
            f"<td>{row.quantity}</td>"
            f"<td>{row.total_area_m2:.3f}</td>"
            "</tr>"
        )
        for row in rows
    ) or f'<tr><td colspan="5">{escape(empty_label)}</td></tr>'
    return "".join(
        [
            '<table class="bom-table">',
            "<thead><tr><th>Materiał</th><th>ID</th><th>Długość arkusza [cm]</th><th>Ilość</th><th>Powierzchnia [m2]</th></tr></thead>",
            f"<tbody>{body_html}</tbody>",
            "</table>",
        ]
    )


def _build_preview_svg(preview: PlanePreview, width: int = 720, height: int = 320) -> str:
    xs = [point[0] for point in preview.outline_points]
    ys = [point[1] for point in preview.outline_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    domain_width = max(max_x - min_x, 1.0)
    domain_height = max(max_y - min_y, 1.0)
    margin = 24.0
    scale = min((width - 2 * margin) / domain_width, (height - 2 * margin) / domain_height)
    offset_x = margin + ((width - 2 * margin) - domain_width * scale) / 2.0
    offset_y = margin + ((height - 2 * margin) - domain_height * scale) / 2.0

    def px(x: float, y: float) -> tuple[float, float]:
        return (
            offset_x + (x - min_x) * scale,
            offset_y + (y - min_y) * scale,
        )

    def polygon_points(points: tuple[tuple[float, float], ...]) -> str:
        return " ".join(f"{px(x, y)[0]:.2f},{px(x, y)[1]:.2f}" for x, y in points)

    parts = [
        f'<svg class="plane-preview" width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#f8fafc"/>',
        f'<polygon points="{polygon_points(preview.outline_points)}" fill="#dbeafe" stroke="#0f172a" stroke-width="2"/>',
    ]
    for hole in preview.hole_points:
        parts.append(
            f'<polygon points="{polygon_points(hole)}" fill="#ffffff" stroke="#475569" stroke-width="1.5" stroke-dasharray="5 4"/>'
        )
    for placement in preview.placements:
        x1, y1 = px(placement.x_left_cm, placement.y_top_cm)
        x2, y2 = px(placement.x_right_cm, placement.y_bottom_cm)
        fill = "#93c5fd" if placement.source == "auto" else "#fdba74"
        parts.append(
            f'<rect x="{x1:.2f}" y="{y1:.2f}" width="{max(x2 - x1, 1.0):.2f}" height="{max(y2 - y1, 1.0):.2f}" fill="{fill}" stroke="#1e293b" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{((x1 + x2) / 2):.2f}" y="{((y1 + y2) / 2):.2f}" font-size="11" text-anchor="middle" dominant-baseline="middle" fill="#0f172a">{placement.final_length_cm:.0f}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


_REPORT_CSS = """
body {
    margin: 0;
    color: #0f172a;
    background: #eef2f7;
    font-family: "DejaVu Sans", "Segoe UI", sans-serif;
}
main.report {
    box-sizing: border-box;
    max-width: 1180px;
    margin: 0 auto;
    padding: 24px;
}
h1, h2, h3, p {
    margin-top: 0;
}
.report-header,
.summary-section,
.plane-section {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
}
.plane-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
}
.plane-subsection {
    margin-bottom: 16px;
}
table {
    width: 100%;
    border-collapse: collapse;
}
th,
td {
    border: 1px solid #cbd5e1;
    padding: 8px 10px;
    text-align: left;
    vertical-align: top;
}
th {
    background: #f8fafc;
}
ul {
    margin: 0;
    padding-left: 18px;
}
svg.plane-preview {
    width: 100%;
    height: auto;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
}
@media print {
    body {
        background: #ffffff;
    }
    main.report {
        max-width: none;
        padding: 0;
    }
    .report-header,
    .summary-section,
    .plane-section {
        border: 0;
        border-radius: 0;
        padding: 0 0 16px 0;
        margin-bottom: 16px;
    }
    .page-break {
        break-after: page;
    }
}
"""
