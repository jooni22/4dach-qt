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
* Right-click closes the polygon when enabled; Escape clears the in-progress
  sketch.
* The controller receives the closed polygon and decides whether it becomes a
  new roof plane outline or a cutout inside the active plane.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from math import ceil, floor, hypot

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QKeyEvent, QMouseEvent, QPainter, QPainterPath, QPalette, QPen, QPolygonF
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QWidget

from core.app_settings import (
    AppSettings,
    SHIFT_DRAG_BEHAVIOR_FREE_MOVE,
    SHIFT_DRAG_BEHAVIOR_ORTHOGONAL_LOCK,
)
from core.canvas_mapper import CanvasMapper
from core.geometry import (
    insert_polygon_point,
    point_in_polygon,
    polygon_edges,
    replace_polygon_point,
    segment_length,
    validate_hole_polygon,
    validate_polygon,
)
from core.models import Bounds2D, Point2D, Polygon2D

SNAP_RADIUS = 10
VERTEX_HANDLE_RADIUS = 6
MIDPOINT_HANDLE_RADIUS = 4
EDGE_LABEL_OFFSET_PX = 14.0
LAYOUT_LABEL_PADDING_X = 6.0
LAYOUT_LABEL_PADDING_Y = 3.0
LAYOUT_LABEL_MIN_WIDTH = 36.0
LAYOUT_LABEL_MIN_HEIGHT = 18.0
VIEW_MARGIN_X_PX = 80.0
VIEW_MARGIN_Y_PX = 36.0
AXIS_WIDGET_LENGTH_PX = 42.0
AXIS_WIDGET_PADDING_PX = 18.0
AXIS_WIDGET_ARROW_SIZE_PX = 6.0
FREE_DRAW_DOMAIN_SIZE_CM = 1000.0
GRID_MINOR_MIN_SPACING_PX = 8.0
GRID_MAJOR_MIN_SPACING_PX = 5.0
CROSSHAIR_LENGTH_PX = 28.0
CROSSHAIR_DEAD_ZONE_PX = 1.0
RUBBER_BAND_LABEL_PADDING_X = 8.0
RUBBER_BAND_LABEL_PADDING_Y = 4.0
ANGLE_ARC_RADIUS_PX = 20.0
INLINE_EDITOR_OFFSET_X = 16.0
INLINE_EDITOR_OFFSET_Y = 14.0
INLINE_EDITOR_MARGIN_PX = 8.0

LIVE_ANGLE_MODE_ABSOLUTE = "absolute"
LIVE_ANGLE_MODE_RELATIVE_TO_PREV = "relative_to_prev"


