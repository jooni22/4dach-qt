# Plan implementacji: `AddPolacDialog` — kreator połaci z wycinkiem/lukarną

## Kontekst i cel zadania

Istniejący kod aplikacji 4Dach-Qt pozwala użytkownikowi tworzyć połaci przez osobne małe
dialogi: `ProstokatDialog`, `TrojkatDialog`, `TrapezDialog`. Każdy z nich otwiera proste
okienko z polami wymiarów i zwraca `get_values() → dict`. Ten przepływ ma ograniczenia:
- Nie ma możliwości wyboru kształtu z wizualnej galerii
- Nie ma opcji flip (odbicie lustrzane) przy podglądzie
- Nie ma osadzania lukarny (wycinka) wewnątrz połaci

**Cel:** zastąpić te trzy osobne dialogi jednym dwuetapowym kreatorem `AddPolacDialog`,
który pozwoli użytkownikowi:

1. Wybrać kształt połaci z wizualnej galerii (9 kształtów z miniaturami rysowanymi przez `QPainter`)
2. Przypisać długości boków przez dynamiczny formularz (inne pola zależnie od kształtu)
3. Opcjonalnie odbić kształt poziomo (`Flip H`) i pionowo (`Flip V`) — niezależnie
4. Przejść do kroku 2 i opcjonalnie osadzić lukarnę (wycinek) — 3 rodzaje lub „Bez wycinka"
5. Zatwierdzić, co zwraca `PolacWizardResult` (dataclass) do callera

Lukarna jest automatycznie osadzana na środku połaci (bounding box center). Użytkownik może
pominąć lukarnę — będzie ją można dorysować ręcznie później (od punktu do punktu).

---

## Stan obecny kodu (baseline)

- `ui/dialogs/shape_dialogs.py` — `ProstokatDialog`, `TrojkatDialog`, `TrapezDialog` dziedziczą
  z `QDialog`, używają `QFormLayout`, `_load_values()` / `get_values()` → wzorzec spójny
- `ui/dialogs/__init__.py` — eksportuje wszystkie dialogi przez `__all__`
- `core/models.py` — dataclassy z `slots=True` dla wszystkich typów domenowych (np. `RoofPlane`,
  `Polygon2D`, `Point2D`)
- Caller (main_window / toolbar) wywołuje dialog przez `dlg.exec()` → `dlg.get_values()`

Nowe rozwiązanie zachowuje ten kontrakt interfejsowy: dialog → `exec()` → `get_result()` →
`PolacWizardResult`. Stare dialogi zostają — nie są usuwane do momentu audytu wszystkich call-site'ów.

---

## Architektura: drzewo klas

```
AddPolacDialog (QDialog)
│   setMinimumSize(920, 580)
│   QStackedWidget (2 strony)
│
├── Step 1 — ShapePickerWidget (wewnętrzny układ)
│   ├── ShapeGalleryWidget        ← QScrollArea + QGridLayout z QToolButton
│   │   └── QButtonGroup(exclusive=True)  ← prawidłowe exclusive selection
│   ├── ShapePreviewWidget        ← QPainter w paintEvent, transform flip
│   ├── DimensionFormWidget       ← QFormLayout odbudowywany dynamicznie
│   └── FlipControlsWidget        ← 2x QToolButton(checkable), BEZ QButtonGroup
│
└── Step 2 — LukarnaPicker
    ├── LukarnaPickerWidget        ← galeria lukarn + „Bez wycinka"
    │   └── ręczne exclusive selection (nie QButtonGroup, bo "none" nie jest przyciskiem radio)
    ├── LukarnaPreviewWidget       ← rysuje lukarnę nałożoną na obrys połaci
    └── dynamiczny QFormLayout dla wymiarów lukarny
```

---

## Warstwa 0 — `core/models.py` (dopisek na końcu pliku)

Projekt stosuje `@dataclass(slots=True)` na wszystkich typach — nowe klasy **muszą** to zachować.
`PolacWizardResult` jest celowo `frozen=False` — caller może potrzebować zmienić `flip_h/v`
po otrzymaniu wyniku.

```python
# core/models.py — dopisz NA KOŃCU, po klasie RoofPlane i funkcjach pomocniczych

@dataclass(slots=True)
class LukarnaSpec:
    """Parametric specification of a lukarna (dormer cutout)."""
    lukarna_type: str          # "lukarna1" | "lukarna2" | "lukarna3"
    dimensions: dict           # {"A": 80, "H1": 60, "H": 60} — values in cm

    def to_dict(self) -> dict:
        return {
            "lukarna_type": self.lukarna_type,
            "dimensions": dict(self.dimensions),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LukarnaSpec":
        return cls(
            lukarna_type=data["lukarna_type"],
            dimensions=dict(data.get("dimensions", {})),
        )


@dataclass(slots=True)
class PolacWizardResult:
    """
    Result returned by AddPolacDialog.
    Intentionally NOT frozen — callers may adjust flip after receiving result.
    Does NOT inherit from RoofPlane — it is raw wizard input, not a domain object.
    """
    shape_type: str            # "prostokat" | "trojkat" | "trapez_row" | ...
    dimensions: dict           # {"A": 800, "B": 300} — cm
    flip_h: bool = False
    flip_v: bool = False
    lukarna: "LukarnaSpec | None" = None

    def to_config_values(self) -> dict:
        """Serialize back to config_data["ksztalty"][shape_type] format."""
        return {
            "dims": dict(self.dimensions),
            "flip_h": self.flip_h,
            "flip_v": self.flip_v,
        }
```

