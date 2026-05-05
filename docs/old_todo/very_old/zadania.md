<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# to jest lista zmian do wprowawdzenia przeanalizuj i napisz prompty do agenta o zmiane

Mam wszystko. Przeanalizuję każde ze zdjęć i pełny opis.md, potem napiszę prompty w tym samym stylu co poprzednie (angielski, szczegółowy, z acceptance criteria).

Ze zdjęć wyłapuję te zmiany:

**Ze zdjęcia 1 (raport):** Długości arkuszy w tabeli i podsumowaniu mają za dużo miejsc po przecinku — np. `8.68`, `34.15`, `104.834`. Minimalna jednostka to 1 cm — wartości powinny być zaokrąglone do 1 miejsca po przecinku lub całkowitych (do ustalenia — `109.6` lub `110`).

**Ze zdjęcia 2 (EDIT mode, pusta siatka):** Zaznaczone strzałkami: brakuje linii prostopadłych do osi od wierzchołków + brakuje etykiet długości boków.

**Ze zdjęcia 3 (DRAW_CUT mode):** Słabo widoczne kąty (czarny tekst na czarnym tle w badgesach narożników 90°), słabo widoczna linia pomocnicza, brak przyciągania do przecięć linii.

**Ze zdjęcia 4 (DRAW_PLANE, X/Y tooltips):** Tooltips X/Y i oś działają — ale brakuje przerywanych linii od kursora.

**Ze zdjęcia 5 (DRAW_PLANE, brak kształtu):** Widać tooltips X/Y ale brak przerywanych linii przy krawędzi canvasa.

**Ze zdjęcia 6 (EDIT, prostokąt 400x300):** Siatka i forma wyglądają OK.

**Ze zdjęcia 7 (DRAW_PLANE, linia pomocnicza):** Nie przyciąga do linii pionowej (przyciąga jak do poziomej), "RMB to close" do usunięcia, dynamiczne linie pomocnicze niewidoczne na dole.

**Ze zdjęcia 8 (IDLE, pusta zakładka ze siatką):** Siatka na pustym canvasie ma za duże oczka i nie powinna się pokazywać zanim nie ma kształtu.

***

Piszę teraz prompty:

***

## Prompt 1 — Raport: zaokrąglenie wartości do 1 cm

```
You are working on the 4dach-qt application (PyQt/PySide, Python).
Repository: https://github.com/jooni22/4dach-qt

## Problem

In the HTML report (core/reporting.py), sheet lengths and summary
values are displayed with too many decimal places.

Examples observed in the report:
  - "Długość arkusza [cm]" column: 8.68, 34.15, 43.47, 78.27, ...
  - "Łączna powierzchnia efektywna [m2]": 104.834
  - "Łączne zużycie materiału [m2]": 109.611
  - "Łączny odpad [m2]": 4.777
  - "Łączny odpad [%]": 4.36
  - "Łączny koszt [zł]": 1096.11

## Requirements

### Sheet lengths (column "Długość arkusza [cm]")
The minimum unit in the system is 1 cm. Sheet lengths must be
rounded to 1 decimal place maximum:
  8.68 → 8.7
  34.15 → 34.2

If there is a project-level setting `round_sheet_length_to_int`
(check AppSettings), use it:
  - True → round to integer: 8.68 → 9
  - False (default) → round to 1 decimal place: 8.68 → 8.7

If the setting does not exist, default to 1 decimal place.

### Summary values (Podsumowanie projektu table)
- Powierzchnia values [m2]: round to 2 decimal places (104.834 → 104.83)
- Odpad [%]: round to 1 decimal place (4.36 → 4.4)
- Liczba arkuszy: integer, no change needed (60 is already correct)
- Koszt [zł]: round to 2 decimal places (1096.11 is already correct —
  verify it is always formatted as 2dp, never as 1096.1 or 1096.115)

### Zbiorowe zestawienie materiałów table
Same rules as sheet lengths — all cm values to 1 decimal place,
all m2 values to 2 decimal places.

## Constraints
- Modify only core/reporting.py (and its helpers if split across files).
- Do NOT change data models or layout engine.
- Do NOT change AppSettings unless the round_sheet_length_to_int
  setting needs to be added (only add it if you use it).
- Run `uv run pytest` after changes; all tests must pass.
- Code comments and log messages in English only.

## Acceptance criteria
1. All sheet length values in the report are formatted to max 1dp.
2. Surface area [m2] values are formatted to exactly 2dp.
3. Waste [%] is formatted to 1dp.
4. Cost [zł] is formatted to exactly 2dp.
5. No value in the report has more than 2 decimal places.
6. `uv run pytest` — 0 failed.
```


***

## Prompt 2 — Canvas: niewidoczne linie przerywane + za mały interfejs pomocniczy