class _InlineSegmentEditor(QFrame):
    """Minimal local widget for length/angle entry while freehand drawing."""

    def __init__(self, canvas: "DrawingCanvas") -> None:
        super().__init__(canvas)
        self._canvas = canvas
        self.setObjectName("inline_segment_editor")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAutoFillBackground(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        self._length_label = QLabel("L")
        self._length_edit = QLineEdit(self)
        self._length_edit.setObjectName("inline_length_edit")
        self._length_edit.setPlaceholderText("cm")
        self._length_edit.setFixedWidth(72)

        self._angle_label = QLabel("A")
        self._angle_edit = QLineEdit(self)
        self._angle_edit.setObjectName("inline_angle_edit")
        self._angle_edit.setPlaceholderText("deg")
        self._angle_edit.setFixedWidth(72)

        layout.addWidget(self._length_label)
        layout.addWidget(self._length_edit)
        layout.addWidget(self._angle_label)
        layout.addWidget(self._angle_edit)

        for widget in (self._length_edit, self._angle_edit):
            widget.installEventFilter(self)

        self.hide()

    @property
    def length_edit(self) -> QLineEdit:
        return self._length_edit

    @property
    def angle_edit(self) -> QLineEdit:
        return self._angle_edit

    def show_for_point(self, point: QPointF, *, length_text: str, angle_text: str, active_field: str) -> None:
        self._length_edit.setText(length_text)
        self._angle_edit.setText(angle_text)
        self.adjustSize()
        self._reposition(point)
        self.show()
        self.raise_()
        self._active_edit(active_field).setFocus(Qt.FocusReason.OtherFocusReason)
        self._active_edit(active_field).selectAll()

    def update_contents(self, *, length_text: str, angle_text: str, active_field: str) -> None:
        self._length_edit.setText(length_text)
        self._angle_edit.setText(angle_text)
        active_edit = self._active_edit(active_field)
        active_edit.setFocus(Qt.FocusReason.OtherFocusReason)
        active_edit.selectAll()

    def move_for_point(self, point: QPointF) -> None:
        if self.isHidden():
            return
        self.adjustSize()
        self._reposition(point)

    def hide_and_release_focus(self) -> None:
        self.hide()
        self._canvas.setFocus(Qt.FocusReason.OtherFocusReason)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            key_event = event
            if key_event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._canvas._confirm_inline_segment_editor()
                return True
            if key_event.key() == Qt.Key.Key_Tab:
                self._canvas._advance_inline_segment_editor_field()
                return True
            if key_event.key() == Qt.Key.Key_Backtab:
                self._canvas._advance_inline_segment_editor_field(reverse=True)
                return True
            if key_event.key() == Qt.Key.Key_Escape:
                self._canvas._cancel_inline_segment_editor()
                return True
        return super().eventFilter(watched, event)

    def _active_edit(self, field_name: str) -> QLineEdit:
        return self._angle_edit if field_name == "angle" else self._length_edit

    def _reposition(self, point: QPointF) -> None:
        viewport = self._canvas.rect().adjusted(
            INLINE_EDITOR_MARGIN_PX,
            INLINE_EDITOR_MARGIN_PX,
            -INLINE_EDITOR_MARGIN_PX,
            -INLINE_EDITOR_MARGIN_PX,
        )
        x = point.x() + INLINE_EDITOR_OFFSET_X
        y = point.y() + INLINE_EDITOR_OFFSET_Y
        width = float(self.width())
        height = float(self.height())
        x = min(max(x, viewport.left()), max(viewport.left(), viewport.right() - width))
        y = min(max(y, viewport.top()), max(viewport.top(), viewport.bottom() - height))
        self.move(int(round(x)), int(round(y)))


@dataclass(slots=True)
class _SheetRenderItem:
    placement_id: str
    source: str
    band_index: int
    polygons: list[Polygon2D]
    raw_length_cm: float
    final_length_cm: float
    split_reason: str | None = None


@dataclass(slots=True)
class _EditOverlayState:
    mode: str
    target_kind: str
    domain_point: Point2D
    hole_index: int | None = None
    vertex_index: int | None = None
    edge_index: int | None = None


@dataclass(slots=True)
class _CoordinateOverlayLabel:
    kind: str
    domain_point: Point2D


@dataclass(slots=True, frozen=True)
class _GridContext:
    mapper: CanvasMapper
    bounds: Bounds2D
    origin: Point2D


@dataclass(slots=True, frozen=True)
class _SelectionSnapshot:
    kind: str | None
    hole_index: int | None = None
    vertex_index: int | None = None


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
    origin_edit_committed = Signal(object)
    outline_edit_rejected = Signal(str)
    selection_changed = Signal(bool)
    delete_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.user_points: list[QPointF] = []
        self.preview_point: QPointF | None = None
        self._last_mouse_point: QPointF | None = None
        self._crosshair_point: QPointF | None = None
        self._crosshair_axis: str | None = None
        self._snap_active: bool = False

        self.roof_plane = None
        self._material = None
        self._app_settings = AppSettings()

        self._mode: str = self.MODE_VIEW
        self._selected_sheet_id: str | None = None
        self._show_grid: bool = True
        self._show_module_count: bool = False
        self._show_sheet_placements: bool = True
        self._snap_to_grid_enabled: bool = True
        self._segment_input_active: bool = False
        self._segment_input_length_text: str = ""
        self._segment_input_angle_text: str = ""
        self._segment_input_active_field: str = "length"
        self._segment_input_anchor_point: QPointF | None = None

        self._plane_selected: bool = False
        self._selected_hole_index: int | None = None
        self._active_vertex_index: int | None = None
        self._active_edge_index: int | None = None
        self._active_hole_vertex_index: int | None = None
        self._dragging_vertex_index: int | None = None
        self._dragging_hole_index: int | None = None
        self._dragging_hole_center_index: int | None = None
        self._drag_start_outline: Polygon2D | None = None
        self._drag_start_hole: Polygon2D | None = None
        self._drag_start_pos: Point2D | None = None
        self._preview_outline: Polygon2D | None = None
        self._preview_hole: Polygon2D | None = None
        self._drag_mapper: CanvasMapper | None = None
        self._edit_overlay: _EditOverlayState | None = None
        self._origin_edit_enabled: bool = False
        self._dragging_origin: bool = False
        self._origin_drag_reference_point: Point2D | None = None
        self._preview_origin_point: Point2D | None = None
        self._last_emitted_selection_state: bool = False
        self._caret_visible: bool = True
        self._caret_timer = QTimer(self)
        self._caret_timer.setInterval(500)
        self._caret_timer.timeout.connect(self._toggle_caret)
        self._caret_timer.start()
        self._inline_segment_editor = _InlineSegmentEditor(self)

        self._render_items_cache: list | None = None
        self._render_items_cache_revision: int = -1

        self.setMouseTracking(True)
        self.setAutoFillBackground(True)
        self.setMinimumSize(640, 420)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _check_selection_changed(self) -> None:
        current_state = self._plane_selected or self._selected_hole_index is not None
        if current_state != self._last_emitted_selection_state:
            self._last_emitted_selection_state = current_state
            self.selection_changed.emit(current_state)

    def toggle_grid(self, enabled: bool | None = None) -> None:
        self._show_grid = not self._show_grid if enabled is None else enabled
        self.update()

    def toggle_module_count(self, enabled: bool | None = None) -> None:
        self._show_module_count = not self._show_module_count if enabled is None else enabled
        self.update()

    def set_sheet_visibility(self, visible: bool) -> None:
        if self._show_sheet_placements == visible:
            return
        self._show_sheet_placements = visible
        if not visible:
            self._selected_sheet_id = None
        self._render_items_cache = None
        self._render_items_cache_revision = -1
        self.update()

    def set_snap_to_grid_enabled(self, enabled: bool) -> None:
        if self._snap_to_grid_enabled == enabled:
            return
        self._snap_to_grid_enabled = enabled
        self.update()

    def snap_to_grid_enabled(self) -> bool:
        return self._snap_to_grid_enabled

    def set_app_settings(self, settings: AppSettings | None) -> None:
        self._app_settings = settings or AppSettings()
        self.update()

    def set_origin_edit_enabled(self, enabled: bool) -> None:
        self._origin_edit_enabled = enabled
        if not enabled:
            self._dragging_origin = False
            self._origin_drag_reference_point = None
            self._preview_origin_point = None
        if self._mode == self.MODE_VIEW:
            self._sync_view_cursor()
        self.update()

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self.user_points.clear()
        self.preview_point = None
        self._last_mouse_point = None
        self._crosshair_point = None
        self._crosshair_axis = None
        self._snap_active = False
        self._cancel_inline_segment_editor()
        self._cancel_geometry_drag()
        if mode != self.MODE_VIEW:
            self._reset_selection()
            self._clear_edit_overlay()
            self._check_selection_changed()
        if mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif mode == self.MODE_SELECT_SHEET:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self._sync_view_cursor()
        self.update()

    def set_roof_plane(self, roof_plane) -> None:
        self.roof_plane = roof_plane
        self._cancel_geometry_drag()
        self._reset_selection(select_plane=bool(roof_plane is not None and roof_plane.outline is not None))
        self._origin_drag_reference_point = None
        self._preview_origin_point = None
        self._check_selection_changed()
        self._sync_view_cursor()
        self._render_items_cache = None
        self._render_items_cache_revision = -1
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

    def selection_snapshot(self) -> _SelectionSnapshot:
        return _SelectionSnapshot(
            kind=self.selected_geometry_kind(),
            hole_index=self._selected_hole_index,
            vertex_index=self._active_hole_vertex_index if self._selected_hole_index is not None else self._active_vertex_index,
        )

    def restore_selection(self, snapshot: _SelectionSnapshot | None) -> None:
        self._reset_selection()
        if snapshot is None or snapshot.kind is None:
            self._check_selection_changed()
            self.update()
            return

        outline = self.display_outline()
        holes = self.display_holes()
        if snapshot.kind == "cutout_vertex" and snapshot.hole_index is not None:
            if 0 <= snapshot.hole_index < len(holes):
                self._selected_hole_index = snapshot.hole_index
                if snapshot.vertex_index is not None and 0 <= snapshot.vertex_index < len(holes[snapshot.hole_index].points):
                    self._active_hole_vertex_index = snapshot.vertex_index
        elif snapshot.kind == "cutout_polygon" and snapshot.hole_index is not None:
            if 0 <= snapshot.hole_index < len(holes):
                self._selected_hole_index = snapshot.hole_index
        elif snapshot.kind == "main_polygon_vertex" and outline is not None:
            self._plane_selected = True
            if snapshot.vertex_index is not None and 0 <= snapshot.vertex_index < len(outline.points):
                self._active_vertex_index = snapshot.vertex_index
        elif snapshot.kind == "main_polygon" and outline is not None:
            self._plane_selected = True

        self._check_selection_changed()
        self.update()

    def _sync_view_cursor(self) -> None:
        if self._mode != self.MODE_VIEW:
            return
        if self._dragging_origin:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif self._origin_edit_enabled:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @classmethod
    def build_view_mapper(cls, bounds, canvas_rect: QRectF) -> CanvasMapper:
        return CanvasMapper(bounds, canvas_rect, margin_x=VIEW_MARGIN_X_PX, margin_y=VIEW_MARGIN_Y_PX)

    @classmethod
    def free_draw_bounds_for_rect(cls, canvas_rect: QRectF) -> Bounds2D:
        height = FREE_DRAW_DOMAIN_SIZE_CM
        safe_height = max(canvas_rect.height(), 1.0)
        width = height * max(canvas_rect.width(), 1.0) / safe_height
        return Bounds2D(0.0, 0.0, width, height)

    @classmethod
    def build_free_draw_mapper(cls, canvas_rect: QRectF) -> CanvasMapper:
        return CanvasMapper(cls.free_draw_bounds_for_rect(canvas_rect), canvas_rect, margin=0.0)

    def _canvas_mapper(self) -> CanvasMapper | None:
        outline = self.display_outline()
        if outline is None:
            return None
        if self._drag_mapper is not None:
            return self._drag_mapper
        return self.build_view_mapper(outline.bounds(), QRectF(self.rect()))

    def _active_mapper(self) -> CanvasMapper | None:
        if self._mode == self.MODE_DRAW_OUTLINE:
            return self._free_draw_mapper()
        mapper = self._canvas_mapper()
        if mapper is not None:
            return mapper
        return None

    def _free_draw_mapper(self) -> CanvasMapper:
        return self.build_free_draw_mapper(QRectF(self.rect()))

    def _free_draw_bounds(self) -> Bounds2D:
        return self.free_draw_bounds_for_rect(QRectF(self.rect()))

    def _free_draw_grid_origin(self, mapper: CanvasMapper | None = None) -> Point2D:
        effective_mapper = self._free_draw_mapper() if mapper is None else mapper
        visible_bounds = effective_mapper.bounds
        return Point2D(visible_bounds.min_x, visible_bounds.max_y)

    def _snap_origin_point(self, mapper: CanvasMapper | None = None) -> Point2D:
        if self._mode == self.MODE_DRAW_OUTLINE:
            return self._free_draw_grid_origin(mapper)
        return self._origin_point()

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

        plane_revision = self.roof_plane.layout_revision
        if self._render_items_cache is not None and self._render_items_cache_revision == plane_revision:
            return self._render_items_cache

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
                
                # Fix #5: Use coverage_polygons from layout engine instead of fallback
                coverage_polygons = [
                    Polygon2D([Point2D(p[0], p[1]) for p in poly_pts])
                    for poly_pts in segment.get("coverage_polygons", [])
                    if len(poly_pts) >= 3
                ]
                if not coverage_polygons:
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

        sorted_items = sorted(render_items, key=lambda item: (item.source != "auto", item.band_index, item.placement_id))
        self._render_items_cache = sorted_items
        self._render_items_cache_revision = plane_revision
        return sorted_items

    def _placement_polygon(self, placement) -> Polygon2D:
        visual_top = placement.y_top_cm
        if placement.split_reason == "partial_cutout_top":
            visual_top -= max(0.0, placement.final_length_cm - placement.raw_length_cm)
        return Polygon2D(
            [
                Point2D(placement.x_left_cm, visual_top),
                Point2D(placement.x_right_cm, visual_top),
                Point2D(placement.x_right_cm, placement.y_bottom_cm),
                Point2D(placement.x_left_cm, placement.y_bottom_cm),
            ]
        )

    def _hit_test_sheet(self, pos: QPointF) -> str | None:
        if not self._show_sheet_placements:
            return None
        mapper = self._canvas_mapper()
        if mapper is None or self.roof_plane is None:
            return None
        domain_point = mapper.unmap_point(pos)
        
        # Fix #6: Use coverage polygons from layout engine for accurate hit testing
        for band in self.roof_plane.layout_bands:
            for segment in band.get("segments", []):
                placement_id = segment.get("placement_id")
                if not placement_id:
                    continue
                
                # Get coverage polygons from layout engine
                coverage_polygons = [
                    Polygon2D([Point2D(p[0], p[1]) for p in poly_pts])
                    for poly_pts in segment.get("coverage_polygons", [])
                    if len(poly_pts) >= 3
                ]
                
                # Fallback to placement polygon if no coverage polygons
                if not coverage_polygons:
                    placement = next((p for p in self._visible_sheet_placements() if p.id == placement_id), None)
                    if placement:
                        coverage_polygons = [self._placement_polygon(placement)]
                
                # Check if point is in any coverage polygon
                for polygon in coverage_polygons:
                    if point_in_polygon(domain_point, polygon):
                        return placement_id
        
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
        self._set_edit_overlay("drag", "outline_vertex", outline.points[vertex_index], vertex_index=vertex_index)
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _start_outline_edge_split_drag(self, edge_index: int, mapper: CanvasMapper, outline: Polygon2D) -> None:
        edges = list(polygon_edges(outline))
        if edge_index >= len(edges):
            return
        start, end = edges[edge_index]
        midpoint = Point2D((start.x + end.x) / 2.0, (start.y + end.y) / 2.0)
        split_outline = insert_polygon_point(outline, edge_index, midpoint)
        self._active_edge_index = edge_index
        self._start_outline_drag(edge_index + 1, mapper, split_outline)

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
        self._set_edit_overlay(
            "drag",
            "hole_vertex",
            hole.points[vertex_index],
            hole_index=hole_index,
            vertex_index=vertex_index,
        )
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _start_hole_center_drag(self, hole_index: int, pos: QPointF, mapper: CanvasMapper, hole: Polygon2D) -> None:
        self._reset_selection()
        self._selected_hole_index = hole_index
        self._dragging_hole_center_index = hole_index
        self._dragging_hole_index = hole_index
        self._drag_start_pos = mapper.unmap_point(pos)
        self._drag_start_hole = hole
        self._preview_hole = hole
        self._drag_mapper = mapper
        self._set_edit_overlay("drag", "hole_center", self._hole_center_point(hole), hole_index=hole_index)
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _update_geometry_drag(self, pos: QPointF, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> None:
        if self._drag_mapper is None:
            return
        if self._shift_orthogonal_lock_active(modifiers):
            raw_domain_point = self._drag_mapper.unmap_point(pos)
            domain_point = self._apply_shift_orthogonal_lock(
                raw_domain_point,
                reference_point=self._drag_reference_point(),
            )
        else:
            domain_point = self._pixel_to_domain_point(pos, self._drag_mapper, modifiers=modifiers)
        
        if self._dragging_hole_center_index is not None and self._drag_start_pos is not None:
            if self._drag_start_hole is not None:
                dx = domain_point.x - self._drag_start_pos.x
                dy = domain_point.y - self._drag_start_pos.y
                new_points = [Point2D(p.x + dx, p.y + dy) for p in self._drag_start_hole.points]
                if self._snap_should_apply(modifiers) and not self._shift_orthogonal_lock_active(modifiers):
                    new_points = self._snap_translated_hole_vertices(new_points, modifiers=modifiers)
                self._preview_hole = Polygon2D(new_points)
                self._set_edit_overlay(
                    "drag",
                    "hole_center",
                    self._hole_center_point(self._preview_hole),
                    hole_index=self._dragging_hole_center_index,
                )
            self.update()
            return

        if self._dragging_vertex_index is None:
            return
        
        if self._drag_start_outline is not None:
            self._preview_outline = replace_polygon_point(self._drag_start_outline, self._dragging_vertex_index, domain_point)
            self._set_edit_overlay("drag", "outline_vertex", domain_point, vertex_index=self._dragging_vertex_index)
        elif self._drag_start_hole is not None:
            self._preview_hole = replace_polygon_point(self._drag_start_hole, self._dragging_vertex_index, domain_point)
            self._set_edit_overlay(
                "drag",
                "hole_vertex",
                domain_point,
                hole_index=self._dragging_hole_index,
                vertex_index=self._dragging_vertex_index,
            )
        self.update()

    def _commit_geometry_drag(self) -> None:
        if self._dragging_vertex_index is None and self._dragging_hole_center_index is None:
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
            self.update()
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
        self.update()
        self.outline_edit_committed.emit(committed_outline)

    def _cancel_geometry_drag(self) -> None:
        self._dragging_vertex_index = None
        self._dragging_hole_index = None
        self._dragging_hole_center_index = None
        self._drag_start_pos = None
        self._drag_start_outline = None
        self._drag_start_hole = None
        self._preview_outline = None
        self._preview_hole = None
        self._drag_mapper = None
        self._clear_edit_overlay()
        if self._mode == self.MODE_VIEW:
            self._sync_view_cursor()

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

    def _hit_test_hole_center(self, pos: QPointF, mapper: CanvasMapper) -> int | None:
        for hole_index, hole in enumerate(self.display_holes()):
            bounds = hole.bounds()
            center_x = (bounds.min_x + bounds.max_x) / 2.0
            center_y = (bounds.min_y + bounds.max_y) / 2.0
            mapped_center = mapper.map_point(Point2D(center_x, center_y))
            if self._distance(pos, mapped_center) <= MIDPOINT_HANDLE_RADIUS + 4:
                return hole_index
        return None

    def _hit_test_edge_label(self, pos: QPointF, mapper: CanvasMapper, outline: Polygon2D) -> int | None:
        polygon_f = QPolygonF([mapper.map_point(point) for point in outline.points])
        for index, (start, end) in enumerate(polygon_edges(outline)):
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
            
            test_point = QPointF(mid_x + normal_x * 5.0, mid_y + normal_y * 5.0)
            if polygon_f.containsPoint(test_point, Qt.FillRule.OddEvenFill):
                normal_x = -normal_x
                normal_y = -normal_y

            label_anchor = QPointF(mid_x + normal_x * EDGE_LABEL_OFFSET_PX, mid_y + normal_y * EDGE_LABEL_OFFSET_PX)
            label_rect = QRectF(label_anchor.x() - 30.0, label_anchor.y() - 11.0, 60.0, 22.0)
            if label_rect.contains(pos):
                return index
        return None

    def _prompt_scale_polygon(self, edge_index: int, outline: Polygon2D) -> None:
        from PySide6.QtWidgets import QInputDialog
        edges = list(polygon_edges(outline))
        if edge_index >= len(edges):
            return
        start, end = edges[edge_index]
        current_len = segment_length(start, end)
        new_len, ok = QInputDialog.getDouble(
            self,
            "Zmień długość krawędzi",
            "Nowa długość (cm):",
            current_len,
            0.1,
            10000.0,
            1,
        )
        if ok and new_len > 0 and abs(new_len - current_len) > 0.1:
            scale = new_len / current_len
            anchor = start  # first vertex of the edited edge
            new_points = [
                Point2D(
                    anchor.x + (p.x - anchor.x) * scale,
                    anchor.y + (p.y - anchor.y) * scale,
                )
                for p in outline.points
            ]
            new_outline = Polygon2D(new_points)
            self.outline_edit_committed.emit(new_outline)

    def _set_edit_overlay(
        self,
        mode: str,
        target_kind: str,
        domain_point: Point2D,
        *,
        hole_index: int | None = None,
        vertex_index: int | None = None,
        edge_index: int | None = None,
    ) -> bool:
        overlay = _EditOverlayState(
            mode=mode,
            target_kind=target_kind,
            domain_point=domain_point,
            hole_index=hole_index,
            vertex_index=vertex_index,
            edge_index=edge_index,
        )
        if overlay == self._edit_overlay:
            return False
        self._edit_overlay = overlay
        return True

    def _clear_edit_overlay(self) -> bool:
        if self._edit_overlay is None:
            return False
        self._edit_overlay = None
        return True

    @staticmethod
    def _hole_center_point(hole: Polygon2D) -> Point2D:
        bounds = hole.bounds()
        return Point2D((bounds.min_x + bounds.max_x) / 2.0, (bounds.min_y + bounds.max_y) / 2.0)

    def _default_origin_point(self, outline: Polygon2D) -> Point2D:
        bounds = outline.bounds()
        return Point2D(bounds.min_x, bounds.max_y)

    def _origin_point(self) -> Point2D:
        if self._preview_origin_point is not None:
            return self._preview_origin_point
        outline = self.display_outline()
        if outline is None:
            return self._free_draw_grid_origin()
        if self.roof_plane is not None:
            settings = self.roof_plane.generation_settings
            if settings.origin_x_cm is not None and settings.origin_y_cm is not None:
                return Point2D(settings.origin_x_cm, settings.origin_y_cm)
        return self._default_origin_point(outline)

    def _relative_coordinate_point(self, point: Point2D) -> Point2D:
        origin = self._origin_point()
        return Point2D(point.x - origin.x, origin.y - point.y)

    def _grid_step_cm(self) -> float:
        return max(0.1, self._app_settings.grid_size_cm)

    def _grid_major_step_cm(self) -> float:
        return float(max(1, self._app_settings.grid_major_cm))

    def _grid_minor_step_cm(self) -> float:
        return float(max(1, self._app_settings.grid_minor_cm))

    def _should_draw_minor_grid(self, mapper: CanvasMapper) -> bool:
        return mapper.map_length(self._grid_minor_step_cm()) >= GRID_MINOR_MIN_SPACING_PX

    def _should_draw_major_grid(self, mapper: CanvasMapper) -> bool:
        return mapper.map_length(self._grid_major_step_cm()) >= GRID_MAJOR_MIN_SPACING_PX

    def _effective_grid_step_cm(self, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> float:
        if self._shift_orthogonal_lock_active(modifiers):
            return 1.0
        step_cm = self._grid_step_cm()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            return max(0.1, step_cm / 10.0)
        return step_cm

    def _shift_drag_behavior(self) -> str:
        behavior = self._app_settings.shift_drag_behavior
        if behavior in {SHIFT_DRAG_BEHAVIOR_FREE_MOVE, SHIFT_DRAG_BEHAVIOR_ORTHOGONAL_LOCK}:
            return behavior
        return SHIFT_DRAG_BEHAVIOR_FREE_MOVE

    def _current_modifiers(self) -> Qt.KeyboardModifier:
        return QApplication.keyboardModifiers()

    def _shift_free_move_active(self, modifiers: Qt.KeyboardModifier) -> bool:
        return bool(
            modifiers & Qt.KeyboardModifier.ShiftModifier
            and self._shift_drag_behavior() == SHIFT_DRAG_BEHAVIOR_FREE_MOVE
        )

    def _shift_orthogonal_lock_active(self, modifiers: Qt.KeyboardModifier) -> bool:
        return bool(
            modifiers & Qt.KeyboardModifier.ShiftModifier
            and self._shift_drag_behavior() == SHIFT_DRAG_BEHAVIOR_ORTHOGONAL_LOCK
        )

    def _snap_should_apply(self, modifiers: Qt.KeyboardModifier | None = None) -> bool:
        effective_modifiers = self._current_modifiers() if modifiers is None else modifiers
        if self._shift_orthogonal_lock_active(effective_modifiers):
            return True
        if not self._snap_to_grid_enabled:
            return False
        if self._shift_free_move_active(effective_modifiers):
            return False
        return True

    def _snap_domain_point(
        self,
        point: Point2D,
        *,
        origin: Point2D | None = None,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ) -> Point2D:
        if not self._snap_should_apply(modifiers):
            return point
        step_cm = self._effective_grid_step_cm(modifiers)
        anchor = self._origin_point() if origin is None else origin
        snapped_x = anchor.x + round((point.x - anchor.x) / step_cm) * step_cm
        snapped_y = anchor.y - round((anchor.y - point.y) / step_cm) * step_cm
        return Point2D(snapped_x, snapped_y)

    def _pixel_to_domain_point(
        self,
        pos: QPointF,
        mapper: CanvasMapper,
        *,
        origin: Point2D | None = None,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ) -> Point2D:
        return self._snap_domain_point(
            mapper.unmap_point(pos),
            origin=self._snap_origin_point(mapper) if origin is None else origin,
            modifiers=modifiers,
        )

    def _domain_to_pixel_point(self, point: Point2D, mapper: CanvasMapper) -> QPointF:
        return mapper.map_point(point)

    def _toggle_caret(self) -> None:
        self._caret_visible = not self._caret_visible
        if self._mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT} and self._segment_input_active:
            self.update()

    def _update_crosshair(self, point: QPointF, *, reference: QPointF | None = None) -> None:
        self._crosshair_point = QPointF(point)
        base = reference if reference is not None else self._last_mouse_point
        axis: str | None = None
        if base is not None:
            dx = point.x() - base.x()
            dy = point.y() - base.y()
            if max(abs(dx), abs(dy)) >= CROSSHAIR_DEAD_ZONE_PX:
                axis = "x" if abs(dx) >= abs(dy) else "y"
        self._crosshair_axis = axis
        self._last_mouse_point = QPointF(point)

    def _clear_crosshair(self) -> None:
        self._crosshair_point = None
        self._crosshair_axis = None
        self._last_mouse_point = None

    def _segment_input_point(self) -> QPointF:
        if self.preview_point is not None:
            return QPointF(self.preview_point)
        if self._segment_input_anchor_point is not None:
            return QPointF(self._segment_input_anchor_point)
        if self.user_points:
            return QPointF(self.user_points[-1])
        return QPointF(self.rect().center())

    def _active_preview_domain_point(self) -> Point2D | None:
        mapper = self._active_mapper()
        if mapper is None or self.preview_point is None:
            return None
        return mapper.unmap_point(self.preview_point)

    def _current_segment_start_domain_point(self) -> Point2D | None:
        mapper = self._active_mapper()
        if mapper is None or not self.user_points:
            return None
        return mapper.unmap_point(self.user_points[-1])

    def _previous_segment_start_domain_point(self) -> Point2D | None:
        mapper = self._active_mapper()
        if mapper is None or len(self.user_points) < 2:
            return None
        return mapper.unmap_point(self.user_points[-2])

    def _preview_segment_delta(self) -> tuple[float, float] | None:
        start = self._current_segment_start_domain_point()
        end = self._active_preview_domain_point()
        if start is None or end is None:
            return None
        return end.x - start.x, end.y - start.y

    def _preview_segment_length_cm(self) -> float | None:
        delta = self._preview_segment_delta()
        if delta is None:
            return None
        dx, dy = delta
        return math.hypot(dx, dy)

    def _absolute_angle_degrees_from_delta(self, dx: float, dy: float) -> float:
        return math.degrees(math.atan2(-dy, dx)) % 360.0

    def _previous_segment_absolute_angle_degrees(self) -> float | None:
        previous_start = self._previous_segment_start_domain_point()
        current_start = self._current_segment_start_domain_point()
        if previous_start is None or current_start is None:
            return None
        dx = current_start.x - previous_start.x
        dy = current_start.y - previous_start.y
        if math.hypot(dx, dy) < 1e-6:
            return None
        return self._absolute_angle_degrees_from_delta(dx, dy)

    def _preview_absolute_angle_degrees(self) -> float | None:
        delta = self._preview_segment_delta()
        if delta is None:
            return None
        dx, dy = delta
        if math.hypot(dx, dy) < 1e-6:
            return None
        return self._absolute_angle_degrees_from_delta(dx, dy)

    def _angle_mode(self) -> str:
        mode = getattr(self._app_settings, "live_angle_mode", LIVE_ANGLE_MODE_ABSOLUTE)
        if mode in {LIVE_ANGLE_MODE_ABSOLUTE, LIVE_ANGLE_MODE_RELATIVE_TO_PREV}:
            return mode
        return LIVE_ANGLE_MODE_ABSOLUTE

    def _normalize_signed_angle(self, angle: float) -> float:
        normalized = (angle + 180.0) % 360.0 - 180.0
        if normalized == -180.0:
            return 180.0
        return normalized

    def _display_angle_degrees(self) -> float | None:
        preview_angle = self._preview_absolute_angle_degrees()
        if preview_angle is None:
            return None
        if self._angle_mode() == LIVE_ANGLE_MODE_RELATIVE_TO_PREV:
            previous_angle = self._previous_segment_absolute_angle_degrees()
            if previous_angle is not None:
                return self._normalize_signed_angle(preview_angle - previous_angle)
        return preview_angle

    def _angle_baseline_degrees(self) -> float:
        if self._angle_mode() == LIVE_ANGLE_MODE_RELATIVE_TO_PREV:
            previous_angle = self._previous_segment_absolute_angle_degrees()
            if previous_angle is not None:
                return previous_angle
        return 0.0

    def _format_live_length_label(self, length_cm: float) -> str:
        if getattr(self._app_settings, "show_decimal_cm", False):
            return f"{length_cm:.1f} cm"
        return f"{int(round(length_cm))} cm"

    def _format_live_angle_label(self, angle_deg: float) -> str:
        rounded = int(round(angle_deg))
        return f"{rounded}°"

    def _parse_segment_input_number(self, text: str) -> float | None:
        normalized = text.strip().replace(",", ".")
        if not normalized:
            return None
        try:
            return float(normalized)
        except ValueError:
            return None

    def _build_point_from_length_and_angle(self, length_cm: float, angle_deg: float) -> Point2D | None:
        start = self._current_segment_start_domain_point()
        if start is None:
            return None
        absolute_angle = angle_deg
        if self._angle_mode() == LIVE_ANGLE_MODE_RELATIVE_TO_PREV:
            previous_angle = self._previous_segment_absolute_angle_degrees()
            if previous_angle is not None:
                absolute_angle = previous_angle + angle_deg
        radians = math.radians(absolute_angle)
        dx = math.cos(radians) * length_cm
        dy = -math.sin(radians) * length_cm
        return Point2D(start.x + dx, start.y + dy)

    def _append_user_point_from_domain(self, point: Point2D) -> None:
        mapper = self._active_mapper()
        if mapper is None:
            return
        pixel_point = mapper.map_point(point)
        self.user_points.append(pixel_point)
        self.preview_point = pixel_point
        self._update_crosshair(pixel_point, reference=self.user_points[-2] if len(self.user_points) >= 2 else None)

    def _start_inline_segment_editor(self, initial_text: str) -> None:
        if not self.user_points:
            return
        if not self._segment_input_active:
            self._segment_input_length_text = initial_text
            self._segment_input_angle_text = self._default_segment_input_angle_text()
            self._segment_input_active_field = "length"
            self._segment_input_active = True
        else:
            if self._segment_input_active_field == "angle":
                self._segment_input_angle_text = initial_text
            else:
                self._segment_input_length_text = initial_text
        self._caret_visible = True
        self._segment_input_anchor_point = self._segment_input_point()
        self._inline_segment_editor.show_for_point(
            self._segment_input_anchor_point,
            length_text=self._segment_input_length_text,
            angle_text=self._segment_input_angle_text,
            active_field=self._segment_input_active_field,
        )
        self.update()

    def _default_segment_input_angle_text(self) -> str:
        angle = self._display_angle_degrees()
        if angle is None:
            return "0"
        return str(int(round(angle)))

    def _sync_segment_input_from_editor(self) -> None:
        if self._inline_segment_editor.isHidden():
            return
        self._segment_input_length_text = self._inline_segment_editor.length_edit.text()
        self._segment_input_angle_text = self._inline_segment_editor.angle_edit.text()

    def _advance_inline_segment_editor_field(self, *, reverse: bool = False) -> None:
        if not self._segment_input_active:
            return
        self._sync_segment_input_from_editor()
        if reverse:
            self._segment_input_active_field = "length" if self._segment_input_active_field == "angle" else "angle"
        else:
            self._segment_input_active_field = "angle" if self._segment_input_active_field == "length" else "length"
        self._inline_segment_editor.update_contents(
            length_text=self._segment_input_length_text,
            angle_text=self._segment_input_angle_text,
            active_field=self._segment_input_active_field,
        )

    def _cancel_inline_segment_editor(self) -> None:
        self._segment_input_active = False
        self._segment_input_length_text = ""
        self._segment_input_angle_text = ""
        self._segment_input_active_field = "length"
        self._segment_input_anchor_point = None
        self._inline_segment_editor.hide_and_release_focus()
        self.update()

    def _confirm_inline_segment_editor(self) -> None:
        if not self._segment_input_active:
            return
        self._sync_segment_input_from_editor()
        length_cm = self._parse_segment_input_number(self._segment_input_length_text)
        angle_deg = self._parse_segment_input_number(self._segment_input_angle_text)
        if length_cm is None or angle_deg is None or length_cm <= 0:
            self._cancel_inline_segment_editor()
            return
        new_domain_point = self._build_point_from_length_and_angle(length_cm, angle_deg)
        if new_domain_point is None:
            self._cancel_inline_segment_editor()
            return
        new_domain_point = self._snap_domain_point(new_domain_point)
        self._append_user_point_from_domain(new_domain_point)
        self._cancel_inline_segment_editor()

    def _typed_segment_input_target(self) -> str:
        return "angle" if self._segment_input_active_field == "angle" else "length"

    def _move_inline_segment_editor_if_needed(self) -> None:
        if not self._segment_input_active:
            return
        anchor = self._segment_input_point()
        self._segment_input_anchor_point = anchor
        self._inline_segment_editor.move_for_point(anchor)

    def _drag_reference_point(self) -> Point2D | None:
        if self._dragging_origin:
            return self._origin_drag_reference_point
        if self._dragging_hole_center_index is not None:
            return self._drag_start_pos
        if self._dragging_vertex_index is None:
            return None
        if self._drag_start_outline is not None:
            return self._drag_start_outline.points[self._dragging_vertex_index]
        if self._drag_start_hole is not None:
            return self._drag_start_hole.points[self._dragging_vertex_index]
        return None

    def _apply_shift_orthogonal_lock(self, point: Point2D, *, reference_point: Point2D | None) -> Point2D:
        if reference_point is None:
            return point
        dx = point.x - reference_point.x
        dy = point.y - reference_point.y
        if abs(dx) >= abs(dy):
            return Point2D(reference_point.x + round(dx), reference_point.y)
        return Point2D(reference_point.x, reference_point.y + round(dy))

    def _snap_translated_hole_vertices(
        self,
        translated_points: list[Point2D],
        *,
        modifiers: Qt.KeyboardModifier,
    ) -> list[Point2D]:
        snapped_adjustment: Point2D | None = None
        best_distance: float | None = None
        for point in translated_points:
            snapped_point = self._snap_domain_point(point, modifiers=modifiers)
            adjustment = Point2D(snapped_point.x - point.x, snapped_point.y - point.y)
            distance = hypot(adjustment.x, adjustment.y)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                snapped_adjustment = adjustment
        if snapped_adjustment is None:
            return translated_points
        return [
            Point2D(point.x + snapped_adjustment.x, point.y + snapped_adjustment.y)
            for point in translated_points
        ]

    def _point_on_polygon_boundary(self, point: Point2D, polygon: Polygon2D) -> bool:
        tolerance = 1e-6
        for start, end in polygon_edges(polygon):
            cross = (end.x - start.x) * (point.y - start.y) - (end.y - start.y) * (point.x - start.x)
            if abs(cross) > tolerance:
                continue
            if (
                min(start.x, end.x) - tolerance <= point.x <= max(start.x, end.x) + tolerance
                and min(start.y, end.y) - tolerance <= point.y <= max(start.y, end.y) + tolerance
            ):
                return True
        return False

    def _point_within_plane(self, point: Point2D, outline: Polygon2D) -> bool:
        return point_in_polygon(point, outline) or self._point_on_polygon_boundary(point, outline)

    def _project_point_to_segment(self, point: Point2D, start: Point2D, end: Point2D) -> Point2D:
        dx = end.x - start.x
        dy = end.y - start.y
        length_sq = dx * dx + dy * dy
        if length_sq <= 1e-9:
            return start
        projection = ((point.x - start.x) * dx + (point.y - start.y) * dy) / length_sq
        t = min(1.0, max(0.0, projection))
        return Point2D(start.x + dx * t, start.y + dy * t)

    def _closest_boundary_point(self, point: Point2D, polygon: Polygon2D) -> Point2D:
        closest_point: Point2D | None = None
        closest_distance_sq: float | None = None
        for start, end in polygon_edges(polygon):
            candidate = self._project_point_to_segment(point, start, end)
            distance_sq = (candidate.x - point.x) ** 2 + (candidate.y - point.y) ** 2
            if closest_distance_sq is None or distance_sq < closest_distance_sq:
                closest_point = candidate
                closest_distance_sq = distance_sq
        return closest_point if closest_point is not None else point

    def _hit_test_origin_handle(self, pos: QPointF, mapper: CanvasMapper) -> bool:
        mapped_origin = mapper.map_point(self._origin_point())
        return self._distance(pos, mapped_origin) <= MIDPOINT_HANDLE_RADIUS + 6

    def _start_origin_drag(self, mapper: CanvasMapper) -> None:
        self._drag_mapper = mapper
        self._dragging_origin = True
        self._origin_drag_reference_point = self._origin_point()
        self._preview_origin_point = self._origin_drag_reference_point
        self._sync_view_cursor()
        self.update()

    def _update_origin_drag(self, pos: QPointF) -> None:
        outline = self.display_outline()
        if self._drag_mapper is None or outline is None:
            return
        base_origin = self._default_origin_point(outline)
        if self.roof_plane is not None:
            settings = self.roof_plane.generation_settings
            if settings.origin_x_cm is not None and settings.origin_y_cm is not None:
                base_origin = Point2D(settings.origin_x_cm, settings.origin_y_cm)
        raw_domain_point = self._drag_mapper.unmap_point(pos)
        modifiers = self._current_modifiers()
        if self._shift_orthogonal_lock_active(modifiers):
            domain_point = self._apply_shift_orthogonal_lock(raw_domain_point, reference_point=base_origin)
        else:
            domain_point = self._snap_domain_point(
                raw_domain_point,
                origin=base_origin,
                modifiers=modifiers,
            )
        if not self._point_within_plane(domain_point, outline):
            domain_point = self._closest_boundary_point(domain_point, outline)
        self._preview_origin_point = domain_point
        self.update()

    def _commit_origin_drag(self) -> None:
        if not self._dragging_origin:
            return
        committed_origin = self._origin_point()
        self._dragging_origin = False
        self._drag_mapper = None
        self._origin_drag_reference_point = None
        self._preview_origin_point = None
        self._sync_view_cursor()
        self.update()
        self.origin_edit_committed.emit(committed_origin)

    def _cancel_origin_drag(self) -> None:
        self._dragging_origin = False
        self._drag_mapper = None
        self._origin_drag_reference_point = None
        self._preview_origin_point = None
        self._sync_view_cursor()
        self.update()

    def _update_edit_overlay_hover(self, pos: QPointF) -> None:
        outline = self.display_outline()
        mapper = self._canvas_mapper()
        if outline is None or mapper is None:
            self._active_edge_index = None
            if self._clear_edit_overlay():
                self.update()
            return

        hole_center_index = self._hit_test_hole_center(pos, mapper)
        if hole_center_index is not None:
            if self._set_edit_overlay(
                "hover",
                "hole_center",
                self._hole_center_point(self.display_holes()[hole_center_index]),
                hole_index=hole_center_index,
            ):
                self.update()
            return

        hole_vertex = self._hit_test_hole_vertex(pos, mapper)
        if hole_vertex is not None:
            hole_index, vertex_index = hole_vertex
            if self._set_edit_overlay(
                "hover",
                "hole_vertex",
                self.display_holes()[hole_index].points[vertex_index],
                hole_index=hole_index,
                vertex_index=vertex_index,
            ):
                self.update()
            return

        vertex_index = self._hit_test_vertex(pos, mapper, outline)
        if vertex_index is not None:
            self._active_edge_index = None
            if self._set_edit_overlay(
                "hover",
                "outline_vertex",
                outline.points[vertex_index],
                vertex_index=vertex_index,
            ):
                self.update()
            return

        edge_index = self._hit_test_edge_midpoint(pos, mapper, outline)
        if edge_index is not None:
            if self._active_edge_index != edge_index:
                self._active_edge_index = edge_index
                self.update()
            if self._clear_edit_overlay():
                self.update()
            return

        edge_changed = self._active_edge_index is not None
        self._active_edge_index = None
        if self._clear_edit_overlay():
            self.update()
        elif edge_changed:
            self.update()

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
            return f"{round(length_cm):.0f}"
        return f"{length_cm:.1f}"

    @staticmethod
    def _format_coordinate_value(value_cm: float) -> str:
        return f"{value_cm:.1f}"

    def _coordinate_label_text(self, point: Point2D) -> str:
        relative_point = self._relative_coordinate_point(point)
        return f"X: {self._format_coordinate_value(relative_point.x)} | Y: {self._format_coordinate_value(relative_point.y)}"

    def _origin_drag_label_text(self) -> str:
        current_origin = self._origin_point()
        reference_origin = self._origin_drag_reference_point or current_origin
        relative_point = Point2D(
            current_origin.x - reference_origin.x,
            reference_origin.y - current_origin.y,
        )
        return f"X: {self._format_coordinate_value(relative_point.x)} | Y: {self._format_coordinate_value(relative_point.y)}"

    def _grid_visible(self) -> bool:
        return self._show_grid or self._dragging_origin or self._mode == self.MODE_DRAW_OUTLINE

    def _grid_context(self) -> _GridContext | None:
        mapper = self._active_mapper()
        if mapper is None:
            return None
        outline = self.display_outline()
        if outline is None or self._mode == self.MODE_DRAW_OUTLINE:
            bounds = self._free_draw_bounds()
        else:
            bounds = self._grid_bounds_for_current_paint(mapper)
        return _GridContext(mapper=mapper, bounds=bounds, origin=self._snap_origin_point(mapper))

    def _coordinate_overlay_labels(self) -> list[_CoordinateOverlayLabel]:
        if self._edit_overlay is None:
            return []

        labels = [_CoordinateOverlayLabel("active", self._edit_overlay.domain_point)]
        if (
            self._edit_overlay.mode == "drag"
            and self._edit_overlay.target_kind == "hole_center"
            and self._preview_hole is not None
        ):
            labels.extend(_CoordinateOverlayLabel("vertex", point) for point in self._preview_hole.points)
        return labels

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
                    mapper = self._active_mapper()
                    if mapper is None:
                        return
                    domain_point = self._pixel_to_domain_point(pos, mapper, modifiers=event.modifiers())
                    self.user_points.append(self._domain_to_pixel_point(domain_point, mapper))
                    self._update_crosshair(self.user_points[-1])
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
                    if self._origin_edit_enabled:
                        self._clear_edit_overlay()
                        if self._hit_test_origin_handle(pos, mapper):
                            self._start_origin_drag(mapper)
                            return
                        return

                    self._clear_edit_overlay()
                    hole_center_index = self._hit_test_hole_center(pos, mapper)
                    if hole_center_index is not None:
                        self._start_hole_center_drag(hole_center_index, pos, mapper, self.display_holes()[hole_center_index])
                        self._check_selection_changed()
                        self.update()
                        return

                    hole_vertex = self._hit_test_hole_vertex(pos, mapper)
                    if hole_vertex is not None:
                        hole_index, vertex_index = hole_vertex
                        self._start_hole_drag(hole_index, vertex_index, mapper, self.display_holes()[hole_index])
                        self._check_selection_changed()
                        self.update()
                        return

                    vertex_index = self._hit_test_vertex(pos, mapper, outline)
                    if vertex_index is not None:
                        self._start_outline_drag(vertex_index, mapper, outline)
                        self._check_selection_changed()
                        self.update()
                        return

                    edge_index = self._hit_test_edge_midpoint(pos, mapper, outline)
                    if edge_index is not None:
                        self._start_outline_edge_split_drag(edge_index, mapper, outline)
                        self._check_selection_changed()
                        self.update()
                        return

                    edge_label_index = self._hit_test_edge_label(pos, mapper, outline)
                    if edge_label_index is not None:
                        self._prompt_scale_polygon(edge_label_index, outline)
                        return

                    if self._select_hole_at(pos, mapper):
                        self._check_selection_changed()
                        self.update()
                        return

                    self._select_plane_at(pos, outline, mapper)
                    self._check_selection_changed()
                    self.update()
                    return

        if event.button() == Qt.MouseButton.RightButton:
            if self._mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
                if getattr(self._app_settings, "close_on_rmb", True) and len(self.user_points) >= 3:
                    self._close_polygon()
                    return
                self.user_points.clear()
                self.preview_point = None
                self._snap_active = False
                self._clear_crosshair()
                self._cancel_inline_segment_editor()
                self.update()
                return
            if self._mode == self.MODE_SELECT_SHEET:
                self._selected_sheet_id = None
                self.update()
                return
            if self._mode == self.MODE_VIEW:
                self._reset_selection()
                self._clear_edit_overlay()
                self._check_selection_changed()
                self.update()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
            pos = event.position()
            mapper = self._active_mapper()
            if mapper is not None:
                domain_point = self._pixel_to_domain_point(pos, mapper, modifiers=event.modifiers())
                pos = self._domain_to_pixel_point(domain_point, mapper)
            self.preview_point = pos
            reference = self.user_points[-1] if self.user_points else None
            self._update_crosshair(pos, reference=reference)
            self._move_inline_segment_editor_if_needed()
            near = self._is_near_first_vertex(pos)
            if near != self._snap_active:
                self._snap_active = near
                cursor = Qt.CursorShape.PointingHandCursor if near else Qt.CursorShape.CrossCursor
                self.setCursor(cursor)
            self.update()
        elif self._mode == self.MODE_VIEW and self._dragging_origin:
            self._update_crosshair(event.position())
            self._update_origin_drag(event.position())
            return
        elif self._mode == self.MODE_VIEW and (self._dragging_vertex_index is not None or self._dragging_hole_center_index is not None):
            reference = None
            if self._drag_mapper is not None:
                drag_reference = self._drag_reference_point()
                if drag_reference is not None:
                    reference = self._drag_mapper.map_point(drag_reference)
            self._update_crosshair(event.position(), reference=reference)
            self._update_geometry_drag(event.position(), event.modifiers())
            return
        elif self._mode == self.MODE_VIEW and not self._origin_edit_enabled:
            self._update_crosshair(event.position())
            self._update_edit_overlay_hover(event.position())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._mode == self.MODE_VIEW and event.button() == Qt.MouseButton.LeftButton and self._dragging_origin:
            self._commit_origin_drag()
            return
        if self._mode == self.MODE_VIEW and event.button() == Qt.MouseButton.LeftButton and (self._dragging_vertex_index is not None or self._dragging_hole_center_index is not None):
            self._commit_geometry_drag()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        if self._mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
            self.preview_point = None
            self._snap_active = False
            self._clear_crosshair()
            self._move_inline_segment_editor_if_needed()
            self.update()
        elif self._mode == self.MODE_VIEW and self._clear_edit_overlay():
            self.update()
        super().leaveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
            key = event.key()
            text = event.text()

            if self.user_points and text and (text.isdigit() or text in (".", ",")):
                self._start_inline_segment_editor(text)
                return

            if self._segment_input_active and key == Qt.Key.Key_Tab:
                self._advance_inline_segment_editor_field()
                return

            if self._segment_input_active and key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._confirm_inline_segment_editor()
                return

            if key == Qt.Key.Key_Escape:
                if self._segment_input_active:
                    self._cancel_inline_segment_editor()
                    return
                self.user_points.clear()
                self.preview_point = None
                self._snap_active = False
                self._clear_crosshair()
                self._cancel_inline_segment_editor()
                self.update()
                return
        elif self._mode == self.MODE_VIEW:
            if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                if self._plane_selected or self._selected_hole_index is not None:
                    self.delete_requested.emit()
                    return
            if event.key() == Qt.Key.Key_Escape and self._dragging_origin:
                self._cancel_origin_drag()
                return
            if event.key() == Qt.Key.Key_Escape and (self._dragging_vertex_index is not None or self._dragging_hole_center_index is not None):
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
            if self._dragging_origin:
                self._draw_roof_plane(painter)
                if self._grid_visible():
                    self._draw_grid(painter)
            else:
                if self._grid_visible():
                    self._draw_grid(painter)
                self._draw_roof_plane(painter)
        else:
            if self._grid_visible():
                self._draw_grid(painter)
            self._draw_empty_state(painter)

        if self._mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
            self._draw_user_path(painter)

        if self._selected_sheet_id and self._mode == self.MODE_SELECT_SHEET:
            self._draw_selected_sheet_highlight(painter)

        mapper = self._canvas_mapper()
        if mapper is not None:
            self._draw_origin_marker(painter, mapper)

        self._draw_freehand_axis_overlay(painter)
        self._draw_crosshair(painter)

    def _draw_grid(self, painter: QPainter) -> None:
        grid_context = self._grid_context()
        if grid_context is not None:
            self._draw_domain_grid(painter, grid_context)
            return

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
            rubber_band_color = QColor(accent)
            rubber_band_color.setAlpha(200)
            painter.setPen(QPen(rubber_band_color, 1.7, Qt.PenStyle.DashLine))
            painter.drawLine(self.user_points[-1], self.preview_point)
            self._draw_live_segment_feedback(painter)

        if len(self.user_points) >= 3 and self.preview_point is not None:
            close_pen = QPen(accent, 1.5, Qt.PenStyle.DashLine)
            painter.setPen(close_pen)
            painter.drawLine(self.preview_point, self.user_points[0])
            self._draw_close_hint(painter)

        painter.setPen(QPen(accent, 1))
        painter.setBrush(accent)
        for index, point in enumerate(self.user_points):
            if index == 0:
                self._draw_start_point_marker(painter, point)
            if index == 0 and self._snap_active:
                snap_color = QColor(accent)
                snap_color.setAlpha(200)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(snap_color, 2))
                painter.drawEllipse(int(point.x()) - SNAP_RADIUS, int(point.y()) - SNAP_RADIUS, SNAP_RADIUS * 2, SNAP_RADIUS * 2)
                painter.setBrush(accent)
                painter.setPen(QPen(accent, 1))
            painter.drawEllipse(int(point.x()) - 3, int(point.y()) - 3, 6, 6)

    def _draw_start_point_marker(self, painter: QPainter, point: QPointF) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QColor(255, 224, 80, 230))
        painter.setPen(QPen(QColor(20, 20, 20, 220), 1.4))
        painter.drawEllipse(point, 6.0, 6.0)
        painter.setPen(QPen(QColor(20, 20, 20, 220), 1.0))
        painter.drawLine(QPointF(point.x() - 8.0, point.y()), QPointF(point.x() + 8.0, point.y()))
        painter.drawLine(QPointF(point.x(), point.y() - 8.0), QPointF(point.x(), point.y() + 8.0))
        painter.restore()

    def _draw_live_segment_feedback(self, painter: QPainter) -> None:
        mapper = self._active_mapper()
        if mapper is None or self.preview_point is None or not self.user_points:
            return
        length_cm = self._preview_segment_length_cm()
        angle_deg = self._display_angle_degrees()
        if length_cm is None or angle_deg is None:
            return

        self._draw_live_length_label(painter, self.user_points[-1], self.preview_point, self._format_live_length_label(length_cm))
        self._draw_live_angle_feedback(painter, mapper, angle_deg)

    def _draw_live_length_label(self, painter: QPainter, start_point: QPointF, end_point: QPointF, label_text: str) -> None:
        font = painter.font()
        font.setPointSize(9)
        painter.save()
        painter.setFont(font)
        metrics = QFontMetricsF(font)
        label_width = metrics.horizontalAdvance(label_text) + RUBBER_BAND_LABEL_PADDING_X * 2.0
        label_height = metrics.height() + RUBBER_BAND_LABEL_PADDING_Y * 2.0
        mid_x = (start_point.x() + end_point.x()) / 2.0
        mid_y = (start_point.y() + end_point.y()) / 2.0
        label_rect = QRectF(mid_x - label_width / 2.0, mid_y - label_height - 8.0, label_width, label_height)
        viewport = self.rect().adjusted(6, 6, -6, -6)
        if label_rect.right() > viewport.right():
            label_rect.moveRight(viewport.right())
        if label_rect.left() < viewport.left():
            label_rect.moveLeft(viewport.left())
        if label_rect.top() < viewport.top():
            label_rect.moveTop(mid_y + 8.0)
        if label_rect.bottom() > viewport.bottom():
            label_rect.moveBottom(viewport.bottom())
        painter.setPen(QPen(QColor(255, 255, 255, 120), 0.8))
        painter.setBrush(QColor(18, 18, 18, 210))
        painter.drawRoundedRect(label_rect, 5.0, 5.0)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label_text)
        painter.restore()

    def _draw_live_angle_feedback(self, painter: QPainter, mapper: CanvasMapper, angle_deg: float) -> None:
        if not getattr(self._app_settings, "show_angle_arc", True):
            return
        vertex_domain = self._current_segment_start_domain_point()
        preview_angle = self._preview_absolute_angle_degrees()
        if vertex_domain is None or preview_angle is None:
            return
        vertex_point = mapper.map_point(vertex_domain)
        baseline_angle = self._angle_baseline_degrees()
        if getattr(self._app_settings, "show_guide_lines", True):
            self._draw_live_angle_guides(painter, mapper, vertex_point, baseline_angle)

        signed_display_angle = angle_deg if self._angle_mode() == LIVE_ANGLE_MODE_RELATIVE_TO_PREV else self._normalize_signed_angle(preview_angle)
        start_angle_qt = -baseline_angle * 16.0
        span_angle_qt = -signed_display_angle * 16.0
        arc_rect = QRectF(
            vertex_point.x() - ANGLE_ARC_RADIUS_PX,
            vertex_point.y() - ANGLE_ARC_RADIUS_PX,
            ANGLE_ARC_RADIUS_PX * 2.0,
            ANGLE_ARC_RADIUS_PX * 2.0,
        )
        arc_color = QColor(84, 210, 111, 230)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(arc_color, 2.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(arc_rect, int(round(start_angle_qt)), int(round(span_angle_qt)))
        label_angle = baseline_angle + signed_display_angle
        radians = math.radians(label_angle)
        label_point = QPointF(
            vertex_point.x() + math.cos(radians) * (ANGLE_ARC_RADIUS_PX + 14.0),
            vertex_point.y() - math.sin(radians) * (ANGLE_ARC_RADIUS_PX + 14.0),
        )
        self._draw_live_angle_label(painter, label_point, self._format_live_angle_label(angle_deg), arc_color)
        painter.restore()

    def _draw_live_angle_guides(self, painter: QPainter, mapper: CanvasMapper, vertex_point: QPointF, baseline_angle: float) -> None:
        guide_color = self.palette().color(QPalette.ColorRole.Highlight)
        guide_color.setAlpha(85)
        painter.save()
        painter.setPen(QPen(guide_color, 1.0, Qt.PenStyle.DotLine))
        painter.drawLine(QPointF(self.rect().left(), vertex_point.y()), QPointF(self.rect().right(), vertex_point.y()))
        painter.drawLine(QPointF(vertex_point.x(), self.rect().top()), QPointF(vertex_point.x(), self.rect().bottom()))
        if len(self.user_points) >= 2:
            radians = math.radians(baseline_angle)
            direction_x = math.cos(radians)
            direction_y = -math.sin(radians)
            span = max(self.width(), self.height())
            painter.drawLine(
                QPointF(vertex_point.x() - direction_x * span, vertex_point.y() - direction_y * span),
                QPointF(vertex_point.x() + direction_x * span, vertex_point.y() + direction_y * span),
            )
        painter.restore()

    def _draw_live_angle_label(self, painter: QPainter, anchor_point: QPointF, label_text: str, label_color: QColor) -> None:
        font = painter.font()
        font.setPointSize(8)
        painter.save()
        painter.setFont(font)
        metrics = QFontMetricsF(font)
        label_rect = QRectF(
            anchor_point.x() - (metrics.horizontalAdvance(label_text) + 12.0) / 2.0,
            anchor_point.y() - (metrics.height() + 6.0) / 2.0,
            metrics.horizontalAdvance(label_text) + 12.0,
            metrics.height() + 6.0,
        )
        viewport = self.rect().adjusted(6, 6, -6, -6)
        if label_rect.right() > viewport.right():
            label_rect.moveRight(viewport.right())
        if label_rect.left() < viewport.left():
            label_rect.moveLeft(viewport.left())
        if label_rect.top() < viewport.top():
            label_rect.moveTop(viewport.top())
        if label_rect.bottom() > viewport.bottom():
            label_rect.moveBottom(viewport.bottom())
        painter.setPen(QPen(label_color, 0.8))
        painter.setBrush(QColor(18, 18, 18, 200))
        painter.drawRoundedRect(label_rect, 4.0, 4.0)
        painter.setPen(label_color)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label_text)
        painter.restore()

    def _draw_close_hint(self, painter: QPainter) -> None:
        hint_text = "RMB to close"
        font = painter.font()
        font.setPointSize(8)
        painter.save()
        painter.setFont(font)
        metrics = QFontMetricsF(font)
        anchor = self.user_points[0]
        label_rect = QRectF(
            anchor.x() + 12.0,
            anchor.y() - metrics.height() - 10.0,
            metrics.horizontalAdvance(hint_text) + 12.0,
            metrics.height() + 6.0,
        )
        viewport = self.rect().adjusted(6, 6, -6, -6)
        if label_rect.right() > viewport.right():
            label_rect.moveRight(viewport.right())
        if label_rect.left() < viewport.left():
            label_rect.moveLeft(viewport.left())
        if label_rect.top() < viewport.top():
            label_rect.moveTop(anchor.y() + 12.0)
        painter.setPen(QPen(QColor(255, 255, 255, 110), 0.8))
        painter.setBrush(QColor(18, 18, 18, 180))
        painter.drawRoundedRect(label_rect, 4.0, 4.0)
        painter.setPen(QColor(255, 255, 255, 225))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, hint_text)
        painter.restore()

    def _edit_overlay_grid_step_cm(self, mapper: CanvasMapper) -> float:
        return self._grid_step_cm()

    def _canvas_domain_bounds(self, mapper: CanvasMapper) -> Bounds2D:
        corners = (
            mapper.unmap_point(QPointF(self.rect().left(), self.rect().top())),
            mapper.unmap_point(QPointF(self.rect().right(), self.rect().top())),
            mapper.unmap_point(QPointF(self.rect().left(), self.rect().bottom())),
            mapper.unmap_point(QPointF(self.rect().right(), self.rect().bottom())),
        )
        xs = [point.x for point in corners]
        ys = [point.y for point in corners]
        return Bounds2D(min(xs), min(ys), max(xs), max(ys))

    def _grid_bounds_for_current_paint(self, mapper: CanvasMapper) -> Bounds2D:
        outline = self.display_outline()
        if outline is None:
            return self._canvas_domain_bounds(mapper)
        if self._dragging_origin:
            return self._canvas_domain_bounds(mapper)
        if (
            self._edit_overlay is not None
            and self._edit_overlay.mode == "drag"
            and self._edit_overlay.target_kind in {"hole_center", "hole_vertex"}
        ):
            return self._canvas_domain_bounds(mapper)
        return outline.bounds()

    def _draw_domain_grid(self, painter: QPainter, grid_context: _GridContext) -> None:
        mapper = grid_context.mapper
        bounds = grid_context.bounds
        domain_rect = mapper.map_rect(bounds.min_x, bounds.max_x, bounds.min_y, bounds.max_y)
        origin = grid_context.origin

        painter.save()
        painter.setClipRect(domain_rect.adjusted(-1, -1, 1, 1))

        if self._should_draw_minor_grid(mapper):
            minor_color = self.palette().color(QPalette.ColorRole.Mid)
            minor_color.setAlpha(64)
            painter.setPen(QPen(minor_color, 0.5))
            self._draw_grid_lines_for_step(painter, mapper, bounds, domain_rect, origin, self._grid_minor_step_cm())

        if self._should_draw_major_grid(mapper):
            major_color = self.palette().color(QPalette.ColorRole.Mid)
            major_color.setAlpha(90)
            painter.setPen(QPen(major_color, 0.85))
            self._draw_grid_lines_for_step(painter, mapper, bounds, domain_rect, origin, self._grid_major_step_cm())

        painter.restore()

    def _draw_grid_lines_for_step(
        self,
        painter: QPainter,
        mapper: CanvasMapper,
        bounds: Bounds2D,
        domain_rect: QRectF,
        origin: Point2D,
        step_cm: float,
    ) -> None:
        x_start = int(floor((bounds.min_x - origin.x) / step_cm))
        x_end = int(ceil((bounds.max_x - origin.x) / step_cm))
        for index in range(x_start, x_end + 1):
            x = mapper.map_x(origin.x + index * step_cm)
            painter.drawLine(QPointF(x, domain_rect.top()), QPointF(x, domain_rect.bottom()))

        y_start = int(floor((origin.y - bounds.max_y) / step_cm))
        y_end = int(ceil((origin.y - bounds.min_y) / step_cm))
        for index in range(y_start, y_end + 1):
            y = mapper.map_y(origin.y - index * step_cm)
            painter.drawLine(QPointF(domain_rect.left(), y), QPointF(domain_rect.right(), y))

    def _draw_edit_overlay(self, painter: QPainter, mapper: CanvasMapper, outline: Polygon2D) -> None:
        if self._edit_overlay is None:
            return

        overlay = self._edit_overlay
        bounds = outline.bounds()
        domain_rect = mapper.map_rect(bounds.min_x, bounds.max_x, bounds.min_y, bounds.max_y)
        active_point = overlay.domain_point

        if not self._grid_visible():
            grid_context = self._grid_context()
            if grid_context is not None:
                self._draw_domain_grid(painter, grid_context)

        axis_color = self.palette().color(QPalette.ColorRole.Highlight)
        axis_color.setAlpha(170)
        axis_pen = QPen(axis_color, 1.2, Qt.PenStyle.DashLine)

        painter.save()
        painter.setClipRect(domain_rect.adjusted(-1, -1, 1, 1))
        painter.setPen(axis_pen)
        if bounds.min_x <= active_point.x <= bounds.max_x:
            x = mapper.map_x(active_point.x)
            painter.drawLine(QPointF(x, domain_rect.top()), QPointF(x, domain_rect.bottom()))
        if bounds.min_y <= active_point.y <= bounds.max_y:
            y = mapper.map_y(active_point.y)
            painter.drawLine(QPointF(domain_rect.left(), y), QPointF(domain_rect.right(), y))
        painter.restore()

        mapped_point = mapper.map_point(active_point)
        marker_color = QColor(axis_color)
        marker_color.setAlpha(220)
        painter.setPen(QPen(marker_color, 1.5))
        painter.setBrush(marker_color)
        painter.drawEllipse(mapped_point, 3.5, 3.5)
        self._draw_coordinate_overlay_labels(painter, mapper)

    def _draw_coordinate_overlay_labels(self, painter: QPainter, mapper: CanvasMapper) -> None:
        labels = self._coordinate_overlay_labels()
        if not labels:
            return

        viewport = self.rect().adjusted(6, 6, -6, -6)
        font = painter.font()
        font.setPointSize(8)
        painter.save()
        painter.setFont(font)
        metrics = QFontMetricsF(font)
        center_point = labels[0].domain_point
        mapped_center = mapper.map_point(center_point)

        for label in labels:
            mapped_point = mapper.map_point(label.domain_point)
            if label.kind == "active":
                label_rect = self._coordinate_label_rect(
                    mapped_point,
                    mapped_center,
                    metrics,
                    self._coordinate_label_text(label.domain_point),
                    viewport,
                    mode="active",
                )
            else:
                label_rect = self._coordinate_label_rect(
                    mapped_point,
                    mapped_center,
                    metrics,
                    self._coordinate_label_text(label.domain_point),
                    viewport,
                    mode="vertex",
                )

            background = QColor(18, 18, 18, 190 if label.kind == "vertex" else 215)
            border = QColor(255, 255, 255, 90 if label.kind == "vertex" else 120)
            painter.setPen(QPen(border, 0.8))
            painter.setBrush(background)
            painter.drawRoundedRect(label_rect, 4.0, 4.0)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self._coordinate_label_text(label.domain_point))

        painter.restore()

    def _coordinate_label_rect(
        self,
        mapped_point: QPointF,
        mapped_center: QPointF,
        metrics: QFontMetricsF,
        label_text: str,
        viewport: QRectF,
        *,
        mode: str,
    ) -> QRectF:
        label_rect = QRectF(0.0, 0.0, metrics.horizontalAdvance(label_text) + 10.0, metrics.height() + 6.0)
        if mode == "active":
            label_rect.moveTopLeft(QPointF(mapped_point.x() + 10.0, mapped_point.y() - label_rect.height() - 12.0))
            if label_rect.right() > viewport.right():
                label_rect.moveRight(viewport.right())
            if label_rect.left() < viewport.left():
                label_rect.moveLeft(viewport.left())
            if label_rect.top() < viewport.top():
                label_rect.moveTop(mapped_point.y() + 10.0)
            if label_rect.bottom() > viewport.bottom():
                label_rect.moveBottom(viewport.bottom())
            return label_rect

        dx = mapped_point.x() - mapped_center.x()
        dy = mapped_point.y() - mapped_center.y()
        if abs(dx) < 0.5 and abs(dy) < 0.5:
            dx, dy = 1.0, -1.0
        length_px = hypot(dx, dy)
        unit_x = dx / length_px
        unit_y = dy / length_px
        anchor = QPointF(mapped_point.x() + unit_x * 12.0, mapped_point.y() + unit_y * 12.0)
        left = anchor.x() + 2.0 if unit_x >= 0 else anchor.x() - label_rect.width() - 2.0
        top = anchor.y() + 2.0 if unit_y >= 0 else anchor.y() - label_rect.height() - 2.0
        label_rect.moveTopLeft(QPointF(left, top))

        if label_rect.right() > viewport.right():
            label_rect.moveRight(viewport.right())
        if label_rect.left() < viewport.left():
            label_rect.moveLeft(viewport.left())
        if label_rect.top() < viewport.top():
            label_rect.moveTop(viewport.top())
        if label_rect.bottom() > viewport.bottom():
            label_rect.moveBottom(viewport.bottom())
        return label_rect

    def _draw_origin_marker(self, painter: QPainter, mapper: CanvasMapper) -> None:
        if not self._origin_edit_enabled:
            return

        mapped_origin = mapper.map_point(self._origin_point())
        marker_color = QColor(255, 120, 120, 230)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(marker_color, 1.6))
        painter.setBrush(QColor(18, 18, 18, 190))
        painter.drawLine(
            QPointF(mapped_origin.x() - 10.0, mapped_origin.y()),
            QPointF(mapped_origin.x() + 10.0, mapped_origin.y()),
        )
        painter.drawLine(
            QPointF(mapped_origin.x(), mapped_origin.y() - 10.0),
            QPointF(mapped_origin.x(), mapped_origin.y() + 10.0),
        )
        painter.drawEllipse(mapped_origin, 4.0, 4.0)
        if self._dragging_origin:
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            label_text = self._origin_drag_label_text()
            metrics = QFontMetricsF(font)
            label_rect = self._coordinate_label_rect(
                mapped_origin,
                mapped_origin,
                metrics,
                label_text,
                self.rect().adjusted(6, 6, -6, -6),
                mode="active",
            )
            painter.setPen(QPen(QColor(255, 255, 255, 120), 0.8))
            painter.setBrush(QColor(18, 18, 18, 215))
            painter.drawRoundedRect(label_rect, 4.0, 4.0)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label_text)
        painter.restore()

    def _axis_indicator_origin(self) -> QPointF:
        canvas_rect = QRectF(self.rect())
        return QPointF(
            canvas_rect.left() + AXIS_WIDGET_PADDING_PX,
            canvas_rect.bottom() - AXIS_WIDGET_PADDING_PX,
        )

    def _freehand_axis_origin(self) -> QPointF:
        if self.user_points:
            return self.user_points[0]
        return self._axis_indicator_origin()

    def _draw_freehand_axis_overlay(self, painter: QPainter) -> None:
        if not self._app_settings.show_axis_overlay:
            return
        if self._mode not in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
            return
        self._draw_axis_indicator_at(painter, self._freehand_axis_origin())

    def _draw_axis_indicator(self, painter: QPainter) -> None:
        if not self._app_settings.show_axis_overlay:
            return
        if self._mode in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}:
            return
        self._draw_axis_indicator_at(painter, self._axis_indicator_origin())

    def _draw_axis_indicator_at(self, painter: QPainter, origin: QPointF) -> None:
        x_tip = QPointF(origin.x() + AXIS_WIDGET_LENGTH_PX, origin.y())
        y_tip = QPointF(origin.x(), origin.y() - AXIS_WIDGET_LENGTH_PX)

        x_color = QColor(220, 70, 70, 255)
        y_color = QColor(70, 180, 80, 255)
        label_font = painter.font()
        label_font.setPointSize(max(label_font.pointSize(), 9))

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setFont(label_font)
        painter.setPen(QPen(x_color, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(origin, x_tip)
        painter.drawLine(x_tip, QPointF(x_tip.x() - AXIS_WIDGET_ARROW_SIZE_PX, x_tip.y() - AXIS_WIDGET_ARROW_SIZE_PX / 2.0))
        painter.drawLine(x_tip, QPointF(x_tip.x() - AXIS_WIDGET_ARROW_SIZE_PX, x_tip.y() + AXIS_WIDGET_ARROW_SIZE_PX / 2.0))
        painter.drawText(QRectF(x_tip.x() + 4.0, x_tip.y() - 12.0, 16.0, 16.0), Qt.AlignmentFlag.AlignCenter, "X")

        painter.setPen(QPen(y_color, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(origin, y_tip)
        painter.drawLine(y_tip, QPointF(y_tip.x() - AXIS_WIDGET_ARROW_SIZE_PX / 2.0, y_tip.y() + AXIS_WIDGET_ARROW_SIZE_PX))
        painter.drawLine(y_tip, QPointF(y_tip.x() + AXIS_WIDGET_ARROW_SIZE_PX / 2.0, y_tip.y() + AXIS_WIDGET_ARROW_SIZE_PX))
        painter.drawText(QRectF(y_tip.x() - 8.0, y_tip.y() - 18.0, 16.0, 16.0), Qt.AlignmentFlag.AlignCenter, "Y")
        painter.restore()

    def _draw_crosshair(self, painter: QPainter) -> None:
        if not self._app_settings.show_crosshair or self._crosshair_point is None:
            return
        if (
            self._mode not in {self.MODE_DRAW_OUTLINE, self.MODE_DRAW_CUTOUT}
            and self._edit_overlay is None
            and not self._dragging_origin
            and self._dragging_vertex_index is None
            and self._dragging_hole_center_index is None
        ):
            return
        point = self._crosshair_point
        color = self.palette().color(QPalette.ColorRole.Text)
        color.setAlpha(95)
        highlight = self.palette().color(QPalette.ColorRole.Highlight)
        highlight.setAlpha(145)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        horizontal_pen = QPen(highlight if self._crosshair_axis == "x" else color, 1.2 if self._crosshair_axis == "x" else 0.8)
        vertical_pen = QPen(highlight if self._crosshair_axis == "y" else color, 1.2 if self._crosshair_axis == "y" else 0.8)
        painter.setPen(horizontal_pen)
        painter.drawLine(QPointF(point.x() - CROSSHAIR_LENGTH_PX, point.y()), QPointF(point.x() + CROSSHAIR_LENGTH_PX, point.y()))
        painter.setPen(vertical_pen)
        painter.drawLine(QPointF(point.x(), point.y() - CROSSHAIR_LENGTH_PX), QPointF(point.x(), point.y() + CROSSHAIR_LENGTH_PX))
        painter.restore()

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
        painter.setBrush(fill_color if self._show_sheet_placements else Qt.BrushStyle.NoBrush)
        painter.drawPolygon(outline_polygon)

        self._draw_sheet_placements(painter, plane, mapper, text_color)

        painter.setPen(QPen(hole_color, 1.5, Qt.PenStyle.DashLine))
        for hole_index, hole in enumerate(holes):
            hole_polygon = QPolygonF([mapper.map_point(point) for point in hole.points])
            if self._show_sheet_placements:
                hole_bg = QColor(background_color)
                hole_bg.setAlpha(150)
                painter.setBrush(hole_bg)
                painter.drawPolygon(hole_polygon)
            if hole_index == self._selected_hole_index:
                painter.setPen(QPen(selected_hole_color, 2.0, Qt.PenStyle.DashLine))
            else:
                painter.setPen(QPen(hole_color, 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolygon(hole_polygon)

        self._draw_midpoint_handles(painter, mapper, outline, outline_color)
        if self._plane_selected:
            self._draw_vertex_handles(
                painter,
                mapper,
                outline,
                outline_color,
                active_vertex_index=self._active_vertex_index,
            )
        if self._selected_hole_index is not None and self._selected_hole_index < len(holes):
            self._draw_vertex_handles(
                painter,
                mapper,
                holes[self._selected_hole_index],
                selected_hole_color,
                active_vertex_index=self._active_hole_vertex_index,
            )

        painter.setPen(QPen(hole_color, 1))
        for hole_index, hole in enumerate(holes):
            bounds = hole.bounds()
            center_x = (bounds.min_x + bounds.max_x) / 2.0
            center_y = (bounds.min_y + bounds.max_y) / 2.0
            mapped_center = mapper.map_point(Point2D(center_x, center_y))
            is_active = hole_index == self._selected_hole_index
            painter.setBrush(selected_hole_color.lighter(140) if is_active else hole_color)
            radius = MIDPOINT_HANDLE_RADIUS + (2 if is_active else 0)
            painter.drawEllipse(mapped_center, radius, radius)

        if self._show_sheet_placements:
            self._draw_edge_measurements(painter, mapper, outline, text_color, outline_color)
        self._draw_axis_indicator(painter)
        self._draw_edit_overlay(painter, mapper, outline)

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
        is_light = self.palette().color(QPalette.ColorRole.Base).lightness() > 128
        label_pen = QPen(outline_color if is_light else text_color)
        guide_pen = QPen(outline_color)
        guide_pen.setStyle(Qt.PenStyle.DotLine)
        guide_pen.setWidthF(1.0)
        painter.setFont(painter.font())
        
        polygon_f = QPolygonF([mapper.map_point(point) for point in outline.points])
        
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
            
            test_point = QPointF(mid_x + normal_x * 5.0, mid_y + normal_y * 5.0)
            if polygon_f.containsPoint(test_point, Qt.FillRule.OddEvenFill):
                normal_x = -normal_x
                normal_y = -normal_y

            label_anchor = QPointF(mid_x + normal_x * EDGE_LABEL_OFFSET_PX, mid_y + normal_y * EDGE_LABEL_OFFSET_PX)

            painter.setPen(guide_pen)
            painter.drawLine(QPointF(mid_x, mid_y), label_anchor)

            label_rect = QRectF(label_anchor.x() - 30.0, label_anchor.y() - 11.0, 60.0, 22.0)
            background = self.palette().color(QPalette.ColorRole.Base)
            background.setAlpha(220)
            painter.setPen(label_pen)
            painter.setBrush(background)
            painter.drawRoundedRect(label_rect, 4.0, 4.0)

            length_cm = segment_length(start, end)
            length_int = int(round(length_cm))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, str(length_int))

    def _draw_sheet_placements(self, painter: QPainter, plane, mapper: CanvasMapper, text_color: QColor) -> None:
        if not self._show_sheet_placements:
            return
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

        # Draw partial-cutout split lines from serialized layout band data
        if plane is not None and hasattr(plane, "layout_bands"):
            for band_dict in plane.layout_bands:
                for seg_dict in band_dict.get("segments", []):
                    if seg_dict.get("cutout_interaction") != "partial":
                        continue
                    cut_y = seg_dict.get("partial_cut_line_y_cm")
                    if cut_y is None:
                        continue
                    x_left = seg_dict["x_left_cm"]
                    x_right = seg_dict["x_right_cm"]

                    p1 = mapper.map_point(Point2D(x_left, cut_y))
                    p2 = mapper.map_point(Point2D(x_right, cut_y))

                    cut_pen = QPen(QColor(230, 140, 0))
                    cut_pen.setWidthF(2.0)
                    cut_pen.setStyle(Qt.PenStyle.DashDotLine)
                    painter.setPen(cut_pen)
                    painter.drawLine(p1, p2)

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

        background = self.palette().color(QPalette.ColorRole.Highlight)
        background.setAlpha(230)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(label_rect, 4.0, 4.0)
        
        highlight_text = self.palette().color(QPalette.ColorRole.HighlightedText)
        painter.setPen(highlight_text)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label_text)

    def _sheet_label_text(self, item: _SheetRenderItem) -> str:
        module_length_cm = self._material.module_length_cm if self._material is not None else None
        if self._show_module_count and module_length_cm and module_length_cm > 0:
            modules = max(1, int(round(item.final_length_cm / module_length_cm)))
            return f"{modules}"
        return f"{item.final_length_cm:.0f}"

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
                painter.setPen(QPen(QColor("#ff3333"), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                polygon = QPolygonF([mapper.map_point(point) for point in self._placement_polygon(sheet).points])
                painter.drawPolygon(polygon)
                break
