from __future__ import annotations

import pytest

from core.geometry import build_add_polac_cutout, build_add_polac_outline, polygon_is_inside_polygon
from ui.dialogs.add_polac_catalog import (
    CUTOUT_CATALOG,
    SHAPE_CATALOG,
    default_add_polac_dialog_cache,
    default_cutout_values,
    default_shape_values,
    merge_add_polac_dialog_cache,
)


def _normalize_polygon_points(points):
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x = min(xs)
    min_y = min(ys)
    width = max(max(xs) - min_x, 1.0)
    height = max(max(ys) - min_y, 1.0)
    return tuple((round((x - min_x) / width, 3), round((y - min_y) / height, 3)) for x, y in points)


def _normalize_polygon(polygon):
    return _normalize_polygon_points([(point.x, point.y) for point in polygon.points])


def test_shape_catalog_uses_domain_labels_and_preview_matches_default_geometry():
    for shape in SHAPE_CATALOG:
        assert not shape.label.startswith("Połać ")

        outline = build_add_polac_outline(shape.key, default_shape_values(shape.key))
        assert _normalize_polygon(outline) == _normalize_polygon_points(shape.preview_points)


def test_cutout_catalog_uses_domain_labels_and_preview_matches_default_geometry():
    outline = build_add_polac_outline("prostokat", {"A": 800, "B": 300})

    for cutout in CUTOUT_CATALOG:
        if cutout.key == "none":
            continue

        assert cutout.label != f"Lukarna {cutout.key[-1]}"

        polygon = build_add_polac_cutout(
            cutout.key,
            default_cutout_values(cutout.key),
            outline,
            {"x": 0.5, "y": 0.5},
        )
        assert polygon is not None
        assert polygon_is_inside_polygon(polygon, outline) is True
        assert _normalize_polygon(polygon) == _normalize_polygon_points(cutout.preview_points)


def test_add_polac_dialog_cache_tracks_normalized_cutout_positions():
    cache = default_add_polac_dialog_cache()

    assert cache["cutout_positions"] == {
        "lukarna1": {"x": pytest.approx(0.5), "y": pytest.approx(0.5)},
        "lukarna2": {"x": pytest.approx(0.5), "y": pytest.approx(0.5)},
        "lukarna3": {"x": pytest.approx(0.5), "y": pytest.approx(0.5)},
    }

    merged = merge_add_polac_dialog_cache(
        {
            "cutout_positions": {
                "lukarna2": {"x": 0.72, "y": 0.34},
                "lukarna3": {"x": 99.0, "y": -2.0},
            }
        }
    )

    assert merged["cutout_positions"]["lukarna1"] == {"x": pytest.approx(0.5), "y": pytest.approx(0.5)}
    assert merged["cutout_positions"]["lukarna2"] == {"x": pytest.approx(0.72), "y": pytest.approx(0.34)}
    assert merged["cutout_positions"]["lukarna3"] == {"x": pytest.approx(0.5), "y": pytest.approx(0.5)}