```
You are working on the 4dach-qt application (PyQt/PySide, Python).
Repository: https://github.com/jooni22/4dach-qt
File to modify: ui/drawing_canvas.py

## Problem summary

Several drawing aid elements are either invisible or too small to be
useful at normal working zoom. This prompt fixes visibility and size
of all drawing aid overlays.

---

## Fix 1: Dynamic helper lines (guide lines) are invisible

### Problem
During DRAW_PLANE and DRAW_CUT modes, dynamic helper lines
(rubber-band projection lines, perpendicular guide lines, or
inference extension lines) exist in the code but are not visible
on screen. The user sees only the cursor crosshair but no dashed
projection lines extending to canvas edges.

### Fix
Find all QPen definitions used for "guide", "helper", "inference",
or "crosshair extension" lines (lines that extend from the current
point to the canvas edge or axis).

For each such pen, ensure:

```python
# Minimum visible pen for guide lines:
pen = QPen(QColor(0, 120, 220, 180))  # blue, alpha 180 (not 30 or 50)
pen.setWidthF(1.2)
pen.setStyle(Qt.DashLine)
# OR use custom dash pattern for better visibility:
pen.setDashPattern()[^1]
```

If the alpha value is currently below 100, raise it to at least 160.
If the line width is currently below 1.0, raise it to at least 1.2.

Apply the same fix to:

- Horizontal inference lines
- Vertical inference lines
- Edge-extension inference lines
- Perpendicular projection lines from active vertex to axes


### Note

Do NOT change the color of snapping indicator circles or the
active vertex highlight — only the dashed guide/inference lines.

---

## Fix 2: Angle badge readability (black text on black background)

### Problem

In DRAW_CUT and DRAW_PLANE modes, angle badges (small rounded
rectangles showing "90°", "60°", "180°" etc.) at polygon corners
are rendered with black text on a dark/black background, making
them unreadable.

Visible in screenshot: corner badges show "90°" and "60°" but
text is nearly invisible.

### Fix

Find the drawing code for angle badges (rounded rect + text overlay).
Change the badge style to:

```python
# Badge background:
badge_bg = QColor(30, 30, 30, 200)      # dark, semi-transparent
badge_text = QColor(255, 255, 255)      # WHITE text
badge_border = QColor(100, 200, 255, 180)  # light blue border, 1px

# Active/snapping badge (when angle is snapped):
badge_bg_active = QColor(0, 100, 200, 220)
badge_text_active = QColor(255, 255, 255)
```

If the badge is currently drawn as text-only without a background,
add a background rounded rect under the text:

```python
rect = QRectF(text_x - 4, text_y - 2, text_width + 8, text_height + 4)
painter.setBrush(QBrush(badge_bg))
painter.setPen(QPen(badge_border, 1))
painter.drawRoundedRect(rect, 3, 3)
painter.setPen(QPen(badge_text))
painter.drawText(rect, Qt.AlignCenter, angle_str)
```


---

## Fix 3: "RMB to close" tooltip — remove it

### Problem

During DRAW_PLANE mode, a "RMB to close" tooltip label is rendered
on the canvas near the first point. This is redundant (the status
bar already shows "Enter lub klik na pkt 1 = zamknij. Esc = anuluj.")
and clutters the drawing area.

### Fix

Find the code that draws the "RMB to close" text label on the canvas
(inside paintEvent or a helper called from paintEvent during
DRAW_PLANE / DRAW_CUT mode).
Remove or comment out ONLY this text rendering call.
Do NOT remove the status bar message.

---

## Fix 4: Increase overall UI element scale (lines, arrows, labels)

### Problem

All drawing aid overlays (guide lines, axis arrows, snap circles,
angle badge text, length label text) are approximately 2x too small
relative to the working area at default zoom.

### Fix

Introduce a scale constant at the top of drawing_canvas.py or as
a class variable:

```python
_UI_SCALE = 1.6  # multiply all drawing-aid sizes by this factor
```

Apply `_UI_SCALE` to:

- Snap circle radius (e.g. if currently 6px → 6 * _UI_SCALE)
- Axis arrow head length (e.g. if currently 8px → 8 * _UI_SCALE)
- Axis label font size
- Angle badge font size (but not below 9pt)
- Length label font size (but not below 9pt)
- Guide line dash pattern lengths

Do NOT apply _UI_SCALE to:

- The main polygon outline stroke width
- The grid line stroke width
- The canvas margin / origin offset

If AppSettings already has a `ui_element_scale: float` field,
use that value instead of the hardcoded 1.6 constant.
If it does not exist, add it:

```python
# In AppSettings (core/app_settings.py or wherever AppSettings is defined):
ui_element_scale: float = 1.6
```

And use `self._app_settings.ui_element_scale` instead of `_UI_SCALE`.

---

## Constraints

- Do NOT change public API of DrawingCanvas.
- Do NOT change the grid rendering logic or polygon geometry.
- Run `uv run pytest` after changes; all tests must pass.
- Code comments and log messages in English only.


## Acceptance criteria

1. Guide/inference lines are clearly visible as dashed blue lines
during drawing (alpha >= 160, width >= 1.2).
2. Angle badges show white text on dark background, readable at
normal zoom.
3. "RMB to close" text no longer appears on the canvas.
4. Snap circles, axis arrows, and label text are visibly larger
(approx 1.6x current size).
5. `uv run pytest` — 0 failed.
```

