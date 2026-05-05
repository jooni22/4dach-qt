"""Wizard dialog for creating a roof plane outline with an optional cutout."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.geometry import build_add_polac_cutout, build_add_polac_outline, flip_polygon_in_bounds
from core.models import Point2D, Polygon2D
from ui.dialogs.add_polac_catalog import (
    CUTOUT_CATALOG,
    CUTOUT_CATALOG_BY_KEY,
    SHAPE_CATALOG,
    SHAPE_CATALOG_BY_KEY,
    default_shape_values,
    merge_add_polac_dialog_cache,
    seed_add_polac_dialog_cache,
)


@dataclass(slots=True)
class AddPolacResult:
    shape_key: str
    shape_values: dict
    cutout_kind: str
    cutout_values: dict
    flip_h: bool
    flip_v: bool


class _PolygonPreviewWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._outline: Polygon2D | None = None
        self._holes: list[Polygon2D] = []
        self._placeholder = "Podgląd"
        self._dimension_labels: tuple[str, ...] = ()
        self._highlight_dimension: str | None = None
        self.setMinimumHeight(180)

    def set_polygons(
        self,
        outline: Polygon2D | None,
        holes: list[Polygon2D] | None = None,
        *,
        placeholder: str = "Podgląd",
        dimension_labels: tuple[str, ...] = (),
        highlight_dimension: str | None = None,
    ) -> None:
        self._outline = outline
        self._holes = list(holes or [])
        self._placeholder = placeholder
        self._dimension_labels = dimension_labels
        self._highlight_dimension = highlight_dimension
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f8fafc"))
        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)

        if self._outline is None:
            painter.setPen(QColor("#64748b"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._placeholder)
            return

        all_points = list(self._outline.points)
        for hole in self._holes:
            all_points.extend(hole.points)
        min_x = min(point.x for point in all_points)
        min_y = min(point.y for point in all_points)
        max_x = max(point.x for point in all_points)
        max_y = max(point.y for point in all_points)
        width = max(max_x - min_x, 1.0)
        height = max(max_y - min_y, 1.0)
        margin = 32.0
        scale = min((self.width() - 2 * margin) / width, (self.height() - 2 * margin) / height)
        offset_x = (self.width() - width * scale) / 2.0
        offset_y = (self.height() - height * scale) / 2.0

        def _to_polygon(polygon: Polygon2D) -> QPolygonF:
            return QPolygonF(
                [
                    QPointF(
                        offset_x + (point.x - min_x) * scale,
                        offset_y + (point.y - min_y) * scale,
                    )
                    for point in polygon.points
                ]
            )

        path = QPainterPath()
        path.addPolygon(_to_polygon(self._outline))
        for hole in self._holes:
            hole_path = QPainterPath()
            hole_path.addPolygon(_to_polygon(hole))
            path = path.subtracted(hole_path)

        painter.fillPath(path, QColor("#dbeafe"))
        painter.setPen(QPen(QColor("#2563eb"), 2))
        painter.drawPolygon(_to_polygon(self._outline))
        painter.setPen(QPen(QColor("#dc2626"), 2))
        for hole in self._holes:
            painter.drawPolygon(_to_polygon(hole))

        self._draw_dimensions(painter, min_x, min_y, max_x, max_y, scale, offset_x, offset_y)

    def _draw_dimensions(
        self,
        painter: QPainter,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        scale: float,
        offset_x: float,
        offset_y: float,
    ) -> None:
        if not self._dimension_labels:
            return

        def to_point(x: float, y: float) -> QPointF:
            return QPointF(offset_x + (x - min_x) * scale, offset_y + (y - min_y) * scale)

        def draw_labelled_line(
            label: str, start: QPointF, end: QPointF, text_offset: QPointF
        ) -> None:
            active = label == self._highlight_dimension
            color = QColor("#1d4ed8" if active else "#64748b")
            painter.setPen(QPen(color, 2 if active else 1))
            painter.drawLine(start, end)
            painter.setPen(color)
            mid = QPointF((start.x() + end.x()) / 2.0, (start.y() + end.y()) / 2.0)
            text_rect = QRectF(
                mid.x() + text_offset.x() - 10, mid.y() + text_offset.y() - 9, 20, 18
            )
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)

        top_y = offset_y - 10
        bottom_y = offset_y + (max_y - min_y) * scale + 12
        left_x = offset_x - 12
        top_start = to_point(min_x, min_y)
        top_end = to_point(max_x, min_y)
        bottom_start = to_point(min_x, max_y)
        bottom_end = to_point(max_x, max_y)
        left_top = to_point(min_x, min_y)
        left_bottom = to_point(min_x, max_y)

        if "A" in self._dimension_labels:
            draw_labelled_line(
                "A",
                QPointF(bottom_start.x(), bottom_y),
                QPointF(bottom_end.x(), bottom_y),
                QPointF(0, 12),
            )
        if "B" in self._dimension_labels:
            draw_labelled_line(
                "B",
                QPointF(top_start.x(), top_y),
                QPointF(top_end.x(), top_y),
                QPointF(0, -10),
            )
        if "H" in self._dimension_labels:
            draw_labelled_line(
                "H",
                QPointF(left_x, left_top.y()),
                QPointF(left_x, left_bottom.y()),
                QPointF(-12, 0),
            )
        if (
            "E" in self._dimension_labels
            and self._outline is not None
            and len(self._outline.points) >= 4
        ):
            top_left = self._outline.points[0]
            bottom_left = self._outline.points[-1]
            start = to_point(min(top_left.x, bottom_left.x), min_y)
            end = to_point(max(top_left.x, bottom_left.x), min_y)
            if abs(end.x() - start.x()) > 1:
                draw_labelled_line(
                    "E",
                    QPointF(start.x(), top_y - 16),
                    QPointF(end.x(), top_y - 16),
                    QPointF(0, -10),
                )


def _make_tile_icon(polygon: Polygon2D | None, *, size: int = 64) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    if polygon is None or not polygon.points:
        return QIcon(pixmap)

    bounds = polygon.bounds()
    width = max(bounds.width, 1.0)
    height = max(bounds.height, 1.0)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    margin = 8.0
    scale = min((size - 2 * margin) / width, (size - 2 * margin) / height)
    offset_x = (size - width * scale) / 2.0
    offset_y = (size - height * scale) / 2.0
    painter.setPen(QPen(QColor("#475569"), 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    points = QPolygonF(
        [
            QPointF(
                offset_x + (point.x - bounds.min_x) * scale,
                offset_y + (point.y - bounds.min_y) * scale,
            )
            for point in polygon.points
        ]
    )
    painter.drawPolygon(points)
    painter.end()
    return QIcon(pixmap)


def _shape_tile_icon(shape_key: str) -> QIcon:
    return _make_tile_icon(
        build_add_polac_outline(shape_key, default_shape_values(shape_key)),
        size=78,
    )


def _cutout_tile_icon(points: tuple[tuple[float, float], ...]) -> QIcon:
    if not points:
        return _make_tile_icon(None)
    return _make_tile_icon(Polygon2D([Point2D(x, y) for x, y in points]))


def _tile_button_stylesheet() -> str:
    return """
        QToolButton {
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            background: #ffffff;
            padding: 6px;
            color: #0f172a;
        }
        QToolButton:checked {
            border: 2px solid #2563eb;
            background: #eff6ff;
            color: #1d4ed8;
        }
    """


def _dimension_label_for_field(field_label: str) -> str:
    return field_label.split(" ", 1)[0]


class AddPolacDialog(QDialog):
    def __init__(self, config_data: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Kreator połaci")
        self.resize(920, 620)
        self.config_data = config_data

        self._cache = seed_add_polac_dialog_cache(config_data)
        self.selected_shape_key = self._cache["last_shape"]
        self.selected_cutout_kind = self._cache["last_cutout"]
        self._shape_values = {key: dict(values) for key, values in self._cache["shapes"].items()}
        self._cutout_values = {key: dict(values) for key, values in self._cache["cutouts"].items()}

        self.shape_buttons: dict[str, QToolButton] = {}
        self.cutout_buttons: dict[str, QToolButton] = {}
        self.shape_form_fields: dict[str, QSpinBox] = {}
        self.cutout_form_fields: dict[str, QSpinBox] = {}
        self.cutout_position_sliders: dict[str, QSlider] = {}
        self._focused_shape_field_key: str | None = None

        self._build_ui()
        self._rebuild_shape_form(self.selected_shape_key)
        self._rebuild_cutout_form(self.selected_cutout_kind)
        self.flip_h_button.setChecked(bool(self._cache["flip_h"]))
        self.flip_v_button.setChecked(bool(self._cache["flip_v"]))
        self._refresh_step_actions()
        self._refresh_shape_preview()
        self._refresh_cutout_preview()

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
        self.back_button = self.button_box.addButton(
            "Wstecz", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.next_button = self.button_box.addButton(
            "Dalej", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.button_box.rejected.connect(self.reject)
        self.button_box.accepted.connect(self.accept)
        self.back_button.clicked.connect(self._go_to_shape_step)
        self.next_button.clicked.connect(self._go_to_cutout_step)
        layout.addWidget(self.button_box)

    def _build_shape_step(self) -> QWidget:
        page = QWidget(self)
        layout = QHBoxLayout(page)

        gallery_group = QGroupBox("Krok 1. Biblioteka połaci", page)
        gallery_group.setMinimumWidth(300)
        gallery_group_layout = QVBoxLayout(gallery_group)
        gallery_widget = QWidget(gallery_group)
        gallery_layout = QGridLayout(gallery_widget)
        gallery_layout.setContentsMargins(10, 10, 18, 10)
        gallery_layout.setHorizontalSpacing(8)
        gallery_layout.setVerticalSpacing(8)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for index, shape in enumerate(SHAPE_CATALOG):
            button = QToolButton(gallery_group)
            button.setText(shape.label)
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setIcon(_shape_tile_icon(shape.key))
            button.setIconSize(QSize(78, 78))
            button.setMinimumSize(124, 112)
            button.setStyleSheet(_tile_button_stylesheet())
            button.clicked.connect(
                lambda checked, key=shape.key: self._on_shape_selected(key, checked)
            )
            if shape.key == self.selected_shape_key:
                button.setChecked(True)
            group.addButton(button)
            gallery_layout.addWidget(button, index // 2, index % 2)
            self.shape_buttons[shape.key] = button
        gallery_layout.setRowStretch((len(SHAPE_CATALOG) + 1) // 2, 1)
        self.shape_library_scroll = QScrollArea(gallery_group)
        self.shape_library_scroll.setWidgetResizable(True)
        self.shape_library_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.shape_library_scroll.setWidget(gallery_widget)
        gallery_group_layout.addWidget(self.shape_library_scroll)
        layout.addWidget(gallery_group, 0)

        workspace_layout = QVBoxLayout()
        preview_column = QVBoxLayout()
        preview_column.addWidget(QLabel("Podgląd obrysu:", page))
        self.shape_preview = _PolygonPreviewWidget(page)
        self.shape_preview.setMinimumSize(320, 320)
        preview_column.addWidget(self.shape_preview, 1)
        workspace_layout.addLayout(preview_column, 1)

        self.shape_parameters_panel = QGroupBox("Parametry", page)
        parameters_layout = QVBoxLayout(self.shape_parameters_panel)
        self.shape_form_host = QWidget(self.shape_parameters_panel)
        self.shape_form_host.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.shape_form_host_layout = QVBoxLayout(self.shape_form_host)
        self.shape_form_host_layout.setContentsMargins(0, 0, 0, 0)
        parameters_layout.addWidget(self.shape_form_host, 1)

        tools_group = QGroupBox("Narzędzia", self.shape_parameters_panel)
        tools_layout = QHBoxLayout(tools_group)
        self.flip_h_button = self._build_flip_button("Odbij poziomo", tools_group)
        self.flip_v_button = self._build_flip_button("Odbij pionowo", tools_group)
        self.flip_h_button.toggled.connect(self._refresh_shape_preview)
        self.flip_v_button.toggled.connect(self._refresh_shape_preview)
        tools_layout.addWidget(self.flip_h_button)
        tools_layout.addWidget(self.flip_v_button)
        tools_layout.addStretch(1)
        parameters_layout.addWidget(tools_group, 0)
        workspace_layout.addWidget(self.shape_parameters_panel, 0)
        layout.addLayout(workspace_layout, 1)
        return page

    def _build_cutout_step(self) -> QWidget:
        page = QWidget(self)
        layout = QHBoxLayout(page)

        gallery_group = QGroupBox("Krok 2. Biblioteka wycinków", page)
        gallery_group.setMinimumWidth(260)
        gallery_group_layout = QVBoxLayout(gallery_group)
        gallery_widget = QWidget(gallery_group)
        gallery_layout = QGridLayout(gallery_widget)
        gallery_layout.setContentsMargins(10, 10, 18, 10)
        gallery_layout.setHorizontalSpacing(8)
        gallery_layout.setVerticalSpacing(8)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for index, cutout in enumerate(CUTOUT_CATALOG):
            button = QToolButton(gallery_group)
            button.setText(cutout.label)
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setIcon(_cutout_tile_icon(cutout.preview_points))
            button.setIconSize(button.icon().actualSize(button.sizeHint()))
            button.setMinimumSize(110, 100)
            button.setStyleSheet(_tile_button_stylesheet())
            button.clicked.connect(
                lambda checked, key=cutout.key: self._on_cutout_selected(key, checked)
            )
            if cutout.key == self.selected_cutout_kind:
                button.setChecked(True)
            group.addButton(button)
            gallery_layout.addWidget(button, index // 2, index % 2)
            self.cutout_buttons[cutout.key] = button
        gallery_layout.setRowStretch((len(CUTOUT_CATALOG) + 1) // 2, 1)
        self.cutout_library_scroll = QScrollArea(gallery_group)
        self.cutout_library_scroll.setWidgetResizable(True)
        self.cutout_library_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.cutout_library_scroll.setWidget(gallery_widget)
        gallery_group_layout.addWidget(self.cutout_library_scroll)
        layout.addWidget(gallery_group, 0)

        workspace_layout = QVBoxLayout()
        preview_column = QVBoxLayout()
        preview_column.addWidget(QLabel("Podgląd połaci z wycinkiem:", page))
        self.cutout_preview = _PolygonPreviewWidget(page)
        self.cutout_preview.setMinimumSize(340, 320)
        preview_column.addWidget(self.cutout_preview, 1)
        workspace_layout.addLayout(preview_column, 1)

        self.cutout_parameters_panel = QGroupBox("Parametry", page)
        parameters_layout = QVBoxLayout(self.cutout_parameters_panel)
        self.cutout_form_host = QWidget(self.cutout_parameters_panel)
        self.cutout_form_host.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.cutout_form_host_layout = QVBoxLayout(self.cutout_form_host)
        self.cutout_form_host_layout.setContentsMargins(0, 0, 0, 0)
        parameters_layout.addWidget(self.cutout_form_host, 1)
        workspace_layout.addWidget(self.cutout_parameters_panel, 0)
        layout.addLayout(workspace_layout, 1)
        return page

    def _build_flip_button(self, text: str, parent: QWidget) -> QToolButton:
        button = QToolButton(parent)
        button.setText(text)
        button.setCheckable(True)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setMinimumHeight(32)
        button.setStyleSheet(
            """
            QToolButton {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                background: #ffffff;
                padding: 6px 10px;
                color: #0f172a;
            }
            QToolButton:checked {
                border-color: #2563eb;
                background: #dbeafe;
                color: #1d4ed8;
            }
            """
        )
        return button

    def _on_shape_selected(self, shape_key: str, checked: bool) -> None:
        if not checked or shape_key == self.selected_shape_key:
            return
        self._store_current_shape_values()
        self.selected_shape_key = shape_key
        self._rebuild_shape_form(shape_key)
        self._refresh_shape_preview()

    def _on_cutout_selected(self, cutout_key: str, checked: bool) -> None:
        if not checked or cutout_key == self.selected_cutout_kind:
            return
        self._store_current_cutout_values()
        self.selected_cutout_kind = cutout_key
        self._rebuild_cutout_form(cutout_key)
        self._refresh_cutout_preview()

    def _rebuild_shape_form(self, shape_key: str) -> None:
        self.shape_form_fields = {}
        self._focused_shape_field_key = None
        self._clear_layout(self.shape_form_host_layout)

        shape = SHAPE_CATALOG_BY_KEY[shape_key]
        form_group = QGroupBox(f"Parametry: {shape.label}", self.shape_form_host)
        form_layout = QFormLayout(form_group)
        values = self._shape_values[shape_key]
        for field in shape.fields:
            spin = self._build_spin_box(form_group, field.max_value, values[field.key])
            spin.valueChanged.connect(self._on_shape_value_changed)
            self.shape_form_fields[field.key] = spin
            form_layout.addRow(field.label, spin)
        self.shape_form_host_layout.addWidget(form_group)
        self.shape_form_host_layout.addStretch(1)

    def _rebuild_cutout_form(self, cutout_key: str) -> None:
        self.cutout_form_fields = {}
        self.cutout_position_sliders = {}
        self._clear_layout(self.cutout_form_host_layout)

        cutout = CUTOUT_CATALOG_BY_KEY[cutout_key]
        if cutout.key == "none":
            self.cutout_form_host_layout.addWidget(
                QLabel("Bez wycinka - brak dodatkowych parametrów.", self.cutout_form_host)
            )
            self.cutout_form_host_layout.addStretch(1)
            return

        form_group = QGroupBox(f"Parametry: {cutout.label}", self.cutout_form_host)
        form_layout = QFormLayout(form_group)
        values = self._cutout_values[cutout_key]
        for field in cutout.fields:
            spin = self._build_spin_box(form_group, field.max_value, values[field.key])
            spin.valueChanged.connect(self._on_cutout_value_changed)
            self.cutout_form_fields[field.key] = spin
            form_layout.addRow(field.label, spin)
        for key in ("X", "Y"):
            slider = self._build_position_slider(form_group, values.get(key, 50))
            slider.valueChanged.connect(self._on_cutout_value_changed)
            self.cutout_position_sliders[key] = slider
            form_layout.addRow(f"{key}:", slider)
        self.cutout_form_host_layout.addWidget(form_group)
        self.cutout_form_host_layout.addStretch(1)

    def _build_spin_box(self, parent: QWidget, max_value: int, value: int) -> QSpinBox:
        spin = QSpinBox(parent)
        spin.setRange(1, max_value)
        spin.setSuffix(" cm")
        spin.setValue(value)
        spin.installEventFilter(self)
        return spin

    def _build_position_slider(self, parent: QWidget, value: int) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal, parent)
        slider.setRange(0, 100)
        slider.setSingleStep(1)
        slider.setPageStep(5)
        slider.setValue(max(0, min(100, int(value))))
        return slider

    def eventFilter(self, watched, event) -> bool:
        if event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            shape_field_key = self._shape_field_key_for_widget(watched)
            if shape_field_key is not None:
                self._focused_shape_field_key = (
                    shape_field_key if event.type() == QEvent.Type.FocusIn else None
                )
                self._refresh_shape_preview()
            elif watched in self.cutout_form_fields.values():
                self._refresh_cutout_preview()
        return super().eventFilter(watched, event)

    def _on_shape_value_changed(self) -> None:
        self._refresh_shape_preview()

    def _on_cutout_value_changed(self) -> None:
        self._refresh_cutout_preview()

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
        values = {key: field.value() for key, field in self.cutout_form_fields.items()}
        values.update(
            {key: slider.value() for key, slider in self.cutout_position_sliders.items()}
        )
        return values

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
        return build_add_polac_cutout(
            self.selected_cutout_kind,
            self._current_cutout_values(),
            outline,
        )

    def _refresh_shape_preview(self) -> None:
        self.shape_preview.set_polygons(
            self._current_outline(),
            placeholder="Uzupełnij parametry połaci",
            dimension_labels=self._shape_dimension_labels(),
            highlight_dimension=self._focused_shape_dimension(),
        )
        self._refresh_cutout_preview()

    def _refresh_cutout_preview(self) -> None:
        outline = self._current_outline()
        cutout = self._current_cutout()
        holes = [] if cutout is None else [cutout]
        self.cutout_preview.set_polygons(
            outline,
            holes,
            placeholder="Najpierw zdefiniuj obrys połaci",
            dimension_labels=self._shape_dimension_labels(),
            highlight_dimension=self._focused_shape_dimension(),
        )

    def _shape_dimension_labels(self) -> tuple[str, ...]:
        labels: list[str] = []
        for field in SHAPE_CATALOG_BY_KEY[self.selected_shape_key].fields:
            label = _dimension_label_for_field(field.label)
            if label not in labels:
                labels.append(label)
        return tuple(labels)

    def _focused_shape_dimension(self) -> str | None:
        if self._focused_shape_field_key is None:
            return None
        for field in SHAPE_CATALOG_BY_KEY[self.selected_shape_key].fields:
            if field.key == self._focused_shape_field_key:
                return _dimension_label_for_field(field.label)
        return None

    def _shape_field_key_for_widget(self, widget) -> str | None:
        for key, field in self.shape_form_fields.items():
            if field is widget:
                return key
        return None

    def _go_to_shape_step(self) -> None:
        self.step_stack.setCurrentWidget(self.shape_step)
        self._refresh_step_actions()

    def _go_to_cutout_step(self) -> None:
        self._store_current_shape_values()
        self.step_stack.setCurrentWidget(self.cutout_step)
        self._refresh_step_actions()
        self._refresh_cutout_preview()

    def _refresh_step_actions(self) -> None:
        is_cutout_step = self.step_stack.currentWidget() is self.cutout_step
        self.back_button.setVisible(is_cutout_step)
        self.next_button.setVisible(not is_cutout_step)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setVisible(is_cutout_step)

    def accept(self) -> None:
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
            flip_h=self.flip_h_button.isChecked(),
            flip_v=self.flip_v_button.isChecked(),
        )

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)
