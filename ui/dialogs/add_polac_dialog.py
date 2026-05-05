"""Wizard dialog for creating a roof plane outline with an optional cutout."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.geometry import (
    build_add_polac_cutout,
    build_add_polac_outline,
    clamp_add_polac_cutout_position,
    find_valid_add_polac_cutout_position,
    flip_polygon_in_bounds,
    normalize_add_polac_cutout_position,
    point_in_polygon,
    validate_hole_polygon,
    validate_polygon,
)
from core.models import Point2D, Polygon2D
from ui.dialogs.add_polac_catalog import (
    CUTOUT_CATALOG,
    CUTOUT_CATALOG_BY_KEY,
    SHAPE_CATALOG,
    SHAPE_CATALOG_BY_KEY,
    default_cutout_position,
    merge_add_polac_dialog_cache,
    seed_add_polac_dialog_cache,
)


@dataclass(slots=True)
class AddPolacResult:
    shape_key: str
    shape_values: dict
    cutout_kind: str
    cutout_values: dict
    cutout_position: dict[str, float]
    flip_h: bool
    flip_v: bool


@dataclass(slots=True)
class _PreviewDimension:
    key: str
    label: str
    start: Point2D
    end: Point2D
    orientation: str
    side: str


class WizardPreviewPanel(QWidget):
    dimensionHovered = Signal(object)
    cutoutDragRequested = Signal(float, float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.outline_polygon: Polygon2D | None = None
        self.cutout_polygon: Polygon2D | None = None
        self.placeholder = "Podgląd"
        self.active_dimension_key: str | None = None
        self._dimensions: list[_PreviewDimension] = []
        self._badge_rects: dict[str, QRectF] = {}
        self._draggable_cutout = False
        self._hover_dimension_key: str | None = None
        self._cutout_hovered = False
        self._dragging_cutout = False
        self._drag_offset = Point2D(0.0, 0.0)
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._scale = 1.0
        self._min_x = 0.0
        self._min_y = 0.0
        self.setMouseTracking(True)
        self.setMinimumHeight(340)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_scene(
        self,
        outline: Polygon2D | None,
        cutout: Polygon2D | None = None,
        *,
        dimensions: list[_PreviewDimension] | None = None,
        placeholder: str = "Podgląd",
        draggable_cutout: bool = False,
        active_dimension_key: str | None = None,
    ) -> None:
        self.outline_polygon = outline.copy() if outline is not None else None
        self.cutout_polygon = cutout.copy() if cutout is not None else None
        self._dimensions = list(dimensions or [])
        self.placeholder = placeholder
        self._draggable_cutout = draggable_cutout
        self.active_dimension_key = active_dimension_key
        self._hover_dimension_key = None
        self._dragging_cutout = False
        self._cutout_hovered = False
        self._badge_rects = {}
        self.update()

    def set_active_dimension(self, key: str | None) -> None:
        self.active_dimension_key = key
        self.update()

    def domain_to_view(self, point: Point2D) -> QPointF:
        return QPointF(
            self._offset_x + (point.x - self._min_x) * self._scale,
            self._offset_y + (point.y - self._min_y) * self._scale,
        )

    def _view_to_domain(self, point: QPointF) -> Point2D | None:
        if self.outline_polygon is None or self._scale <= 0.0:
            return None
        return Point2D(
            self._min_x + (point.x() - self._offset_x) / self._scale,
            self._min_y + (point.y() - self._offset_y) / self._scale,
        )

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f8fafc"))
        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 10, 10)

        if self.outline_polygon is None:
            painter.setPen(QColor("#64748b"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.placeholder)
            return

        self._compute_transform()

        outline_polygon = self._to_qpolygon(self.outline_polygon)
        path = QPainterPath()
        path.addPolygon(outline_polygon)
        if self.cutout_polygon is not None:
            hole_path = QPainterPath()
            hole_path.addPolygon(self._to_qpolygon(self.cutout_polygon))
            path = path.subtracted(hole_path)

        painter.fillPath(path, QColor("#dbeafe"))
        painter.setPen(QPen(QColor("#2563eb"), 2))
        painter.drawPolygon(outline_polygon)

        if self.cutout_polygon is not None:
            painter.setPen(QPen(QColor("#d97706"), 2))
            painter.drawPolygon(self._to_qpolygon(self.cutout_polygon))
            if self._draggable_cutout and (self._cutout_hovered or self._dragging_cutout):
                bounds = self.cutout_polygon.bounds()
                center = Point2D(
                    bounds.min_x + bounds.width / 2.0,
                    bounds.min_y + bounds.height / 2.0,
                )
                center_point = self.domain_to_view(center)
                painter.setBrush(QColor("#d97706"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(center_point, 4.0, 4.0)

        self._draw_dimensions(painter)

    def mousePressEvent(self, event) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._draggable_cutout
            and self.cutout_polygon is not None
        ):
            domain_point = self._view_to_domain(event.position())
            if domain_point is not None and point_in_polygon(domain_point, self.cutout_polygon):
                bounds = self.cutout_polygon.bounds()
                center = Point2D(
                    bounds.min_x + bounds.width / 2.0,
                    bounds.min_y + bounds.height / 2.0,
                )
                self._dragging_cutout = True
                self._drag_offset = Point2D(domain_point.x - center.x, domain_point.y - center.y)
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self.outline_polygon is None:
            return super().mouseMoveEvent(event)

        if self._dragging_cutout:
            domain_point = self._view_to_domain(event.position())
            if domain_point is not None:
                bounds = self.outline_polygon.bounds()
                desired_center = Point2D(
                    domain_point.x - self._drag_offset.x,
                    domain_point.y - self._drag_offset.y,
                )
                desired_x = (desired_center.x - bounds.min_x) / max(bounds.width, 1.0)
                desired_y = (desired_center.y - bounds.min_y) / max(bounds.height, 1.0)
                self.cutoutDragRequested.emit(desired_x, desired_y)
                event.accept()
                return

        hover_key = None
        for key, rect in self._badge_rects.items():
            if rect.contains(event.position()):
                hover_key = key
                break
        if hover_key != self._hover_dimension_key:
            self._hover_dimension_key = hover_key
            self.dimensionHovered.emit(hover_key)
            self.update()

        self._cutout_hovered = False
        if self._draggable_cutout and self.cutout_polygon is not None:
            domain_point = self._view_to_domain(event.position())
            self._cutout_hovered = domain_point is not None and point_in_polygon(domain_point, self.cutout_polygon)
        self.setCursor(
            Qt.CursorShape.SizeAllCursor
            if self._cutout_hovered or self._dragging_cutout
            else Qt.CursorShape.ArrowCursor
        )
        self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging_cutout:
            self._dragging_cutout = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        if not self._dragging_cutout and self._hover_dimension_key is not None:
            self._hover_dimension_key = None
            self._cutout_hovered = False
            self.dimensionHovered.emit(None)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
        super().leaveEvent(event)

    def _compute_transform(self) -> None:
        all_points = list(self.outline_polygon.points)
        if self.cutout_polygon is not None:
            all_points.extend(self.cutout_polygon.points)
        self._min_x = min(point.x for point in all_points)
        self._min_y = min(point.y for point in all_points)
        max_x = max(point.x for point in all_points)
        max_y = max(point.y for point in all_points)
        width = max(max_x - self._min_x, 1.0)
        height = max(max_y - self._min_y, 1.0)
        margin = 28.0
        self._scale = min((self.width() - 2 * margin) / width, (self.height() - 2 * margin) / height)
        self._offset_x = (self.width() - width * self._scale) / 2.0
        self._offset_y = (self.height() - height * self._scale) / 2.0

    def _to_qpolygon(self, polygon: Polygon2D) -> QPolygonF:
        return QPolygonF([self.domain_to_view(point) for point in polygon.points])

    def _draw_dimensions(self, painter: QPainter) -> None:
        self._badge_rects = {}
        if not self._dimensions:
            return

        for dimension in self._dimensions:
            is_active = dimension.key in {self.active_dimension_key, self._hover_dimension_key}
            line_color = QColor("#1d4ed8" if is_active else "#64748b")
            badge_fill = QColor("#dbeafe" if is_active else "#ffffff")
            badge_text = QColor("#1e3a8a" if is_active else "#334155")
            start = self.domain_to_view(dimension.start)
            end = self.domain_to_view(dimension.end)

            if dimension.orientation == "h":
                offset = QPointF(0.0, -18.0 if dimension.side == "top" else 18.0)
            else:
                offset = QPointF(-18.0 if dimension.side == "left" else 18.0, 0.0)

            line_start = start + offset
            line_end = end + offset
            painter.setPen(QPen(line_color, 1.3))
            painter.drawLine(start, line_start)
            painter.drawLine(end, line_end)
            painter.drawLine(line_start, line_end)

            center = QPointF((line_start.x() + line_end.x()) / 2.0, (line_start.y() + line_end.y()) / 2.0)
            badge_rect = QRectF(center.x() - 15.0, center.y() - 10.0, 30.0, 20.0)
            self._badge_rects[dimension.key] = badge_rect
            painter.setBrush(badge_fill)
            painter.setPen(QPen(line_color, 1))
            painter.drawRoundedRect(badge_rect, 8.0, 8.0)
            painter.setPen(badge_text)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, dimension.label)


class _DimensionSpinBox(QSpinBox):
    focusEntered = Signal()
    focusLeft = Signal()
    hoverEntered = Signal()
    hoverLeft = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self.focusEntered.emit()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.focusLeft.emit()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.focusEntered.emit()
        self.hoverEntered.emit()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.hoverEntered.emit()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.hoverLeft.emit()


def _make_tile_icon(points: tuple[tuple[float, float], ...], *, size: int = 72) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    if not points:
        return QIcon(pixmap)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    margin = 10.0
    span = size - 2 * margin
    painter.setPen(QPen(QColor("#475569"), 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    polygon = QPolygonF([QPointF(margin + x * span, margin + y * span) for x, y in points])
    painter.drawPolygon(polygon)
    painter.end()
    return QIcon(pixmap)


def _make_flip_icon(axis: str, *, size: int = 24) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor("#475569"), 2))
    if axis == "h":
        painter.drawLine(4, 6, 20, 6)
        painter.drawLine(4, 18, 20, 18)
        painter.drawLine(7, 4, 4, 6)
        painter.drawLine(7, 8, 4, 6)
        painter.drawLine(17, 16, 20, 18)
        painter.drawLine(17, 20, 20, 18)
    else:
        painter.drawLine(6, 4, 6, 20)
        painter.drawLine(18, 4, 18, 20)
        painter.drawLine(4, 7, 6, 4)
        painter.drawLine(8, 7, 6, 4)
        painter.drawLine(16, 17, 18, 20)
        painter.drawLine(20, 17, 18, 20)
    painter.end()
    return QIcon(pixmap)


class AddPolacDialog(QDialog):
    def __init__(self, config_data: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Kreator połaci")
        self.resize(1180, 760)
        self.setStyleSheet(
            """
            QGroupBox {
                font-weight: 600;
            }
            QFrame[fieldRow="true"] {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background: #ffffff;
            }
            QFrame[fieldRow="true"][activeDimension="true"] {
                border-color: #2563eb;
                background: #eff6ff;
            }
            QFrame[fieldRow="true"][invalidField="true"] {
                border-color: #dc2626;
                background: #fef2f2;
            }
            QLabel[fieldChip="true"] {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 2px 6px;
                background: #f8fafc;
                color: #334155;
                font-weight: 600;
            }
            QToolButton[wizardTile="true"] {
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                background: #ffffff;
                padding: 8px;
                text-align: left;
            }
            QToolButton[wizardTile="true"]:hover {
                background: #f8fafc;
                border-color: #94a3b8;
            }
            QToolButton[wizardTile="true"]:checked {
                background: #eff6ff;
                border-color: #2563eb;
            }
            QToolButton[geomTool="true"] {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background: #ffffff;
                padding: 6px 10px;
            }
            QToolButton[geomTool="true"]:checked {
                background: #eff6ff;
                border-color: #2563eb;
            }
            QLabel[validation="true"] {
                color: #b91c1c;
            }
            """
        )

        self.config_data = config_data
        self._cache = seed_add_polac_dialog_cache(config_data)
        self.selected_shape_key = self._cache["last_shape"]
        self.selected_cutout_kind = self._cache["last_cutout"]
        self._shape_values = {key: dict(values) for key, values in self._cache["shapes"].items()}
        self._cutout_values = {key: dict(values) for key, values in self._cache["cutouts"].items()}
        self._cutout_positions = {
            key: normalize_add_polac_cutout_position(values)
            for key, values in self._cache["cutout_positions"].items()
        }

        self.shape_buttons: dict[str, QToolButton] = {}
        self.cutout_buttons: dict[str, QToolButton] = {}
        self.shape_form_fields: dict[str, QSpinBox] = {}
        self.cutout_form_fields: dict[str, QSpinBox] = {}
        self._shape_field_rows: dict[str, QFrame] = {}
        self._cutout_field_rows: dict[str, QFrame] = {}
        self._field_context: dict[QWidget, tuple[str, str]] = {}
        self._shape_focus_key: str | None = None
        self._shape_hover_key: str | None = None
        self._shape_preview_hover_key: str | None = None
        self._cutout_focus_key: str | None = None
        self._cutout_hover_key: str | None = None
        self._cutout_preview_hover_key: str | None = None
        self._shape_invalid_fields: set[str] = set()
        self._cutout_invalid_fields: set[str] = set()
        self._shape_issues: list[str] = []
        self._cutout_issues: list[str] = []
        self._last_valid_outline: Polygon2D | None = None
        self._last_valid_cutout_outline: Polygon2D | None = None
        self._last_valid_cutout: Polygon2D | None = None

        self._build_ui()
        self._rebuild_shape_form(self.selected_shape_key)
        self._rebuild_cutout_form(self.selected_cutout_kind)
        self.flip_h_button.setChecked(bool(self._cache["flip_h"]))
        self.flip_v_button.setChecked(bool(self._cache["flip_v"]))
        self._refresh_dialog_state()

    def eventFilter(self, watched, event):
        context_info = self._field_context.get(watched)
        if context_info is None:
            return super().eventFilter(watched, event)

        context, key = context_info
        if event.type() == QEvent.Type.FocusIn:
            self._set_active_field(context, key)
        elif event.type() == QEvent.Type.FocusOut:
            self._clear_active_field(context, key)
        elif event.type() == QEvent.Type.Enter:
            self._set_hover_field(context, key)
        elif event.type() == QEvent.Type.Leave:
            self._clear_hover_field(context, key)
        return super().eventFilter(watched, event)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.step_stack = QStackedWidget(self)
        self.shape_step = self._build_shape_step()
        self.cutout_step = self._build_cutout_step()
        self.step_stack.addWidget(self.shape_step)
        self.step_stack.addWidget(self.cutout_step)
        layout.addWidget(self.step_stack)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        self.back_button = self.button_box.addButton("Wstecz", QDialogButtonBox.ButtonRole.ActionRole)
        self.next_button = self.button_box.addButton("Dalej", QDialogButtonBox.ButtonRole.ActionRole)
        self.button_box.rejected.connect(self.reject)
        self.button_box.accepted.connect(self.accept)
        self.back_button.clicked.connect(self._go_to_shape_step)
        self.next_button.clicked.connect(self._go_to_cutout_step)
        layout.addWidget(self.button_box)

    def _build_shape_step(self) -> QWidget:
        page = QWidget(self)
        page_layout = QVBoxLayout(page)
        page_layout.addWidget(QLabel("Krok 1. Wybierz kształt połaci i od razu doprecyzuj jego wymiary.", page))

        self.shape_workspace_layout = QHBoxLayout()
        page_layout.addLayout(self.shape_workspace_layout, 1)

        self.shape_workspace_layout.addWidget(
            self._build_library_column(
                "Biblioteka połaci",
                SHAPE_CATALOG,
                self.shape_buttons,
                self._on_shape_selected,
                is_shape=True,
            ),
            23,
        )

        center_column = QWidget(page)
        center_layout = QVBoxLayout(center_column)
        center_layout.addWidget(QLabel("Preview połaci", center_column))
        self.shape_preview = WizardPreviewPanel(center_column)
        self.shape_preview.dimensionHovered.connect(self._on_shape_preview_dimension_hovered)
        center_layout.addWidget(self.shape_preview, 1)
        self.shape_workspace_layout.addWidget(center_column, 54)

        right_column = QWidget(page)
        right_layout = QVBoxLayout(right_column)
        self.shape_fields_group = QGroupBox("Wymiary połaci", right_column)
        self.shape_fields_layout = QVBoxLayout(self.shape_fields_group)
        right_layout.addWidget(self.shape_fields_group)

        self.shape_tools_group = QGroupBox("Narzędzia geometrii", right_column)
        tools_layout = QHBoxLayout(self.shape_tools_group)
        self.flip_h_button = QToolButton(self.shape_tools_group)
        self.flip_h_button.setProperty("geomTool", True)
        self.flip_h_button.setCheckable(True)
        self.flip_h_button.setText("Flip H")
        self.flip_h_button.setIcon(_make_flip_icon("h"))
        self.flip_h_button.toggled.connect(self._refresh_dialog_state)
        tools_layout.addWidget(self.flip_h_button)
        self.flip_v_button = QToolButton(self.shape_tools_group)
        self.flip_v_button.setProperty("geomTool", True)
        self.flip_v_button.setCheckable(True)
        self.flip_v_button.setText("Flip V")
        self.flip_v_button.setIcon(_make_flip_icon("v"))
        self.flip_v_button.toggled.connect(self._refresh_dialog_state)
        tools_layout.addWidget(self.flip_v_button)
        tools_layout.addStretch(1)
        right_layout.addWidget(self.shape_tools_group)

        self.shape_validation_group = QGroupBox("Walidacja i wskazówki", right_column)
        validation_layout = QVBoxLayout(self.shape_validation_group)
        self.shape_validation_label = QLabel(" ", self.shape_validation_group)
        self.shape_validation_label.setProperty("validation", True)
        self.shape_validation_label.setWordWrap(True)
        validation_layout.addWidget(self.shape_validation_label)
        right_layout.addWidget(self.shape_validation_group)
        right_layout.addStretch(1)
        self.shape_workspace_layout.addWidget(right_column, 23)
        return page

    def _build_cutout_step(self) -> QWidget:
        page = QWidget(self)
        page_layout = QVBoxLayout(page)
        page_layout.addWidget(QLabel("Krok 2. Dobierz wycinek i ustaw jego położenie bezpośrednio na preview.", page))

        self.cutout_workspace_layout = QHBoxLayout()
        page_layout.addLayout(self.cutout_workspace_layout, 1)

        self.cutout_workspace_layout.addWidget(
            self._build_library_column(
                "Biblioteka wycinków",
                CUTOUT_CATALOG,
                self.cutout_buttons,
                self._on_cutout_selected,
                is_shape=False,
            ),
            23,
        )

        center_column = QWidget(page)
        center_layout = QVBoxLayout(center_column)
        center_layout.addWidget(QLabel("Preview połaci z wycinkiem", center_column))
        self.cutout_preview = WizardPreviewPanel(center_column)
        self.cutout_preview.dimensionHovered.connect(self._on_cutout_preview_dimension_hovered)
        self.cutout_preview.cutoutDragRequested.connect(self._on_cutout_drag_requested)
        center_layout.addWidget(self.cutout_preview, 1)
        self.cutout_workspace_layout.addWidget(center_column, 54)

        right_column = QWidget(page)
        right_layout = QVBoxLayout(right_column)
        self.cutout_fields_group = QGroupBox("Wymiary wycinka", right_column)
        self.cutout_fields_layout = QVBoxLayout(self.cutout_fields_group)
        right_layout.addWidget(self.cutout_fields_group)

        self.cutout_position_group = QGroupBox("Położenie wycinka", right_column)
        position_layout = QGridLayout(self.cutout_position_group)
        position_layout.addWidget(QLabel("X środka:", self.cutout_position_group), 0, 0)
        self.cutout_position_x_value = QLabel("—", self.cutout_position_group)
        position_layout.addWidget(self.cutout_position_x_value, 0, 1)
        position_layout.addWidget(QLabel("Y środka:", self.cutout_position_group), 1, 0)
        self.cutout_position_y_value = QLabel("—", self.cutout_position_group)
        position_layout.addWidget(self.cutout_position_y_value, 1, 1)
        right_layout.addWidget(self.cutout_position_group)

        self.cutout_validation_group = QGroupBox("Walidacja i wskazówki", right_column)
        validation_layout = QVBoxLayout(self.cutout_validation_group)
        self.cutout_validation_label = QLabel(" ", self.cutout_validation_group)
        self.cutout_validation_label.setProperty("validation", True)
        self.cutout_validation_label.setWordWrap(True)
        validation_layout.addWidget(self.cutout_validation_label)
        right_layout.addWidget(self.cutout_validation_group)
        right_layout.addStretch(1)
        self.cutout_workspace_layout.addWidget(right_column, 23)
        return page

    def _build_library_column(self, title, catalog, button_store, on_selected, *, is_shape: bool) -> QWidget:
        column = QWidget(self)
        column_layout = QVBoxLayout(column)
        column_layout.addWidget(QLabel(title, column))
        scroll = QScrollArea(column)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        host = QWidget(scroll)
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(8)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for spec in catalog:
            button = QToolButton(host)
            button.setProperty("wizardTile", True)
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setIcon(_make_tile_icon(spec.preview_points))
            button.setIconSize(button.icon().actualSize(button.sizeHint()))
            button.setText(spec.label)
            button.setToolTip(spec.description)
            button.setMinimumHeight(72)
            button.clicked.connect(lambda checked, key=spec.key: on_selected(key, checked))
            current_key = self.selected_shape_key if is_shape else self.selected_cutout_kind
            if spec.key == current_key:
                button.setChecked(True)
            group.addButton(button)
            host_layout.addWidget(button)
            button_store[spec.key] = button
        host_layout.addStretch(1)
        scroll.setWidget(host)
        column_layout.addWidget(scroll, 1)
        return column

    def _rebuild_shape_form(self, shape_key: str) -> None:
        self.shape_form_fields = {}
        self._shape_field_rows = {}
        self._clear_layout(self.shape_fields_layout)

        shape = SHAPE_CATALOG_BY_KEY[shape_key]
        for field in shape.fields:
            row, spin = self._build_field_row(self.shape_fields_group, "shape", field.key, field.label, self._shape_values[shape_key][field.key])
            spin.valueChanged.connect(self._on_shape_value_changed)
            self.shape_form_fields[field.key] = spin
            self._shape_field_rows[field.key] = row
            self.shape_fields_layout.addWidget(row)
        self.shape_fields_layout.addStretch(1)

    def _rebuild_cutout_form(self, cutout_key: str) -> None:
        self.cutout_form_fields = {}
        self._cutout_field_rows = {}
        self._clear_layout(self.cutout_fields_layout)

        cutout = CUTOUT_CATALOG_BY_KEY[cutout_key]
        if cutout.key == "none":
            self.cutout_fields_layout.addWidget(
                QLabel("Bez wycinka - brak dodatkowych parametrów i brak dragowania na preview.", self.cutout_fields_group)
            )
            self.cutout_fields_layout.addStretch(1)
            return

        for field in cutout.fields:
            row, spin = self._build_field_row(
                self.cutout_fields_group,
                "cutout",
                field.key,
                field.label,
                self._cutout_values[cutout_key][field.key],
            )
            spin.valueChanged.connect(self._on_cutout_value_changed)
            self.cutout_form_fields[field.key] = spin
            self._cutout_field_rows[field.key] = row
            self.cutout_fields_layout.addWidget(row)
        self.cutout_fields_layout.addStretch(1)

    def _build_field_row(
        self,
        parent: QWidget,
        context: str,
        key: str,
        label: str,
        value: int,
    ) -> tuple[QFrame, QSpinBox]:
        row = QFrame(parent)
        row.setProperty("fieldRow", True)
        row.setProperty("activeDimension", False)
        row.setProperty("invalidField", False)
        layout = QHBoxLayout(row)
        title = QLabel(f"{key} - {label}", row)
        title.setWordWrap(True)
        chip = QLabel(key, row)
        chip.setProperty("fieldChip", True)
        spin = self._build_spin_box(row, value)
        spin.focusEntered.connect(lambda ctx=context, current_key=key: self._set_active_field(ctx, current_key))
        spin.focusLeft.connect(lambda ctx=context, current_key=key: self._clear_active_field(ctx, current_key))
        spin.hoverEntered.connect(lambda ctx=context, current_key=key: self._set_hover_field(ctx, current_key))
        spin.hoverLeft.connect(lambda ctx=context, current_key=key: self._clear_hover_field(ctx, current_key))
        layout.addWidget(title, 1)
        layout.addWidget(chip)
        layout.addWidget(spin)
        return row, spin

    def _build_spin_box(self, parent: QWidget, value: int) -> QSpinBox:
        spin = _DimensionSpinBox(parent)
        spin.setRange(1, 9999)
        spin.setSuffix(" cm")
        spin.setValue(value)
        return spin

    def _on_shape_selected(self, shape_key: str, checked: bool) -> None:
        if not checked or shape_key == self.selected_shape_key:
            return
        self._store_current_shape_values()
        self.selected_shape_key = shape_key
        self._shape_focus_key = None
        self._shape_hover_key = None
        self._shape_preview_hover_key = None
        self._rebuild_shape_form(shape_key)
        self._refresh_dialog_state()

    def _on_cutout_selected(self, cutout_key: str, checked: bool) -> None:
        if not checked or cutout_key == self.selected_cutout_kind:
            return
        self._store_current_cutout_values()
        self.selected_cutout_kind = cutout_key
        self._cutout_focus_key = None
        self._cutout_hover_key = None
        self._cutout_preview_hover_key = None
        self._rebuild_cutout_form(cutout_key)
        self._refresh_dialog_state()

    def _on_shape_value_changed(self) -> None:
        self._refresh_dialog_state()

    def _on_cutout_value_changed(self) -> None:
        self._refresh_dialog_state()

    def _on_shape_preview_dimension_hovered(self, key: str | None) -> None:
        self._shape_preview_hover_key = key
        self._refresh_field_highlights()

    def _on_cutout_preview_dimension_hovered(self, key: str | None) -> None:
        self._cutout_preview_hover_key = key
        self._refresh_field_highlights()

    def _on_cutout_drag_requested(self, x_value: float, y_value: float) -> None:
        outline = self._build_valid_outline()
        if outline is None or self.selected_cutout_kind == "none":
            return
        desired = {"x": x_value, "y": y_value}
        current = self._cutout_positions.get(self.selected_cutout_kind, default_cutout_position())
        clamped = clamp_add_polac_cutout_position(
            self.selected_cutout_kind,
            self._current_cutout_values(),
            outline,
            current,
            desired,
        )
        if clamped is None:
            return
        self._cutout_positions[self.selected_cutout_kind] = clamped
        self._refresh_dialog_state()

    def _set_active_field(self, context: str, key: str) -> None:
        if context == "shape":
            self._shape_focus_key = key
        else:
            self._cutout_focus_key = key
        self._refresh_field_highlights()

    def _clear_active_field(self, context: str, key: str) -> None:
        if context == "shape" and self._shape_focus_key == key:
            self._shape_focus_key = None
        elif context == "cutout" and self._cutout_focus_key == key:
            self._cutout_focus_key = None
        self._refresh_field_highlights()

    def _set_hover_field(self, context: str, key: str) -> None:
        if context == "shape":
            self._shape_hover_key = key
        else:
            self._cutout_hover_key = key
        self._refresh_field_highlights()

    def _clear_hover_field(self, context: str, key: str) -> None:
        if context == "shape" and self._shape_hover_key == key:
            self._shape_hover_key = None
        elif context == "cutout" and self._cutout_hover_key == key:
            self._cutout_hover_key = None
        self._refresh_field_highlights()

    def _store_current_shape_values(self) -> None:
        if not self.shape_form_fields:
            return
        self._shape_values[self.selected_shape_key] = self._current_shape_values()

    def _store_current_cutout_values(self) -> None:
        if self.selected_cutout_kind == "none" or not self.cutout_form_fields:
            return
        self._cutout_values[self.selected_cutout_kind] = self._current_cutout_values()

    def _current_shape_values(self) -> dict:
        return {key: field.value() for key, field in self.shape_form_fields.items()}

    def _current_cutout_values(self) -> dict:
        return {key: field.value() for key, field in self.cutout_form_fields.items()}

    def _build_valid_outline(self) -> Polygon2D | None:
        issues, _, outline = self._validate_shape_state()
        if issues:
            return None
        return outline

    def _current_outline(self) -> Polygon2D:
        outline = build_add_polac_outline(self.selected_shape_key, self._current_shape_values())
        return flip_polygon_in_bounds(
            outline,
            horizontal=self.flip_h_button.isChecked(),
            vertical=self.flip_v_button.isChecked(),
        )

    def _current_cutout(self) -> Polygon2D | None:
        outline = self._current_outline()
        if self.selected_cutout_kind == "none":
            return None
        position = self._cutout_positions.get(self.selected_cutout_kind, default_cutout_position())
        return build_add_polac_cutout(
            self.selected_cutout_kind,
            self._current_cutout_values(),
            outline,
            position,
        )

    def _validate_shape_state(self) -> tuple[list[str], set[str], Polygon2D | None]:
        self._store_current_shape_values()
        values = self._shape_values[self.selected_shape_key]
        issues: list[str] = []
        invalid_fields: set[str] = set()

        if self.selected_shape_key.startswith("trapez") and values["C"] > values["A"]:
            issues.append("Podstawa górna C nie może być większa od podstawy dolnej A.")
            invalid_fields.update({"A", "C"})

        if issues:
            return issues, invalid_fields, None

        try:
            outline = build_add_polac_outline(self.selected_shape_key, values)
            outline = flip_polygon_in_bounds(
                outline,
                horizontal=self.flip_h_button.isChecked(),
                vertical=self.flip_v_button.isChecked(),
            )
        except ValueError as exc:
            return [str(exc)], set(values), None

        polygon_issues = validate_polygon(outline)
        if polygon_issues:
            return polygon_issues, set(values), None
        return [], invalid_fields, outline

    def _validate_cutout_state(
        self,
        outline: Polygon2D | None,
    ) -> tuple[list[str], set[str], Polygon2D | None, dict[str, float]]:
        default_position = self._cutout_positions.get(self.selected_cutout_kind, default_cutout_position())
        if self.selected_cutout_kind == "none":
            return [], set(), None, default_position

        self._store_current_cutout_values()
        values = self._cutout_values[self.selected_cutout_kind]
        issues: list[str] = []
        invalid_fields: set[str] = set()

        if self.selected_cutout_kind == "lukarna3" and values["H1"] >= values["H"]:
            issues.append("Wysokość załamania H1 musi być mniejsza od wysokości całkowitej H.")
            invalid_fields.update({"H1", "H"})
            return issues, invalid_fields, None, default_position

        if outline is None:
            return [], invalid_fields, None, default_position

        desired_position = self._cutout_positions.get(self.selected_cutout_kind, default_cutout_position())
        valid_position = find_valid_add_polac_cutout_position(
            self.selected_cutout_kind,
            values,
            outline,
            desired_position,
        )
        if valid_position is None:
            issues.append("Wycinek nie mieści się w tej połaci dla podanych wymiarów.")
            invalid_fields.update(values)
            return issues, invalid_fields, None, desired_position

        self._cutout_positions[self.selected_cutout_kind] = normalize_add_polac_cutout_position(valid_position)
        cutout = build_add_polac_cutout(
            self.selected_cutout_kind,
            values,
            outline,
            self._cutout_positions[self.selected_cutout_kind],
        )
        if cutout is None:
            return [], invalid_fields, None, self._cutout_positions[self.selected_cutout_kind]
        issues.extend(validate_hole_polygon(outline, cutout))
        if issues:
            invalid_fields.update(values)
            return issues, invalid_fields, None, self._cutout_positions[self.selected_cutout_kind]
        return [], invalid_fields, cutout, self._cutout_positions[self.selected_cutout_kind]

    def _refresh_dialog_state(self) -> None:
        self._shape_issues, self._shape_invalid_fields, outline = self._validate_shape_state()
        if outline is not None:
            self._last_valid_outline = outline.copy()

        cutout_outline = outline if outline is not None else self._last_valid_outline
        self._cutout_issues, self._cutout_invalid_fields, cutout, cutout_position = self._validate_cutout_state(cutout_outline)
        if cutout_outline is not None and not self._cutout_issues:
            self._last_valid_cutout_outline = cutout_outline.copy()
            self._last_valid_cutout = cutout.copy() if cutout is not None else None

        preview_outline = outline if outline is not None else self._last_valid_outline
        preview_cutout_outline = cutout_outline if cutout_outline is not None else self._last_valid_cutout_outline
        preview_cutout = cutout if cutout is not None else self._last_valid_cutout

        self.shape_validation_label.setText("\n".join(self._shape_issues) if self._shape_issues else "Wymiary są poprawne.")
        self.cutout_validation_label.setText("\n".join(self._cutout_issues) if self._cutout_issues else "Wycinek mieści się poprawnie w obrysie.")

        if preview_outline is not None:
            self.shape_preview.set_scene(
                preview_outline,
                None,
                dimensions=self._build_shape_dimensions(preview_outline),
                placeholder="Uzupełnij parametry połaci",
                active_dimension_key=self._shape_active_dimension_key(),
            )
        else:
            self.shape_preview.set_scene(None, placeholder="Uzupełnij parametry połaci")

        if preview_cutout_outline is not None:
            self.cutout_preview.set_scene(
                preview_cutout_outline,
                preview_cutout if self.selected_cutout_kind != "none" else None,
                dimensions=self._build_cutout_dimensions(preview_cutout),
                placeholder="Najpierw zdefiniuj poprawny obrys połaci",
                draggable_cutout=self.selected_cutout_kind != "none" and not self._cutout_issues,
                active_dimension_key=self._cutout_active_dimension_key(),
            )
        else:
            self.cutout_preview.set_scene(None, placeholder="Najpierw zdefiniuj poprawny obrys połaci")

        self._update_position_readout(preview_cutout, preview_cutout_outline, cutout_position)
        self._refresh_field_highlights()
        self._refresh_step_actions()

    def _refresh_field_highlights(self) -> None:
        shape_active = self._shape_active_dimension_key()
        cutout_active = self._cutout_active_dimension_key()
        self.shape_preview.set_active_dimension(shape_active)
        self.cutout_preview.set_active_dimension(cutout_active)
        self._apply_field_highlights(self._shape_field_rows, self._shape_invalid_fields, shape_active)
        self._apply_field_highlights(self._cutout_field_rows, self._cutout_invalid_fields, cutout_active)

    def _shape_active_dimension_key(self) -> str | None:
        return self._shape_preview_hover_key or self._shape_focus_key or self._shape_hover_key

    def _cutout_active_dimension_key(self) -> str | None:
        return self._cutout_preview_hover_key or self._cutout_focus_key or self._cutout_hover_key

    def _apply_field_highlights(self, rows: dict[str, QFrame], invalid_fields: set[str], active_key: str | None) -> None:
        for key, row in rows.items():
            row.setProperty("activeDimension", key == active_key)
            row.setProperty("invalidField", key in invalid_fields)
            row.style().unpolish(row)
            row.style().polish(row)

    def _build_shape_dimensions(self, outline: Polygon2D) -> list[_PreviewDimension]:
        points = outline.points
        bounds = outline.bounds()
        if self.selected_shape_key == "prostokat":
            return [
                _PreviewDimension("A", "A", points[0], points[1], "h", "top"),
                _PreviewDimension("B", "B", points[1], points[2], "v", "right"),
            ]
        if self.selected_shape_key == "trojkat":
            return [
                _PreviewDimension("A", "A", points[2], points[1], "h", "bottom"),
                _PreviewDimension("B", "B", Point2D(bounds.max_x, bounds.min_y), Point2D(bounds.max_x, bounds.max_y), "v", "right"),
            ]
        if self.selected_shape_key.startswith("trapez"):
            return [
                _PreviewDimension("C", "C", points[0], points[1], "h", "top"),
                _PreviewDimension("A", "A", points[3], points[2], "h", "bottom"),
                _PreviewDimension("B", "B", Point2D(bounds.max_x, bounds.min_y), Point2D(bounds.max_x, bounds.max_y), "v", "right"),
            ]
        return [
            _PreviewDimension("A", "A", Point2D(bounds.min_x, bounds.max_y), Point2D(bounds.max_x, bounds.max_y), "h", "bottom"),
            _PreviewDimension("B", "B", Point2D(bounds.max_x, bounds.min_y), Point2D(bounds.max_x, bounds.max_y), "v", "right"),
        ]

    def _build_cutout_dimensions(self, cutout: Polygon2D | None) -> list[_PreviewDimension]:
        if cutout is None or self.selected_cutout_kind == "none":
            return []
        bounds = cutout.bounds()
        points = cutout.points
        if self.selected_cutout_kind == "lukarna1":
            return [
                _PreviewDimension("A", "A", points[0], points[1], "h", "top"),
                _PreviewDimension("H1", "H1", points[1], points[2], "v", "right"),
            ]
        if self.selected_cutout_kind == "lukarna2":
            return [
                _PreviewDimension("A", "A", Point2D(bounds.min_x, bounds.max_y), Point2D(bounds.max_x, bounds.max_y), "h", "bottom"),
                _PreviewDimension("H", "H", Point2D(bounds.max_x, bounds.min_y), Point2D(bounds.max_x, bounds.max_y), "v", "right"),
            ]
        return [
            _PreviewDimension("A", "A", Point2D(bounds.min_x, bounds.max_y), Point2D(bounds.max_x, bounds.max_y), "h", "bottom"),
            _PreviewDimension("H1", "H1", Point2D(bounds.max_x, bounds.min_y), Point2D(bounds.max_x, points[1].y), "v", "right"),
            _PreviewDimension("H", "H", Point2D(bounds.max_x + 6.0, bounds.min_y), Point2D(bounds.max_x + 6.0, bounds.max_y), "v", "right"),
        ]

    def _update_position_readout(
        self,
        cutout: Polygon2D | None,
        outline: Polygon2D | None,
        position: dict[str, float],
    ) -> None:
        if cutout is None or outline is None or self.selected_cutout_kind == "none":
            self.cutout_position_x_value.setText("—")
            self.cutout_position_y_value.setText("—")
            return
        bounds = cutout.bounds()
        center_x = bounds.min_x + bounds.width / 2.0
        center_y = bounds.min_y + bounds.height / 2.0
        self.cutout_position_x_value.setText(f"{center_x:.0f} cm")
        self.cutout_position_y_value.setText(f"{center_y:.0f} cm")

    def _go_to_shape_step(self) -> None:
        self.step_stack.setCurrentWidget(self.shape_step)
        self._refresh_step_actions()

    def _go_to_cutout_step(self) -> None:
        self._store_current_shape_values()
        self.step_stack.setCurrentWidget(self.cutout_step)
        self._refresh_dialog_state()

    def _refresh_step_actions(self) -> None:
        is_cutout_step = self.step_stack.currentWidget() is self.cutout_step
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.back_button.setVisible(is_cutout_step)
        self.next_button.setVisible(not is_cutout_step)
        ok_button.setVisible(is_cutout_step)
        self.next_button.setEnabled(not self._shape_issues)
        ok_button.setEnabled(not self._shape_issues and not self._cutout_issues)

    def _refresh_shape_preview(self) -> None:
        self._refresh_dialog_state()

    def _refresh_cutout_preview(self) -> None:
        self._refresh_dialog_state()

    def accept(self) -> None:
        self._refresh_dialog_state()
        if self._shape_issues or self._cutout_issues:
            return

        self._store_current_shape_values()
        self._store_current_cutout_values()
        self.config_data["add_polac_dialog"] = merge_add_polac_dialog_cache(
            {
                "last_shape": self.selected_shape_key,
                "last_cutout": self.selected_cutout_kind,
                "flip_h": self.flip_h_button.isChecked(),
                "flip_v": self.flip_v_button.isChecked(),
                "shapes": self._shape_values,
                "cutouts": self._cutout_values,
                "cutout_positions": self._cutout_positions,
            }
        )
        super().accept()

    def get_result(self) -> AddPolacResult | None:
        if self.result() != QDialog.DialogCode.Accepted:
            return None
        self._store_current_shape_values()
        self._store_current_cutout_values()
        cutout_values = {}
        if self.selected_cutout_kind != "none":
            cutout_values = dict(self._cutout_values[self.selected_cutout_kind])
        return AddPolacResult(
            shape_key=self.selected_shape_key,
            shape_values=dict(self._shape_values[self.selected_shape_key]),
            cutout_kind=self.selected_cutout_kind,
            cutout_values=cutout_values,
            cutout_position=dict(self._cutout_positions.get(self.selected_cutout_kind, default_cutout_position())),
            flip_h=self.flip_h_button.isChecked(),
            flip_v=self.flip_v_button.isChecked(),
        )

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)
