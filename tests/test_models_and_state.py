from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.geometry import build_rectangle_outline, build_trapezoid_outline, build_triangle_outline
from core.layout_engine import generate_layout
from core.models import CompanyData, Material, Point2D, Polygon2D, RoofPlane, almost_equal
from core.project_state import ProjectState


def test_company_data_round_trip():
    company = CompanyData.from_dict(
        {
            "name": "Super Dach",
            "nip": "123",
            "address": "Ogrodniki",
            "website": "example.test",
            "logo": "logo",
        }
    )

    assert company.to_dict()["name"] == "Super Dach"
    assert company.to_dict()["website"] == "example.test"


def test_project_state_loads_materials_from_config():
    config_path = Path(__file__).resolve().parents[1] / "config.json"
    config_data = json.loads(config_path.read_text(encoding="utf-8"))

    state = ProjectState.from_config(config_data)

    assert state.company_data.name == "Super Dach Bis Jerzy Zimnoch"
    assert state.available_material_ids() == ["PD510"]
    assert state.material_by_id("PD510") is not None


def test_layout_engine_splits_band_by_hole_and_flags_long_sheet():
    plane = RoofPlane(
        id="plane-1",
        name="Połać testowa",
        outline=Polygon2D.rectangle(100, 100),
        holes=[Polygon2D.rectangle(50, 50, origin_x=25, origin_y=25)],
    )
    material = Material(
        id="TEST",
        nazwa="TEST",
        type="trapezowa",
        effective_width_cm=30,
        module_length_cm=0,
        bottom_margin_cm=0,
        top_margin_cm=0,
        min_sheet_length_cm=10,
        max_sheet_length_cm=40,
    )

    result = generate_layout(plane, material)

    assert len(result.placements) == 5
    assert result.requires_transverse_split is True
    middle_band = [placement for placement in result.placements if placement.band_index == 1]
    assert len(middle_band) == 2
    assert all(placement.final_length_cm == 25 for placement in middle_band)
    assert all(placement.split_reason is None for placement in middle_band)
    outer_bands = [placement for placement in result.placements if placement.band_index != 1]
    assert all(placement.split_reason == "exceeds_max_length" for placement in outer_bands)


def test_project_state_config_fragment_serializes_roof_planes():
    state = ProjectState(
        roof_planes=[
            RoofPlane(
                id="plane-1",
                name="A",
                outline=Polygon2D([Point2D(0, 0), Point2D(300, 0), Point2D(300, 200), Point2D(0, 200)]),
                selected_material_id="PD510",
            )
        ],
        active_plane_id="plane-1",
    )

    fragment = state.to_config_fragment()
    plane_payload = fragment["project_state"]["roof_planes"][0]

    assert plane_payload["id"] == "plane-1"
    assert plane_payload["selected_material_id"] == "PD510"
    assert len(plane_payload["outline"]) == 4


def test_project_state_add_roof_plane_round_trip():
    state = ProjectState(
        materials=[
            Material(
                id="PD510",
                nazwa="PD510",
                type="dachówkowa",
                effective_width_cm=51,
                module_length_cm=25,
                bottom_margin_cm=10,
                top_margin_cm=80,
                min_sheet_length_cm=20,
            )
        ]
    )

    plane = state.add_roof_plane(build_rectangle_outline(300, 200))
    payload = {"blachy": [material.to_dict() for material in state.materials]}
    state.apply_to_config(payload)
    reloaded = ProjectState.from_config(payload)
    reloaded_plane = reloaded.active_roof_plane()

    assert plane.id == "plane-1"
    assert state.active_plane_id == "plane-1"
    assert reloaded_plane is not None
    assert reloaded_plane.selected_material_id == "PD510"
    assert almost_equal(reloaded_plane.outline.area(), 60000.0)
    assert almost_equal(reloaded_plane.generation_settings.base_line_y_cm or 0.0, 200.0)


def test_project_state_hole_workflow_updates_layout_revision_and_serialization():
    state = ProjectState(
        materials=[
            Material(
                id="PD510",
                nazwa="PD510",
                type="dachówkowa",
                effective_width_cm=50,
                module_length_cm=25,
                bottom_margin_cm=5,
                top_margin_cm=5,
                min_sheet_length_cm=20,
            )
        ]
    )
    plane = state.add_roof_plane(build_rectangle_outline(300, 200))

    state.add_hole_to_plane(Polygon2D.rectangle(50, 60, origin_x=100, origin_y=40), plane.id)
    moved_plane = state.move_hole_in_plane(0, 10, 15, plane.id)
    payload = state.to_config_fragment()
    plane_payload = payload["project_state"]["roof_planes"][0]

    assert moved_plane.layout_revision == 2
    assert len(moved_plane.holes) == 1
    assert moved_plane.holes[0].points[0] == Point2D(110, 55)
    assert plane_payload["layout_revision"] == 2
    assert plane_payload["holes"][0][0] == {"x": 110, "y": 55}