***

## Prompt 3 — Canvas: brakujące linie prostopadłe do osi + etykiety długości boków w EDIT mode

```

You are working on the 4dach-qt application (PyQt/PySide, Python).
Repository: https://github.com/jooni22/4dach-qt
File to modify: ui/drawing_canvas.py

## Problem

In EDIT mode (Mode: EDIT), two visual elements are missing:

1. Perpendicular projection lines from polygon vertices to both axes
(the dashed lines that run horizontally to the Y-axis and
vertically to the X-axis from each vertex or the hovered vertex).
2. Edge length labels on the polygon sides (the "XXX" placeholders
visible in the screenshot indicate the labels exist but render
as "XXX" — either a placeholder was left in the code, or the
actual value calculation is broken).

---

## Fix 1: Projection lines from vertices to axes (crosshair extensions)

### Visual spec (from reference screenshot)

When a polygon is selected in EDIT mode:

- For each vertex (or for the hovered/active vertex only — see note):
    - Draw a horizontal dashed line from the vertex LEFT to the Y-axis
(x=0 in world coords → left edge of the shape bounding box).
    - Draw a vertical dashed line from the vertex DOWN to the X-axis
(y=0 in world coords → bottom edge of the shape bounding box).

The lines must:

- Be dashed (Qt.DashLine or dash pattern [5, 4])
- Color: QColor(0, 100, 200, 140) — medium blue, semi-transparent
- Width: 1.0px (not affected by zoom)
- Not extend BEYOND the axis (stop exactly at the axis line)
- Be drawn BELOW the polygon outline (behind the shape, not on top)


### Note on "all vertices" vs "hovered vertex"

Draw projection lines for ALL vertices of the selected polygon
when the polygon has 6 or fewer vertices.
For polygons with more vertices, draw only for the hovered/active
vertex (to avoid visual clutter).

### Where to add this code

Find the section in paintEvent (or its helpers) that draws the
selected polygon in EDIT mode. Add the projection lines BEFORE
drawing the polygon outline, so they render behind it.

---

## Fix 2: Edge length labels showing "XXX" instead of actual values

### Problem

Edge length labels on polygon sides in EDIT mode display "XXX"
(literal placeholder text) instead of the computed edge length.

### Fix

Find all occurrences of the string "XXX" used as a length label
in drawing_canvas.py. Replace each with the actual computed
edge length using the same formula used elsewhere in the file:

```python
# Pattern to find:
label_text = "XXX"

# Replace with:
edge_length_cm = math.hypot(b.x - a.x, b.y - a.y)
if getattr(self._app_settings, 'show_decimal_cm', False):
    label_text = f"{edge_length_cm:.1f} cm"
else:
    label_text = f"{int(round(edge_length_cm))} cm"
```

Where `a` and `b` are the two endpoints of the edge being labeled.

If "XXX" is NOT a string literal but rather a variable that is
never assigned, trace back to where it should be assigned and
fix the assignment.

---

## Constraints

- Do NOT change public API of DrawingCanvas.
- Do NOT change polygon geometry or layout engine.
- Do NOT remove existing label rendering code — only fix the values.
- Run `uv run pytest` after changes; all tests must pass.
- Code comments and log messages in English only.


## Acceptance criteria

1. In EDIT mode with a selected polygon, dashed blue lines extend
from each vertex horizontally to the left edge and vertically
to the bottom edge of the shape.
2. Edge length labels show numeric values (e.g. "234 cm") instead
of "XXX".
3. Projection lines render behind the polygon outline, not on top.
4. `uv run pytest` — 0 failed.
```

***

## Prompt 4 — Canvas: siatka na pustym canvasie + snap do przecięć linii

```

You are working on the 4dach-qt application (PyQt/PySide, Python).
Repository: https://github.com/jooni22/4dach-qt
File to modify: ui/drawing_canvas.py (primary), possibly ui/main_window.py

## Problem 1: Grid shown on empty canvas (no shape)

When no roof plane exists on the active tab (Mode: IDLE or DRAW_PLANE
before first point), the canvas shows a large-cell grid that:

- Has cells that are too large (visually different from the grid
shown when a shape exists)
- Cannot be adjusted by the user
- Should either NOT be shown at all, or use the same grid as
when a shape is present


### Fix

Find the grid drawing code. Add a guard:

```python
# Only draw grid when a roof plane exists on this tab:
if self.roof_plane is None:
    return  # or skip the grid draw call
