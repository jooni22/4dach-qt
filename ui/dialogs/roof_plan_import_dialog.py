from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.geometry import polygon_edges, segment_length
from core.models import Bounds2D, Point2D, Polygon2D
from core.roof_plan_import import (
    cleanup_import_points,
    longest_edge_index,
    normalize_polygon_to_reference_edge,
    validate_import_polygon,
)
from ui.canvas.snap_helpers import resolve_angular_snap, resolve_axis_snap
from ui.dialogs.button_text import show_warning


@dataclass(slots=True)
class _ImportDraft:
    points: list[Point2D]
    reference_edge_index: int
    reference_length_cm: float = 0.0


class RoofPlanImportCanvas(QWidget):
    crop_changed = Signal()
    draft_closed = Signal(list)

    MODE_CROP = "crop"
    MODE_DRAW = "draw"

    def __init__(self, image_path: Path | str, parent=None) -> None:
        super().__init__(parent)
        self._pixmap = QPixmap(str(image_path))
        self._crop_rect = QRectF()
        self._draft_points: list[Point2D] = []
        self._drafts: list[list[Point2D]] = []
        self._mode = self.MODE_CROP
        self._drag_start: Point2D | None = None
        self._zoom_mode = "fit"
        self._zoom_factor = 1.0
        self.image_opacity = 0.75
        self.line_opacity = 1.0
        self.show_image = True
        self.setMinimumSize(520, 360)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self.update()

    def set_crop_rect(self, rect: QRectF) -> None:
        self._crop_rect = rect.normalized()
        self.crop_changed.emit()
        self.update()

    def crop_rect(self) -> QRectF:
        return QRectF(self._crop_rect)

    def has_crop(self) -> bool:
        return self._crop_rect.width() >= 5 and self._crop_rect.height() >= 5

    def set_fit_zoom(self) -> None:
        self._zoom_mode = "fit"
        self.update()

    def set_zoom_factor(self, factor: float) -> None:
        self._zoom_mode = "manual"
        self._zoom_factor = max(0.1, min(8.0, factor))
        self.update()

    def zoom_in(self) -> None:
        self.set_zoom_factor(self._zoom_factor * 1.25)

    def zoom_out(self) -> None:
        self.set_zoom_factor(self._zoom_factor / 1.25)

    def zoom_mode(self) -> str:
        return self._zoom_mode

    def zoom_factor(self) -> float:
        return self._zoom_factor

    def set_drafts(self, drafts: list[list[Point2D]]) -> None:
        self._drafts = [[Point2D(point.x, point.y) for point in draft] for draft in drafts]
        self.update()

    def draft_points(self) -> list[Point2D]:
        return list(self._draft_points)

    def add_sketch_point(self, point: Point2D) -> None:
        self._draft_points.append(point)
        self.update()

    def close_active_sketch(self) -> bool:
        issues = validate_import_polygon(self._draft_points)
        if issues:
            return False
        points = cleanup_import_points(self._draft_points)
        self._drafts.append(points)
        self._draft_points = []
        self.draft_closed.emit(points)
        self.update()
        return True

    def set_image_opacity(self, value: float) -> None:
        self.image_opacity = max(0.0, min(1.0, value))
        self.update()

    def set_line_opacity(self, value: float) -> None:
        self.line_opacity = max(0.0, min(1.0, value))
        self.update()

    def set_show_image(self, value: bool) -> None:
        self.show_image = bool(value)
        self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Z and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self._draft_points:
                self._draft_points.pop()
                self.update()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self._draft_points = []
            self.update()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._mode == self.MODE_CROP:
            point = self._canvas_to_image_point(event.position())
            if point is None:
                return
            self._drag_start = point
            self.set_crop_rect(QRectF(point.x, point.y, 0, 0))
            return
        point = self._canvas_to_image_point(event.position())
        if point is None:
            return
        if len(self._draft_points) >= 3 and segment_length(point, self._draft_points[0]) <= 8:
            self.close_active_sketch()
            return
        self.add_sketch_point(self._snap_point(point))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._mode != self.MODE_CROP or self._drag_start is None:
            return
        point = self._canvas_to_image_point(event.position())
        if point is not None:
            self.set_crop_rect(
                QRectF(
                    self._drag_start.x,
                    self._drag_start.y,
                    point.x - self._drag_start.x,
                    point.y - self._drag_start.y,
                )
            )

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._mode == self.MODE_CROP and self._drag_start is not None:
            point = self._canvas_to_image_point(event.position())
            if point is not None:
                self.set_crop_rect(
                    QRectF(
                        self._drag_start.x,
                        self._drag_start.y,
                        point.x - self._drag_start.x,
                        point.y - self._drag_start.y,
                    )
                )
            self._drag_start = None

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f8fafc"))
        target = self._image_target_rect()
        if not self._pixmap.isNull() and self.show_image:
            painter.setOpacity(self.image_opacity)
            painter.drawPixmap(target, self._pixmap, self._pixmap.rect())
            painter.setOpacity(1.0)
        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.drawRect(target)

        if self.has_crop():
            painter.setPen(QPen(QColor("#f59e0b"), 2))
            painter.drawRect(self._image_to_canvas_rect(self._crop_rect))

        painter.setOpacity(self.line_opacity)
        for draft in self._drafts:
            painter.setBrush(QColor(37, 99, 235, 45))
            self._draw_polyline(painter, draft, QColor("#2563eb"), closed=True)
        self._draw_polyline(painter, self._draft_points, QColor("#dc2626"), closed=False)
        painter.setOpacity(1.0)

    def _draw_polyline(
        self,
        painter: QPainter,
        points: list[Point2D],
        color: QColor,
        *,
        closed: bool,
    ) -> None:
        if not points:
            return
        mapped = QPolygonF([self._image_to_canvas_point(point) for point in points])
        painter.setPen(QPen(color, 2))
        if closed and len(points) >= 3:
            painter.drawPolygon(mapped)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(mapped)
        painter.setBrush(color)
        for point in mapped:
            painter.drawEllipse(point, 3.5, 3.5)

    def _snap_point(self, point: Point2D) -> Point2D:
        if not self._draft_points:
            return point
        start = self._draft_points[-1]
        axis_snap = resolve_axis_snap(point, start, threshold_deg=3.0)
        if axis_snap is not None:
            return axis_snap.point
        angular_snap = resolve_angular_snap(
            point,
            start,
            snap_to_45deg=True,
            threshold_45_deg=3.0,
            snap_to_3060deg=True,
            threshold_3060_deg=3.0,
        )
        if angular_snap is not None:
            return angular_snap.point
        return point

    def _image_target_rect(self) -> QRectF:
        if self._pixmap.isNull():
            return QRectF(self.rect())
        bounds = Bounds2D(0, 0, self._pixmap.width(), self._pixmap.height())
        available = QRectF(self.rect()).adjusted(12, 12, -12, -12)
        if self._zoom_mode == "manual":
            scale = self._zoom_factor
        else:
            scale = min(available.width() / bounds.width, available.height() / bounds.height)
        width = bounds.width * scale
        height = bounds.height * scale
        return QRectF(
            available.left() + (available.width() - width) / 2.0,
            available.top() + (available.height() - height) / 2.0,
            width,
            height,
        )

    def _canvas_to_image_point(self, point: QPointF) -> Point2D | None:
        target = self._image_target_rect()
        if not target.contains(point):
            return None
        if self._pixmap.isNull():
            return Point2D(point.x(), point.y())
        scale_x = self._pixmap.width() / target.width()
        scale_y = self._pixmap.height() / target.height()
        return Point2D(
            (point.x() - target.left()) * scale_x,
            (point.y() - target.top()) * scale_y,
        )

    def _image_to_canvas_point(self, point: Point2D) -> QPointF:
        target = self._image_target_rect()
        if self._pixmap.isNull():
            return QPointF(point.x, point.y)
        return QPointF(
            target.left() + point.x * target.width() / self._pixmap.width(),
            target.top() + point.y * target.height() / self._pixmap.height(),
        )

    def _image_to_canvas_rect(self, rect: QRectF) -> QRectF:
        top_left = self._image_to_canvas_point(Point2D(rect.left(), rect.top()))
        bottom_right = self._image_to_canvas_point(Point2D(rect.right(), rect.bottom()))
        return QRectF(top_left, bottom_right).normalized()

    def _canvas_to_image_rect(self, rect: QRectF) -> QRectF:
        top_left = self._canvas_to_image_point(rect.topLeft())
        bottom_right = self._canvas_to_image_point(rect.bottomRight())
        if top_left is None or bottom_right is None:
            return QRectF()
        return QRectF(
            top_left.x,
            top_left.y,
            bottom_right.x - top_left.x,
            bottom_right.y - top_left.y,
        ).normalized()


