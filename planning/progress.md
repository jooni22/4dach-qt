# Progress Log

## Session: 2026-04-23

### Phase 10: Manual Sheet Overrides + Dirty State
- **Status:** complete
- Actions taken:
  - Rozszerzono `core/models.py` i `core/project_state.py` o `manually_removed_auto_sheet_ids` oraz `layout_dirty_reason` persystowane w `config.json`.
  - Dodano domenowy workflow ręcznych korekt arkuszy: `active_sheet_placements_for_plane()`, `add_manual_sheet_placement()` i `remove_sheet_placement()`.
  - Ujednolicono invalidation layoutu po zmianie geometrii i materiału, tak aby auto-layout był czyszczony, ręczne arkusze zostawały, a połać otrzymywała jawny `dirty-state`.
  - Podłączono menu `Arkusze` w `mainwindow.py` do rzeczywistych akcji: dodanie/usunięcie arkusza, podgląd aktywnych arkuszy i zmiana materiału aktywnej połaci.
  - Zmieniono `core/reporting.py`, aby BOM, koszt i powierzchnie bazowały na aktywnych arkuszach po korektach manualnych.
  - Rozszerzono testy domenowe i raportowe o regresje dla manualnych korekt oraz `dirty-state`.
- Files created/modified:
  - `core/models.py`
  - `core/project_state.py`
  - `core/reporting.py`
  - `mainwindow.py`
  - `tests/test_models_and_state.py`
  - `planning/task_plan.md`
  - `planning/findings.md`
  - `planning/progress.md`

### Phase 9: Report UI Integration
- **Status:** complete
- Actions taken:
  - Podłączono akcje menu `Drukuj raport`, `Drukuj raport ciągły` i `Drukuj raport skrócony` do rzeczywistego workflow domenowego: generacja layoutu, budowa raportu i render HTML.
  - Zmieniono drugą zakładkę `QTabWidget` na wbudowany podgląd raportu oparty o `QTextBrowser`, dzięki czemu UI pokazuje BOM, koszt, odpady i ostrzeżenia bez otwierania osobnego okna.
  - Dodano czyszczenie ostatniego raportu po zmianie geometrii, materiału lub danych firmy, aby nie pokazywać nieaktualnych wyników.
  - Rozszerzono `core/reporting.py` o warianty HTML (`include_bom`, `title_suffix`) używane przez UI.
  - Zsynchronizowano `planning/task_plan.md` i `planning/findings.md` z nowym stanem implementacji.
- Files created/modified:
  - `mainwindow.py`
  - `core/reporting.py`
  - `planning/task_plan.md`
  - `planning/findings.md`
  - `planning/progress.md`

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

### Phase 8: Scope Cleanup + Reporting
- **Status:** complete
- Actions taken:
  - Usunięto z menu Qt akcje `Przesuń`, `Przesuń punkt`, `Dodaj punkt`, `Usuń punkt`, flip/rotate, align oraz linie podziału zgodnie z decyzją użytkownika.
  - Wycięto usunięty zakres z aktywnego planu i przestawiono roadmapę na raportowanie, HTML raportu i dalsze ręczne korekty arkuszy.
  - Rozszerzono `core/reporting.py` o BOM według długości arkusza, koszt całkowity, odpady oraz agregację ostrzeżeń i odrzuconych segmentów.
  - Dodano prosty generator HTML raportu oparty o dane firmy, materiał, podsumowanie, BOM i ostrzeżenia.
  - Dodano `tests/test_reporting.py` i zweryfikowano nowy zakres testami domenowymi.
- Files created/modified:
  - `mainwindow.py`
  - `core/reporting.py`
  - `tests/test_reporting.py`
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

### Phase 11: Dynamic Plane Tabs + Active Plane Sync
- **Status:** complete
- Actions taken:
  - Dodano do `ProjectState` jawne `set_active_plane()`, aby UI mogło bezpiecznie przełączać aktywną połać niezależnie od dodawania geometrii.
  - Przebudowano synchronizację `QTabWidget` w `mainwindow.py`: każda połać ma własną zakładkę z canvasem, a zakładka `Raport` jest utrzymywana jako stała zakładka końcowa.
  - Ujednolicono przełączanie aktywnej połaci z wyborem zakładki i odświeżaniem `variant_combo` oraz widoku raportu.
  - Ograniczono pokazywanie ostatniego HTML raportu tylko do połaci, dla której został wygenerowany, aby nie mieszać wyników między zakładkami.
  - Rozszerzono testy domenowe i kontraktowe UI o regresje dla przełączania aktywnej połaci i dynamicznych zakładek.
