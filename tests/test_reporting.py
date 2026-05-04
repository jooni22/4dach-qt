from __future__ import annotations

from core.layout_engine import generate_layout
from core.models import Material, Polygon2D, SheetPlacement, almost_equal
from core.project_state import ProjectState
from core.reporting import (
    build_project_report,
    build_project_report_html,
    build_report,
    build_report_html,
)


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
    assert almost_equal(report.gross_sheet_area_m2, 2.2)
    assert almost_equal(report.waste_area_m2, 0.0)
    assert almost_equal(report.waste_percent, 0.0)
    assert almost_equal(report.total_cost, 27.5)
    assert [(row.sheet_length_cm, row.quantity) for row in report.bom_rows] == [(70, 1), (80, 1), (200, 2)]
    assert almost_equal(report.bom_rows[0].total_area_m2, 0.28)
    assert almost_equal(report.bom_rows[1].total_area_m2, 0.32)
    assert almost_equal(report.bom_rows[2].total_area_m2, 1.6)
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
    assert report.total_cost == 1 * 99.0
    assert [(row.sheet_length_cm, row.quantity) for row in report.bom_rows] == [(120, 1)]
    assert len(report.warnings) == 1
    assert "Pominięto 3" in report.warnings[0]


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
    assert "podziału poprzecznego" not in html


def test_build_report_html_contains_svg_with_sheet_rects():
    config_dict = {
        "company_data": {"name": "Test", "nip": "123", "address": "Addr", "website": "web.test", "logo": "logo.png"},
        "blachy": [
            {"id": "MAT1", "nazwa": "Material 1", "type": "trapezowa", "szerokosc_efektywna": 50, "dlugosc_modulu": 25, "zapas_dolny": 10, "zapas_gorny": 15, "min_dlugosc_arkusza": 20},
        ],
    }

    state = ProjectState.from_config(config_dict)
    plane = state.add_roof_plane(Polygon2D.rectangle(300, 200), selected_material_id="MAT1")
    layout_result = state.generate_layout_for_plane(plane.id)
    report = build_report(state, layout_result, "MAT1", plane.id)
    html = build_report_html(state, report, "MAT1", plane.id)

    assert "<svg" in html
    assert "</svg>" in html
    assert html.count("<rect") >= len(layout_result.placements)
    assert "Ostrzeżenia" in html


def test_build_report_html_uses_supplied_report_when_project_state_has_no_saved_placements():
    material = Material(
        id="MAT1",
        nazwa="Material 1",
        type="trapezowa",
        effective_width_cm=50,
        module_length_cm=0,
        bottom_margin_cm=0,
        top_margin_cm=0,
        min_sheet_length_cm=1,
        max_sheet_length_cm=500,
    )
    state = ProjectState(materials=[material])
    plane = state.add_roof_plane(Polygon2D.rectangle(100, 150), selected_material_id=material.id)

    layout_result = generate_layout(plane, material)
    report = build_report(state, layout_result, material.id, plane.id)
    html = build_report_html(state, report, material.id, plane.id)

    assert "Powierzchnia efektywna [m2]</th><td>1.50" in html
    assert "Zużycie materiału [m2]</th><td>1.50" in html
    assert "Długość arkusza [cm]" in html
    assert "<td>Material 1</td><td>MAT1</td><td>150</td><td>2</td><td>1.50</td>" in html


def test_build_report_html_formats_summary_and_bom_values():
    material = Material(
        id="MAT1",
        nazwa="Material 1",
        type="trapezowa",
        effective_width_cm=50,
        module_length_cm=0,
        bottom_margin_cm=0,
        top_margin_cm=0,
        min_sheet_length_cm=1,
        max_sheet_length_cm=500,
        price_unit="m2",
        price_value=12.5,
    )
    state = ProjectState(materials=[material])
    plane = state.add_roof_plane(Polygon2D.rectangle(100, 150), selected_material_id=material.id)
    report = build_report(
        state,
        generate_layout(plane, material),
        material.id,
        plane.id,
    )
    report.net_roof_area_m2 = 104.834
    report.gross_sheet_area_m2 = 109.611
    report.waste_area_m2 = 4.777
    report.waste_percent = 4.36
    report.total_cost = 1096.11
    report.bom_rows[0].sheet_length_cm = 8.68
    report.bom_rows[0].total_area_m2 = 34.155

    html = build_report_html(state, report, material.id, plane.id)

    assert "Łączna powierzchnia efektywna [m2]</th><td>104.83" in html
    assert "Łączne zużycie materiału [m2]</th><td>109.61" in html
    assert "Łączny odpad [m2]</th><td>4.78" in html
    assert "Łączny odpad [%]</th><td>4</td>" in html
    assert "Łączny koszt [zł]" not in html
    assert "<td>Material 1</td><td>MAT1</td><td>9</td><td>2</td><td>34.16</td>" in html


def test_build_report_html_always_rounds_sheet_lengths_up_to_full_centimeters():
    material = Material(
        id="MAT1",
        nazwa="Material 1",
        type="trapezowa",
        effective_width_cm=50,
        module_length_cm=0,
        bottom_margin_cm=0,
        top_margin_cm=0,
        min_sheet_length_cm=1,
        max_sheet_length_cm=500,
    )
    state = ProjectState(materials=[material])
    plane = state.add_roof_plane(Polygon2D.rectangle(100, 150), selected_material_id=material.id)
    report = build_report(
        state,
        generate_layout(plane, material),
        material.id,
        plane.id,
    )
    report.bom_rows[0].sheet_length_cm = 8.68

    html = build_report_html(state, report, material.id, plane.id)

    assert "<td>Material 1</td><td>MAT1</td><td>9</td><td>2</td><td>1.50</td>" in html


