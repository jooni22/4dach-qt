from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF

from core.models import Bounds2D, Point2D


class CanvasMapper:
    """Transforms domain coordinates (cm) to canvas pixels and back."""

    def __init__(self, bounds: Bounds2D, canvas_rect: QRectF, margin: float = 30.0):
        self.bounds = bounds
        self.canvas_rect = canvas_rect
        self.margin = margin
        available = canvas_rect.adjusted(margin, margin, -margin, -margin)
        domain_width = max(bounds.width, 1.0)
        domain_height = max(bounds.height, 1.0)
        self.scale = min(available.width() / domain_width, available.height() / domain_height)
        self.offset_x = available.left() + (available.width() - domain_width * self.scale) / 2.0
        self.offset_y = available.top() + (available.height() - domain_height * self.scale) / 2.0

    def map_point(self, point: Point2D) -> QPointF:
        return QPointF(
            self.offset_x + (point.x - self.bounds.min_x) * self.scale,
            self.offset_y + (point.y - self.bounds.min_y) * self.scale,
        )

    def map_x(self, x_cm: float) -> float:
        return self.offset_x + (x_cm - self.bounds.min_x) * self.scale

    def map_y(self, y_cm: float) -> float:
        return self.offset_y + (y_cm - self.bounds.min_y) * self.scale

    def map_rect(self, x_left: float, x_right: float, y_top: float, y_bottom: float) -> QRectF:
        left = self.map_x(x_left)
        right = self.map_x(x_right)
        top = self.map_y(y_top)
        bottom = self.map_y(y_bottom)
        return QRectF(left, top, right - left, bottom - top)

    def map_length(self, length_cm: float) -> float:
        return length_cm * self.scale
