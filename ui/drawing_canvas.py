# This Python file uses the following encoding: utf-8
"""DrawingCanvas — the interactive QWidget for roof-plane visualisation and drawing.

Modes
-----
MODE_VIEW          — passive display of the active roof plane
MODE_DRAW_OUTLINE  — click to add vertices; close polygon to create a new roof plane
MODE_SELECT_SHEET  — click a sheet placement to select/highlight it

Polygon drawing (MODE_DRAW_OUTLINE)
------------------------------------
* Left-click adds a vertex.
* When the cursor is within SNAP_RADIUS pixels of the *first* vertex (and ≥ 3
  vertices have been placed) the canvas shows a snap indicator and the cursor
  changes to a crosshair — clicking there closes the polygon.
* Pressing Enter also closes the polygon when ≥ 3 vertices are present.
* Right-click / Escape clears the in-progress sketch.
* The ``polygon_closed`` signal is emitted with the list of QPointF vertices so
  that the controller can convert them to domain coordinates and add a RoofPlane.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPalette, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from core.canvas_mapper import CanvasMapper
from core.models import Bounds2D

SNAP_RADIUS = 10  # pixels — distance to first vertex that triggers polygon closing


class DrawingCanvas(QWidget):
    """Interactive canvas for displaying and drawing roof planes."""

    MODE_VIEW = "view"
    MODE_DRAW_OUTLINE = "draw_outline"
    MODE_SELECT_SHEET = "select_sheet"

    # Emitted when the user closes a polygon in MODE_DRAW_OUTLINE.
    # Payload: list of QPointF in *canvas* pixel coordinates.
    polygon_closed = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Drawing state
        self.user_points: list[QPointF] = []
        self.preview_point: QPointF | None = None
        self._snap_active: bool = False  # True when cursor is near first vertex

        # Domain state
        self.roof_plane = None
        self._material = None  # always declared here to prevent AttributeError in paintEvent

        # UI state
        self._mode: str = self.MODE_VIEW
        self._selected_sheet_id: str | None = None
        self._show_grid: bool = False
        self._show_module_count: bool = False

        self.setMouseTracking(True)
        self.setAutoFillBackground(True)
        self.setMinimumSize(640, 420)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def toggle_grid(self, enabled: bool | None = None) -> None:
        self._show_grid = not self._show_grid if enabled is None else enabled
        self.update()

    def toggle_module_count(self, enabled: bool | None = None) -> None:
        self._show_module_count = not self._show_module_count if enabled is None else enabled
        self.update()

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self.user_points.clear()
        self.preview_point = None
        self._snap_active = False
        if mode == self.MODE_DRAW_OUTLINE:
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif mode == self.MODE_SELECT_SHEET:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def set_roof_plane(self, roof_plane) -> None:
        self.roof_plane = roof_plane
        self.update()

    def set_material(self, material) -> None:
        self._material = material
        self.update()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _canvas_mapper(self) -> CanvasMapper | None:
        if self.roof_plane is None or self.roof_plane.outline is None:
            return None
        return CanvasMapper(self.roof_plane.outline.bounds(), QRectF(self.rect()))

    def _hit_test_sheet(self, pos: QPointF) -> str | None:
        mapper = self._canvas_mapper()
        if mapper is None:
            return None
        for sheet in self.roof_plane.manual_sheet_placements + self.roof_plane.auto_sheet_placements:
            rect = mapper.map_rect(sheet.x_left_cm, sheet.x_right_cm, sheet.y_top_cm, sheet.y_bottom_cm)
            if rect.contains(pos.x(), pos.y()):
                return sheet.id
        return None

    def _is_near_first_vertex(self, pos: QPointF) -> bool:
        """Return True when *pos* is within SNAP_RADIUS of the first drawn vertex."""
        if len(self.user_points) < 3:
            return False
        first = self.user_points[0]
        dx = pos.x() - first.x()
        dy = pos.y() - first.y()
        return (dx * dx + dy * dy) <= SNAP_RADIUS * SNAP_RADIUS

    def _close_polygon(self) -> None:
        """Emit polygon_closed and reset drawing state."""
        if len(self.user_points) < 3:
            return
        self.polygon_closed.emit(list(self.user_points))
        self.user_points.clear()
        self.preview_point = None
        self._snap_active = False
        self.update()

    # ------------------------------------------------------------------
    # Qt event overrides
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position()

        if event.button() == Qt.MouseButton.LeftButton:
            if self._mode == self.MODE_DRAW_OUTLINE:
                if self._snap_active:
                    # Close the polygon on snap-click
                    self._close_polygon()
                else:
                    self.user_points.append(pos)
                    self.update()
                return

            if self._mode == self.MODE_SELECT_SHEET:
                sheet_id = self._hit_test_sheet(pos)
                if sheet_id != self._selected_sheet_id:
                    self._selected_sheet_id = sheet_id
                    self.update()
                return

        if event.button() == Qt.MouseButton.RightButton:
            if self._mode == self.MODE_DRAW_OUTLINE:
                self.user_points.clear()
                self.preview_point = None
                self._snap_active = False
                self.update()
                return
            if self._mode == self.MODE_SELECT_SHEET:
                self._selected_sheet_id = None
                self.update()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._mode == self.MODE_DRAW_OUTLINE:
            pos = event.position()
            self.preview_point = pos
            near = self._is_near_first_vertex(pos)
            if near != self._snap_active:
                self._snap_active = near
                cursor = Qt.CursorShape.PointingHandCursor if near else Qt.CursorShape.CrossCursor
                self.setCursor(cursor)
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        if self._mode == self.MODE_DRAW_OUTLINE:
            self.preview_point = None
            self._snap_active = False
            self.update()
        super().leaveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._mode == self.MODE_DRAW_OUTLINE:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._close_polygon()
                return
            if event.key() == Qt.Key.Key_Escape:
                self.user_points.clear()
                self.preview_point = None
                self._snap_active = False
                self.update()
                return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().color(QPalette.ColorRole.Base))

        frame_color = self.palette().color(QPalette.ColorRole.Mid)
        painter.setPen(QPen(frame_color, 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        if self.roof_plane is not None and self.roof_plane.outline is not None:
            if self._show_grid:
                self._draw_grid(painter)
            self._draw_roof_plane(painter)
        else:
            if self._show_grid:
                self._draw_grid(painter)
            self._draw_empty_state(painter)

        if self._mode == self.MODE_DRAW_OUTLINE:
            self._draw_user_path(painter)

        if self._selected_sheet_id and self._mode == self.MODE_SELECT_SHEET:
            self._draw_selected_sheet_highlight(painter)


    def _draw_grid(self, painter: QPainter) -> None:
        grid_color = self.palette().color(QPalette.ColorRole.Mid)
        grid_color.setAlpha(60)
        painter.setPen(QPen(grid_color, 0.5))
        w, h, step = self.width(), self.height(), 50
        for x in range(0, w, step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            painter.drawLine(0, y, w, y)

    def _draw_empty_state(self, painter: QPainter) -> None:
        """Draw a minimal empty-state hint when no roof plane is loaded."""
        muted = self.palette().color(QPalette.ColorRole.PlaceholderText)
        if not muted.isValid():
            muted = self.palette().color(QPalette.ColorRole.Mid)
        painter.setPen(QPen(muted, 1))
        font = painter.font()
        font.setPointSize(11)
        painter.setFont(font)
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "Brak połaci\n\nUżyj menu Kształt, aby dodać pierwszą połać.",
        )

    def _draw_user_path(self, painter: QPainter) -> None:
        if not self.user_points:
            return

        accent = self.palette().color(QPalette.ColorRole.Highlight)
        painter.setPen(QPen(accent, 2.0))

        for index in range(len(self.user_points) - 1):
            painter.drawLine(self.user_points[index], self.user_points[index + 1])

        # Preview line to cursor
        if self.preview_point is not None:
            painter.drawLine(self.user_points[-1], self.preview_point)

        # Closing line preview (dashed) from cursor back to first vertex
        if len(self.user_points) >= 3 and self.preview_point is not None:
            close_pen = QPen(accent, 1.5, Qt.PenStyle.DashLine)
            painter.setPen(close_pen)
            painter.drawLine(self.preview_point, self.user_points[0])

        # Vertex dots
        painter.setPen(QPen(accent, 1))
        painter.setBrush(accent)
        for index, point in enumerate(self.user_points):
            if index == 0 and self._snap_active:
                # Draw snap indicator: larger ring
                snap_color = QColor(accent)
                snap_color.setAlpha(200)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(snap_color, 2))
                painter.drawEllipse(int(point.x()) - SNAP_RADIUS, int(point.y()) - SNAP_RADIUS,
                                    SNAP_RADIUS * 2, SNAP_RADIUS * 2)
                painter.setBrush(accent)
                painter.setPen(QPen(accent, 1))
            painter.drawEllipse(int(point.x()) - 3, int(point.y()) - 3, 6, 6)

    def _draw_roof_plane(self, painter: QPainter) -> None:
        plane = self.roof_plane
        if plane is None or plane.outline is None:
            return

        bounds = plane.outline.bounds()
        mapper = CanvasMapper(bounds, QRectF(self.rect()))

        outline_polygon = QPolygonF([mapper.map_point(point) for point in plane.outline.points])
        fill_color = self.palette().color(QPalette.ColorRole.AlternateBase)
        outline_color = self.palette().color(QPalette.ColorRole.Highlight)
        text_color = self.palette().color(QPalette.ColorRole.Text)
        hole_color = QColor(outline_color)
        hole_color.setAlpha(180)

        painter.setPen(QPen(outline_color, 2))
        painter.setBrush(fill_color)
        painter.drawPolygon(outline_polygon)

        # Vertex handles
        painter.setPen(QPen(outline_color, 1))
        painter.setBrush(outline_color)
        for point in plane.outline.points:
            mp = mapper.map_point(point)
            painter.drawRect(int(mp.x()) - 3, int(mp.y()) - 3, 6, 6)

        painter.setPen(QPen(hole_color, 1.5, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for hole in plane.holes:
            painter.drawPolygon(QPolygonF([mapper.map_point(point) for point in hole.points]))

        self._draw_sheet_placements(painter, plane, mapper, text_color)

        painter.setPen(text_color)
        label = f"Połać {plane.name}"
        if plane.selected_material_id:
            label += f" | Blacha: {plane.selected_material_id}"
        r = self.rect().adjusted(40, 30, -40, -30)
        painter.drawText(r.left(), r.top() - 8, label)

    def _draw_sheet_placements(self, painter: QPainter, plane, mapper: CanvasMapper, text_color: QColor) -> None:
        if not plane.auto_sheet_placements and not plane.manual_sheet_placements:
            return

        is_light = self.palette().color(QPalette.ColorRole.Base).lightness() > 128
        auto_color = QColor("#6aa7ff" if is_light else "#8dc7ff")
        manual_color = QColor("#ff9d7a" if is_light else "#ff7a5c")
        auto_color.setAlpha(120)
        manual_color.setAlpha(140)

        all_sheets = list(plane.auto_sheet_placements) + list(plane.manual_sheet_placements)
        for sheet in all_sheets:
            color = manual_color if sheet.source == "manual" else auto_color
            rect = mapper.map_rect(sheet.x_left_cm, sheet.x_right_cm, sheet.y_top_cm, sheet.y_bottom_cm)
            painter.setPen(QPen(color.darker(150), 1))
            painter.setBrush(color)
            painter.drawRect(rect)

            # Module lines for modular materials
            if self._material and self._material.module_length_cm > 0:
                mod_len_px = mapper.map_length(self._material.module_length_cm)
                if mod_len_px > 4:
                    mod_pen = QPen(text_color)
                    mod_pen.setStyle(Qt.PenStyle.DotLine)
                    mod_pen.setWidthF(0.5)
                    painter.setPen(mod_pen)
                    y_start = rect.y()
                    y_end = rect.y() + rect.height()
                    x_left = rect.x()
                    x_right = rect.x() + rect.width()
                    mod_y = y_start + mod_len_px
                    while mod_y < y_end - 1:
                        painter.drawLine(QPointF(x_left, mod_y), QPointF(x_right, mod_y))
                        mod_y += mod_len_px

            # Label
            if self._show_module_count and self._material and self._material.module_length_cm > 0:
                modules = max(1, int(round(sheet.final_length_cm / self._material.module_length_cm)))
                label_text = f"{modules}"
            else:
                label_text = f"{sheet.final_length_cm:.0f}"
            painter.setPen(text_color)
            font = painter.font()
            font.setPointSize(max(7, int(min(rect.width(), rect.height()) / 8)))
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label_text)
            font.setPointSize(font.pointSize() + 2)
            painter.setFont(font)

    def _draw_selected_sheet_highlight(self, painter: QPainter) -> None:
        if self.roof_plane is None or self._selected_sheet_id is None:
            return
        mapper = self._canvas_mapper()
        if mapper is None:
            return
        all_sheets = list(self.roof_plane.auto_sheet_placements) + list(self.roof_plane.manual_sheet_placements)
        for sheet in all_sheets:
            if sheet.id == self._selected_sheet_id:
                rect = mapper.map_rect(sheet.x_left_cm, sheet.x_right_cm, sheet.y_top_cm, sheet.y_bottom_cm)
                painter.setPen(QPen(QColor("#ff3333"), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(rect.adjusted(-2, -2, 2, 2))
                break
