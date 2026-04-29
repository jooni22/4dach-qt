from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.geometry import (
    build_rectangle_outline,
    build_trapezoid_outline,
    build_triangle_outline,
    make_rectangle,
    make_trapezoid,
    make_triangle,
)
from core.layout_engine import generate_layout
from core.models import (
    CompanyData,
    Material,
    Point2D,
    Polygon2D,
    RoofPlane,
    SheetPlacement,
    almost_equal,
)
from core.project_state import ProjectState


def _compact_plane_payload(fragment: dict, plane_id: str) -> dict:
    roof_planes = fragment["project_state"]["roof_planes"]
    return roof_planes["items"][plane_id]


def _legacy_like_fragment(state: ProjectState) -> dict:
    return {
        "app_settings": state.app_settings.to_dict(),
        "materials": [material.to_dict() for material in state.materials],
        "blachy": [material.to_dict() for material in state.materials],
        "project_state": {
            "version": state.version,
            "active_plane_id": state.active_plane_id,
            "roof_planes": [
                {
                    "id": plane.id,
                    "name": plane.name,
                    "selected_material_id": plane.selected_material_id,
                    "generation_settings": plane.generation_settings.to_dict(),
                    "auto_sheet_placements": [placement.to_dict() for placement in plane.auto_sheet_placements],
                    "layout_bands": list(plane.layout_bands),
                    "manual_sheet_placements": [placement.to_dict() for placement in plane.manual_sheet_placements],
                    "manually_removed_auto_sheet_ids": list(plane.manually_removed_auto_sheet_ids),
                    "layout_revision": plane.layout_revision,
                    "layout_dirty_reason": plane.layout_dirty_reason,
                    "outline": [] if plane.outline is None else [{"x": point.x, "y": point.y} for point in plane.outline.points],
                    "holes": [
                        [{"x": point.x, "y": point.y} for point in hole.points]
                        for hole in plane.holes
                    ],
                }
                for plane in state.roof_planes
            ],
        },
    }


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


def test_material_definition_supports_min_sheet_length_dual_keys():
    material = Material.from_dict(
        {
            "id": "MAT1",
            "display_name": "Material 1",
            "type": "trapezowa",
            "effective_width_cm": 50,
            "min_sheet_length_cm": 42,
            "max_sheet_length_cm": 300,
        }
    )

    payload = material.to_dict()

    assert material.min_sheet_length_cm == 42
    assert payload["min_sheet_length_cm"] == 42
    assert payload["min_dlugosc_arkusza"] == 42


def test_material_definition_rounds_centimeter_fields_to_ints():
    material = Material.from_dict(
        {
            "id": "MAT1",
            "display_name": "Material 1",
            "type": "trapezowa",
            "effective_width_cm": 51.2,
            "min_sheet_length_cm": 42.4,
            "max_sheet_length_cm": 299.6,
            "top_allowance_cm": 14.6,
            "bottom_allowance_cm": 9.6,
            "module_length_cm": 24.6,
            "odleglosc_miedzy_latami": 34.6,
            "odleglosc_miedzy_kontrlatami": 19.6,
        }
    )

    payload = material.to_dict()

    assert material.effective_width_cm == 51
    assert material.min_sheet_length_cm == 42
    assert material.max_sheet_length_cm == 300
    assert material.top_margin_cm == 15
    assert material.bottom_margin_cm == 10
    assert material.module_length_cm == 25
    assert material.batten_spacing_cm == 35
    assert material.counter_batten_spacing_cm == 20
    assert payload["effective_width_cm"] == 51
    assert payload["top_allowance_cm"] == 15
    assert payload["bottom_allowance_cm"] == 10
    assert payload["module_length_cm"] == 25


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

    assert len(result.placements) == 11
    # Check that sheets are properly stacked without exceeding max length
    assert all(placement.raw_length_cm <= 40 for placement in result.placements)


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
    plane_payload = _compact_plane_payload(fragment, "plane-1")

    assert fragment["project_state"]["roof_planes"]["order"] == ["plane-1"]
    assert plane_payload["m"] == "PD510"
    assert len(plane_payload["o"]) == 4


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