- Files created/modified:
  - `core/project_state.py`
  - `mainwindow.py`
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
| Raportowanie domenowe + HTML report | `pytest -q tests/test_reporting.py tests/test_models_and_state.py` | BOM, koszt, odpady, ostrzeżenia i HTML raportu przechodzą | 17 testów przeszło | pass |
| Raport UI + regresja domeny | `pytest -q tests/test_reporting.py tests/test_models_and_state.py tests/test_geometry.py tests/test_mainwindow_ui_contract.py` | Integracja podglądu raportu nie psuje domeny ani kontraktu UI | 21 testów przeszło, 1 skip (`pytestqt`) | pass |
| Ręczne korekty arkuszy + dirty-state | `pytest -q tests/test_models_and_state.py tests/test_reporting.py` | Manualne arkusze, usuwanie auto-arkuszy i `layout_dirty_reason` przechodzą regresję | 20 testów przeszło | pass |
| Pełny zestaw po wdrożeniu korekt arkuszy | `pytest -q` | Repo pozostaje zielone po rozszerzeniu workflow `Arkusze` | 24 testy przeszły, 1 skip (`pytestqt`) | pass |
| Dynamiczne zakładki połaci + aktywna połać | `pytest -q tests/test_models_and_state.py tests/test_reporting.py tests/test_geometry.py tests/test_mainwindow_ui_contract.py` | Synchronizacja zakładek z `ProjectState` nie psuje domeny ani kontraktu UI | 25 testów przeszło, 1 skip (`pytestqt`) | pass |

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
| 2026-04-23 18:47 | Pierwsza wersja testów raportowania miała błędne expectedy względem rzeczywistej geometrii pasów | 1 | Zweryfikowano wyniki `generate_layout()` i skorygowano oczekiwania testowe |
| 2026-04-23 19:30 | UI miało akcje `Drukuj raport*`, ale bez realnego podłączenia do domeny i bez miejsca na pokazanie wyników | 1 | Podłączono akcje do generacji raportu i zamieniono drugą zakładkę na podgląd HTML raportu |

## 5-Question Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | Po iteracji edycji outline i pierwszym spięciu menu `Kształt` / `Wycinki` z domeną |
| Where am I going? | Do kolejnej iteracji: ręczne korekty arkuszy, dirty-state i pełniejsza synchronizacja zakładek połaci z modelem projektu |
| What's the goal? | Rozwijać realne workflow domenowe małymi krokami bez przebudowy UI |
| What have I learned? | Najbezpieczniej rozwijać repo przez stabilne kontrakty domenowe i dopiero potem doszywać UI; osadzony preview raportu dobrze mieści się w istniejącym shellu Qt |
| What have I done? | Usunięto odłożony zakres z menu i planu, wdrożono raportowanie domenowe, generator HTML raportu i podgląd raportu bezpośrednio w UI |

### Phase 13: Smoke Tests for Load/Save and Basic Workflow
- **Status:** complete
- Actions taken:
  - Dodano smoke test `test_load_config_and_save_config_round_trip` weryfikujący, że zapis/odczyt JSON config zachowuje dane.
  - Dodano smoke test `test_project_state_config_round_trip` weryfikujący round-trip przez config dict z `company_data` i `blachy`.
  - Dodano smoke test `test_basic_user_workflow_smoke` weryfikujący podstawowy workflow: dodanie połaci, generowanie layoutu, ręczne arkusze, persystencję.
  - Naprawiono błędy w testach: poprawiono wywołanie `add_manual_sheet_placement` z obiektem `SheetPlacement`, dodano brakujące parametry `Material`.
  - Wszystkie 28 testów przechodzą (1 skipped przez brak PySide6).
- Files created/modified:
  - `tests/test_models_and_state.py`
  - `planning/task_plan.md`
  - `planning/findings.md`
  - `planning/progress.md`
