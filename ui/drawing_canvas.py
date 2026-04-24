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

from math import hypot

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPalette, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from core.canvas_mapper import CanvasMapper
from core.geometry import point_in_polygon, polygon_edges, replace_polygon_point, segment_length, validate_polygon
from core.models import Point2D, Polygon2D

SNAP_RADIUS = 10
VERTEX_HANDLE_RADIUS = 6
MIDPOINT_HANDLE_RADIUS = 4
EDGE_LABEL_OFFSET_PX = 14.0


class DrawingCanvas(QWidget):
    """Interactive canvas for displaying and drawing roof planes."""

    MODE_VIEW = "view"
    MODE_DRAW_OUTLINE = "draw_outline"
    MODE_SELECT_SHEET = "select_sheet"

    polygon_closed = Signal(list)
    outline_edit_committed = Signal(object)
    outline_edit_rejected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.user_points: list[QPointF] = []
        self.preview_point: QPointF | None = None
        self._snap_active: bool = False

        self.roof_plane = None
        self._material = None

        self._mode: str = self.MODE_VIEW
        self._selected_sheet_id: str | None = None
        self._show_grid: bool = False
        self._show_module_count: bool = False

        self._plane_selected: bool = False
        self._active_vertex_index: int | None = None
        self._active_edge_index: int | None = None
        self._dragging_vertex_index: int | None = None
        self._drag_start_outline: Polygon2D | None = None
        self._preview_outline: Polygon2D | None = None
        self._drag_mapper: CanvasMapper | None = None

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
        self._cancel_outline_drag()
        if mode == self.MODE_DRAW_OUTLINE:
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif mode == self.MODE_SELECT_SHEET:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def set_roof_plane(self, roof_plane) -> None:
        self.roof_plane = roof_plane
        self._cancel_outline_drag()
        self._plane_selected = bool(roof_plane is not None and roof_plane.outline is not None)
        self._active_vertex_index = None
        self._active_edge_index = None
        self.update()

    def set_material(self, material) -> None:
        self._material = material
        self.update()

    def display_outline(self) -> Polygon2D | None:
        if self._preview_outline is not None:
            return self._preview_outline
        if self.roof_plane is None:
            return None
        return self.roof_plane.outline

    def edge_lengths_cm(self) -> list[float]:
        outline = self.display_outline()
        if outline is None:
            return []
        return [segment_length(start, end) for start, end in polygon_edges(outline)]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _canvas_mapper(self) -> CanvasMapper | None:
        outline = self.display_outline()
        if outline is None:
            return None
        if self._drag_mapper is not None:
            return self._drag_mapper
        return CanvasMapper(outline.bounds(), QRectF(self.rect()))

    def _hit_test_sheet(self, pos: QPointF) -> str | None:
        mapper = self._canvas_mapper()
        if mapper is None or self.roof_plane is None:
            return None
        for sheet in self.roof_plane.manual_sheet_placements + self.roof_plane.auto_sheet_placements:
            rect = mapper.map_rect(sheet.x_left_cm, sheet.x_right_cm, sheet.y_top_cm, sheet.y_bottom_cm)
            if rect.contains(pos.x(), pos.y()):
                return sheet.id
        return None

    def _is_near_first_vertex(self, pos: QPointF) -> bool:
        if len(self.user_points) < 3:
            return False
        first = self.user_points[0]
        dx = pos.x() - first.x()
        dy = pos.y() - first.y()
        return (dx * dx + dy * dy) <= SNAP_RADIUS * SNAP_RADIUS

    def _close_polygon(self) -> None:
        if len(self.user_points) < 3:
            return
        self.polygon_closed.emit(list(self.user_points))
        self.user_points.clear()
        self.preview_point = None
        self._snap_active = False
        self.update()

    def _outline_handle_points(self, mapper: CanvasMapper, outline: Polygon2D) -> list[QPointF]:
        return [mapper.map_point(point) for point in outline.points]

    def _edge_midpoints(self, mapper: CanvasMapper, outline: Polygon2D) -> list[QPointF]:
        handles: list[QPointF] = []
        for start, end in polygon_edges(outline):
            start_point = mapper.map_point(start)
            end_point = mapper.map_point(end)
            handles.append(QPointF((start_point.x() + end_point.x()) / 2.0, (start_point.y() + end_point.y()) / 2.0))
        return handles

    def _hit_test_vertex(self, pos: QPointF, mapper: CanvasMapper, outline: Polygon2D) -> int | None:
        for index, vertex in enumerate(self._outline_handle_points(mapper, outline)):
            if self._distance(pos, vertex) <= VERTEX_HANDLE_RADIUS + 2:
                return index
        return None

    def _hit_test_edge_midpoint(self, pos: QPointF, mapper: CanvasMapper, outline: Polygon2D) -> int | None:
        for index, midpoint in enumerate(self._edge_midpoints(mapper, outline)):
            if self._distance(pos, midpoint) <= MIDPOINT_HANDLE_RADIUS + 2:
                return index
        return None

    def _start_outline_drag(self, vertex_index: int, mapper: CanvasMapper, outline: Polygon2D) -> None:
        self._plane_selected = True
        self._active_vertex_index = vertex_index
        self._active_edge_index = None
        self._dragging_vertex_index = vertex_index
        self._drag_start_outline = outline
        self._preview_outline = outline
        self._drag_mapper = mapper
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _update_outline_drag(self, pos: QPointF) -> None:
        if self._dragging_vertex_index is None or self._drag_start_outline is None or self._drag_mapper is None:
            return
        domain_point = self._drag_mapper.unmap_point(pos)
        self._preview_outline = replace_polygon_point(self._drag_start_outline, self._dragging_vertex_index, domain_point)
        self.update()

    def _commit_outline_drag(self) -> None:
        if self._dragging_vertex_index is None or self._preview_outline is None:
            self._cancel_outline_drag()
            return
        issues = validate_polygon(self._preview_outline)
        if issues:
            self.outline_edit_rejected.emit("; ".join(issues))
            self._preview_outline = self._drag_start_outline
            self._cancel_outline_drag()
            self.update()
            return
        committed_outline = self._preview_outline
        self._cancel_outline_drag()
        self.outline_edit_committed.emit(committed_outline)

    def _cancel_outline_drag(self) -> None:
        self._dragging_vertex_index = None
        self._drag_start_outline = None
        self._preview_outline = None
        self._drag_mapper = None
        if self._mode == self.MODE_VIEW:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _select_plane_at(self, pos: QPointF, outline: Polygon2D, mapper: CanvasMapper) -> None:
        domain_point = mapper.unmap_point(pos)
        self._plane_selected = point_in_polygon(domain_point, outline)
        if not self._plane_selected:
            self._active_vertex_index = None
            self._active_edge_index = None

    @staticmethod
    def _distance(left: QPointF, right: QPointF) -> float:
        return hypot(left.x() - right.x(), left.y() - right.y())

    @staticmethod
    def _format_length(length_cm: float) -> str:
        if abs(length_cm - round(length_cm)) < 0.05:
            return f"{round(length_cm):.0f} cm"
        return f"{length_cm:.1f} cm"

    # ------------------------------------------------------------------
    # Qt event overrides
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position()

        if event.button() == Qt.MouseButton.LeftButton:
            if self._mode == self.MODE_DRAW_OUTLINE:
                if self._snap_active:
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

            if self._mode == self.MODE_VIEW:
                outline = self.display_outline()
                mapper = self._canvas_mapper()
                if outline is not None and mapper is not None:
                    vertex_index = self._hit_test_vertex(pos, mapper, outline)
                    if vertex_index is not None:
                        self._start_outline_drag(vertex_index, mapper, outline)
                        self.update()
                        return

                    self._select_plane_at(pos, outline, mapper)
                    if self._plane_selected:
                        self._active_edge_index = self._hit_test_edge_midpoint(pos, mapper, outline)
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
        elif self._mode == self.MODE_VIEW and self._dragging_vertex_index is not None:
            self._update_outline_drag(event.position())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._mode == self.MODE_VIEW and event.button() == Qt.MouseButton.LeftButton and self._dragging_vertex_index is not None:
            self._commit_outline_drag()
            return
        super().mouseReleaseEvent(event)

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
        elif self._mode == self.MODE_VIEW and event.key() == Qt.Key.Key_Escape and self._dragging_vertex_index is not None:
            self._cancel_outline_drag()
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

        if self.roof_plane is not None and self.display_outline() is not None:
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

        if self.preview_point is not None:
            painter.drawLine(self.user_points[-1], self.preview_point)

        if len(self.user_points) >= 3 and self.preview_point is not None:
            close_pen = QPen(accent, 1.5, Qt.PenStyle.DashLine)
            painter.setPen(close_pen)
            painter.drawLine(self.preview_point, self.user_points[0])

        painter.setPen(QPen(accent, 1))
        painter.setBrush(accent)
        for index, point in enumerate(self.user_points):
            if index == 0 and self._snap_active:
                snap_color = QColor(accent)
                snap_color.setAlpha(200)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(snap_color, 2))
                painter.drawEllipse(int(point.x()) - SNAP_RADIUS, int(point.y()) - SNAP_RADIUS, SNAP_RADIUS * 2, SNAP_RADIUS * 2)
                painter.setBrush(accent)
                painter.setPen(QPen(accent, 1))
            painter.drawEllipse(int(point.x()) - 3, int(point.y()) - 3, 6, 6)

    def _draw_roof_plane(self, painter: QPainter) -> None:
        plane = self.roof_plane
        outline = self.display_outline()
        mapper = self._canvas_mapper()
        if plane is None or outline is None or mapper is None:
            return

        outline_polygon = QPolygonF([mapper.map_point(point) for point in outline.points])
        fill_color = self.palette().color(QPalette.ColorRole.AlternateBase)
        outline_color = self.palette().color(QPalette.ColorRole.Highlight)
        text_color = self.palette().color(QPalette.ColorRole.Text)
        hole_color = QColor(outline_color)
        hole_color.setAlpha(180)

        invalid_preview = self._preview_outline is not None and bool(validate_polygon(outline))
        if invalid_preview:
            outline_color = QColor("#d44848")
            fill_color = QColor(fill_color)
            fill_color.setAlpha(90)

        painter.setPen(QPen(outline_color, 2))
        painter.setBrush(fill_color)
        painter.drawPolygon(outline_polygon)

        painter.setPen(QPen(hole_color, 1.5, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for hole in plane.holes:
            painter.drawPolygon(QPolygonF([mapper.map_point(point) for point in hole.points]))

        self._draw_edge_measurements(painter, mapper, outline, text_color, outline_color)
        if self._plane_selected:
            self._draw_vertex_handles(painter, mapper, outline, outline_color)
            self._draw_midpoint_handles(painter, mapper, outline, outline_color)

        self._draw_sheet_placements(painter, plane, mapper, text_color)

        painter.setPen(text_color)
        label = f"Połać {plane.name}"
        if plane.selected_material_id:
            label += f" | Blacha: {plane.selected_material_id}"
        r = self.rect().adjusted(40, 30, -40, -30)
        painter.drawText(r.left(), r.top() - 8, label)

    def _draw_vertex_handles(self, painter: QPainter, mapper: CanvasMapper, outline: Polygon2D, outline_color: QColor) -> None:
        painter.setPen(QPen(outline_color, 1))
        for index, point in enumerate(outline.points):
            mapped = mapper.map_point(point)
            is_active = index == self._active_vertex_index
            painter.setBrush(outline_color.lighter(140) if is_active else outline_color)
            radius = VERTEX_HANDLE_RADIUS + (2 if is_active else 0)
            painter.drawEllipse(mapped, radius, radius)

    def _draw_midpoint_handles(self, painter: QPainter, mapper: CanvasMapper, outline: Polygon2D, outline_color: QColor) -> None:
        midpoint_color = QColor(outline_color)
        midpoint_color.setAlpha(170)
        painter.setPen(QPen(midpoint_color, 1))
        for index, midpoint in enumerate(self._edge_midpoints(mapper, outline)):
            is_active = index == self._active_edge_index
            painter.setBrush(midpoint_color.lighter(140) if is_active else self.palette().color(QPalette.ColorRole.Base))
            radius = MIDPOINT_HANDLE_RADIUS + (1 if is_active else 0)
            painter.drawEllipse(midpoint, radius, radius)

    def _draw_edge_measurements(
        self,
        painter: QPainter,
        mapper: CanvasMapper,
        outline: Polygon2D,
        text_color: QColor,
        outline_color: QColor,
    ) -> None:
        label_pen = QPen(text_color)
        guide_pen = QPen(outline_color)
        guide_pen.setStyle(Qt.PenStyle.DotLine)
        guide_pen.setWidthF(1.0)
        painter.setFont(painter.font())
        for start, end in polygon_edges(outline):
            start_point = mapper.map_point(start)
            end_point = mapper.map_point(end)
            dx = end_point.x() - start_point.x()
            dy = end_point.y() - start_point.y()
            length_px = hypot(dx, dy)
            if length_px < 1.0:
                continue

            normal_x = -dy / length_px
            normal_y = dx / length_px
            mid_x = (start_point.x() + end_point.x()) / 2.0
            mid_y = (start_point.y() + end_point.y()) / 2.0
            label_anchor = QPointF(mid_x + normal_x * EDGE_LABEL_OFFSET_PX, mid_y + normal_y * EDGE_LABEL_OFFSET_PX)

            painter.setPen(guide_pen)
            painter.drawLine(QPointF(mid_x, mid_y), label_anchor)

            label_rect = QRectF(label_anchor.x() - 30.0, label_anchor.y() - 11.0, 60.0, 22.0)
            background = self.palette().color(QPalette.ColorRole.Base)
            background.setAlpha(220)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(background)
            painter.drawRoundedRect(label_rect, 4.0, 4.0)

            painter.setPen(label_pen)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self._format_length(segment_length(start, end)))

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