def test_project_state_round_trip_preserves_custom_coordinate_origin():
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
    plane.generation_settings.origin_x_cm = 45.5
    plane.generation_settings.origin_y_cm = 188.0

    payload = {"blachy": [material.to_dict() for material in state.materials]}
    state.apply_to_config(payload)
    reloaded = ProjectState.from_config(payload)
    reloaded_plane = reloaded.active_roof_plane()

    assert reloaded_plane is not None
    assert almost_equal(reloaded_plane.generation_settings.origin_x_cm or 0.0, 45.5)
    assert almost_equal(reloaded_plane.generation_settings.origin_y_cm or 0.0, 188.0)


def test_project_state_can_switch_active_plane_explicitly():
    state = ProjectState()
    first_plane = state.add_roof_plane(build_rectangle_outline(300, 200))
    second_plane = state.add_roof_plane(build_rectangle_outline(240, 160))

    changed = state.set_active_plane(first_plane.id)

    assert changed is True
    assert state.active_plane_id == first_plane.id
    assert state.active_roof_plane() is first_plane
    assert state.set_active_plane("missing-plane") is False
    assert state.active_plane_id == first_plane.id
    assert second_plane.id != first_plane.id


def test_project_state_can_add_multiple_empty_roof_planes_and_persist_them():
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

    first_plane = state.add_empty_roof_plane()
    second_plane = state.add_empty_roof_plane()
    third_plane = state.add_empty_roof_plane()
    payload = {"blachy": [material.to_dict() for material in state.materials]}
    state.apply_to_config(payload)
    reloaded = ProjectState.from_config(payload)

    assert [plane.id for plane in state.roof_planes] == ["plane-1", "plane-2", "plane-3"]
    assert [plane.name for plane in state.roof_planes] == ["1", "2", "3"]
    assert state.active_plane_id == third_plane.id
    assert first_plane.outline is None
    assert second_plane.selected_material_id == "PD510"
    assert len(reloaded.roof_planes) == 3
    assert all(plane.outline is None for plane in reloaded.roof_planes)


def test_project_state_delete_roof_plane_keeps_other_planes_intact():
    state = ProjectState()
    first_plane = state.add_roof_plane(build_rectangle_outline(300, 200))
    second_plane = state.add_roof_plane(build_rectangle_outline(240, 160))
    third_plane = state.add_roof_plane(build_rectangle_outline(180, 120))

    removed_plane = state.delete_roof_plane(second_plane.id)

    assert removed_plane.id == second_plane.id
    assert [plane.id for plane in state.roof_planes] == [first_plane.id, third_plane.id]
    assert state.roof_plane_by_id(second_plane.id) is None
    assert state.roof_plane_by_id(first_plane.id) is first_plane
    assert state.roof_plane_by_id(third_plane.id) is third_plane
    assert state.active_plane_id == third_plane.id


def test_project_state_round_trip_preserves_multiple_roof_planes():
    state = ProjectState(
        materials=[
            Material(
                id="MAT1",
                nazwa="Material 1",
                type="trapezowa",
                effective_width_cm=50,
                module_length_cm=25,
                bottom_margin_cm=10,
                top_margin_cm=15,
                min_sheet_length_cm=20,
            )
        ]
    )
    first_plane = state.add_roof_plane(build_rectangle_outline(300, 200), selected_material_id="MAT1")
    second_plane = state.add_empty_roof_plane(name="Taras", selected_material_id="MAT1")
    state.rename_roof_plane(first_plane.id, "Front")
    payload = {"blachy": [material.to_dict() for material in state.materials]}

    state.apply_to_config(payload)
    reloaded = ProjectState.from_config(payload)

    assert [plane.name for plane in reloaded.roof_planes] == ["Front", "Taras"]
    assert reloaded.roof_planes[0].outline is not None
    assert reloaded.roof_planes[1].outline is None
    assert reloaded.active_plane_id == second_plane.id


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
    plane_payload = _compact_plane_payload(payload, plane.id)

    assert moved_plane.layout_revision == 2
    assert len(moved_plane.holes) == 1
    assert moved_plane.holes[0].points[0] == Point2D(110, 55)
    assert plane_payload["r"] == 2
    assert plane_payload["h"][0][0] == [110, 55]


