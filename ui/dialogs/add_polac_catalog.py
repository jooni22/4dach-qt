from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FieldSpec:
    key: str
    label: str
    default: int
    max_value: int = 9999
    dimension_role: str = "generic"


@dataclass(frozen=True, slots=True)
class ShapeSpec:
    key: str
    label: str
    description: str
    preview_points: tuple[tuple[float, float], ...]
    fields: tuple[FieldSpec, ...]


@dataclass(frozen=True, slots=True)
class CutoutSpec:
    key: str
    label: str
    description: str
    preview_points: tuple[tuple[float, float], ...]
    fields: tuple[FieldSpec, ...]


SHAPE_CATALOG: tuple[ShapeSpec, ...] = (
    ShapeSpec(
        key="prostokat",
        label="Prostokąt",
        description="pełny obrys prostokątny",
        preview_points=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
        fields=(
            FieldSpec("A", "szerokość", 800, dimension_role="width"),
            FieldSpec("B", "wysokość", 300, dimension_role="height"),
        ),
    ),
    ShapeSpec(
        key="trojkat",
        label="Trójkąt",
        description="szczyt centralny",
        preview_points=((0.5, 0.0), (1.0, 1.0), (0.0, 1.0)),
        fields=(
            FieldSpec("A", "podstawa", 800, dimension_role="base"),
            FieldSpec("B", "wysokość", 300, dimension_role="height"),
        ),
    ),
    ShapeSpec(
        key="trapez_row",
        label="Trapez równoramienny",
        description="górna podstawa wyśrodkowana",
        preview_points=((0.188, 0.0), (0.812, 0.0), (1.0, 1.0), (0.0, 1.0)),
        fields=(
            FieldSpec("A", "podstawa dolna", 800, dimension_role="bottom_base"),
            FieldSpec("C", "podstawa górna", 500, dimension_role="top_base"),
            FieldSpec("B", "wysokość", 300, dimension_role="height"),
        ),
    ),
    ShapeSpec(
        key="trapez_prl",
        label="Trapez prawy",
        description="górna podstawa dosunięta do prawej",
        preview_points=((0.375, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
        fields=(
            FieldSpec("A", "podstawa dolna", 800, dimension_role="bottom_base"),
            FieldSpec("C", "podstawa górna", 500, dimension_role="top_base"),
            FieldSpec("B", "wysokość", 300, dimension_role="height"),
        ),
    ),
    ShapeSpec(
        key="trapez_l",
        label="Trapez lewy",
        description="górna podstawa dosunięta do lewej",
        preview_points=((0.0, 0.0), (0.625, 0.0), (1.0, 1.0), (0.0, 1.0)),
        fields=(
            FieldSpec("A", "podstawa dolna", 800, dimension_role="bottom_base"),
            FieldSpec("C", "podstawa górna", 500, dimension_role="top_base"),
            FieldSpec("B", "wysokość", 300, dimension_role="height"),
        ),
    ),
    ShapeSpec(
        key="trapez6",
        label="Trapez skośny",
        description="wariant katalogowy ze skosem lewym",
        preview_points=((0.0, 0.0), (0.625, 0.0), (1.0, 1.0), (0.0, 1.0)),
        fields=(
            FieldSpec("A", "podstawa dolna", 800, dimension_role="bottom_base"),
            FieldSpec("C", "podstawa górna", 500, dimension_role="top_base"),
            FieldSpec("B", "wysokość", 300, dimension_role="height"),
        ),
    ),
    ShapeSpec(
        key="trapez7",
        label="Trapez osiowy",
        description="wariant katalogowy ze szczytem centralnym",
        preview_points=((0.188, 0.0), (0.812, 0.0), (1.0, 1.0), (0.0, 1.0)),
        fields=(
            FieldSpec("A", "podstawa dolna", 800, dimension_role="bottom_base"),
            FieldSpec("C", "podstawa górna", 500, dimension_role="top_base"),
            FieldSpec("B", "wysokość", 300, dimension_role="height"),
        ),
    ),
    ShapeSpec(
        key="pieciokat",
        label="Pięciokąt symetryczny",
        description="ścięcia po obu stronach",
        preview_points=((0.5, 0.0), (1.0, 0.4), (1.0, 1.0), (0.0, 1.0), (0.0, 0.4)),
        fields=(
            FieldSpec("A", "szerokość", 800, dimension_role="width"),
            FieldSpec("B", "wysokość", 300, dimension_role="height"),
        ),
    ),
    ShapeSpec(
        key="pieciokat2",
        label="Pięciokąt zwężony",
        description="dolna krawędź zawężona",
        preview_points=((0.5, 0.0), (1.0, 0.4), (0.85, 1.0), (0.15, 1.0), (0.0, 0.4)),
        fields=(
            FieldSpec("A", "szerokość", 800, dimension_role="width"),
            FieldSpec("B", "wysokość", 300, dimension_role="height"),
        ),
    ),
)

SHAPE_CATALOG_BY_KEY = {shape.key: shape for shape in SHAPE_CATALOG}
SHAPE_ORDER = tuple(shape.key for shape in SHAPE_CATALOG)

CUTOUT_CATALOG: tuple[CutoutSpec, ...] = (
    CutoutSpec(
        key="none",
        label="Bez wycinka",
        description="pełna połać bez wycięcia",
        preview_points=(),
        fields=(),
    ),
    CutoutSpec(
        key="lukarna1",
        label="Lukarna prostokątna",
        description="prostokątny wycinek",
        preview_points=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
        fields=(
            FieldSpec("A", "szerokość", 80, dimension_role="width"),
            FieldSpec("H1", "wysokość", 60, dimension_role="height"),
        ),
    ),
    CutoutSpec(
        key="lukarna2",
        label="Lukarna trójkątna",
        description="wycinek ze szczytem centralnym",
        preview_points=((0.5, 0.0), (1.0, 1.0), (0.0, 1.0)),
        fields=(
            FieldSpec("A", "szerokość", 80, dimension_role="width"),
            FieldSpec("H", "wysokość całkowita", 60, dimension_role="height"),
        ),
    ),
    CutoutSpec(
        key="lukarna3",
        label="Lukarna pięciokątna",
        description="wycinek z linią załamania",
        preview_points=((0.5, 0.0), (1.0, 0.5), (1.0, 1.0), (0.0, 1.0), (0.0, 0.5)),
        fields=(
            FieldSpec("A", "szerokość", 80, dimension_role="width"),
            FieldSpec("H1", "wysokość załamania", 30, dimension_role="break_height"),
            FieldSpec("H", "wysokość całkowita", 60, dimension_role="height"),
        ),
    ),
)

CUTOUT_CATALOG_BY_KEY = {cutout.key: cutout for cutout in CUTOUT_CATALOG}
CUTOUT_ORDER = tuple(cutout.key for cutout in CUTOUT_CATALOG)


def default_shape_values(shape_key: str) -> dict[str, int]:
    return {field.key: field.default for field in SHAPE_CATALOG_BY_KEY[shape_key].fields}


def default_cutout_values(cutout_key: str) -> dict[str, int]:
    return {field.key: field.default for field in CUTOUT_CATALOG_BY_KEY[cutout_key].fields}


def default_cutout_position() -> dict[str, float]:
    return {"x": 0.5, "y": 0.5}


def default_add_polac_dialog_cache() -> dict[str, Any]:
    return {
        "last_shape": SHAPE_ORDER[0],
        "last_cutout": "none",
        "flip_h": False,
        "flip_v": False,
        "shapes": {shape_key: default_shape_values(shape_key) for shape_key in SHAPE_ORDER},
        "cutouts": {cutout_key: default_cutout_values(cutout_key) for cutout_key in CUTOUT_ORDER if cutout_key != "none"},
        "cutout_positions": {
            cutout_key: default_cutout_position() for cutout_key in CUTOUT_ORDER if cutout_key != "none"
        },
    }


def merge_add_polac_dialog_cache(raw_cache: dict[str, Any] | None) -> dict[str, Any]:
    cache = default_add_polac_dialog_cache()
    payload = raw_cache or {}

    last_shape = payload.get("last_shape")
    if last_shape in SHAPE_CATALOG_BY_KEY:
        cache["last_shape"] = last_shape

    last_cutout = payload.get("last_cutout")
    if last_cutout in CUTOUT_CATALOG_BY_KEY:
        cache["last_cutout"] = last_cutout

    cache["flip_h"] = bool(payload.get("flip_h", cache["flip_h"]))
    cache["flip_v"] = bool(payload.get("flip_v", cache["flip_v"]))

    shape_payloads = payload.get("shapes", {})
    if isinstance(shape_payloads, dict):
        for shape_key in SHAPE_ORDER:
            cache["shapes"][shape_key] = _merge_field_values(
                cache["shapes"][shape_key],
                shape_payloads.get(shape_key, {}),
            )

    cutout_payloads = payload.get("cutouts", {})
    if isinstance(cutout_payloads, dict):
        for cutout_key in CUTOUT_ORDER:
            if cutout_key == "none":
                continue
            cache["cutouts"][cutout_key] = _merge_field_values(
                cache["cutouts"][cutout_key],
                cutout_payloads.get(cutout_key, {}),
            )

    cutout_positions = payload.get("cutout_positions", {})
    if isinstance(cutout_positions, dict):
        for cutout_key in CUTOUT_ORDER:
            if cutout_key == "none":
                continue
            cache["cutout_positions"][cutout_key] = _merge_position_values(
                cutout_positions.get(cutout_key),
                cache["cutout_positions"][cutout_key],
            )

    return cache


def seed_add_polac_dialog_cache(config_data: dict[str, Any] | None) -> dict[str, Any]:
    payload = config_data or {}
    existing_cache = payload.get("add_polac_dialog")
    if isinstance(existing_cache, dict):
        return merge_add_polac_dialog_cache(existing_cache)

    cache = default_add_polac_dialog_cache()
    legacy_shapes = payload.get("ksztalty", {})
    if not isinstance(legacy_shapes, dict):
        return cache

    legacy_rectangle = legacy_shapes.get("prostokat", {})
    cache["shapes"]["prostokat"] = _merge_field_values(
        cache["shapes"]["prostokat"],
        {"A": legacy_rectangle.get("szerokosc"), "B": legacy_rectangle.get("wysokosc")},
    )

    legacy_triangle = legacy_shapes.get("trojkat", {})
    cache["shapes"]["trojkat"] = _merge_field_values(
        cache["shapes"]["trojkat"],
        {"A": legacy_triangle.get("podstawa"), "B": legacy_triangle.get("wysokosc")},
    )

    legacy_trapezoid = legacy_shapes.get("trapez", {})
    cache["shapes"]["trapez_row"] = _merge_field_values(
        cache["shapes"]["trapez_row"],
        {
            "A": legacy_trapezoid.get("podstawa_dolna"),
            "B": legacy_trapezoid.get("wysokosc"),
            "C": legacy_trapezoid.get("podstawa_gorna"),
        },
    )
    return cache


def _merge_field_values(defaults: dict[str, int], raw_values: Any) -> dict[str, int]:
    merged = dict(defaults)
    if not isinstance(raw_values, dict):
        return merged
    for key, default_value in defaults.items():
        raw_value = raw_values.get(key)
        try:
            merged[key] = int(raw_value) if raw_value is not None else default_value
        except (TypeError, ValueError):
            merged[key] = default_value
    return merged


def _merge_position_values(raw_value: Any, default_value: dict[str, float]) -> dict[str, float]:
    if not isinstance(raw_value, dict):
        return dict(default_value)
    try:
        x_value = float(raw_value.get("x", default_value["x"]))
        y_value = float(raw_value.get("y", default_value["y"]))
    except (TypeError, ValueError):
        return dict(default_value)
    if not 0.0 <= x_value <= 1.0 or not 0.0 <= y_value <= 1.0:
        return dict(default_value)
    return {"x": x_value, "y": y_value}
