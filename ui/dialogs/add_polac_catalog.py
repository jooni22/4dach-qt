from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FieldSpec:
    key: str
    label: str
    default: int
    max_value: int = 9999


@dataclass(frozen=True, slots=True)
class ShapeSpec:
    key: str
    label: str
    fields: tuple[FieldSpec, ...]


@dataclass(frozen=True, slots=True)
class CutoutSpec:
    key: str
    label: str
    preview_points: tuple[tuple[float, float], ...]
    fields: tuple[FieldSpec, ...]


SHAPE_CATALOG: tuple[ShapeSpec, ...] = (
    ShapeSpec(
        key="prostokat",
        label="Prostokąt",
        fields=(FieldSpec("A", "A - szerokość:", 800), FieldSpec("B", "H - wysokość:", 300)),
    ),
    ShapeSpec(
        key="trojkat",
        label="Trójkąt",
        fields=(FieldSpec("A", "A - podstawa:", 800), FieldSpec("B", "H - wysokość:", 300)),
    ),
    ShapeSpec(
        key="trapez_row",
        label="Trapez\nrównoram.",
        fields=(
            FieldSpec("A", "A - podstawa dolna:", 800),
            FieldSpec("C", "B - podstawa górna:", 500),
            FieldSpec("B", "H - wysokość:", 300),
        ),
    ),
    ShapeSpec(
        key="trapez_prl",
        label="Równoległobok\nprawy",
        fields=(
            FieldSpec("A", "A - podstawa:", 800),
            FieldSpec("C", "E - przesunięcie:", 500),
            FieldSpec("B", "H - wysokość:", 300),
        ),
    ),
    ShapeSpec(
        key="trapez_l",
        label="Równoległobok\nlewy",
        fields=(
            FieldSpec("A", "A - podstawa:", 800),
            FieldSpec("C", "E - przesunięcie:", 500),
            FieldSpec("B", "H - wysokość:", 300),
        ),
    ),
    ShapeSpec(
        key="trapez6",
        label="Trapez\nprawy",
        fields=(
            FieldSpec("A", "A - podstawa dolna:", 800),
            FieldSpec("C", "B - podstawa górna:", 500),
            FieldSpec("B", "H - wysokość:", 300),
        ),
    ),
    ShapeSpec(
        key="trapez7",
        label="Trapez\nlewy",
        fields=(
            FieldSpec("A", "A - podstawa dolna:", 800),
            FieldSpec("C", "B - podstawa górna:", 500),
            FieldSpec("B", "H - wysokość:", 300),
        ),
    ),
    ShapeSpec(
        key="pieciokat",
        label="Pięciokąt",
        fields=(FieldSpec("A", "A - szerokość:", 800), FieldSpec("B", "H - wysokość:", 300)),
    ),
    ShapeSpec(
        key="pieciokat2",
        label="Sześciokąt",
        fields=(FieldSpec("A", "A - szerokość:", 800), FieldSpec("B", "H - wysokość:", 300)),
    ),
)

SHAPE_CATALOG_BY_KEY = {shape.key: shape for shape in SHAPE_CATALOG}
SHAPE_ORDER = tuple(shape.key for shape in SHAPE_CATALOG)

CUTOUT_CATALOG: tuple[CutoutSpec, ...] = (
    CutoutSpec(key="none", label="Bez wycinka", preview_points=(), fields=()),
    CutoutSpec(
        key="lukarna1",
        label="Lukarna 1",
        preview_points=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
        fields=(FieldSpec("A", "A:", 80), FieldSpec("H1", "H1:", 60)),
    ),
    CutoutSpec(
        key="lukarna2",
        label="Lukarna 2",
        preview_points=((0.5, 0.0), (1.0, 1.0), (0.0, 1.0)),
        fields=(FieldSpec("A", "A:", 80), FieldSpec("H", "H:", 60)),
    ),
    CutoutSpec(
        key="lukarna3",
        label="Lukarna 3",
        preview_points=((0.5, 0.0), (1.0, 0.4), (1.0, 1.0), (0.0, 1.0), (0.0, 0.4)),
        fields=(FieldSpec("A", "A:", 80), FieldSpec("H1", "H1:", 60), FieldSpec("H", "H:", 60)),
    ),
)

CUTOUT_CATALOG_BY_KEY = {cutout.key: cutout for cutout in CUTOUT_CATALOG}
CUTOUT_ORDER = tuple(cutout.key for cutout in CUTOUT_CATALOG)


def default_shape_values(shape_key: str) -> dict[str, int]:
    return {field.key: field.default for field in SHAPE_CATALOG_BY_KEY[shape_key].fields}


def default_cutout_values(cutout_key: str) -> dict[str, int]:
    values = {field.key: field.default for field in CUTOUT_CATALOG_BY_KEY[cutout_key].fields}
    if cutout_key != "none":
        values.update({"X": 0, "Y": 0})
    return values


def default_add_polac_dialog_cache() -> dict[str, Any]:
    return {
        "last_shape": SHAPE_ORDER[0],
        "last_cutout": "none",
        "flip_h": False,
        "flip_v": False,
        "shapes": {shape_key: default_shape_values(shape_key) for shape_key in SHAPE_ORDER},
        "cutouts": {
            cutout_key: default_cutout_values(cutout_key)
            for cutout_key in CUTOUT_ORDER
            if cutout_key != "none"
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