def test_project_state_supports_multiple_holes_and_round_trip():
    state = ProjectState()
    plane = state.add_roof_plane(build_rectangle_outline(400, 300))
    first_hole = Polygon2D.rectangle(50, 60, origin_x=40, origin_y=50)
    second_hole = Polygon2D.rectangle(70, 40, origin_x=220, origin_y=120)

    state.add_hole_to_plane(first_hole, plane.id)
    state.add_hole_to_plane(second_hole, plane.id)
    payload = state.to_config_fragment()
    reloaded = ProjectState.from_config(payload)

    assert len(plane.holes) == 2
    assert len(reloaded.roof_planes[0].holes) == 2
    assert reloaded.roof_planes[0].holes[0].points == first_hole.points
    assert reloaded.roof_planes[0].holes[1].points == second_hole.points


def test_project_state_allows_hole_outside_outline():
    state = ProjectState()
    plane = state.add_roof_plane(build_rectangle_outline(300, 200))

    updated_plane = state.add_hole_to_plane(Polygon2D.rectangle(80, 80, origin_x=260, origin_y=20), plane.id)

    assert len(updated_plane.holes) == 1
    assert updated_plane.holes[0].points[0] == Point2D(260, 20)


def test_project_state_rejects_overlapping_holes():
    state = ProjectState()
    plane = state.add_roof_plane(build_rectangle_outline(300, 200))
    state.add_hole_to_plane(Polygon2D.rectangle(80, 80, origin_x=40, origin_y=30), plane.id)

    with pytest.raises(ValueError, match="Wycinki nie mogą na siebie nachodzić"):
        state.add_hole_to_plane(Polygon2D.rectangle(60, 60, origin_x=90, origin_y=70), plane.id)


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


def test_project_state_allows_outline_edit_when_it_breaks_hole_containment():
    state = ProjectState()
    plane = state.add_roof_plane(build_rectangle_outline(300, 200))
    state.add_hole_to_plane(Polygon2D.rectangle(60, 60, origin_x=30, origin_y=40), plane.id)

    updated_plane = state.move_roof_plane_point(0, 80, 0, plane.id)

    assert updated_plane.outline.points[0] == Point2D(80, 0)


def test_project_state_rebuilds_sheet_split_inputs_after_outline_edit_moves_hole_outside_outline():
    state = ProjectState(
        materials=[
            Material(
                id="MAT",
                nazwa="Material",
                type="trapezowa",
                effective_width_cm=50,
                module_length_cm=0,
                bottom_margin_cm=0,
                top_margin_cm=0,
                min_sheet_length_cm=0,
                max_sheet_length_cm=400,
            )
        ]
    )
    plane = state.add_roof_plane(build_rectangle_outline(150, 150), selected_material_id="MAT")
    state.add_hole_to_plane(Polygon2D.rectangle(20, 50, origin_x=20, origin_y=40), plane.id)

    state.generate_layout_for_plane(plane.id)
    assert plane.layout_bands[0]["segments"][0]["cutout_interaction"] == "partial"

    updated_outline = Polygon2D(
        [
            Point2D(0, 80),
            Point2D(150, 0),
            Point2D(150, 150),
            Point2D(0, 150),
        ]
    )
    state.set_roof_plane_outline(updated_outline, plane.id)
    result = state.generate_layout_for_plane(plane.id)

    band_segment = result.bands[0].segments[0]
    assert band_segment.cutout_interaction is None
    assert band_segment.partial_cut_line_y_cm is None
    assert len(band_segment.coverage_polygons) == 1


