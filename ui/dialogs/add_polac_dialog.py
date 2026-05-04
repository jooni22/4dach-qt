"""Wizard dialog for creating a roof plane outline with an optional cutout."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.geometry import build_add_polac_cutout, build_add_polac_outline, flip_polygon_in_bounds
from core.models import Polygon2D
from ui.dialogs.add_polac_catalog import (
    CUTOUT_CATALOG,
    CUTOUT_CATALOG_BY_KEY,
    SHAPE_CATALOG,
    SHAPE_CATALOG_BY_KEY,
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
        self.setMinimumHeight(180)

    def set_polygons(
        self,
        outline: Polygon2D | None,
        holes: list[Polygon2D] | None = None,
        *,
        placeholder: str = "Podgląd",
    ) -> None:
        self._outline = outline
        self._holes = list(holes or [])
        self._placeholder = placeholder
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
        margin = 20.0
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


def _make_tile_icon(points: tuple[tuple[float, float], ...], *, size: int = 64) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    if not points:
        return QIcon(pixmap)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    margin = 8.0
    span = size - 2 * margin
    painter.setPen(QPen(QColor("#475569"), 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    polygon = QPolygonF([QPointF(margin + x * span, margin + y * span) for x, y in points])
    painter.drawPolygon(polygon)
    painter.end()
    return QIcon(pixmap)


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

        self._build_ui()
        self._rebuild_shape_form(self.selected_shape_key)
        self._rebuild_cutout_form(self.selected_cutout_kind)
        self.flip_h_checkbox.setChecked(bool(self._cache["flip_h"]))
        self.flip_v_checkbox.setChecked(bool(self._cache["flip_v"]))
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
        self.back_button = self.button_box.addButton("Wstecz", QDialogButtonBox.ButtonRole.ActionRole)
        self.next_button = self.button_box.addButton("Dalej", QDialogButtonBox.ButtonRole.ActionRole)
        self.button_box.rejected.connect(self.reject)
        self.button_box.accepted.connect(self.accept)
        self.back_button.clicked.connect(self._go_to_shape_step)
        self.next_button.clicked.connect(self._go_to_cutout_step)
        layout.addWidget(self.button_box)

    def _build_shape_step(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)

        gallery_group = QGroupBox("Krok 1. Wybierz kształt połaci", page)
        gallery_layout = QGridLayout(gallery_group)
        gallery_layout.setHorizontalSpacing(8)
        gallery_layout.setVerticalSpacing(8)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for index, shape in enumerate(SHAPE_CATALOG):
            button = QToolButton(gallery_group)
            button.setText(shape.label)
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setIcon(_make_tile_icon(shape.preview_points))
            button.setIconSize(button.icon().actualSize(button.sizeHint()))
            button.setMinimumSize(110, 100)
            button.clicked.connect(lambda checked, key=shape.key: self._on_shape_selected(key, checked))
            if shape.key == self.selected_shape_key:
                button.setChecked(True)
            group.addButton(button)
            gallery_layout.addWidget(button, index // 3, index % 3)
            self.shape_buttons[shape.key] = button
        layout.addWidget(gallery_group)

        content_layout = QHBoxLayout()
        preview_column = QVBoxLayout()
        preview_column.addWidget(QLabel("Podgląd obrysu:", page))
        self.shape_preview = _PolygonPreviewWidget(page)
        preview_column.addWidget(self.shape_preview)

        flip_row = QHBoxLayout()
        self.flip_h_checkbox = QCheckBox("Flip H", page)
        self.flip_v_checkbox = QCheckBox("Flip V", page)
        self.flip_h_checkbox.toggled.connect(self._refresh_shape_preview)
        self.flip_v_checkbox.toggled.connect(self._refresh_shape_preview)
        flip_row.addWidget(self.flip_h_checkbox)
        flip_row.addWidget(self.flip_v_checkbox)
        flip_row.addStretch(1)
        preview_column.addLayout(flip_row)
        content_layout.addLayout(preview_column, 1)

        self.shape_form_host = QWidget(page)
        self.shape_form_host.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.shape_form_host_layout = QVBoxLayout(self.shape_form_host)
        self.shape_form_host_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self.shape_form_host, 1)
        layout.addLayout(content_layout)
        return page

    def _build_cutout_step(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)

        gallery_group = QGroupBox("Krok 2. Wybierz wycinek", page)
        gallery_layout = QGridLayout(gallery_group)
        gallery_layout.setHorizontalSpacing(8)
        gallery_layout.setVerticalSpacing(8)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for index, cutout in enumerate(CUTOUT_CATALOG):
            button = QToolButton(gallery_group)
            button.setText(cutout.label)
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setIcon(_make_tile_icon(cutout.preview_points))
            button.setIconSize(button.icon().actualSize(button.sizeHint()))
            button.setMinimumSize(110, 100)
            button.clicked.connect(lambda checked, key=cutout.key: self._on_cutout_selected(key, checked))
            if cutout.key == self.selected_cutout_kind:
                button.setChecked(True)
            group.addButton(button)
            gallery_layout.addWidget(button, index // 2, index % 2)
            self.cutout_buttons[cutout.key] = button
        layout.addWidget(gallery_group)

        content_layout = QHBoxLayout()
        self.cutout_form_host = QWidget(page)
        self.cutout_form_host.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.cutout_form_host_layout = QVBoxLayout(self.cutout_form_host)
        self.cutout_form_host_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self.cutout_form_host, 1)

        preview_column = QVBoxLayout()
        preview_column.addWidget(QLabel("Podgląd połaci z wycinkiem:", page))
        self.cutout_preview = _PolygonPreviewWidget(page)
        preview_column.addWidget(self.cutout_preview)
        content_layout.addLayout(preview_column, 1)
        layout.addLayout(content_layout)
        return page

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
        self._clear_layout(self.cutout_form_host_layout)

        cutout = CUTOUT_CATALOG_BY_KEY[cutout_key]
        if cutout.key == "none":
            self.cutout_form_host_layout.addWidget(QLabel("Bez wycinka - brak dodatkowych parametrów.", self.cutout_form_host))
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
        self.cutout_form_host_layout.addWidget(form_group)
        self.cutout_form_host_layout.addStretch(1)

    def _build_spin_box(self, parent: QWidget, max_value: int, value: int) -> QSpinBox:
        spin = QSpinBox(parent)
        spin.setRange(1, max_value)
        spin.setSuffix(" cm")
        spin.setValue(value)
        return spin

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
        return {
            key: field.value()
            for key, field in self.shape_form_fields.items()
        }

    def _current_cutout_values(self) -> dict:
        return {
            key: field.value()
            for key, field in self.cutout_form_fields.items()
        }

    def _current_outline(self) -> Polygon2D:
        outline = build_add_polac_outline(self.selected_shape_key, self._current_shape_values())
        return flip_polygon_in_bounds(
            outline,
            horizontal=self.flip_h_checkbox.isChecked(),
            vertical=self.flip_v_checkbox.isChecked(),
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
        self.shape_preview.set_polygons(self._current_outline(), placeholder="Uzupełnij parametry połaci")
        self._refresh_cutout_preview()

    def _refresh_cutout_preview(self) -> None:
        outline = self._current_outline()
        cutout = self._current_cutout()
        holes = [] if cutout is None else [cutout]
        self.cutout_preview.set_polygons(outline, holes, placeholder="Najpierw zdefiniuj obrys połaci")

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
                "flip_h": self.flip_h_checkbox.isChecked(),
                "flip_v": self.flip_v_checkbox.isChecked(),
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
            flip_h=self.flip_h_checkbox.isChecked(),
            flip_v=self.flip_v_checkbox.isChecked(),
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
