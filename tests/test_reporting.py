from __future__ import annotations

from core.layout_engine import generate_layout
from core.models import Material, Polygon2D, almost_equal
from core.project_state import ProjectState
from core.reporting import build_report, build_report_html


def test_build_report_aggregates_bom_by_sheet_length_and_cost():
    material = Material(
        id="PD510",
        nazwa="PD510",
        type="dachówkowa",
        effective_width_cm=40,
        module_length_cm=25,
        bottom_margin_cm=10,
        top_margin_cm=15,
        min_sheet_length_cm=20,
        max_sheet_length_cm=500,
        price_unit="m2",
        price_value=12.5,
    )
    state = ProjectState(materials=[material])
    plane = state.add_roof_plane(Polygon2D.rectangle(120, 200), selected_material_id=material.id)
    state.add_hole_to_plane(Polygon2D.rectangle(40, 50, origin_x=40, origin_y=70), plane.id)

    layout_result = generate_layout(plane, material)
    report = build_report(state, layout_result, material.id, plane.id)

    assert almost_equal(report.net_roof_area_m2, 2.2)
    assert almost_equal(report.gross_sheet_area_m2, 2.68)
    assert almost_equal(report.waste_area_m2, 0.48)
    assert almost_equal(report.waste_percent, (4800.0 / 26800.0) * 100.0)
    assert almost_equal(report.total_cost, 33.5)
    assert [(row.sheet_length_cm, row.quantity) for row in report.bom_rows] == [(95, 1), (125, 1), (225, 2)]
    assert almost_equal(report.bom_rows[0].total_area_m2, 0.38)
    assert almost_equal(report.bom_rows[1].total_area_m2, 0.5)
    assert almost_equal(report.bom_rows[2].total_area_m2, 1.8)
    assert report.warnings == []


def test_build_report_includes_layout_warnings_and_rejected_segments():
    material = Material(
        id="TEST",
        nazwa="TEST",
        type="trapezowa",
        effective_width_cm=50,
        module_length_cm=0,
        bottom_margin_cm=0,
        top_margin_cm=0,
        min_sheet_length_cm=80,
        max_sheet_length_cm=120,
        price_unit="arkusz",
        price_value=99.0,
    )
    state = ProjectState(materials=[material])
    plane = state.add_roof_plane(Polygon2D.rectangle(100, 150), selected_material_id=material.id)
    state.add_hole_to_plane(Polygon2D.rectangle(50, 90, origin_x=0, origin_y=30), plane.id)

    layout_result = generate_layout(plane, material)
    report = build_report(state, layout_result, material.id, plane.id)

    assert len(layout_result.placements) == 1
    assert report.total_cost == 99.0
    assert [(row.sheet_length_cm, row.quantity) for row in report.bom_rows] == [(150, 1)]
    assert any("podziału poprzecznego" in warning for warning in report.warnings)
    assert any("krótsze niż minimalna długość arkusza" in warning for warning in report.warnings)


def test_build_report_html_contains_summary_bom_and_warnings():
    material = Material(
        id="TEST",
        nazwa="Blacha testowa",
        type="trapezowa",
        effective_width_cm=50,
        module_length_cm=0,
        bottom_margin_cm=0,
        top_margin_cm=0,
        min_sheet_length_cm=80,
        max_sheet_length_cm=120,
    )
    state = ProjectState(materials=[material])
    state.company_data.name = "Firma Test"
    state.company_data.address = "Ulica 1\n00-001 Miasto"
    state.company_data.website = "example.test"
    plane = state.add_roof_plane(Polygon2D.rectangle(100, 150), selected_material_id=material.id)
    state.add_hole_to_plane(Polygon2D.rectangle(50, 90, origin_x=0, origin_y=30), plane.id)

    layout_result = generate_layout(plane, material)
    report = build_report(state, layout_result, material.id, plane.id)
    html = build_report_html(state, report, material.id, plane.id)

    assert "Raport 4Dach - 1" in html
    assert "Firma Test" in html
    assert "Blacha testowa" in html
    assert "Długość arkusza [cm]" in html
    assert "Ostrzeżenia" in html
    assert "podziału poprzecznego" in html