def test_project_state_delete_hole_marks_geometry_changed():
    state = ProjectState()
    plane = state.add_roof_plane(build_rectangle_outline(300, 200))
    state.add_hole_to_plane(Polygon2D.rectangle(50, 50, origin_x=80, origin_y=60), plane.id)

    updated_plane = state.delete_hole_from_plane(0, plane.id)

    assert updated_plane.layout_revision == 2
    assert updated_plane.holes == []
    assert almost_equal(updated_plane.generation_settings.base_line_y_cm or 0.0, 200.0)


def test_project_state_can_edit_cutout_vertex_and_persist_result():
    state = ProjectState()
    plane = state.add_roof_plane(build_rectangle_outline(300, 200))
    state.add_hole_to_plane(Polygon2D.rectangle(50, 50, origin_x=80, origin_y=60), plane.id)

    updated_plane = state.move_hole_point(0, 1, 20, 10, plane.id)
    payload = state.to_config_fragment()
    reloaded = ProjectState.from_config(payload)

    assert updated_plane.holes[0].points[1] == Point2D(150, 70)
    assert reloaded.roof_planes[0].holes[0].points[1] == Point2D(150, 70)


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
    plane_payload = _compact_plane_payload(fragment, plane.id)

    assert len(result.placements) == 4
    assert len(result.bands) == 3
    assert len(result.bands[1].segments) == 1
    assert len(result.bands[1].segments[0].coverage_polygons) == 4
    assert result.bands[1].segments[0].cutout_interaction == "partial"
    assert len(plane.auto_sheet_placements) == 4
    assert almost_equal(plane.generation_settings.base_line_y_cm or 0.0, 200.0)
    assert plane.layout_revision == 2
    assert "auto_sheet_placements" not in plane_payload
    assert "layout_bands" not in plane_payload


def test_project_state_manual_sheet_overrides_are_merged_and_serialized():
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
    plane = state.add_roof_plane(build_rectangle_outline(153, 200), selected_material_id="PD510")
    state.generate_layout_for_plane(plane.id)

    removed_auto_id = plane.auto_sheet_placements[0].id
    state.remove_sheet_placement(removed_auto_id, plane.id)
    state.add_manual_sheet_placement(
        SheetPlacement(
            id="plane-1-manual-1",
            band_index=99,
            x_left_cm=10.0,
            x_right_cm=40.0,
            y_top_cm=20.0,
            y_bottom_cm=140.0,
            raw_length_cm=120.0,
            final_length_cm=120.0,
        ),
        plane.id,
    )
    fragment = state.to_config_fragment()
    plane_payload = _compact_plane_payload(fragment, plane.id)
    active_ids = [placement.id for placement in state.active_sheet_placements_for_plane(plane.id)]

    assert removed_auto_id not in active_ids
    assert "plane-1-manual-1" in active_ids
    assert plane.layout_dirty_reason == "manual_override"
    assert plane_payload["mp"]["order"] == ["plane-1-manual-1"]
    assert plane_payload["rm"] == [removed_auto_id]
    assert plane_payload["d"] == "manual_override"


def test_project_state_geometry_change_keeps_manual_sheets_but_marks_layout_dirty():
    state = ProjectState()
    plane = state.add_roof_plane(build_rectangle_outline(300, 200))
    state.add_manual_sheet_placement(
        SheetPlacement(
            id="plane-1-manual-1",
            band_index=0,
            x_left_cm=0.0,
            x_right_cm=50.0,
            y_top_cm=0.0,
            y_bottom_cm=120.0,
            raw_length_cm=120.0,
            final_length_cm=120.0,
        ),
        plane.id,
    )

    updated_plane = state.move_roof_plane(10, 5, plane.id)

    assert len(updated_plane.manual_sheet_placements) == 1
    assert updated_plane.layout_dirty_reason == "geometry_changed"


