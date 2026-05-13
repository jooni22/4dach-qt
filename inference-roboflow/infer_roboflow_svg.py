from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.geometry import validate_polygon
from core.models import Point2D, Polygon2D
from core.project_state import ProjectState
from persistence import load_config

DEFAULT_API_URL = "https://serverless.roboflow.com"
DEFAULT_MODEL_ID = "roof-plan-strict-clean/2"
DEFAULT_API_KEY = "PofvpbO277Fof3GFUXU4"
DEFAULT_SIMPLIFY_TOLERANCE = 2.0
POINT_EPSILON = 1e-9

PointTuple = tuple[float, float]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Roboflow roof segmentation and write a 4dach project next to the image."
    )
    parser.add_argument(
        "image",
        nargs="?",
        type=Path,
        default=Path(__file__).with_name("1.jpg"),
        help="Input image path. Defaults to 1.jpg next to this script.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional .4dach output path. Defaults to input image with .4dach suffix.",
    )
    parser.add_argument(
        "--simplify-tolerance",
        type=float,
        default=DEFAULT_SIMPLIFY_TOLERANCE,
        help="RDP simplification tolerance in centimeters/pixels. Defaults to 2.0.",
    )
    parser.add_argument(
        "--no-simplify",
        action="store_true",
        help="Disable polygon simplification and save valid raw Roboflow polygons.",
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_MODEL_ID,
        help="Roboflow model id.",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="Roboflow inference API URL.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("ROBOFLOW_API_KEY", DEFAULT_API_KEY),
        help="Roboflow API key. Can also be set with ROBOFLOW_API_KEY.",
    )
    return parser.parse_args(argv)


def points_from_prediction(prediction: dict[str, Any]) -> list[PointTuple]:
    points = prediction.get("points", [])
    if not isinstance(points, list):
        return []

    parsed: list[PointTuple] = []
    for point in points:
        if not isinstance(point, dict):
            continue
        x = point.get("x")
        y = point.get("y")
        if isinstance(x, int | float) and isinstance(y, int | float):
            parsed.append((float(x), float(y)))
    return parsed


def polygon_from_points(points: list[PointTuple]) -> Polygon2D:
    return Polygon2D([Point2D(x, y) for x, y in points])


def prepare_polygon_points(
    points: list[PointTuple],
    *,
    simplify_tolerance: float | None = DEFAULT_SIMPLIFY_TOLERANCE,
) -> list[PointTuple]:
    cleaned = _remove_duplicate_and_closing_points(points)
    if len(cleaned) < 3:
        return []
    if simplify_tolerance is None or simplify_tolerance <= 0:
        return cleaned
    return _remove_duplicate_and_closing_points(_simplify_closed_polygon(cleaned, simplify_tolerance))


def build_project_payload(
    result: dict[str, Any],
    image_path: Path,
    *,
    default_config: dict | None = None,
    simplify_tolerance: float | None = DEFAULT_SIMPLIFY_TOLERANCE,
) -> dict:
    source_config = load_config() if default_config is None else default_config
    state = ProjectState(materials=_default_materials(source_config), version=2)
    selected_material_id = state.materials[0].id if state.materials else None

    raw_predictions = result.get("predictions", [])
    predictions = raw_predictions if isinstance(raw_predictions, list) else []
    skipped_count = 0

    for prediction_index, prediction in enumerate(predictions, start=1):
        if not isinstance(prediction, dict):
            _warn_skip(prediction_index, "prediction is not an object")
            skipped_count += 1
            continue

        raw_points = prepare_polygon_points(
            points_from_prediction(prediction),
            simplify_tolerance=None,
        )
        raw_polygon, raw_issues = _validated_polygon(raw_points)
        if raw_polygon is None:
            _warn_skip(prediction_index, "; ".join(raw_issues))
            skipped_count += 1
            continue

        polygon = raw_polygon
        if simplify_tolerance is not None and simplify_tolerance > 0:
            simplified_points = prepare_polygon_points(
                raw_points,
                simplify_tolerance=simplify_tolerance,
            )
            simplified_polygon, simplified_issues = _validated_polygon(simplified_points)
            if simplified_polygon is not None:
                polygon = simplified_polygon
            else:
                _warn_prediction(
                    prediction_index,
                    "simplified polygon invalid, using raw polygon: "
                    + "; ".join(simplified_issues),
                )

        state.add_roof_plane(
            polygon,
            name=str(len(state.roof_planes) + 1),
            selected_material_id=selected_material_id,
        )

    if not state.roof_planes:
        raise ValueError(f"No valid roof polygons found in Roboflow result ({skipped_count} skipped).")

    fragment = state.to_config_fragment()
    fragment.pop("app_settings", None)
    return {
        "project_meta": {"name": image_path.stem},
        "materials": fragment.get("materials", {"order": [], "items": {}}),
        "blachy": fragment.get("blachy", []),
        "project_state": fragment["project_state"],
    }


