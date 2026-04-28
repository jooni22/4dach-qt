from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QRectF

from core.canvas_mapper import CanvasMapper
from core.models import Bounds2D, Point2D


def test_mapper_scales_and_offsets_correctly():
    bounds = Bounds2D(0.0, 0.0, 100.0, 50.0)
    rect = QRectF(0, 0, 400, 300)
    mapper = CanvasMapper(bounds, rect, margin=0)

    # scale = min(400/100, 300/50) = min(4.0, 6.0) = 4.0  (fit-by-width wins)
    # offset_x = (400 - 100*4) / 2 = 0.0
    # offset_y = (300 - 50*4)  / 2 = 50.0
    p = mapper.map_point(Point2D(0.0, 0.0))
    assert p.x() == pytest.approx(0.0, abs=0.01)
    assert p.y() == pytest.approx(50.0, abs=0.01)

    p = mapper.map_point(Point2D(100.0, 50.0))
    assert p.x() == pytest.approx(400.0, abs=0.01)
    assert p.y() == pytest.approx(250.0, abs=0.01)


def test_mapper_maps_rect():
    bounds = Bounds2D(0.0, 0.0, 200.0, 100.0)
    rect = QRectF(0, 0, 400, 200)
    mapper = CanvasMapper(bounds, rect, margin=0)

    r = mapper.map_rect(0.0, 100.0, 0.0, 50.0)
    assert r.width() == pytest.approx(200.0, abs=0.01)
    assert r.height() == pytest.approx(100.0, abs=0.01)


def test_mapper_applies_margin():
    bounds = Bounds2D(0.0, 0.0, 100.0, 100.0)
    rect = QRectF(0, 0, 200, 200)
    mapper = CanvasMapper(bounds, rect, margin=20.0)

    # available area is 160x160
    p = mapper.map_point(Point2D(0.0, 0.0))
    assert p.x() >= 20.0
    assert p.y() >= 20.0


def test_mapper_can_unmap_canvas_points_back_to_domain():
    bounds = Bounds2D(10.0, 20.0, 110.0, 70.0)
    rect = QRectF(0, 0, 400, 300)
    mapper = CanvasMapper(bounds, rect, margin=0)

    original = Point2D(55.0, 35.0)
    mapped = mapper.map_point(original)
    unmapped = mapper.unmap_point(mapped)

    assert unmapped.x == pytest.approx(original.x, abs=0.01)
    assert unmapped.y == pytest.approx(original.y, abs=0.01)