def test_project_state_material_change_marks_layout_dirty_without_dropping_manual_sheets():
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
            ),
            Material(
                id="T20",
                nazwa="T20",
                type="trapezowa",
                effective_width_cm=110,
                module_length_cm=0,
                bottom_margin_cm=0,
                top_margin_cm=0,
                min_sheet_length_cm=20,
            ),
        ]
    )
    plane = state.add_roof_plane(build_rectangle_outline(300, 200), selected_material_id="PD510")
    state.add_manual_sheet_placement(
        SheetPlacement(
            id="plane-1-manual-1",
            band_index=0,
            x_left_cm=0.0,
            x_right_cm=50.0,
            y_top_cm=0.0,
            y_bottom_cm=120.0,
            raw_length_cm=120.0,
            final_length_cm=120.0,
        ),
        plane.id,
    )

    changed = state.set_active_material_for_plane("T20", plane.id)

    assert changed is True
    assert plane.selected_material_id == "T20"
    assert len(plane.manual_sheet_placements) == 1


def test_project_state_can_duplicate_roof_plane_with_independent_geometry_and_layout():
    state = ProjectState(
        materials=[
            Material(
                id="MAT",
                nazwa="Material",
                type="trapezowa",
                effective_width_cm=50,
                module_length_cm=25,
                bottom_margin_cm=10,
                top_margin_cm=15,
                min_sheet_length_cm=20,
                max_sheet_length_cm=400,
            )
        ]
    )
    plane = state.add_roof_plane(Polygon2D.rectangle(120, 100), name="Front", selected_material_id="MAT")
    state.add_hole_to_plane(Polygon2D.rectangle(30, 20, origin_x=10, origin_y=15), plane.id)
    state.generate_layout_for_plane(plane.id)

    duplicate = state.duplicate_roof_plane(plane.id)

    assert duplicate.id != plane.id
    assert duplicate.name != plane.name
    assert duplicate.outline == plane.outline
    assert duplicate.outline is not plane.outline
    assert duplicate.holes == plane.holes
    assert duplicate.holes[0] is not plane.holes[0]
    assert duplicate.auto_sheet_placements == plane.auto_sheet_placements
    assert duplicate.auto_sheet_placements[0] is not plane.auto_sheet_placements[0]
    assert duplicate.layout_bands == plane.layout_bands


def test_project_state_can_create_and_edit_material_definitions():
    state = ProjectState()

    created = state.upsert_material(
        Material(
            id="MAT1",
            nazwa="Material 1",
            type="trapezowa",
            effective_width_cm=50,
            module_length_cm=0,
            bottom_margin_cm=10,
            top_margin_cm=15,
            min_sheet_length_cm=20,
            max_sheet_length_cm=800,
            price_value=42.5,
        )
    )

    updated = state.upsert_material(
        Material(
            id="MAT1",
            nazwa="Material 1 Plus",
            type="trapezowa",
            effective_width_cm=53,
            module_length_cm=0,
            bottom_margin_cm=12,
            top_margin_cm=18,
            min_sheet_length_cm=25,
            max_sheet_length_cm=820,
            price_value=55.0,
        )
    )

    assert created is updated
    assert state.available_material_ids() == ["MAT1"]
    assert state.material_by_id("MAT1") is updated
    assert updated.nazwa == "Material 1 Plus"
    assert updated.effective_width_cm == 53
    assert almost_equal(updated.price_value, 55.0)


