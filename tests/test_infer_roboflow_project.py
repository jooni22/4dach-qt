from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

from core.geometry import validate_polygon
from core.project_state import ProjectState

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "inference-roboflow" / "infer_roboflow_svg.py"


@pytest.fixture()
def infer_module(monkeypatch):
    fake_sdk = types.ModuleType("inference_sdk")
    fake_sdk.InferenceHTTPClient = object
    monkeypatch.setitem(sys.modules, "inference_sdk", fake_sdk)
    spec = importlib.util.spec_from_file_location("infer_roboflow_svg", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _prediction(points: list[tuple[float, float]]) -> dict:
    return {"points": [{"x": x, "y": y} for x, y in points], "confidence": 0.9}


def _default_config() -> dict:
    return {
        "materials": {
            "order": ["PD510"],
            "items": {
                "PD510": {
                    "n": "PD510",
                    "t": "trapezowa",
                    "w": 51,
                    "min": 50,
                    "max": 900,
                    "top": 0,
                    "bottom": 0,
                    "mod": None,
                    "p": 0.0,
                    "bat": 0,
                    "cbat": 0,
                    "mods": [],
                    "u": "m2",
                }
            },
        }
    }


def test_build_project_payload_creates_one_roof_plane_per_prediction(infer_module):
    result = {
        "predictions": [
            _prediction([(0, 0), (120, 0), (120, 80), (0, 80)]),
            _prediction([(10, 10), (90, 20), (60, 100)]),
        ]
    }

    payload = infer_module.build_project_payload(
        result,
        Path("/tmp/1.jpg"),
        default_config=_default_config(),
        simplify_tolerance=0.0,
    )

    roof_planes = payload["project_state"]["roof_planes"]
    assert payload["project_meta"]["name"] == "1"
    assert roof_planes["order"] == ["plane-1", "plane-2"]
    assert roof_planes["items"]["plane-1"]["n"] == "1"
    assert roof_planes["items"]["plane-2"]["n"] == "2"
    assert roof_planes["items"]["plane-1"]["o"] == [
        [0.0, 0.0],
        [120.0, 0.0],
        [120.0, 80.0],
        [0.0, 80.0],
    ]


def test_project_payload_loads_through_project_state_with_selected_material(infer_module):
    result = {"predictions": [_prediction([(0, 0), (100, 0), (100, 50), (0, 50)])]}

    payload = infer_module.build_project_payload(
        result,
        Path("/tmp/roof.jpg"),
        default_config=_default_config(),
        simplify_tolerance=0.0,
    )
    state = ProjectState.from_config(payload)

    assert payload["materials"]["order"] == ["PD510"]
    assert payload["blachy"][0]["id"] == "PD510"
    assert state.available_material_ids() == ["PD510"]
    assert len(state.roof_planes) == 1
    assert state.roof_planes[0].selected_material_id == "PD510"
    assert state.roof_planes[0].outline is not None
    assert [(point.x, point.y) for point in state.roof_planes[0].outline.points] == [
        (0.0, 0.0),
        (100.0, 0.0),
        (100.0, 50.0),
        (0.0, 50.0),
    ]


def test_simplification_reduces_dense_polygon_and_keeps_it_valid(infer_module):
    dense_rectangle = [
        (0, 0),
        (25, 0),
        (50, 0),
        (75, 0),
        (100, 0),
        (100, 30),
        (100, 60),
        (75, 60),
        (50, 60),
        (25, 60),
        (0, 60),
        (0, 30),
        (0, 0),
    ]

    points = infer_module.prepare_polygon_points(dense_rectangle, simplify_tolerance=2.0)

    assert len(points) < len(dense_rectangle) - 1
    assert len(points) >= 3
    assert validate_polygon(infer_module.polygon_from_points(points)) == []


def test_invalid_or_too_short_predictions_are_skipped(infer_module, capsys):
    result = {
        "predictions": [
            _prediction([(0, 0), (10, 10)]),
            _prediction([(0, 0), (100, 100), (0, 100), (100, 0)]),
            _prediction([(0, 0), (80, 0), (80, 40), (0, 40)]),
        ]
    }

    payload = infer_module.build_project_payload(
        result,
        Path("/tmp/skipped.jpg"),
        default_config=_default_config(),
        simplify_tolerance=0.0,
    )

    assert payload["project_state"]["roof_planes"]["order"] == ["plane-1"]
    assert "Skipping Roboflow prediction 1" in capsys.readouterr().err


def test_project_payload_fails_when_no_valid_predictions_exist(infer_module):
    result = {"predictions": [_prediction([(0, 0), (10, 10)])]}

    with pytest.raises(ValueError, match="No valid roof polygons"):
        infer_module.build_project_payload(
            result,
            Path("/tmp/empty.jpg"),
            default_config=_default_config(),
        )
