# Progress Log

## Session: 2026-04-23

### Phase 1: Requirements & Discovery
- **Status:** complete
- **Started:** 2026-04-23 16:00
- Actions taken:
  - Przeczytano dokumentację domenową i opis UI.
  - Zweryfikowano `mainwindow.py`, `dialogs.py`, `config.json`, `form.ui`, `ui_form.py`, `pyproject.toml`, `requirements.txt`.
  - Potwierdzono brak wydzielonych modeli domenowych, stanu projektu i testów.
- Files created/modified:
  - `planning/task_plan.md`
  - `planning/findings.md`
  - `planning/progress.md`

### Phase 7: Geometry Editing + Menu Integration
- **Status:** complete
- Actions taken:
  - Dodano do `ProjectState` walidowane operacje edycji obrysu połaci: `move_roof_plane()`, `move_roof_plane_point()`, `insert_roof_plane_point()` i `delete_roof_plane_point()`.
  - Ujednolicono obsługę zmian geometrii przez helpery walidujące outline, wycinki, `layout_revision`, `auto_sheet_placements` i automatyczne `base_line_y_cm`.
  - Podłączono akcje menu `Kształt` i `Wycinki` do domeny przez proste dialogi wejściowe oparte o `QInputDialog`.
  - Dodano regresyjne testy domenowe dla edycji outline i usuwania wycinka.
  - Skorygowano `resolve_base_line_y_cm()` tak, aby po zmianach geometrii bazował na aktualnym `max_y` obrysu.
- Files created/modified:
  - `core/project_state.py`
  - `mainwindow.py`
  - `tests/test_models_and_state.py`
  - `planning/findings.md`
  - `planning/progress.md`

### Phase 2: Planning & Structure
- **Status:** complete
- Actions taken:
  - Zdefiniowano minimalny pierwszy milestone oparty o wydzielenie domeny i testów.
  - Ustalono, że UI pozostaje bez większej przebudowy, a integracja będzie cienka.
  - Ustalono zestaw nowych modułów: `core/models.py`, `core/project_state.py`, `core/geometry.py`, `core/layout_engine.py`, `core/reporting.py`.
- Files created/modified:
  - `planning/task_plan.md`
  - `planning/findings.md`
  - `planning/progress.md`

### Phase 3: Implementation
- **Status:** complete
- Actions taken:
  - Dodano `core/models.py` z modelami domenowymi dla geometrii, materiałów, połaci i arkuszy.
  - Dodano `core/project_state.py` z podstawowym stanem projektu i mapowaniem z `config.json`.
  - Dodano szkielety `core/geometry.py`, `core/layout_engine.py` i `core/reporting.py`.
  - Zintegrowano `ProjectState` z `MainWindow` do odświeżania listy materiałów w toolbarze.
- Files created/modified:
  - `core/models.py`
  - `core/project_state.py`
  - `core/geometry.py`
  - `core/layout_engine.py`
  - `core/reporting.py`
  - `mainwindow.py`
  - `pyproject.toml`
  - `requirements.txt`

### Phase 4: Testing & Verification
- **Status:** in_progress
- Actions taken:
  - Dodano `tests/test_models_and_state.py`.
  - Dodano `tests/test_mainwindow_ui_contract.py`.
  - Dodano `tests/conftest.py` z ustawieniem `QT_QPA_PLATFORM=offscreen`.
  - Uruchomiono `pytest -q`, poprawiono test i konfigurację `pytest`.
  - Rozszerzono testy o round-trip `ProjectState` i fabryki obrysów geometrycznych.
- Files created/modified:
  - `tests/conftest.py`
  - `tests/test_models_and_state.py`
  - `tests/test_mainwindow_ui_contract.py`
  - `pyproject.toml`
  - `core/geometry.py`
  - `core/project_state.py`
  - `mainwindow.py`

### Phase 5: Handoff Preparation
- **Status:** in_progress
- Actions taken:
  - Zsynchronizowano plan roboczy z pełnym zakresem wdrożenia.
  - Zebrano decyzje i założenia do handoffu.
  - Przygotowano prompt dla kolejnej sesji implementacyjnej.
  - Przeniesiono rdzeń domenowy do `core/` i pliki planowania do `planning/`.
- Files created/modified:
  - `planning/task_plan.md`
  - `planning/findings.md`
  - `planning/progress.md`