def test_project_state_material_edit_marks_only_dependent_planes_dirty():
    state = ProjectState(
        materials=[
            Material(
                id="MAT1",
                nazwa="Material 1",
                type="trapezowa",
                effective_width_cm=50,
                module_length_cm=0,
                bottom_margin_cm=10,
                top_margin_cm=15,
                min_sheet_length_cm=20,
            ),
            Material(
                id="MAT2",
                nazwa="Material 2",
                type="trapezowa",
                effective_width_cm=60,
                module_length_cm=0,
                bottom_margin_cm=5,
                top_margin_cm=5,
                min_sheet_length_cm=20,
            ),
        ]
    )
    first_plane = state.add_roof_plane(build_rectangle_outline(300, 200), selected_material_id="MAT1")
    second_plane = state.add_roof_plane(build_rectangle_outline(240, 160), selected_material_id="MAT1")
    third_plane = state.add_roof_plane(build_rectangle_outline(180, 120), selected_material_id="MAT2")

    state.generate_layout_for_plane(first_plane.id)
    state.generate_layout_for_plane(second_plane.id)
    state.generate_layout_for_plane(third_plane.id)

    original_revision = third_plane.layout_revision

    state.upsert_material(
        Material(
            id="MAT1",
            nazwa="Material 1 New",
            type="trapezowa",
            effective_width_cm=52,
            module_length_cm=0,
            bottom_margin_cm=10,
            top_margin_cm=20,
            min_sheet_length_cm=25,
        )
    )

    assert first_plane.layout_dirty_reason == "material_changed"
    assert second_plane.layout_dirty_reason == "material_changed"
    assert third_plane.layout_dirty_reason is None
    assert first_plane.auto_sheet_placements == []
    assert second_plane.auto_sheet_placements == []
    assert third_plane.auto_sheet_placements
    assert third_plane.layout_revision == original_revision


def test_project_state_round_trip_preserves_material_registry_and_assignments():
    state = ProjectState(
        materials=[
            Material(
                id="MAT1",
                nazwa="Material 1",
                type="trapezowa",
                effective_width_cm=50,
                module_length_cm=0,
                bottom_margin_cm=10,
                top_margin_cm=15,
                min_sheet_length_cm=20,
                max_sheet_length_cm=800,
                price_value=44.99,
            )
        ]
    )
    plane = state.add_roof_plane(build_rectangle_outline(300, 200), selected_material_id="MAT1")
    state.generate_layout_for_plane(plane.id)
    state.upsert_material(
        Material(
            id="MAT1",
            nazwa="Material 1 Updated",
            type="trapezowa",
            effective_width_cm=54,
            module_length_cm=0,
            bottom_margin_cm=12,
            top_margin_cm=16,
            min_sheet_length_cm=22,
            max_sheet_length_cm=850,
            price_value=49.5,
        )
    )

    payload: dict = {}
    state.apply_to_config(payload)
    reloaded = ProjectState.from_config(payload)

    reloaded_material = reloaded.material_by_id("MAT1")
    reloaded_plane = reloaded.roof_planes[0]

    assert reloaded_material is not None
    assert reloaded_material.nazwa == "Material 1 Updated"
    assert reloaded_material.effective_width_cm == 54
    assert almost_equal(reloaded_material.price_value, 49.5)
    assert reloaded_plane.selected_material_id == "MAT1"
    assert reloaded_plane.layout_dirty_reason == "material_changed"


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

    assert [placement.final_length_cm for placement in middle_band] == [70.0, 80.0]


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


def test_shape_factories_create_expected_polygons():
    rectangle = make_rectangle(320, 180)
    triangle = make_triangle("dowolny", 300, 180, 250)
    trapezoid = make_trapezoid("równoramienny", 500, 300, 200)

    assert rectangle.points == [
        Point2D(0.0, 0.0),
        Point2D(320.0, 0.0),
        Point2D(320.0, 180.0),
        Point2D(0.0, 180.0),
    ]
    assert triangle.points[0] == Point2D(0.0, 180.0)
    assert triangle.points[2] == Point2D(300.0, 180.0)
    assert 0.0 < triangle.points[1].x < 300.0
    assert trapezoid.points == [
        Point2D(0.0, 200.0),
        Point2D(100.0, 0.0),
        Point2D(400.0, 0.0),
        Point2D(500.0, 200.0),
    ]


