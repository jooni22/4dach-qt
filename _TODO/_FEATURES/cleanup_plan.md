
> Status: historyczny artefakt. Aktualną kanoniczną roadmapą dalszych prac jest `_TODO/12_POST_STAGE1_FULL_CLEANUP_ROADMAP.md`.

## Analiza wyników

### Ranking plików wg rozmiaru (linie kodu)

| Plik | Linie | Klasy | Metody/Funkcje |
|---|---|---|---|
| `ui/drawing_canvas.py` | **4199** | 15 | 249 |
| `ui/main_window.py` | **1418** | 2 | 121 |
| `core/project_state.py` | **932** | 1 | 55+16 |
| `core/layout_engine.py` | **795** | 8 | 7+22 |
| `core/reporting.py` | **718** | 7 | 20 |

### Zidentyfikowane semantyczne duplikaty

**1. Klonowanie polygonów** — 3 identyczne implementacje:
- `DrawingCanvas._copy_polygon()` → `Polygon2D([Point2D(p.x, p.y) for p in polygon.points])`
- `_clone_polygon()` w `project_state.py` → identyczny wzorzec
- Powinno być jedną funkcją w `core/models.py` lub `core/geometry.py`

**2. Serializacja polygonów do list** — 2 równoważne:
- `_serialize_polygon()` w `project_state.py` → `[[p.x, p.y] for p in polygon.points]`
- `_polygon_to_dict()` w `layout_engine.py` → identyczny wzorzec
- `_polygon_points()` w `layout_engine.py` → `[(p.x, p.y) for p in polygon.points]`

**3. Odległość między punktami** — 3 implementacje:
- `DrawingCanvas._distance_cm()` → `math.hypot(a.x-b.x, a.y-b.y)` (Point2D)
- `geometry.segment_length()` → `sqrt((end.x-start.x)**2 + ...)` (Point2D)
- `DrawingCanvas._distance()` → `hypot(a.x()-b.x(), ...)` (QPointF — ta jest inna, OK)

**4. Projekcja punktu na odcinek** — 2 niemal identyczne:
- `DrawingCanvas._project_point_to_segment()` (linia 2503)
- `DrawingCanvas._project_point_to_segment_inside()` (linia 1805)
- Różnią się tylko zachowaniem na granicach (clamp vs None) — można unifikować z flagą

**5. Punkt na granicy polygonu** — duplikat z geometry:
- `DrawingCanvas._point_on_polygon_boundary()` robi to samo co `geometry._point_on_segment()` w pętli

**6. Wrappery geometrii** — triwialne aliasy:
- `build_rectangle_outline = make_rectangle`, `build_triangle_outline = make_triangle`, `build_trapezoid_outline = make_trapezoid`

---

## Plan implementacji

### Etap 1: Usunięcie semantycznych duplikatów (niski risk)

**Pliki do modyfikacji:**
- `core/models.py` — dodać `Polygon2D.copy()` (lub `clone()`)
- `core/geometry.py` — dodać `project_point_to_segment()`, `point_on_polygon_boundary()`, usunąć aliasy `build_*_outline`
- `ui/drawing_canvas.py` — zastąpić `_copy_polygon` / `_copy_polygons` → `polygon.copy()`, zastąpić `_distance_cm` → `segment_length`, zastąpić `_project_point_to_segment*` → importy z geometry, zastąpić `_point_on_polygon_boundary` → import z geometry
- `core/project_state.py` — zastąpić `_clone_polygon` → `polygon.copy()`, usunąć zduplikowaną implementację
- `core/layout_engine.py` — zastąpić `_polygon_to_dict` → ujednolicić z `_serialize_polygon` (albo przenieść do models)
- Testy — zaktualizować importy jeśli `build_*_outline` zostaną usunięte

### Etap 2: Podział `drawing_canvas.py` (4199→~5 plików)

Proponuję podział w katalogu `ui/canvas/`:

| Nowy moduł | Odpowiedzialność | Estymacja linii | Źródłowe zakresy linii |
|---|---|---|---|
| `ui/canvas/__init__.py` | Re-eksport `DrawingCanvas` | ~5 | — |
| `ui/canvas/drawing_canvas.py` | Klasa `DrawingCanvas` — fasada, state, events | ~800 | 315-505, 2759-2934, __init__, set_mode, etc. |
| `ui/canvas/rendering.py` | Wszystkie metody `_draw_*` i `paintEvent` | ~1200 | 3008-4199 |
| `ui/canvas/snap_engine.py` | Snap, inference, grid, angle calc | ~500 | 1649-2085 |
| `ui/canvas/geometry_edit.py` | Drag, undo/redo, vertex/hole editing | ~600 | 556-669, 1059-1370 |
| `ui/canvas/sheet_renderer.py` | Sheet placement clipping & rendering | ~400 | 791-1013 |
| `ui/canvas/inline_editor.py` | `_InlineSegmentEditor`, post-draw editor | ~350 | 99-208, 2107-2456 |
| `ui/canvas/data_types.py` | Dataclassy pomocnicze | ~100 | 208-315 |

**Technika podziału**: Mixins albo delegacja. Rendering i snap są wystarczająco niezależne, żeby być oddzielnymi klasami/modułami wywoływanymi przez `DrawingCanvas`.

### Etap 3: Podział `main_window.py` (1418 linii) — opcjonalny

Plik jest duży, ale bardziej spójny niż drawing_canvas. Jeśli go dzielić:
- `ui/main_window_dialogs.py` — metody `_dlg_*` (~250 linii)
- `ui/main_window_commands.py` — metody `_on_*` i edycja stanu (~300 linii)
- Reszta (build_chrome, history, project I/O) zostaje w `main_window.py`

### Etap 4: Podział `project_state.py` (932 linii) — opcjonalny

- `core/serialization.py` — funkcje `_serialize_*` / `_deserialize_*` (linie 669-932, ~260 linii)
- `core/project_state.py` — klasa `ProjectState` (~670 linii)

### Weryfikacja

- `uv run pytest` po każdym etapie
- Sprawdzenie, że importy z testów i innych modułów działają
- Brak zmian semantyki — tylko przeorganizacja + usunięcie duplikatów

### Ryzyka

- **Etap 2 jest najbardziej ryzykowny** — `DrawingCanvas` ma 249 metod z dużym coupling wewnętrznym. Mixin-based split jest bezpieczniejszy niż pełna delegacja
- **Aliasy `build_*_outline`** są używane masowo w testach (80+ wystąpień) — albo zachować je jako aliasy, albo zrobić mass-rename
- **Serializacja** w `project_state.py` jest blisko kontekstu użycia — przeniesienie jest opcjonalne

Rozumiem, kontynuuję analizę w trybie planowania. Czy chcesz, żebym bardziej szczegółowo zbadał któryś z aspektów, albo masz uwagi do proponowanego planu?