**Dlaczego nie dodawać `PolacWizardResult` do `RoofPlane`?**
`RoofPlane.outline` przyjmuje `Polygon2D` — geometrię już obliczoną. `PolacWizardResult`
to surowe parametry przed przeliczeniem. Separacja zgodna z wzorcem
`get_values() → dict → caller builds domain object` stosowanym w istniejących dialogach.

---

## Warstwa 1 — `ui/dialogs/add_polac_dialog.py` (plik kompletny, nowy)

Stwórz nowy plik. Poniżej pełny kod produkcyjny:

```python
"""add_polac_dialog.py — Two-step wizard for creating a new roof plane (połać)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import (
    QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF, QTransform,
)
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QFormLayout, QGridLayout, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QSpinBox, QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

from core.models import LukarnaSpec, PolacWizardResult


# ---------------------------------------------------------------------------
# Catalogues — shape points normalized 0..1 (origin top-left, Y down)
# ---------------------------------------------------------------------------
_SHAPE_CATALOGUE: list[tuple[str, str, list[tuple[float, float]]]] = [
    ("prostokat",  "Połać 1", [(0, 0), (1, 0), (1, 1), (0, 1)]),
    ("trojkat",    "Połać 2", [(0.5, 0), (1, 1), (0, 1)]),
    ("trapez_row", "Połać 3", [(0.2, 0), (0.8, 0), (1, 1), (0, 1)]),
    ("trapez_prl", "Połać 4", [(0.25, 0), (1, 0), (1, 1), (0, 1)]),
    ("trapez_l",   "Połać 5", [(0, 0), (0.75, 0), (1, 1), (0, 1)]),
    ("trapez6",    "Połać 6", [(0, 0), (0.75, 0), (1, 1), (0.2, 1)]),
    ("trapez7",    "Połać 7", [(0.2, 0), (0.8, 0), (1, 1), (0, 1)]),
    ("pieciokat",  "Połać 8", [(0.5, 0), (1, 0.4), (1, 1), (0, 1), (0, 0.4)]),
    ("pieciokat2", "Połać 9", [(0.5, 0), (1, 0.4), (0.85, 1), (0.15, 1), (0, 0.4)]),
]

_LUKARNA_CATALOGUE: list[tuple[str, str, list[tuple[float, float]]]] = [
    ("lukarna1", "Lukarna 1", [(0, 0), (1, 0), (1, 1), (0, 1)]),
    ("lukarna2", "Lukarna 2", [(0.5, 0), (1, 1), (0, 1)]),
    ("lukarna3", "Lukarna 3", [(0.5, 0), (1, 0.4), (1, 1), (0, 1), (0, 0.4)]),
]

# Dimension fields per shape: (key, label, default_cm, max_cm)
_SHAPE_FIELDS: dict[str, list[tuple[str, str, int, int]]] = {
    "prostokat":  [("A", "A — szerokość:", 800, 9999),
                   ("B", "B — wysokość:",  300, 9999)],
    "trojkat":    [("A", "A — podstawa:", 800, 9999),
                   ("B", "B — wysokość:", 300, 9999)],
    "trapez_row": [("A", "A — podstawa dolna:", 800, 9999),
                   ("C", "C — podstawa górna:", 500, 9999),
                   ("B", "B — wysokość:",       300, 9999)],
    "trapez_prl": [("A", "A — podstawa dolna:", 800, 9999),
                   ("C", "C — podstawa górna:", 500, 9999),
                   ("B", "B — wysokość:",       300, 9999)],
    "trapez_l":   [("A", "A — podstawa dolna:", 800, 9999),
                   ("C", "C — podstawa górna:", 500, 9999),
                   ("B", "B — wysokość:",       300, 9999)],
    "trapez6":    [("A", "A — podstawa dolna:", 800, 9999),
                   ("C", "C — podstawa górna:", 500, 9999),
                   ("B", "B — wysokość:",       300, 9999)],
    "trapez7":    [("A", "A — podstawa dolna:", 800, 9999),
                   ("C", "C — podstawa górna:", 500, 9999),
                   ("B", "B — wysokość:",       300, 9999)],
    "pieciokat":  [("A", "A — szerokość:", 800, 9999),
                   ("B", "B — wysokość:", 300, 9999)],
    "pieciokat2": [("A", "A — szerokość:", 800, 9999),
                   ("B", "B — wysokość:", 300, 9999)],
}

_LUKARNA_FIELDS: dict[str, list[tuple[str, str, int]]] = {
    "lukarna1": [("A", "A:", 80), ("H1", "H1:", 60)],
    "lukarna2": [("A", "A:", 80), ("H",  "H:",  60)],
    "lukarna3": [("A", "A:", 80), ("H1", "H1:", 60), ("H", "H:", 60)],
}


# ---------------------------------------------------------------------------
# Helper — render polygon outline into a QPixmap (SAFE outside paintEvent)
# NOTE: QPainter on QPixmap is always safe outside paintEvent.
#       QPainter on QWidget is ONLY safe inside paintEvent.
# ---------------------------------------------------------------------------
def _make_shape_pixmap(
    pts: list[tuple[float, float]], size: int = 56
) -> QPixmap:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    margin = 6
    span = size - 2 * margin
    p.setPen(QPen(QColor("#555555"), 1.8))
    p.setBrush(Qt.BrushStyle.NoBrush)
    poly = QPolygonF([QPointF(margin + x * span, margin + y * span) for x, y in pts])
    p.drawPolygon(poly)
    p.end()
    return px


# ===========================================================================
# ShapeGalleryWidget
# UWAGA: QButtonGroup(exclusive=True) jest PRAWIDŁOWE dla galerii kształtów.
# Dla przycisków flip jest BŁĘDEM (flip H i V są niezależne).
# ===========================================================================
class ShapeGalleryWidget(QWidget):
    shape_selected = Signal(str)  # emits shape_type id

    def __init__(
        self,
        catalogue: list[tuple[str, str, list[tuple[float, float]]]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._catalogue = catalogue
        self._id_map: dict[QToolButton, str] = {}
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(4)
        grid.setContentsMargins(4, 4, 4, 4)

        for idx, (shape_id, label, pts) in enumerate(self._catalogue):
            btn = QToolButton()
            btn.setText(label)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setFixedSize(100, 90)
            btn.setCheckable(True)
            btn.setIcon(QIcon(_make_shape_pixmap(pts)))
            btn.setIconSize(_make_shape_pixmap(pts).size())
            self._btn_group.addButton(btn)
            self._id_map[btn] = shape_id
            grid.addWidget(btn, idx // 4, idx % 4)

        self._btn_group.buttonClicked.connect(self._on_btn_clicked)

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _on_btn_clicked(self, btn: QToolButton) -> None:
        shape_id = self._id_map.get(btn)
        if shape_id:
            self.shape_selected.emit(shape_id)

    @property
    def selected_id(self) -> str | None:
        checked = self._btn_group.checkedButton()
        return self._id_map.get(checked) if checked else None


# ===========================================================================
# ShapePreviewWidget
# Rysuje wybrany kształt w dużej skali z transformacją flip.
# ZASADA Qt: QPainter(QWidget) TYLKO w paintEvent.
# ===========================================================================
class ShapePreviewWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pts: list[tuple[float, float]] = []
        self._dims: dict[str, int] = {}
        self._flip_h = False
        self._flip_v = False
        self.setMinimumSize(260, 260)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

    def update_shape(
        self,
        pts: list[tuple[float, float]],
        dims: dict,
        flip_h: bool = False,
        flip_v: bool = False,
    ) -> None:
        self._pts = pts
        self._dims = dims
        self._flip_h = flip_h
        self._flip_v = flip_v
        self.update()  # schedule repaint — NEVER call paintEvent directly

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._pts:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        margin = 36

        # Build QTransform for flip — must translate to center BEFORE scale,
        # then translate back. Order matters: Qt transforms are applied right-to-left.
        t = QTransform()
        t.translate(w / 2.0, h / 2.0)
        if self._flip_h:
            t.scale(-1.0, 1.0)
        if self._flip_v:
            t.scale(1.0, -1.0)
        t.translate(-w / 2.0, -h / 2.0)
        painter.setTransform(t)

        span_x = w - 2 * margin
        span_y = h - 2 * margin
        poly = QPolygonF([
            QPointF(margin + x * span_x, margin + y * span_y)
            for x, y in self._pts
        ])
        painter.setPen(QPen(QColor("#333333"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(poly)

        # Dimension labels — draw WITHOUT flip transform
        painter.resetTransform()
        painter.setPen(QPen(QColor("#006494"), 1))
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        if "A" in self._dims:
            painter.drawText(w // 2 - 24, h - 6, f"A = {self._dims['A']} cm")
        if "B" in self._dims:
            painter.drawText(4, h // 2, f"B = {self._dims['B']} cm")
        if "C" in self._dims:
            painter.drawText(w // 2 - 24, margin - 4, f"C = {self._dims['C']} cm")


# ===========================================================================
# FlipControlsWidget
# KLUCZOWE: flip H i flip V są NIEZALEŻNE — NIE używamy QButtonGroup.
# QButtonGroup z exclusive=True sprawia że kliknięcie H odznacza V i odwrotnie,
# co jest BŁĘDEM logicznym — użytkownik może chcieć oba jednocześnie.
# ===========================================================================
class FlipControlsWidget(QWidget):
    flip_changed = Signal(bool, bool)  # flip_h, flip_v

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)

        self.btn_flip_h = QToolButton()
        self.btn_flip_h.setText("⇔  Flip H")
        self.btn_flip_h.setCheckable(True)
        self.btn_flip_h.setToolTip("Odbicie lustrzane poziome (flip horizontal)")

        self.btn_flip_v = QToolButton()
        self.btn_flip_v.setText("⇕  Flip V")
        self.btn_flip_v.setCheckable(True)
        self.btn_flip_v.setToolTip("Odbicie lustrzane pionowe (flip vertical)")

        layout.addWidget(self.btn_flip_h)
        layout.addWidget(self.btn_flip_v)
        layout.addStretch()

        # Connect AFTER both buttons are created — avoids premature emit
        self.btn_flip_h.toggled.connect(self._emit)
        self.btn_flip_v.toggled.connect(self._emit)

    def _emit(self) -> None:
        self.flip_changed.emit(
            self.btn_flip_h.isChecked(),
            self.btn_flip_v.isChecked(),
        )

    def values(self) -> tuple[bool, bool]:
        return self.btn_flip_h.isChecked(), self.btn_flip_v.isChecked()


# ===========================================================================
# DimensionFormWidget
# WAŻNE — blockSignals(True/False) przy setValue:
# QSpinBox.valueChanged odpala się NATYCHMIAST przy setValue() podczas
# load_for_shape. Bez blokowania sygnałów preview aktualizuje się wielokrotnie
# przy ładowaniu każdego pola z osobna — z niepełnymi danymi.
# Rozwiązanie: blokuj sygnały przy setValue, emituj raz na końcu _emit_dims().
# ===========================================================================
class DimensionFormWidget(QWidget):
    dims_changed = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._spins: dict[str, QSpinBox] = {}
        self._form = QFormLayout(self)
        self._form.setContentsMargins(0, 0, 0, 0)

    def load_for_shape(self, shape_id: str, saved: dict) -> None:
        # removeRow(0) in loop — available Qt 5.8+, always safe in PySide6
        while self._form.rowCount():
            self._form.removeRow(0)
        self._spins.clear()

        fields = _SHAPE_FIELDS.get(shape_id, [])
        for key, label, default, max_val in fields:
            spin = QSpinBox()
            spin.setRange(1, max_val)
            spin.setSuffix(" cm")

            # Block signals during setValue to prevent spurious dims_changed
            spin.blockSignals(True)
            spin.setValue(saved.get(key, default))
            spin.blockSignals(False)

            spin.valueChanged.connect(self._emit_dims)
            self._form.addRow(label, spin)
            self._spins[key] = spin

        self._emit_dims()  # emit once after all fields are loaded

    def _emit_dims(self) -> None:
        self.dims_changed.emit(self.get_dims())

    def get_dims(self) -> dict:
        return {k: s.value() for k, s in self._spins.items()}


# ===========================================================================
# LukarnaPreviewWidget
# Rysuje obrys połaci (szara linia przerywana) + lukarnę wycentrowaną (zielona).
# Wymiary połaci są przekazywane przez set_polac_pts() przy przejściu do kroku 2.
# ===========================================================================
class LukarnaPreviewWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lukarna_pts: list[tuple[float, float]] = []
        self._polac_pts: list[tuple[float, float]] = []
        self._lukarna_dims: dict = {}
        self.setMinimumSize(260, 260)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

    def update_lukarna(
        self,
        lukarna_pts: list[tuple[float, float]],
        polac_pts: list[tuple[float, float]],
        lukarna_dims: dict,
    ) -> None:
        self._lukarna_pts = lukarna_pts
        self._polac_pts = polac_pts
        self._lukarna_dims = lukarna_dims
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        margin = 30
        span_x = w - 2 * margin
        span_y = h - 2 * margin

        # Draw polac outline — gray dashed
        if self._polac_pts:
            painter.setPen(QPen(QColor("#999999"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            poly = QPolygonF([
                QPointF(margin + x * span_x, margin + y * span_y)
                for x, y in self._polac_pts
            ])
            painter.drawPolygon(poly)

        # Draw lukarna centered horizontally — green filled
        if self._lukarna_pts:
            painter.setPen(QPen(QColor("#007700"), 2))
            painter.setBrush(QColor(200, 255, 200, 60))
            lw = 0.35   # lukarna width as fraction of polac bounding box
            lh = 0.3
            lx0 = 0.5 - lw / 2
            ly0 = 0.6 - lh
            poly = QPolygonF([
                QPointF(
                    margin + (lx0 + x * lw) * span_x,
                    margin + (ly0 + y * lh) * span_y,
                )
                for x, y in self._lukarna_pts
            ])
            painter.drawPolygon(poly)

            if "A" in self._lukarna_dims:
                painter.setPen(QPen(QColor("#007700"), 1))
                font = painter.font()
                font.setPointSize(9)
                painter.setFont(font)
                painter.drawText(
                    w // 2 - 24,
                    int(margin + (ly0 + lh + 0.05) * span_y),
                    f"A = {self._lukarna_dims['A']} cm",
                )


# ===========================================================================
# LukarnaPickerWidget — Step 2
# Używa ręcznego exclusive selection (nie QButtonGroup), bo "Bez wycinka"
# (btn_none) nie jest prawdziwym przyciskiem radio — to opcja zerowa.
# ===========================================================================
class LukarnaPickerWidget(QWidget):
    lukarna_changed = Signal(object)  # LukarnaSpec | None

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selected_type: str | None = None
        self._spins: dict[str, QSpinBox] = {}
        self._dim_form: QFormLayout | None = None
        self._polac_pts: list[tuple[float, float]] = []
        self._cat_map = {lid: pts for lid, _, pts in _LUKARNA_CATALOGUE}
        self._setup_ui()

    def set_polac_pts(self, pts: list[tuple[float, float]]) -> None:
        """Called by parent dialog when polac shape is confirmed (step 1 → step 2)."""
        self._polac_pts = pts
        self._refresh_preview()

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)

        left = QWidget()
        left.setFixedWidth(130)
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(4)

        self._all_btns: list[QToolButton] = []

        self._btn_none = QToolButton()
        self._btn_none.setText("Bez\nwycinka")
        self._btn_none.setCheckable(True)
        self._btn_none.setChecked(True)
        self._btn_none.setFixedSize(100, 50)
        self._btn_none.clicked.connect(lambda: self._on_select(None))
        self._all_btns.append(self._btn_none)
        left_layout.addWidget(self._btn_none)

        for ltype, lname, pts in _LUKARNA_CATALOGUE:
            btn = QToolButton()
            btn.setText(lname)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setFixedSize(100, 90)
            btn.setCheckable(True)
            btn.setIcon(QIcon(_make_shape_pixmap(pts)))
            btn.setIconSize(_make_shape_pixmap(pts).size())
            btn.clicked.connect(
                lambda _checked=False, lt=ltype: self._on_select(lt)
            )
            self._all_btns.append(btn)
            left_layout.addWidget(btn)

        left_layout.addStretch()
        main_layout.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        self._preview = LukarnaPreviewWidget()
        right_layout.addWidget(self._preview, stretch=1)

        dim_container = QWidget()
        self._dim_form = QFormLayout(dim_container)
        self._dim_form.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(dim_container)

        main_layout.addWidget(right, stretch=1)

    def _on_select(self, lukarna_type: str | None) -> None:
        for btn in self._all_btns:
            btn.setChecked(False)
        if lukarna_type is None:
            self._btn_none.setChecked(True)
        else:
            for i, (lt, _, _) in enumerate(_LUKARNA_CATALOGUE):
                if lt == lukarna_type:
                    self._all_btns[i + 1].setChecked(True)
                    break

        self._selected_type = lukarna_type
        self._reload_dims(lukarna_type)
        self._refresh_preview()
        self.lukarna_changed.emit(self.get_result())

    def _reload_dims(self, lukarna_type: str | None) -> None:
        assert self._dim_form is not None
        while self._dim_form.rowCount():
            self._dim_form.removeRow(0)
        self._spins.clear()

        if lukarna_type is None:
            return

        for key, label, default in _LUKARNA_FIELDS.get(lukarna_type, []):
            spin = QSpinBox()
            spin.setRange(1, 999)
            spin.setSuffix(" cm")
            spin.blockSignals(True)   # block signals during setValue (same as DimensionFormWidget)
            spin.setValue(default)
            spin.blockSignals(False)
            spin.valueChanged.connect(self._on_dims_changed)
            self._dim_form.addRow(label, spin)
            self._spins[key] = spin

    def _on_dims_changed(self) -> None:
        self._refresh_preview()
        self.lukarna_changed.emit(self.get_result())

    def _refresh_preview(self) -> None:
        if not self._selected_type:
            self._preview.update_lukarna([], self._polac_pts, {})
        else:
            pts = self._cat_map.get(self._selected_type, [])
            self._preview.update_lukarna(pts, self._polac_pts, self._get_dims())

    def _get_dims(self) -> dict:
        return {k: s.value() for k, s in self._spins.items()}

    def get_result(self) -> LukarnaSpec | None:
        if self._selected_type is None:
            return None
        return LukarnaSpec(
            lukarna_type=self._selected_type,
            dimensions=self._get_dims(),
        )


# ===========================================================================
# AddPolacDialog — main two-step wizard
# ===========================================================================
class AddPolacDialog(QDialog):
    """
    Two-step wizard for creating a new roof plane (połać).

    Step 1: select shape + set dimensions + optional flip H/V
    Step 2: optionally attach a lukarna (dormer cutout)

    Usage:
        dlg = AddPolacDialog(config_data, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result = dlg.get_result()  # PolacWizardResult

    Returns PolacWizardResult via get_result() after accept().
    """

    def __init__(
        self, config_data: dict, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nowa połać")
        self.setMinimumSize(920, 580)
        self._config_data = config_data
        self._result: PolacWizardResult | None = None
        self._shape_pts_map = {
            sid: pts for sid, _, pts in _SHAPE_CATALOGUE
        }
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        self._stack = QStackedWidget()

        # --- Step 1 ---
        s1 = QWidget()
        s1_layout = QHBoxLayout(s1)

        self._gallery = ShapeGalleryWidget(_SHAPE_CATALOGUE, self)
        self._gallery.setFixedWidth(440)
        s1_layout.addWidget(self._gallery)

        right1 = QWidget()
        r1_layout = QVBoxLayout(right1)

        self._preview = ShapePreviewWidget()
        self._dim_form = DimensionFormWidget()
        self._flip_ctrl = FlipControlsWidget()

        r1_layout.addWidget(self._preview, stretch=1)
        r1_layout.addWidget(self._dim_form)
        r1_layout.addWidget(self._flip_ctrl)
        s1_layout.addWidget(right1, stretch=1)

        self._stack.addWidget(s1)

        # --- Step 2 ---
        s2 = QWidget()
        s2_layout = QVBoxLayout(s2)
        hint = QLabel("Wybierz wycinek/lukarnę (opcjonalnie):")
        hint.setStyleSheet("font-weight: bold; margin-bottom: 4px;")
        s2_layout.addWidget(hint)
        self._lukarna_picker = LukarnaPickerWidget()
        s2_layout.addWidget(self._lukarna_picker)
        self._stack.addWidget(s2)

        root.addWidget(self._stack)

        # --- Navigation ---
        nav = QHBoxLayout()
        self._btn_cancel = QPushButton("Anuluj")
        self._btn_back = QPushButton("← Wstecz")
        self._btn_back.setEnabled(False)
        self._btn_next = QPushButton("Dalej →")
        self._btn_ok = QPushButton("Zatwierdź")
        self._btn_ok.setDefault(True)
        self._btn_ok.setVisible(False)

        nav.addWidget(self._btn_cancel)
        nav.addStretch()
        nav.addWidget(self._btn_back)
        nav.addWidget(self._btn_next)
        nav.addWidget(self._btn_ok)
        root.addLayout(nav)

    def _connect_signals(self) -> None:
        self._btn_cancel.clicked.connect(self.reject)
        self._btn_next.clicked.connect(self._go_next)
        self._btn_back.clicked.connect(self._go_back)
        self._btn_ok.clicked.connect(self._on_accept)

        self._gallery.shape_selected.connect(self._on_shape_selected)
        self._dim_form.dims_changed.connect(self._on_dims_changed)
        self._flip_ctrl.flip_changed.connect(self._on_flip_changed)

    # -----------------------------------------------------------------------
    # Navigation
    # -----------------------------------------------------------------------
    def _go_next(self) -> None:
        if self._gallery.selected_id is None:
            QMessageBox.warning(
                self,
                "Brak wyboru",
                "Wybierz kształt połaci przed przejściem dalej.",
            )
            return
        sid = self._gallery.selected_id
        if sid:
            pts = self._shape_pts_map.get(sid, [])
            self._lukarna_picker.set_polac_pts(pts)

        self._stack.setCurrentIndex(1)
        self._update_nav()

    def _go_back(self) -> None:
        self._stack.setCurrentIndex(0)
        self._update_nav()

    def _update_nav(self) -> None:
        idx = self._stack.currentIndex()
        self._btn_back.setEnabled(idx > 0)
        self._btn_next.setVisible(idx == 0)
        self._btn_ok.setVisible(idx == 1)
        # adjustSize prevents QStackedWidget size glitch when switching pages
        self.adjustSize()

    # -----------------------------------------------------------------------
    # Shape selection and preview
    # -----------------------------------------------------------------------
    def _on_shape_selected(self, shape_id: str) -> None:
        saved = (
            self._config_data
            .get("ksztalty", {})
            .get(shape_id, {})
            .get("dims", {})
        )
        self._dim_form.load_for_shape(shape_id, saved)
        self._refresh_preview()

    def _on_dims_changed(self, dims: dict) -> None:
        self._refresh_preview()

    def _on_flip_changed(self, flip_h: bool, flip_v: bool) -> None:
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        sid = self._gallery.selected_id
        if not sid:
            return
        pts = self._shape_pts_map.get(sid, [])
        flip_h, flip_v = self._flip_ctrl.values()
        self._preview.update_shape(pts, self._dim_form.get_dims(), flip_h, flip_v)

    # -----------------------------------------------------------------------
    # Accept — build result and persist to config
    # -----------------------------------------------------------------------
    def _on_accept(self) -> None:
        sid = self._gallery.selected_id
        if not sid:
            QMessageBox.warning(self, "Błąd", "Nie wybrano kształtu połaci.")
            return

        flip_h, flip_v = self._flip_ctrl.values()
        dims = self._dim_form.get_dims()
        lukarna = self._lukarna_picker.get_result()

        self._result = PolacWizardResult(
            shape_type=sid,
            dimensions=dims,
            flip_h=flip_h,
            flip_v=flip_v,
            lukarna=lukarna,
        )

        # Persist dims to config_data for next session (same pattern as existing dialogs)
        self._config_data.setdefault("ksztalty", {}).setdefault(
            sid, {}
        )["dims"] = dict(dims)

        self.accept()

    def get_result(self) -> PolacWizardResult | None:
        return self._result
```

