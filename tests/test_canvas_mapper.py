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

    # Should fit to height (scale = 300/50 = 6), centered horizontally
    # domain width * scale = 600, canvas width = 400, offset_x = (400-600)/2 = -100
    p = mapper.map_point(Point2D(0.0, 0.0))
    assert p.x() == pytest.approx(-100.0, abs=0.01)
    assert p.y() == pytest.approx(0.0, abs=0.01)

    p = mapper.map_point(Point2D(100.0, 50.0))
    assert p.x() == pytest.approx(500.0, abs=0.01)
    assert p.y() == pytest.approx(300.0, abs=0.01)


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