def test_build_project_report_groups_sheet_lengths_using_ceil_cm():
    material = Material(
        id="MAT",
        nazwa="Panel Dachowy",
        type="trapezowa",
        effective_width_cm=50,
        module_length_cm=0,
        bottom_margin_cm=0,
        top_margin_cm=0,
        min_sheet_length_cm=1,
        max_sheet_length_cm=500,
    )
    state = ProjectState(materials=[material])
    plane = state.add_roof_plane(Polygon2D.rectangle(120, 250), selected_material_id=material.id)
    plane.manual_sheet_placements = [
        SheetPlacement(
            id="manual-1",
            band_index=0,
            x_left_cm=0.0,
            x_right_cm=50.0,
            y_top_cm=0.0,
            y_bottom_cm=100.3,
            raw_length_cm=100.3,
            final_length_cm=100.3,
            source="manual",
        ),
        SheetPlacement(
            id="manual-2",
            band_index=1,
            x_left_cm=50.0,
            x_right_cm=100.0,
            y_top_cm=0.0,
            y_bottom_cm=100.5,
            raw_length_cm=100.5,
            final_length_cm=100.5,
            source="manual",
        ),
    ]

    report = build_project_report(state)

    assert [(row.sheet_length_cm, row.quantity) for row in report.plane_sections[0].sheet_rows] == [(101, 2)]
    assert [(row.material_id, row.sheet_length_cm, row.quantity) for row in report.aggregated_bom_rows] == [("MAT", 101, 2)]


def test_build_project_report_aggregates_multiple_roof_planes_and_groups_lengths():
    material = Material(
        id="MAT",
        nazwa="Panel Dachowy",
        type="trapezowa",
        effective_width_cm=50,
        module_length_cm=0,
        bottom_margin_cm=0,
        top_margin_cm=0,
        min_sheet_length_cm=1,
        max_sheet_length_cm=500,
        price_unit="m2",
        price_value=10.0,
    )
    state = ProjectState(materials=[material])
    first_plane = state.add_roof_plane(Polygon2D.rectangle(100, 100), name="Front", selected_material_id=material.id)
    second_plane = state.add_roof_plane(Polygon2D.rectangle(50, 100), name="Back", selected_material_id=material.id)

    report = build_project_report(state)

    assert [section.plane_name for section in report.plane_sections] == ["Front", "Back"]
    assert len(report.plane_sections) == 2
    assert [(row.sheet_length_cm, row.quantity) for row in report.plane_sections[0].sheet_rows] == [(100, 2)]
    assert [(row.sheet_length_cm, row.quantity) for row in report.plane_sections[1].sheet_rows] == [(100, 1)]
    assert [(row.material_id, row.sheet_length_cm, row.quantity) for row in report.aggregated_bom_rows] == [("MAT", 100, 3)]
    assert almost_equal(report.totals.total_effective_area_m2, 1.5)
    assert almost_equal(report.totals.total_material_usage_area_m2, 1.5)
    assert almost_equal(report.totals.total_waste_area_m2, 0.0)
    assert almost_equal(report.totals.total_waste_percent, 0.0)
    assert almost_equal(report.totals.total_cost, 15.0)


def test_build_project_report_html_contains_all_plane_sections_and_global_summary():
    material = Material(
        id="MAT",
        nazwa="Blacha testowa",
        type="trapezowa",
        effective_width_cm=50,
        module_length_cm=0,
        bottom_margin_cm=0,
        top_margin_cm=0,
        min_sheet_length_cm=1,
        max_sheet_length_cm=500,
        price_unit="m2",
        price_value=10.0,
    )
    state = ProjectState(materials=[material])
    state.company_data.name = "Firma Test"
    first_plane = state.add_roof_plane(Polygon2D.rectangle(100, 100), name="Połać A", selected_material_id=material.id)
    second_plane = state.add_roof_plane(Polygon2D.rectangle(50, 100), name="Połać B", selected_material_id=material.id)

    report = build_project_report(state)
    html = build_project_report_html(report)

    assert "Raport projektu 4Dach" in html
    assert "Firma Test" in html
    assert "Zbiorcze zestawienie materiałów" in html
    assert "Połać A" in html
    assert "Połać B" in html
    assert "Panel Dachowy" not in html
    assert "Blacha testowa" in html
    assert html.count("<svg") == 2
    assert "Łączna powierzchnia efektywna [m2]" in html
    assert "Łączny koszt [zł]" not in html


def test_build_project_report_html_escapes_user_entered_text():
    material = Material(
        id="MAT<script>",
        nazwa='Blacha <img src=x onerror="alert(1)">',
        type="trapezowa",
        effective_width_cm=50,
        module_length_cm=0,
        bottom_margin_cm=0,
        top_margin_cm=0,
        min_sheet_length_cm=1,
        max_sheet_length_cm=500,
    )
    state = ProjectState(materials=[material])
    state.company_data.name = 'Firma <script>alert("x")</script>'
    state.company_data.address = "Adres & 1"
    state.add_roof_plane(
        Polygon2D.rectangle(50, 100),
        name='Połać <b>niebezpieczna</b>',
        selected_material_id=material.id,
    )

    report = build_project_report(state)
    html = build_project_report_html(report)

    assert "<script>" not in html
    assert "<img" not in html
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in html
    assert "Połać &lt;b&gt;niebezpieczna&lt;/b&gt;" in html
    assert "Blacha &lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html