@pytest.mark.parametrize(
    ("factory", "args", "message"),
    [
        (make_rectangle, (0, 200), "Szerokość musi być dodatnia"),
        (make_triangle, ("dowolny", 300, 180, 170), "Ramię musi być większe od wysokości"),
        (make_trapezoid, ("prostokątny", 500, 0, 200), "Podstawa górna musi być dodatnia"),
    ],
)
def test_shape_factories_validate_invalid_dimensions(factory, args, message):
    with pytest.raises(ValueError, match=message):
        factory(*args)


def test_polygon_area_is_counted_in_cm2():
    polygon = Polygon2D.rectangle(300, 200)

    assert almost_equal(polygon.area(), 60000.0)


def test_load_config_and_save_config_round_trip():
    """Smoke test: load_config and save_config functions preserve data correctly."""
    import tempfile

    test_config = {
        "ksztalty": {"prostokat": {"szerokosc": 400, "wysokosc": 300}},
        "company_data": {"name": "Test Firma", "nip": "123456", "address": "Test Adres", "website": "test.test", "logo": "test.png"},
        "blachy": [{"id": "TEST", "nazwa": "Test Blacha", "type": "trapezowa", "effective_width_cm": 50}],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        temp_path = f.name
        json.dump(test_config, f, ensure_ascii=False, indent=2)

    try:
        loaded = json.loads(Path(temp_path).read_text(encoding="utf-8"))
        assert loaded == test_config

        loaded["ksztalty"]["prostokat"]["szerokosc"] = 500
        Path(temp_path).write_text(json.dumps(loaded, ensure_ascii=False, indent=2), encoding="utf-8")
        reloaded = json.loads(Path(temp_path).read_text(encoding="utf-8"))
        assert reloaded["ksztalty"]["prostokat"]["szerokosc"] == 500

    finally:
        import os
        os.unlink(temp_path)


def test_project_state_config_round_trip():
    """Smoke test: ProjectState round-trip through config dict preserves all state."""
    company = CompanyData(name="Test", nip="123", address="Addr", website="web.test", logo="logo.png")
    material = Material(id="MAT1", nazwa="Material 1", type="trapezowa", effective_width_cm=50, module_length_cm=25, bottom_margin_cm=10, top_margin_cm=15, min_sheet_length_cm=20)

    config_dict = {
        "company_data": company.to_dict(),
        "blachy": [material.to_dict()],
    }

    state = ProjectState.from_config(config_dict)

    plane = state.add_roof_plane(build_rectangle_outline(300, 200), selected_material_id="MAT1")
    state.generate_layout_for_plane(plane.id)

    state.apply_to_config(config_dict)

    state2 = ProjectState.from_config(config_dict)

    assert state2.company_data.name == "Test"
    assert len(state2.materials) == 1
    assert state2.material_by_id("MAT1") is not None
    assert len(state2.roof_planes) == 1
    assert state2.roof_planes[0].id == plane.id
    assert state2.roof_planes[0].selected_material_id == "MAT1"
    assert state2.roof_planes[0].layout_dirty_reason is None


def test_project_state_compact_fragment_is_substantially_smaller_than_legacy_shape():
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
    plane = state.add_roof_plane(build_rectangle_outline(600, 400), selected_material_id="PD510")
    state.add_hole_to_plane(Polygon2D.rectangle(120, 100, origin_x=180, origin_y=120), plane.id)
    state.generate_layout_for_plane(plane.id)
    state.add_manual_sheet_placement(
        SheetPlacement(
            id="plane-1-manual-1",
            band_index=99,
            x_left_cm=10.0,
            x_right_cm=40.0,
            y_top_cm=20.0,
            y_bottom_cm=140.0,
            raw_length_cm=120.0,
            final_length_cm=120.0,
        ),
        plane.id,
    )

    compact = state.to_config_fragment()
    legacy = _legacy_like_fragment(state)

    compact_bytes = len(json.dumps(compact, ensure_ascii=False, separators=(",", ":")))
    legacy_bytes = len(json.dumps(legacy, ensure_ascii=False, separators=(",", ":")))

    assert compact_bytes < legacy_bytes * 0.5


def test_basic_user_workflow_smoke():
    """Smoke test: basic user workflow - add plane, generate layout, verify state."""
    config_dict = {
        "company_data": {"name": "Test", "nip": "123", "address": "Addr", "website": "web.test", "logo": "logo.png"},
        "blachy": [
            {"id": "MAT1", "nazwa": "Material 1", "type": "trapezowa", "szerokosc_efektywna": 50, "dlugosc_modulu": 25, "zapas_dolny": 10, "zapas_gorny": 15, "min_dlugosc_arkusza": 20},
        ],
    }

    state = ProjectState.from_config(config_dict)

    plane = state.add_roof_plane(build_rectangle_outline(300, 200), selected_material_id="MAT1")
    assert len(state.roof_planes) == 1
    assert plane.selected_material_id == "MAT1"
    assert plane.layout_dirty_reason is None

    layout_result = state.generate_layout_for_plane(plane.id)
    assert layout_result is not None
    assert len(plane.auto_sheet_placements) > 0
    assert plane.layout_dirty_reason == None

    manual_placement = SheetPlacement(
        id="manual-1",
        band_index=0,
        x_left_cm=0,
        x_right_cm=100,
        y_top_cm=0,
        y_bottom_cm=50,
        raw_length_cm=50,
        final_length_cm=50,
    )
    state.add_manual_sheet_placement(manual_placement, plane.id)
    assert len(plane.manual_sheet_placements) == 1
    assert plane.layout_dirty_reason == "manual_override"

    config_after = {}
    state.apply_to_config(config_after)
    assert "project_state" in config_after
    assert config_after["project_state"]["roof_planes"]["order"] == [plane.id]
    assert _compact_plane_payload(config_after, plane.id)["d"] == "manual_override"


def test_is_placement_removed_legacy_prefix_match():
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
            )
        ]
    )
    plane = state.add_roof_plane(build_rectangle_outline(300, 200), selected_material_id="PD510")
    state.generate_layout_for_plane(plane.id)

    legacy_removed_id = plane.auto_sheet_placements[0].id.rsplit("-r", 1)[0]
    assert "-r" not in legacy_removed_id
    removed_ids_set = {legacy_removed_id}

    placement_with_row_suffix_id = f"{legacy_removed_id}-r99"
    result = state._is_placement_removed(placement_with_row_suffix_id, removed_ids_set)
    assert result is True

    result_unrelated = state._is_placement_removed("plane-999-b0-s0-r1", removed_ids_set)
    assert result_unrelated is False


def test_is_placement_removed_legacy_prefix_match_hardcoded():
    """Test that legacy removed IDs (without -r suffix) match placement IDs with -r suffix."""
    state = ProjectState(materials=[])
    
    # Store legacy removed ID without -r suffix
    removed_ids = {"plane-1-b0-s0"}
    
    # Verify that placement with -r3 suffix is treated as removed
    assert state._is_placement_removed("plane-1-b0-s0-r3", removed_ids) is True
    
    # Verify exact match still works
    assert state._is_placement_removed("plane-1-b0-s0", removed_ids) is True
    
    # Verify unrelated placement is not treated as removed
    assert state._is_placement_removed("plane-2-b0-s0-r1", removed_ids) is False
    assert state._is_placement_removed("plane-1-b1-s0-r1", removed_ids) is False
