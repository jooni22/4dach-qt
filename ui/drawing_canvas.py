# This Python file uses the following encoding: utf-8
"""DrawingCanvas — the interactive QWidget for roof-plane visualisation and drawing.

Modes
-----
MODE_VIEW          — passive display of the active roof plane
MODE_DRAW_OUTLINE  — click to add vertices; close polygon to create a new roof plane
MODE_DRAW_CUTOUT   — click to add vertices; close polygon to create a cutout inside the plane
MODE_SELECT_SHEET  — click a sheet placement to select/highlight it

Polygon drawing (MODE_DRAW_OUTLINE / MODE_DRAW_CUTOUT)
------------------------------------------------------
* Left-click adds a vertex.
* When the cursor is within SNAP_RADIUS pixels of the *first* vertex (and ≥ 3
  vertices have been placed) the canvas shows a snap indicator and the cursor
  changes to a crosshair — clicking there closes the polygon.
* Pressing Enter also closes the polygon when ≥ 3 vertices are present.
* Right-click / Escape clears the in-progress sketch.
* The controller receives the closed polygon and decides whether it becomes a
  new roof plane outline or a cutout inside the active plane.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFontMetricsF, QKeyEvent, QMouseEvent, QPainter, QPainterPath, QPalette, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from core.canvas_mapper import CanvasMapper
from core.geometry import point_in_polygon, polygon_edges, replace_polygon_point, segment_length, validate_hole_polygon, validate_polygon
from core.models import Point2D, Polygon2D

SNAP_RADIUS = 10
VERTEX_HANDLE_RADIUS = 6
MIDPOINT_HANDLE_RADIUS = 4
EDGE_LABEL_OFFSET_PX = 14.0
LAYOUT_LABEL_PADDING_X = 6.0
LAYOUT_LABEL_PADDING_Y = 3.0
LAYOUT_LABEL_MIN_WIDTH = 36.0
LAYOUT_LABEL_MIN_HEIGHT = 18.0


@dataclass(slots=True)
class _SheetRenderItem:
    placement_id: str
    source: str
    band_index: int
    polygons: list[Polygon2D]
    raw_length_cm: float
    final_length_cm: float
    split_reason: str | None = None


class DrawingCanvas(QWidget):
    """Interactive canvas for displaying and drawing roof planes."""

    MODE_VIEW = "view"
    MODE_DRAW_OUTLINE = "draw_outline"
    MODE_DRAW_CUTOUT = "draw_cutout"
    MODE_SELECT_SHEET = "select_sheet"

    polygon_closed = Signal(list)
    cutout_closed = Signal(list)
    outline_edit_committed = Signal(object)
    hole_edit_committed = Signal(int, object)
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
        self._selected_hole_index: int | None = None
        self._active_vertex_index: int | None = None
        self._active_edge_index: int | None = None
        self._active_hole_vertex_index: int | None = None
        self._dragging_vertex_index: int | None = None
        self._dragging_hole_index: int | None = None
        self._drag_start_outline: Polygon2D | None = None
        self._drag_start_hole: Polygon2D | None = None
        self._preview_outline: Polygon2D | None = None
        self._preview_hole: Polygon2D | None = None
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
        self._cancel_geometry_drag()
        if mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif mode == self.MODE_SELECT_SHEET:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def set_roof_plane(self, roof_plane) -> None:
        self.roof_plane = roof_plane
        self._cancel_geometry_drag()
        self._reset_selection(select_plane=bool(roof_plane is not None and roof_plane.outline is not None))
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

    def display_holes(self) -> list[Polygon2D]:
        if self.roof_plane is None:
            return []
        holes = list(self.roof_plane.holes)
        if self._preview_hole is not None and self._dragging_hole_index is not None:
            holes[self._dragging_hole_index] = self._preview_hole
        return holes

    def selected_cutout_index(self) -> int | None:
        return self._selected_hole_index

    def selected_geometry_kind(self) -> str | None:
        if self._selected_hole_index is not None and self._active_hole_vertex_index is not None:
            return "cutout_vertex"
        if self._selected_hole_index is not None:
            return "cutout_polygon"
        if self._plane_selected and self._active_vertex_index is not None:
            return "main_polygon_vertex"
        if self._plane_selected:
            return "main_polygon"
        return None

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

    def _visible_sheet_placements(self) -> list:
        if self.roof_plane is None:
            return []
        removed_ids = set(self.roof_plane.manually_removed_auto_sheet_ids)
        placements = [sheet for sheet in self.roof_plane.auto_sheet_placements if sheet.id not in removed_ids]
        placements.extend(self.roof_plane.manual_sheet_placements)
        return sorted(placements, key=lambda sheet: (sheet.source != "auto", sheet.band_index, sheet.y_top_cm, sheet.id))

    def _sheet_render_items(self) -> list[_SheetRenderItem]:
        if self.roof_plane is None:
            return []

        visible_placements = self._visible_sheet_placements()
        placements_by_id = {placement.id: placement for placement in visible_placements}
        render_items: list[_SheetRenderItem] = []
        seen_ids: set[str] = set()

        for band in self.roof_plane.layout_bands:
            for segment in band.get("segments", []):
                placement_id = segment.get("placement_id")
                if not placement_id:
                    continue
                placement = placements_by_id.get(placement_id)
                if placement is None:
                    continue
                coverage_polygons = [self._placement_polygon(placement)]
                render_items.append(
                    _SheetRenderItem(
                        placement_id=placement.id,
                        source=placement.source,
                        band_index=placement.band_index,
                        polygons=coverage_polygons,
                        raw_length_cm=placement.raw_length_cm,
                        final_length_cm=placement.final_length_cm,
                        split_reason=placement.split_reason,
                    )
                )
                seen_ids.add(placement.id)

        for placement in visible_placements:
            if placement.id in seen_ids:
                continue
            render_items.append(
                _SheetRenderItem(
                    placement_id=placement.id,
                    source=placement.source,
                    band_index=placement.band_index,
                    polygons=[self._placement_polygon(placement)],
                    raw_length_cm=placement.raw_length_cm,
                    final_length_cm=placement.final_length_cm,
                    split_reason=placement.split_reason,
                )
            )

        return sorted(render_items, key=lambda item: (item.source != "auto", item.band_index, item.placement_id))

    def _placement_polygon(self, placement) -> Polygon2D:
        return Polygon2D(
            [
                Point2D(placement.x_left_cm, placement.y_top_cm),
                Point2D(placement.x_right_cm, placement.y_top_cm),
                Point2D(placement.x_right_cm, placement.y_bottom_cm),
                Point2D(placement.x_left_cm, placement.y_bottom_cm),
            ]
        )

    def _hit_test_sheet(self, pos: QPointF) -> str | None:
        mapper = self._canvas_mapper()
        if mapper is None or self.roof_plane is None:
            return None
        for sheet in self._visible_sheet_placements():
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
        points = list(self.user_points)
        self.user_points.clear()
        self.preview_point = None
        self._snap_active = False
        if self._mode == self.MODE_DRAW_CUTOUT:
            self.cutout_closed.emit(points)
        else:
            self.polygon_closed.emit(points)
        self.update()

    def _polygon_handle_points(self, mapper: CanvasMapper, polygon: Polygon2D) -> list[QPointF]:
        return [mapper.map_point(point) for point in polygon.points]

    def _edge_midpoints(self, mapper: CanvasMapper, polygon: Polygon2D) -> list[QPointF]:
        handles: list[QPointF] = []
        for start, end in polygon_edges(polygon):
            start_point = mapper.map_point(start)
            end_point = mapper.map_point(end)
            handles.append(QPointF((start_point.x() + end_point.x()) / 2.0, (start_point.y() + end_point.y()) / 2.0))
        return handles

    def _hit_test_vertex(self, pos: QPointF, mapper: CanvasMapper, polygon: Polygon2D) -> int | None:
        for index, vertex in enumerate(self._polygon_handle_points(mapper, polygon)):
            if self._distance(pos, vertex) <= VERTEX_HANDLE_RADIUS + 2:
                return index
        return None

    def _hit_test_edge_midpoint(self, pos: QPointF, mapper: CanvasMapper, outline: Polygon2D) -> int | None:
        for index, midpoint in enumerate(self._edge_midpoints(mapper, outline)):
            if self._distance(pos, midpoint) <= MIDPOINT_HANDLE_RADIUS + 2:
                return index
        return None

    def _start_outline_drag(self, vertex_index: int, mapper: CanvasMapper, outline: Polygon2D) -> None:
        self._reset_selection(select_plane=True)
        self._active_vertex_index = vertex_index
        self._dragging_vertex_index = vertex_index
        self._dragging_hole_index = None
        self._drag_start_outline = outline
        self._drag_start_hole = None
        self._preview_outline = outline
        self._preview_hole = None
        self._drag_mapper = mapper
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _start_hole_drag(self, hole_index: int, vertex_index: int, mapper: CanvasMapper, hole: Polygon2D) -> None:
        self._reset_selection()
        self._selected_hole_index = hole_index
        self._active_hole_vertex_index = vertex_index
        self._dragging_vertex_index = vertex_index
        self._dragging_hole_index = hole_index
        self._drag_start_outline = None
        self._drag_start_hole = hole
        self._preview_outline = None
        self._preview_hole = hole
        self._drag_mapper = mapper
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _update_geometry_drag(self, pos: QPointF) -> None:
        if self._dragging_vertex_index is None or self._drag_mapper is None:
            return
        domain_point = self._drag_mapper.unmap_point(pos)
        if self._drag_start_outline is not None:
            self._preview_outline = replace_polygon_point(self._drag_start_outline, self._dragging_vertex_index, domain_point)
        elif self._drag_start_hole is not None:
            self._preview_hole = replace_polygon_point(self._drag_start_hole, self._dragging_vertex_index, domain_point)
        self.update()

    def _commit_geometry_drag(self) -> None:
        if self._dragging_vertex_index is None:
            self._cancel_geometry_drag()
            return

        if self._preview_hole is not None and self._dragging_hole_index is not None and self.roof_plane is not None:
            outline = self.display_outline()
            issues = validate_polygon(self._preview_hole)
            if outline is not None and not issues:
                sibling_holes = [
                    hole for index, hole in enumerate(self.display_holes()) if index != self._dragging_hole_index
                ]
                issues = validate_hole_polygon(outline, self._preview_hole, sibling_holes)
            if issues:
                self.outline_edit_rejected.emit("; ".join(issues))
                self._cancel_geometry_drag()
                self.update()
                return
            hole_index = self._dragging_hole_index
            committed_hole = self._preview_hole
            self._cancel_geometry_drag()
            self.hole_edit_committed.emit(hole_index, committed_hole)
            return

        if self._preview_outline is None:
            self._cancel_geometry_drag()
            return

        issues = validate_polygon(self._preview_outline)
        if issues:
            self.outline_edit_rejected.emit("; ".join(issues))
            self._cancel_geometry_drag()
            self.update()
            return
        committed_outline = self._preview_outline
        self._cancel_geometry_drag()
        self.outline_edit_committed.emit(committed_outline)

    def _cancel_geometry_drag(self) -> None:
        self._dragging_vertex_index = None
        self._dragging_hole_index = None
        self._drag_start_outline = None
        self._drag_start_hole = None
        self._preview_outline = None
        self._preview_hole = None
        self._drag_mapper = None
        if self._mode == self.MODE_VIEW:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _select_plane_at(self, pos: QPointF, outline: Polygon2D, mapper: CanvasMapper) -> None:
        domain_point = mapper.unmap_point(pos)
        self._reset_selection(select_plane=point_in_polygon(domain_point, outline))
        if self._plane_selected:
            self._active_edge_index = self._hit_test_edge_midpoint(pos, mapper, outline)

    def _select_hole_at(self, pos: QPointF, mapper: CanvasMapper) -> bool:
        domain_point = mapper.unmap_point(pos)
        for hole_index, hole in enumerate(self.display_holes()):
            if point_in_polygon(domain_point, hole):
                self._reset_selection()
                self._selected_hole_index = hole_index
                return True
        return False

    def _hit_test_hole_vertex(self, pos: QPointF, mapper: CanvasMapper) -> tuple[int, int] | None:
        for hole_index, hole in enumerate(self.display_holes()):
            vertex_index = self._hit_test_vertex(pos, mapper, hole)
            if vertex_index is not None:
                return hole_index, vertex_index
        return None

    def _reset_selection(self, *, select_plane: bool = False) -> None:
        self._plane_selected = select_plane
        self._selected_hole_index = None
        self._active_vertex_index = None
        self._active_edge_index = None
        self._active_hole_vertex_index = None

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
            if self._mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
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
                    hole_vertex = self._hit_test_hole_vertex(pos, mapper)
                    if hole_vertex is not None:
                        hole_index, vertex_index = hole_vertex
                        self._start_hole_drag(hole_index, vertex_index, mapper, self.display_holes()[hole_index])
                        self.update()
                        return

                    vertex_index = self._hit_test_vertex(pos, mapper, outline)
                    if vertex_index is not None:
                        self._start_outline_drag(vertex_index, mapper, outline)
                        self.update()
                        return

                    if self._select_hole_at(pos, mapper):
                        self.update()
                        return

                    self._select_plane_at(pos, outline, mapper)
                    self.update()
                    return

        if event.button() == Qt.MouseButton.RightButton:
            if self._mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
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
        if self._mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
            pos = event.position()
            self.preview_point = pos
            near = self._is_near_first_vertex(pos)
            if near != self._snap_active:
                self._snap_active = near
                cursor = Qt.CursorShape.PointingHandCursor if near else Qt.CursorShape.CrossCursor
                self.setCursor(cursor)
            self.update()
        elif self._mode == self.MODE_VIEW and self._dragging_vertex_index is not None:
            self._update_geometry_drag(event.position())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._mode == self.MODE_VIEW and event.button() == Qt.MouseButton.LeftButton and self._dragging_vertex_index is not None:
            self._commit_geometry_drag()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        if self._mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
            self.preview_point = None
            self._snap_active = False
            self.update()
        super().leaveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
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
            self._cancel_geometry_drag()
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

        if self._mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
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
        holes = self.display_holes()
        mapper = self._canvas_mapper()
        if plane is None or outline is None or mapper is None:
            return

        outline_polygon = QPolygonF([mapper.map_point(point) for point in outline.points])
        fill_color = self.palette().color(QPalette.ColorRole.AlternateBase)
        outline_color = self.palette().color(QPalette.ColorRole.Highlight)
        text_color = self.palette().color(QPalette.ColorRole.Text)
        background_color = self.palette().color(QPalette.ColorRole.Base)
        hole_color = QColor(outline_color)
        hole_color.setAlpha(180)
        selected_hole_color = QColor("#d44848")

        invalid_preview = self._preview_outline is not None and bool(validate_polygon(outline))
        if invalid_preview:
            outline_color = QColor("#d44848")
            fill_color = QColor(fill_color)
            fill_color.setAlpha(90)

        painter.setPen(QPen(outline_color, 2))
        painter.setBrush(fill_color)
        painter.drawPolygon(outline_polygon)

        self._draw_sheet_placements(painter, plane, mapper, text_color)

        painter.setPen(QPen(hole_color, 1.5, Qt.PenStyle.DashLine))
        for hole_index, hole in enumerate(holes):
            hole_polygon = QPolygonF([mapper.map_point(point) for point in hole.points])
            painter.setBrush(background_color)
            painter.drawPolygon(hole_polygon)
            if hole_index == self._selected_hole_index:
                painter.setPen(QPen(selected_hole_color, 2.0, Qt.PenStyle.DashLine))
            else:
                painter.setPen(QPen(hole_color, 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolygon(hole_polygon)

        self._draw_edge_measurements(painter, mapper, outline, text_color, outline_color)
        if self._plane_selected:
            self._draw_vertex_handles(
                painter,
                mapper,
                outline,
                outline_color,
                active_vertex_index=self._active_vertex_index,
            )
            self._draw_midpoint_handles(painter, mapper, outline, outline_color)
        if self._selected_hole_index is not None and self._selected_hole_index < len(holes):
            self._draw_vertex_handles(
                painter,
                mapper,
                holes[self._selected_hole_index],
                selected_hole_color,
                active_vertex_index=self._active_hole_vertex_index,
            )

        painter.setPen(text_color)
        label = f"Połać {plane.name}"
        if plane.selected_material_id:
            label += f" | Blacha: {plane.selected_material_id}"
            
        if plane.generation_settings.layout_origin == "right":
            label += " | Układ: <--- od prawej"
        else:
            label += " | Układ: od lewej --->"
            
        r = self.rect().adjusted(40, 30, -40, -30)
        painter.drawText(r.left(), r.top() - 8, label)

    def _draw_vertex_handles(
        self,
        painter: QPainter,
        mapper: CanvasMapper,
        polygon: Polygon2D,
        outline_color: QColor,
        *,
        active_vertex_index: int | None = None,
    ) -> None:
        painter.setPen(QPen(outline_color, 1))
        for index, point in enumerate(polygon.points):
            mapped = mapper.map_point(point)
            is_active = index == active_vertex_index
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
        render_items = self._sheet_render_items()
        if not render_items:
            return

        is_light = self.palette().color(QPalette.ColorRole.Base).lightness() > 128
        auto_color = QColor("#6aa7ff" if is_light else "#8dc7ff")
        manual_color = QColor("#ff9d7a" if is_light else "#ff7a5c")
        auto_color.setAlpha(120)
        manual_color.setAlpha(140)
        split_color = QColor("#d44848")
        split_color.setAlpha(180)
        module_length_cm = self._material.module_length_cm if self._material is not None else None

        for item in render_items:
            fill_color = manual_color if item.source == "manual" else auto_color
            outline_color = split_color if item.split_reason else fill_color.darker(150)
            mapped_polygons = [QPolygonF([mapper.map_point(point) for point in polygon.points]) for polygon in item.polygons]

            painter.setPen(QPen(outline_color, 1.2))
            painter.setBrush(fill_color)
            for mapped_polygon in mapped_polygons:
                painter.drawPolygon(mapped_polygon)

            if module_length_cm and module_length_cm > 0:
                self._draw_module_guides(painter, mapped_polygons, mapper, module_length_cm, text_color)

            self._draw_sheet_label(painter, mapped_polygons, item, text_color)

        # Hint has been moved to the main label

    def _draw_module_guides(
        self,
        painter: QPainter,
        mapped_polygons: list[QPolygonF],
        mapper: CanvasMapper,
        module_length_cm: float,
        text_color: QColor,
    ) -> None:
        mod_len_px = mapper.map_length(module_length_cm)
        if mod_len_px <= 4:
            return

        guide_path = QPainterPath()
        bounds = QRectF()
        for polygon in mapped_polygons:
            polygon_path = QPainterPath()
            polygon_path.addPolygon(polygon)
            guide_path = guide_path.united(polygon_path)
            bounds = bounds.united(polygon.boundingRect()) if not bounds.isNull() else polygon.boundingRect()

        mod_pen = QPen(text_color)
        mod_pen.setStyle(Qt.PenStyle.DotLine)
        mod_pen.setWidthF(0.5)
        painter.save()
        painter.setClipPath(guide_path)
        painter.setPen(mod_pen)
        mod_y = bounds.top() + mod_len_px
        while mod_y < bounds.bottom() - 1:
            painter.drawLine(QPointF(bounds.left(), mod_y), QPointF(bounds.right(), mod_y))
            mod_y += mod_len_px
        painter.restore()

    def _draw_sheet_label(
        self,
        painter: QPainter,
        mapped_polygons: list[QPolygonF],
        item: _SheetRenderItem,
        text_color: QColor,
    ) -> None:
        label_text = self._sheet_label_text(item)
        anchor_rect = self._label_anchor_rect(mapped_polygons)
        if anchor_rect.width() <= 1 or anchor_rect.height() <= 1:
            return

        font = painter.font()
        font.setPointSize(self._layout_label_font_size(anchor_rect))
        painter.setFont(font)
        metrics = QFontMetricsF(font)
        text_width = metrics.horizontalAdvance(label_text)
        text_height = metrics.height()
        label_width = max(LAYOUT_LABEL_MIN_WIDTH, text_width + LAYOUT_LABEL_PADDING_X * 2.0)
        label_height = max(LAYOUT_LABEL_MIN_HEIGHT, text_height + LAYOUT_LABEL_PADDING_Y * 2.0)
        label_rect = QRectF(
            anchor_rect.center().x() - label_width / 2.0,
            anchor_rect.center().y() - label_height / 2.0,
            label_width,
            label_height,
        )

        if label_rect.width() > anchor_rect.width() and anchor_rect.width() > label_rect.height() + 8.0:
            label_rect.moveLeft(anchor_rect.left() + (anchor_rect.width() - label_rect.width()) / 2.0)
        label_rect = label_rect.intersected(self.rect().adjusted(6, 6, -6, -6))
        if label_rect.width() <= 1 or label_rect.height() <= 1:
            return

        background = self.palette().color(QPalette.ColorRole.Base)
        background.setAlpha(220)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(label_rect, 4.0, 4.0)
        painter.setPen(text_color)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label_text)

    def _sheet_label_text(self, item: _SheetRenderItem) -> str:
        module_length_cm = self._material.module_length_cm if self._material is not None else None
        if self._show_module_count and module_length_cm and module_length_cm > 0:
            modules = max(1, int(round(item.final_length_cm / module_length_cm)))
            return f"{modules}"
        return f"{item.final_length_cm:.0f} cm"

    def _label_anchor_rect(self, mapped_polygons: list[QPolygonF]) -> QRectF:
        polygon_bounds = [polygon.boundingRect() for polygon in mapped_polygons]
        largest = max(polygon_bounds, key=lambda rect: rect.width() * rect.height())
        if largest.width() >= LAYOUT_LABEL_MIN_WIDTH and largest.height() >= LAYOUT_LABEL_MIN_HEIGHT:
            return largest.adjusted(4.0, 4.0, -4.0, -4.0)

        union_rect = polygon_bounds[0]
        for rect in polygon_bounds[1:]:
            union_rect = union_rect.united(rect)
        return union_rect.adjusted(2.0, 2.0, -2.0, -2.0)

    def _layout_label_font_size(self, anchor_rect: QRectF) -> int:
        min_dimension = min(anchor_rect.width(), anchor_rect.height())
        if min_dimension < 24:
            return 7
        if min_dimension < 34:
            return 8
        if min_dimension < 48:
            return 9
        return 10

    def _draw_selected_sheet_highlight(self, painter: QPainter) -> None:
        if self.roof_plane is None or self._selected_sheet_id is None:
            return
        mapper = self._canvas_mapper()
        if mapper is None:
            return
        all_sheets = self._visible_sheet_placements()
        for sheet in all_sheets:
            if sheet.id == self._selected_sheet_id:
                rect = mapper.map_rect(sheet.x_left_cm, sheet.x_right_cm, sheet.y_top_cm, sheet.y_bottom_cm)
                painter.setPen(QPen(QColor("#ff3333"), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(rect.adjusted(-2, -2, 2, 2))
                break