### Phase 6: Geometry + Layout Iteration
- **Status:** complete
- Actions taken:
  - Rozbudowano `ProjectState` o pełniejszą serializację `generation_settings`, `auto_sheet_placements`, `manual_sheet_placements` i `layout_revision`.
  - Dodano domenowy workflow wycinków: walidowane `add_hole_to_plane()` oraz `move_hole_in_plane()`.
  - Rozszerzono `core/geometry.py` o walidację samoprzecięć, długości krawędzi, nakładania wycinków i podstawowe operacje edycyjne poligonu.
  - Podłączono `core/layout_engine.py` do wspólnej reguły `base_line_y_cm` oraz do `ProjectState.generate_layout_for_active_plane()`.
  - Dodano nowe testy domenowe i geometrii oraz rozszerzono kontrakt UI o odświeżanie aktywnej połaci na głównym canvasie.
- Files created/modified:
  - `core/models.py`
  - `core/project_state.py`
  - `core/geometry.py`
  - `core/layout_engine.py`
  - `tests/test_geometry.py`
  - `tests/test_models_and_state.py`
  - `tests/test_mainwindow_ui_contract.py`
  - `planning/task_plan.md`
  - `planning/findings.md`
  - `planning/progress.md`

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Domena + stan projektu | `pytest -q` | Testy modeli i stanu przechodzą | 5 testów przeszło | pass |
| Kontrakt UI głównego okna | `pytest -q` | Test UI wykonuje się przy dostępnych zależnościach Qt | Skipped, bo brak `pytest-qt` w środowisku | skip |
| Domena + round-trip połaci | `pytest -q` | Nowe połacie serializują się do `project_state` i wracają z configu | 7 testów przeszło łącznie | pass |
| Geometria + ProjectState + layout | `pytest -q tests/test_geometry.py tests/test_models_and_state.py` | Nowe workflow wycinków i globalna baza modułów przechodzą | 15 testów przeszło | pass |
| Pełny zestaw testów repo | `pytest -q` | Testy domenowe przechodzą, UI kontrakt jest co najwyżej skip przy braku pluginu | 15 testów przeszło, 1 skip (`pytestqt`) | pass |
| Geometria edycji outline + ProjectState | `pytest -q tests/test_geometry.py tests/test_models_and_state.py` | Operacje przesuwania/wstawiania/usuwania punktów są walidowane i przechodzą | 18 testów przeszło | pass |
| Pełny zestaw po spięciu menu z domeną | `pytest -q` | Integracja `mainwindow.py` nie psuje istniejących testów | 18 testów przeszło, 1 skip (`pytestqt`) | pass |

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-04-23 15:55 | Pliki planowania zawierały starszy kontekst analityczny, nie plan wdrożenia | 1 | Zastąpiono je aktualnym planem implementacyjnym |
| 2026-04-23 16:18 | Zbyt mocne założenie w teście layout engine o flagach długości | 1 | Skorygowano oczekiwania dla segmentów przeciętych przez wycinek |
| 2026-04-23 16:19 | Ostrzeżenie `pytest` o nieznanej opcji `qt_api` bez pluginu | 1 | Usunięto `qt_api` z `pyproject.toml` |
| 2026-04-23 16:35 | Brak pełnej specyfikacji geometrii dla trójkąta `dowolny` | 1 | Wdrożono jawne uproszczenie i objęto je testami geometrii |
| 2026-04-23 17:10 | Test globalnej bazy modułów nie przecinał wycinka, więc dawał błędny expected | 1 | Zmieniono szerokość pasa z 60 cm na 40 cm i zostawiono sprawdzenie długości wynikających ze wspólnej bazy |
| 2026-04-23 18:20 | Pierwszy test edycji outline wstawiał punkt powodujący samoprzecięcie | 1 | Poprawiono dane testowe, aby scenariusz sprawdzał poprawną geometrię |
| 2026-04-23 18:23 | `base_line_y_cm` nie odświeżało się po zmianie outline zgodnie z nową regułą domenową | 1 | Uproszczono `resolve_base_line_y_cm()` do bieżącego `outline.max_y` |

## 5-Question Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | Po iteracji edycji outline i pierwszym spięciu menu `Kształt` / `Wycinki` z domeną |
| Where am I going? | Do kolejnej iteracji: flip/rotate, ręczne korekty arkuszy i lepszy workflow edycji bezpośrednio na canvasie |
| What's the goal? | Rozwijać realne workflow domenowe małymi krokami bez przebudowy UI |
| What have I learned? | Proste dialogi wejściowe wystarczają, by odblokować sensowną integrację UI z walidowaną domeną |
| What have I done? | Dodano walidowaną edycję outline, spięto podstawowe akcje menu z `ProjectState` i utrwalono to testami |