---

## Warstwa 2 — `ui/dialogs/__init__.py` (aktualizacja)

Dodaj `AddPolacDialog` do importów i `__all__`. Stare dialogi zostają — używane przez
istniejące call-site'y w toolbar/canvas.

```python
# ui/dialogs/__init__.py — re-exports all dialog classes.
from ui.dialogs.add_polac_dialog import AddPolacDialog          # NOWE
from ui.dialogs.company_dialog import DaneFirmyDialog
from ui.dialogs.material_dialog import BlachyDialog, DaneBlachyDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.shape_dialogs import ProstokatDialog, TrapezDialog, TrojkatDialog

__all__ = [
    "AddPolacDialog",            # NOWE
    "ProstokatDialog",
    "TrojkatDialog",
    "TrapezDialog",
    "BlachyDialog",
    "DaneBlachyDialog",
    "DaneFirmyDialog",
    "SettingsDialog",
]
```

---

## Warstwa 3 — integracja w toolbar / main window

Dodaj jedną nową akcję `"Nowa połać..."`. Stare trzy akcje (`Prostokąt...`, `Trójkąt...`,
`Trapez...`) możesz zachować obok lub usunąć po weryfikacji call-site'ów.

```python
# ui/main_window.py lub ui/toolbar.py

from __future__ import annotations

import uuid

from PySide6.QtWidgets import QDialog

from core.models import Point2D, Polygon2D, PolacWizardResult, RoofPlane
from ui.dialogs import AddPolacDialog


def _on_add_polac(self) -> None:
    dlg = AddPolacDialog(self._config_data, parent=self)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return
    result = dlg.get_result()
    if result is None:
        return

    polygon = _build_polygon_from_result(result)
    if polygon is None:
        return

    plane = RoofPlane(
        id=str(uuid.uuid4()),
        name=f"Połać {result.shape_type}",
        outline=polygon,
    )

    if result.lukarna is not None:
        hole = _build_lukarna_hole(result.lukarna, polygon)
        if hole is not None:
            plane.holes.append(hole)

    self._project_state.add_roof_plane(plane)
    self._canvas.refresh()


def _build_polygon_from_result(result: PolacWizardResult) -> Polygon2D | None:
    """Convert PolacWizardResult dimensions → Polygon2D in cm.
    This logic belongs in the CALLER, not in the dialog (separation of concerns).
    """
    d = result.dimensions
    shape = result.shape_type
    pts: list[Point2D] = []

    if shape == "prostokat":
        w, h = d.get("A", 800), d.get("B", 300)
        pts = [Point2D(0, 0), Point2D(w, 0),
               Point2D(w, h), Point2D(0, h)]

    elif shape == "trojkat":
        base, ht = d.get("A", 800), d.get("B", 300)
        pts = [Point2D(0, ht), Point2D(base, ht), Point2D(base / 2, 0)]

    elif shape in ("trapez_row", "trapez_prl", "trapez_l", "trapez6", "trapez7"):
        a, c, b = d.get("A", 800), d.get("C", 500), d.get("B", 300)
        offset = (a - c) / 2
        pts = [Point2D(0, b), Point2D(a, b),
               Point2D(a - offset, 0), Point2D(offset, 0)]

    elif shape in ("pieciokat", "pieciokat2"):
        w, h = d.get("A", 800), d.get("B", 300)
        pts = [
            Point2D(w / 2, 0), Point2D(w, h * 0.4),
            Point2D(w, h), Point2D(0, h), Point2D(0, h * 0.4),
        ]

    if not pts:
        return None

    # Apply flip transforms on Point2D level (geometry, not UI)
    if result.flip_h:
        max_x = max(p.x for p in pts)
        pts = [Point2D(max_x - p.x, p.y) for p in pts]
    if result.flip_v:
        max_y = max(p.y for p in pts)
        pts = [Point2D(p.x, max_y - p.y) for p in pts]

    return Polygon2D(pts)


def _build_lukarna_hole(lukarna: LukarnaSpec, polac: Polygon2D) -> Polygon2D | None:
    """Build lukarna as Polygon2D hole, centered on polac bounding box.
    Polygon2D.bounds() must return an object with .min_x .max_x .min_y .max_y.
    Raises ValueError for < 3 points — caught here with try/except.
    """
    bounds = polac.bounds()
    cx = (bounds.min_x + bounds.max_x) / 2
    cy = (bounds.min_y + bounds.max_y) / 2
    a = lukarna.dimensions.get("A", 80)
    h1 = lukarna.dimensions.get("H1", 60)
    h = lukarna.dimensions.get("H", h1)

    ltype = lukarna.lukarna_type
    if ltype == "lukarna1":   # prostokątna
        pts = [
            Point2D(cx - a / 2, cy - h1 / 2),
            Point2D(cx + a / 2, cy - h1 / 2),
            Point2D(cx + a / 2, cy + h1 / 2),
            Point2D(cx - a / 2, cy + h1 / 2),
        ]
    elif ltype == "lukarna2":  # trójkątna
        pts = [
            Point2D(cx - a / 2, cy + h / 2),
            Point2D(cx + a / 2, cy + h / 2),
            Point2D(cx, cy - h / 2),
        ]
    elif ltype == "lukarna3":  # pięciokątna
        pts = [
            Point2D(cx, cy - h / 2),
            Point2D(cx + a / 2, cy - h1 / 2 + h / 2 - h),
            Point2D(cx + a / 2, cy + h / 2),
            Point2D(cx - a / 2, cy + h / 2),
            Point2D(cx - a / 2, cy - h1 / 2 + h / 2 - h),
        ]
    else:
        return None

    try:
        return Polygon2D(pts)
    except ValueError:
        # Polygon2D raises ValueError for < 3 points
        return None
```