def write_project_payload(payload: dict, output_path: Path) -> None:
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _default_materials(config_data: dict) -> list:
    material_source = {
        "materials": config_data.get("materials"),
        "blachy": config_data.get("blachy", []),
        "project_state": {"version": 2, "roof_planes": {"order": [], "items": {}}},
    }
    materials = ProjectState.from_config(material_source).materials
    return materials[:1]


def _validated_polygon(points: list[PointTuple]) -> tuple[Polygon2D | None, list[str]]:
    if len(points) < 3:
        return None, ["polygon has fewer than 3 points"]
    try:
        polygon = polygon_from_points(points)
    except ValueError as exc:
        return None, [str(exc)]

    issues = validate_polygon(polygon)
    if issues:
        return None, issues
    return polygon, []


def _warn_skip(prediction_index: int, reason: str) -> None:
    print(f"Skipping Roboflow prediction {prediction_index}: {reason}", file=sys.stderr)


def _warn_prediction(prediction_index: int, reason: str) -> None:
    print(f"Roboflow prediction {prediction_index}: {reason}", file=sys.stderr)


def _same_point(first: PointTuple, second: PointTuple) -> bool:
    return (
        math.isclose(first[0], second[0], abs_tol=POINT_EPSILON)
        and math.isclose(first[1], second[1], abs_tol=POINT_EPSILON)
    )


def _remove_duplicate_and_closing_points(points: list[PointTuple]) -> list[PointTuple]:
    cleaned: list[PointTuple] = []
    for point in points:
        if cleaned and _same_point(cleaned[-1], point):
            continue
        cleaned.append((float(point[0]), float(point[1])))

    while len(cleaned) > 1 and _same_point(cleaned[0], cleaned[-1]):
        cleaned.pop()
    return cleaned


def _simplify_closed_polygon(points: list[PointTuple], tolerance: float) -> list[PointTuple]:
    if len(points) <= 3:
        return list(points)
    closed_points = [*points, points[0]]
    simplified = _rdp(closed_points, tolerance)
    return simplified[:-1] if simplified and _same_point(simplified[0], simplified[-1]) else simplified


def _rdp(points: list[PointTuple], tolerance: float) -> list[PointTuple]:
    if len(points) <= 2:
        return list(points)

    start = points[0]
    end = points[-1]
    max_distance = -1.0
    split_index = 0

    for index, point in enumerate(points[1:-1], start=1):
        distance = _point_line_distance(point, start, end)
        if distance > max_distance:
            max_distance = distance
            split_index = index

    if max_distance > tolerance:
        left = _rdp(points[: split_index + 1], tolerance)
        right = _rdp(points[split_index:], tolerance)
        return [*left[:-1], *right]
    return [start, end]


def _point_line_distance(point: PointTuple, start: PointTuple, end: PointTuple) -> float:
    if _same_point(start, end):
        return math.hypot(point[0] - start[0], point[1] - start[1])

    numerator = abs(
        (end[1] - start[1]) * point[0]
        - (end[0] - start[0]) * point[1]
        + end[0] * start[1]
        - end[1] * start[0]
    )
    denominator = math.hypot(end[1] - start[1], end[0] - start[0])
    return numerator / denominator


def _infer(image_path: Path, *, api_url: str, api_key: str, model_id: str) -> dict[str, Any]:
    from inference_sdk import InferenceHTTPClient  # noqa: PLC0415

    client = InferenceHTTPClient(api_url=api_url, api_key=api_key)
    result = client.infer(str(image_path), model_id=model_id)
    if not isinstance(result, dict):
        raise ValueError("Roboflow inference result is not a JSON object.")
    return result


def main() -> int:
    args = parse_args()
    image_path = args.image.expanduser().resolve()
    if not image_path.exists():
        raise SystemExit(f"Image not found: {image_path}")

    output_path = (
        args.output.expanduser().resolve()
        if args.output
        else image_path.with_suffix(".4dach")
    )
    simplify_tolerance = None if args.no_simplify else args.simplify_tolerance
    try:
        result = _infer(
            image_path,
            api_url=args.api_url,
            api_key=args.api_key,
            model_id=args.model_id,
        )
        payload = build_project_payload(
            result,
            image_path,
            simplify_tolerance=simplify_tolerance,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    write_project_payload(payload, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