def test_project_state_rejects_hole_outside_outline():
    state = ProjectState()
    plane = state.add_roof_plane(build_rectangle_outline(300, 200))

    with pytest.raises(ValueError, match="Wycinek musi leżeć w całości wewnątrz obrysu"):
        state.add_hole_to_plane(Polygon2D.rectangle(80, 80, origin_x=260, origin_y=20), plane.id)


def test_project_state_roof_plane_edit_operations_update_geometry_revision():
    state = ProjectState()
    plane = state.add_roof_plane(build_rectangle_outline(300, 200))

    state.move_roof_plane(10, 5, plane.id)
    state.insert_roof_plane_point(0, Point2D(160, 40), plane.id)
    state.move_roof_plane_point(1, 0, 10, plane.id)
    edited_plane = state.delete_roof_plane_point(1, plane.id)

    assert edited_plane.layout_revision == 4
    assert edited_plane.outline.points[0] == Point2D(10, 5)
    assert edited_plane.outline.points[1] == Point2D(310, 5)
    assert len(edited_plane.outline.points) == 4
    assert almost_equal(edited_plane.generation_settings.base_line_y_cm or 0.0, 205.0)


def test_project_state_rejects_outline_edit_when_it_breaks_hole_containment():
    state = ProjectState()
    plane = state.add_roof_plane(build_rectangle_outline(300, 200))
    state.add_hole_to_plane(Polygon2D.rectangle(60, 60, origin_x=30, origin_y=40), plane.id)

    with pytest.raises(ValueError, match="Wycinek musi leżeć w całości wewnątrz obrysu"):
        state.move_roof_plane_point(0, 80, 0, plane.id)


def test_project_state_delete_hole_marks_geometry_changed():
    state = ProjectState()
    plane = state.add_roof_plane(build_rectangle_outline(300, 200))
    state.add_hole_to_plane(Polygon2D.rectangle(50, 50, origin_x=80, origin_y=60), plane.id)

    updated_plane = state.delete_hole_from_plane(0, plane.id)

    assert updated_plane.layout_revision == 2
    assert updated_plane.holes == []
    assert almost_equal(updated_plane.generation_settings.base_line_y_cm or 0.0, 200.0)


def test_project_state_generates_layout_for_active_plane_and_persists_auto_placements():
    state = ProjectState(
        materials=[
            Material(
                id="PD510",
                nazwa="PD510",
                type="dachówkowa",
                effective_width_cm=51,
                module_length_cm=25,
                bottom_margin_cm=10,
                top_margin_cm=15,
                min_sheet_length_cm=20,
                max_sheet_length_cm=400,
            )
        ]
    )
    plane = state.add_roof_plane(build_rectangle_outline(153, 200))
    state.add_hole_to_plane(Polygon2D.rectangle(30, 50, origin_x=60, origin_y=70), plane.id)

    result = state.generate_layout_for_active_plane()
    fragment = state.to_config_fragment()
    plane_payload = fragment["project_state"]["roof_planes"][0]

    assert len(result.placements) == 4
    assert len(plane.auto_sheet_placements) == 4
    assert almost_equal(plane.generation_settings.base_line_y_cm or 0.0, 200.0)
    assert plane.layout_revision == 2
    assert len(plane_payload["auto_sheet_placements"]) == 4
    assert plane_payload["auto_sheet_placements"][0]["id"].startswith("plane-1-b0-s0")


def test_layout_engine_uses_shared_baseline_for_module_lengths():
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
    )
    plane = RoofPlane(
        id="plane-1",
        name="Test",
        outline=Polygon2D.rectangle(120, 200),
        holes=[Polygon2D.rectangle(40, 50, origin_x=40, origin_y=70)],
    )
    plane.generation_settings.base_line_y_cm = 200

    result = generate_layout(plane, material)
    middle_band = [placement for placement in result.placements if placement.band_index == 1]

    assert [placement.final_length_cm for placement in middle_band] == [95, 125]


def test_shape_builders_create_valid_polygons():
    rectangle = build_rectangle_outline(300, 200)
    triangle = build_triangle_outline("równoramienny", 300, 180)
    trapezoid = build_trapezoid_outline("prostokątny", 500, 300, 200)

    assert len(rectangle.points) == 4
    assert len(triangle.points) == 3
    assert len(trapezoid.points) == 4
    assert rectangle.area() > 0
    assert triangle.area() > 0
    assert trapezoid.area() > 0


def test_polygon_area_is_counted_in_cm2():
    polygon = Polygon2D.rectangle(300, 200)

    assert almost_equal(polygon.area(), 60000.0)