---

## Tabela ulepszeń (vs. plan wstępny z rozmowy)

Poniższe problemy zostały zidentyfikowane w trakcie weryfikacji i poprawione w finalnym kodzie:

| # | Problem w pierwotnym planie | Poprawka w finalnym planie |
|---|---|---|
| U1 | `@dataclass` bez `slots=True` | `@dataclass(slots=True)` — spójność z projektem |
| U2 | Brak walidacji przed `_go_next()` i `_on_accept()` | `QMessageBox.warning` gdy brak wybranego kształtu |
| U3 | `blockSignals` opisane tylko w komentarzu, nie w kodzie | `spin.blockSignals(True/False)` w `load_for_shape` i `_reload_dims` |
| U4 | Brak persystencji wartości między sesjami | Zapis/odczyt do `config_data["ksztalty"][sid]["dims"]` |
| U5 | `QButtonGroup` użyty dla flip H/V (BŁĄD logiczny) | `FlipControlsWidget` bez `QButtonGroup` — flip H i V niezależne |
| U6 | `LukarnaPreviewWidget` zdefiniowany tylko sygnaturą | Pełna implementacja `paintEvent` z połacią (szara) i lukarną (zielona) |
| U7 | `_update_nav_visibility` ukrywał btn_ok na kroku 1 | `btn_ok.setVisible(idx == 1)` + `adjustSize()` po zmianie strony |
| U8 | Brak przekazania `polac_pts` do `LukarnaPickerWidget` | `set_polac_pts()` wywoływane w `_go_next()` |
| U9 | Brak eksportu w `__init__.py` | `AddPolacDialog` dodany do `__all__` |
| U10 | Brak obsługi `ValueError` z `Polygon2D` | `try/except ValueError` w `_build_lukarna_hole` |