class RoofPlanImportWidget(QWidget):
    accepted = Signal(list)
    cancelled = Signal()

    def __init__(self, image_path: Path | str, app_settings, parent=None) -> None:
        super().__init__(parent)
        self._image_path = Path(image_path)
        self._app_settings = app_settings
        self._drafts: list[_ImportDraft] = []
        self._dimension_rows: list[tuple[QComboBox, QDoubleSpinBox]] = []
        self._build_ui()
        self._sync_buttons()

    def result_polygons(self) -> list[Polygon2D]:
        return [
            normalize_polygon_to_reference_edge(
                draft.points,
                reference_edge_index=draft.reference_edge_index,
                reference_length_cm=draft.reference_length_cm,
            )
            for draft in self._drafts
        ]

    def imported_drafts(self) -> list[list[Point2D]]:
        return [list(draft.points) for draft in self._drafts]

    def add_import_draft(self, points: list[Point2D]) -> None:
        cleaned = cleanup_import_points(points)
        issues = validate_import_polygon(cleaned, cleanup=False)
        if issues:
            show_warning(self, "Nieprawidłowa połać", "; ".join(issues))
            return
        self._drafts.append(_ImportDraft(cleaned, longest_edge_index(cleaned)))
        self.canvas.set_drafts(self.imported_drafts())
        self._rebuild_dimension_step()
        self._sync_buttons()

    def dimension_spin_for_draft(self, index: int) -> QDoubleSpinBox:
        return self._dimension_rows[index][1]

    def dimension_row_count(self) -> int:
        return len(self._dimension_rows)

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        left = QVBoxLayout()
        controls = QHBoxLayout()
        self.crop_mode_button = QPushButton("Kadruj", self)
        self.draw_mode_button = QPushButton("Rysuj", self)
        self.fit_button = QPushButton("Dopasuj", self)
        self.zoom_100_button = QPushButton("100%", self)
        self.zoom_in_button = QPushButton("+", self)
        self.zoom_out_button = QPushButton("-", self)
        self.show_image_toggle = QCheckBox("Pokaż obraz", self)
        self.show_image_toggle.setChecked(True)
        self.image_opacity_slider = self._opacity_slider(75)
        self.line_opacity_slider = self._opacity_slider(100)
        controls.addWidget(self.crop_mode_button)
        controls.addWidget(self.draw_mode_button)
        controls.addWidget(self.fit_button)
        controls.addWidget(self.zoom_100_button)
        controls.addWidget(self.zoom_in_button)
        controls.addWidget(self.zoom_out_button)
        controls.addWidget(self.show_image_toggle)
        controls.addWidget(QLabel("Obraz:", self))
        controls.addWidget(self.image_opacity_slider)
        controls.addWidget(QLabel("Linie:", self))
        controls.addWidget(self.line_opacity_slider)
        left.addLayout(controls)

        self.canvas = RoofPlanImportCanvas(self._image_path, self)
        self.canvas.set_mode(RoofPlanImportCanvas.MODE_DRAW)
        left.addWidget(self.canvas, 1)
        root.addLayout(left, 1)

        side = QVBoxLayout()
        side.addWidget(QLabel("Połacie z rzutu", self))
        self.add_plane_button = QPushButton("Dodaj połać", self)
        side.addWidget(self.add_plane_button)
        self._drafts_container = QWidget(self)
        self._dimensions_layout = QVBoxLayout(self._drafts_container)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(280)
        scroll.setWidget(self._drafts_container)
        side.addWidget(scroll, 1)
        self.import_button = QPushButton("Importuj", self)
        self.cancel_button = QPushButton("Anuluj", self)
        side.addWidget(self.import_button)
        side.addWidget(self.cancel_button)
        root.addLayout(side)

        self.canvas.crop_changed.connect(self._sync_buttons)
        self.canvas.draft_closed.connect(self.add_import_draft)
        self.crop_mode_button.clicked.connect(
            lambda: self.canvas.set_mode(RoofPlanImportCanvas.MODE_CROP)
        )
        self.draw_mode_button.clicked.connect(
            lambda: self.canvas.set_mode(RoofPlanImportCanvas.MODE_DRAW)
        )
        self.fit_button.clicked.connect(self.canvas.set_fit_zoom)
        self.zoom_100_button.clicked.connect(lambda: self.canvas.set_zoom_factor(1.0))
        self.zoom_in_button.clicked.connect(self.canvas.zoom_in)
        self.zoom_out_button.clicked.connect(self.canvas.zoom_out)
        self.show_image_toggle.toggled.connect(self.canvas.set_show_image)
        self.image_opacity_slider.valueChanged.connect(
            lambda value: self.canvas.set_image_opacity(value / 100)
        )
        self.line_opacity_slider.valueChanged.connect(
            lambda value: self.canvas.set_line_opacity(value / 100)
        )
        self.import_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.cancelled.emit)
        self.add_plane_button.clicked.connect(self._close_active_sketch_or_warn)

    def _opacity_slider(self, value: int) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal, self)
        slider.setRange(0, 100)
        slider.setValue(value)
        return slider

    def _close_active_sketch_or_warn(self) -> None:
        if not self.canvas.close_active_sketch():
            show_warning(self, "Nieprawidłowa połać", "Połać wymaga minimum 3 poprawnych punktów.")

    def _rebuild_dimension_step(self) -> None:
        self._clear_layout(self._dimensions_layout)
        self._dimension_rows = []
        self._dimensions_layout.addWidget(QLabel("Wybierz krawędź i wpisz długość w cm.", self))
        for index, draft in enumerate(self._drafts):
            row_widget = QWidget(self)
            row = QFormLayout(row_widget)
            row.addRow(QLabel(f"Połać {index + 1}: {len(draft.points)} pkt", row_widget))
            edge_combo = QComboBox(row_widget)
            for edge_index, (start, end) in enumerate(polygon_edges(Polygon2D(draft.points))):
                edge_combo.addItem(
                    f"Krawędź {edge_index + 1} ({segment_length(start, end):.1f} px)",
                    edge_index,
                )
            edge_combo.setCurrentIndex(draft.reference_edge_index)
            length_spin = QDoubleSpinBox(row_widget)
            length_spin.setRange(0.0, 100000.0)
            length_spin.setDecimals(2)
            length_spin.setSuffix(" cm")
            length_spin.setValue(draft.reference_length_cm)
            edge_combo.currentIndexChanged.connect(
                lambda _value, draft_index=index: self._update_reference_edge(draft_index)
            )
            length_spin.valueChanged.connect(
                lambda value, draft_index=index: self._update_reference_length(draft_index, value)
            )
            row.addRow(f"Połać {index + 1} krawędź:", edge_combo)
            row.addRow("Długość:", length_spin)
            self._dimensions_layout.addWidget(row_widget)
            self._dimension_rows.append((edge_combo, length_spin))
        self._dimensions_layout.addStretch(1)

    def _update_reference_edge(self, draft_index: int) -> None:
        combo = self._dimension_rows[draft_index][0]
        self._drafts[draft_index].reference_edge_index = int(combo.currentData())
        self._sync_buttons()

    def _update_reference_length(self, draft_index: int, value: float) -> None:
        self._drafts[draft_index].reference_length_cm = float(value)
        self._sync_buttons()

    def _all_dimensions_ready(self) -> bool:
        return bool(self._drafts) and all(draft.reference_length_cm > 0 for draft in self._drafts)

    def _sync_buttons(self) -> None:
        self.import_button.setEnabled(self._all_dimensions_ready())

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def accept(self) -> None:
        if not self._all_dimensions_ready():
            show_warning(self, "Brak wymiarów", "Każda połać musi mieć długość referencyjną.")
            return
        try:
            polygons = self.result_polygons()
        except ValueError as exc:
            show_warning(self, "Błąd importu", str(exc))
            return
        self.accepted.emit(polygons)


class RoofPlanImportDialog(QDialog):
    def __init__(self, image_path: Path | str, app_settings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Importuj połacie z rzutu")
        self.setMinimumSize(960, 640)
        self.widget = RoofPlanImportWidget(image_path, app_settings, self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.widget)
        self.widget.accepted.connect(lambda _polygons: super(RoofPlanImportDialog, self).accept())
        self.widget.cancelled.connect(self.reject)

    def result_polygons(self) -> list[Polygon2D]:
        return self.widget.result_polygons()