```

If the grid is intentionally shown on an empty canvas as a
reference, replace the "empty canvas grid" with the standard
configurable grid (same cell size as the grid shown when a
shape is present). Do not show a different, larger grid.

---

## Problem 2: Snap does not work for intersection points of guide lines

### Problem

During DRAW_PLANE and DRAW_CUT modes, the snapping system
recognizes:

- Existing polygon vertices (snap to vertex)
- Horizontal/vertical alignment (snap to H/V inference)

But it does NOT snap to the INTERSECTION of two guide lines.

Example: if a horizontal guide line from vertex A and a vertical
guide line from vertex B cross at point P, the cursor does NOT
snap to P even when close to it. The user cannot easily draw
a perfectly aligned corner.

### Fix

In `_build_snap_candidates()` (or the equivalent method that
builds the list of snap targets), add intersection snapping:

1. Collect all active inference/guide lines as `_InferenceLine`
objects (horizontal, vertical, edge-extension).
2. Compute pairwise intersections of ALL pairs of inference lines
that are not parallel (H×V, H×EdgeExt, V×EdgeExt).
3. For each intersection point that falls within the visible
canvas bounds, add it as a snap candidate with type
`"intersection"` and a slightly higher priority than
regular inferences (so it wins when the cursor is near the
intersection).

Render intersection snap candidates as a small "X" mark or
a filled diamond (◆) in a distinct color (e.g. yellow or
orange, 8px):

```python
# Intersection snap indicator:
painter.setPen(QPen(QColor(255, 180, 0), 1.5))
painter.drawLine(px-5, py-5, px+5, py+5)
painter.drawLine(px-5, py+5, px+5, py-5)
```


---

## Problem 3: Snap does not work for vertical guide lines

### Problem

From the screenshot annotation:
"nie przyciąga do tej linii pionowej, rysuje się ale jak do poziomej"
(does not snap to the vertical line, behaves as if it were horizontal)

This suggests the snap distance is computed correctly for horizontal
inferences but the vertical inference snap uses the WRONG axis
(compares X distance instead of Y distance, or vice versa).

### Fix

In the snap candidate evaluation code, verify that:

- For a HORIZONTAL inference line at y=C: snap distance = |cursor_y - C|
- For a VERTICAL inference line at x=C: snap distance = |cursor_x - C|

If they are swapped (vertical line uses `cursor_y` instead of
`cursor_x`), swap them back.

Also verify that when snapped to a vertical inference line,
the snapped point's X coordinate is forced to the line's X,
not its Y.

---

## Constraints

- Do NOT change public API of DrawingCanvas.
- Do NOT change polygon geometry or layout engine.
- Run `uv run pytest` after changes; all tests must pass.
- Code comments and log messages in English only.


## Acceptance criteria

1. Empty canvas (no roof plane) shows no grid, or shows the same
configurable grid as when a shape is present — NOT a different
large-cell grid.
2. When cursor is near the intersection of a horizontal and a
vertical guide line, it snaps to the intersection point
(marked with a small X or diamond indicator).
3. When drawing along a vertical guide line, the cursor snaps
to the line's X coordinate (not Y), producing a perfectly
vertical segment.
4. `uv run pytest` — 0 failed.
```

***

## Kolejność wysyłania promptów

| Kolejność | Prompt | Ryzyko | Szacowany czas agenta |
|---|---|---|---|
| **1** | Prompt 1 — Raport zaokrąglenia | niskie | ~10 min |
| **2** | Prompt 2 — Widoczność UI (linie, odznaki, skala) | średnie | ~25 min |
| **3** | Prompt 3 — Linie prostopadłe + etykiety XXX | średnie | ~20 min |
| **4** | Prompt 4 — Siatka na pustym + snap przecięć + pionowy snap | wyższe | ~35 min |

Każdy prompt jest osobny i niezależny — możesz wysyłać je równolegle na osobnych branchach, ale bezpieczniej kolejno bo wszystkie dotykają `drawing_canvas.py`. [Certainty 94%]

END
<span style="display:none">[^10][^11][^2][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: freehand-draw-talk-v1.md
[^2]: opis.md
[^3]: image-2.jpg
[^4]: image-4-6.jpg
[^5]: image-1-3.jpg
[^6]: image-3-5.jpg
[^7]: image-2-4.jpg
[^8]: image-5-7.jpg
[^9]: 7-8.jpg
[^10]: 8-9.jpg
[^11]: prompty.md```