---

## Sugerowana kolejność implementacji

Implementuj inkrementalnie — każdy krok daje działający, testowalny stan:

1. **`core/models.py`** — dopisz `LukarnaSpec` i `PolacWizardResult` (10 min)
2. **`ShapeGalleryWidget`** + `_make_shape_pixmap` — galeria z miniaturami (30 min)
3. **`DimensionFormWidget`** — dynamiczny formularz z `blockSignals` (20 min)
4. **`AddPolacDialog` Step 1** — dialog z galerią i formularzem, bez preview i flip (20 min)
5. **`ShapePreviewWidget`** — `paintEvent` + `QTransform` flip (30 min)
6. **`FlipControlsWidget`** — dwa niezależne przyciski toggle (10 min)
7. **`LukarnaPreviewWidget`** + **`LukarnaPickerWidget`** — krok 2 z podglądem (40 min)
8. **`ui/dialogs/__init__.py`** — eksport (2 min)
9. **Integracja w toolbar/main window** — `_on_add_polac`, `_build_polygon_from_result`, `_build_lukarna_hole` (30 min)

---

## Znane pułapki PySide6 (lista kontrolna przed review)

- **`QPainter` na `QWidget`** — TYLKO wewnątrz `paintEvent`. Na `QPixmap` zawsze można.
- **`QStackedWidget` rozmiar** — po `setCurrentIndex` wywołaj `self.adjustSize()` na dialogu.
  `QStackedWidget` rezerwuje rozmiar największego widgetu. Dla dialogów z `setMinimumSize`
  o podobnych rozmiarach kroków problem jest marginalny, ale `adjustSize()` jest dobrą praktyką.
- **`QFormLayout.removeRow(0)`** — Qt 5.8+, PySide6 ≥ 6.0 zawsze OK.
- **`QButtonGroup(exclusive=True)` dla galerii** — OK, prawidłowe.
  **`QButtonGroup` dla flip H/V** — BŁĄD, nie używać.
- **`QSpinBox.blockSignals`** — obowiązkowo przy `setValue()` w metodach ładowania.
- **`QTransform` flip** — kolejność: `translate(center)` → `scale(-1,1)` → `translate(-center)`.
- **`from __future__ import annotations`** — obowiązkowe na początku pliku dla `X | Y` w Python < 3.10.

