# Plan podziału dużych plików i usunięcia duplikatów

## Analiza dodatkowych plików (>300 linii)

### Dodatkowe duże pliki zidentyfikowane:

**1. scripts/print_test_expectations.py (494 linii)**
- Zawiera listę 80+ `Expectation` dataclassów z testami
- Każdy wpis ma test_id, input_summary, expected_summary
- **Rekomendacja:** Podział na moduły per kategoria testów:
  - `scripts/expectations/geometry.py` — testy geometrii
  - `scripts/expectations/canvas_mapper.py` — testy canvas mapper
  - `scripts/expectations/mainwindow.py` — testy main window
  - `scripts/expectations/layout_engine.py` — testy layout engine
- **Ryzyko:** Niskie — to tylko dane testowe

**2. ui/dialogs/material_dialog.py (295 linii)**
- Zawiera 2 klasy dialogów: `BlachyDialog` i `MaterialDialog`
- Każda klasa ~140-150 linii z UI setup, walidacją, pobieraniem wartości
- **Rekomendacja:** Podział na osobne pliki:
  - `ui/dialogs/blachy_dialog.py` — `BlachyDialog`
  - `ui/dialogs/material_dialog.py` — `MaterialDialog` (pozostała)
- **Ryzyko:** Niskie — klasy są niezależne

**3. ui/dialogs/settings_dialog.py (282 linii)**
- Jedna klasa `SettingsDialog` z wieloma grupami ustawień
- Mix UI setup, walidacji, ładowania/zapisu wartości
- **Rekomendacja:** Podział na komponenty:
  - `ui/dialogs/settings_dialog.py` — główna klasa dialogu
  - `ui/dialogs/settings_groups.py` — helper classes dla różnych grup ustawień (grid, snap, UI, etc.)
- **Ryzyko:** Średnie — wymaga refaktoringu UI setup

**4. core/geometry.py (453 linii)**
- Mix: kształty (make_*), walidacja, geometria obliczeniowa, layout helpers
- Funkcje o różnych poziomach abstrakcji
- **Rekomendacja:** Podział logiczny:
  - `core/geometry/shapes.py` — make_rectangle, make_triangle, make_trapezoid
  - `core/geometry/validation.py` — validate_polygon, point_in_polygon, etc.
  - `core/geometry/computational.py` — segment_length, orientation, intersections
  - `core/geometry/layout_helpers.py` — vertical_segments_for_band, subtract_segments
- **Ryzyko:** Średnie — wiele zależności między funkcjami

**5. core/models.py (353 linii)**
- Mix: podstawowe modele (Point2D, Polygon2D) + biznesowe modele (RoofPlane, Material, etc.)
- Utility functions mixed z dataclasses
- **Rekomendacja:** Podział warstw:
  - `core/models/basic.py` — Point2D, Bounds2D, Polygon2D
  - `core/models/business.py` — Material, RoofPlane, SheetPlacement, etc.
  - `core/models/utilities.py` — cm2_to_m2 i inne helper functions
- **Ryzyko:** Średnie — cykliczne zależności możliwe

**6. core/app_settings.py (213 linii)**
- Jedna klasa z 25+ fields + constants + validation
- Mix definicji, walidacji, serializacji
- **Rekomendacja:** Podział na:
  - `core/app_settings.py` — główna klasa AppSettings
  - `core/app_settings/constants.py` — wszystkie stałe (SHIFT_DRAG_BEHAVIOR_*, etc.)
  - `core/app_settings/validation.py` — metody walidacji
- **Ryzyko:** Niskie — czysty podział organizacyjny

## Zaktualizowany plan implementacji

### Etap 1: Usunięcie semantycznych duplikatów (niski risk)
- Dodać `Polygon2D.copy()` do `core/models.py` → zastąpić `_copy_polygon` (drawing_canvas) i `_clone_polygon` (project_state)
- Przenieść `_distance_cm` → użycie `segment_length` z geometry
- Ujednolicić `_serialize_polygon` / `_polygon_to_dict` (project_state vs layout_engine)  
- Przenieść `_project_point_to_segment` i `_point_on_polygon_boundary` → `core/geometry.py`
- Zachować aliasy `build_*_outline` (80+ użyć w testach)

### Etap 2: Podział `drawing_canvas.py` (4199 linii → ~6 modułów)
Nowy katalog `ui/canvas/`:
- `drawing_canvas.py` — fasada, state, events (~800 linii)
- `rendering.py` — wszystkie metody `_draw_*` i `paintEvent` (~1200 linii)
- `snap_engine.py` — snap, inference, grid (~500 linii)
- `geometry_edit.py` — drag, undo/redo, vertex editing (~600 linii)
- `sheet_renderer.py` — sheet placement clipping (~400 linii)
- `inline_editor.py` + `data_types.py` — pomocnicze (~450 linii)

### Etap 3: Podział dialogów UI (niski/średni risk)
- Podzielić `material_dialog.py` → `blachy_dialog.py` + `material_dialog.py`
- Zrefaktorować `settings_dialog.py` → główna klasa + helper groups

### Etap 4: Podział `scripts/print_test_expectations.py` (niski risk)
- Podzielić na kategorie testów w `scripts/expectations/`

### Etap 5: Podział core modules (średni risk)
- Podzielić `core/geometry.py` na 4 moduły tematyczne
- Podzielić `core/models.py` na warstwy (basic/business/utilities)
- Podzielić `core/app_settings.py` na 3 moduły

### Etap 6: Podział pozostałych dużych plików (opcjonalny)
- `main_window.py` (1418 linii) → dialogi + commands
- `project_state.py` (932 linii) → klasa + serializacja
- `layout_engine.py` (795 linii) → data structures + algorithms
- `reporting.py` (718 linii) → data classes + formatters

### Weryfikacja: `uv run pytest` po każdym etapie

## Priorytety

1. **Wysoki:** Etap 1 (duplikaty) + Etap 2 (drawing_canvas)
2. **Średni:** Etap 3 (dialogi) + Etap 5 (core modules)
3. **Niski:** Etap 4 (test expectations) + Etap 6 (pozostałe)

## Szacowany efekt

- Redukcja największych plików: 4199→~800, 1418→~700, 932→~600
- Lepsza spójność tematyczna modułów
- Łatwiejsze testowanie i utrzymanie
- Usunięcie 6+ semantycznych duplikatów