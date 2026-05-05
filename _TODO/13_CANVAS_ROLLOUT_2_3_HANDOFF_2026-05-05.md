# Canvas Rollout 2-3 Handoff

## Status

- Data: 2026-05-05
- Rollout 1 jest wykonany i zweryfikowany.
- Ten plik jest trwałym handoffem do wznowienia prac po wyczyszczeniu kontekstu.

## Co już jest zrobione

Rollout 1 wdrożony:

- nowe defaulty `AppSettings`:
  - `show_crosshair = False`
  - `snap_to_3060deg = True`
  - `label_always_visible = True`
- przycisk `Domyślne` w `SettingsDialog`
- usunięty `material_button` z toolbaru
- dodany osobny toolbarowy toggle `Snap to Grid`
- `Pokaż arkusze` startuje jako wyłączone
- w menu `Plik` został tylko `Drukuj raport`

## Zweryfikowany baseline po Rollout 1

Uruchomione i zielone:

- `uv run pytest tests/test_app_settings.py -q`
- `uv run pytest tests/test_workspace.py -q`
- `uv run pytest tests/test_mainwindow_ui_contract.py -q`
- `uv run ruff check core/app_settings.py ui/dialogs/settings_dialog.py ui/toolbar.py ui/main_window.py ui/workspace.py ui/theme_manager.py tests/test_app_settings.py tests/test_mainwindow_ui_contract.py tests/test_workspace.py`
- `uv run pytest`

Stan końcowy po rollout 1:

- `298 passed`

## Gdzie jest pełniejszy plan

Szczegółowy opis etapów 2-4 istnieje także w:

- [docs/plan-zmian-canvas-ustawienia-toolbar-2026-05-04.md](/data/APP/83_4dach_zimnoch/qt/4dach/docs/plan-zmian-canvas-ustawienia-toolbar-2026-05-04.md)

Uwaga:

- ten plik w bieżącym worktree jest `untracked`, więc nie traktować go jako jedynego źródła handoffu
- kanonicznym punktem startowym do nowej sesji ma być ten plik w `_TODO/`

## Rollout 2

Zakres:

- usunąć `edge_drag_mode` z `AppSettings`, `SettingsDialog`, serializacji i testów
- zachować kompatybilność odczytu starych configów z kluczem `edge_drag_mode`
- w `DrawingCanvas` rozdzielić midpointy po typie geometrii:
  - outline midpoint przesuwa całą krawędź
  - cutout midpoint dodaje nowy wierzchołek i od razu uruchamia drag tego punktu
- dodać render i hit-test midpointów dla wycinków
- usunąć środkową kulkę wycinka, ale zachować drag całego wycinka po kliknięciu wewnątrz
- naprawić drag bocznej krawędzi outline tak, aby pionowe krawędzie poruszały się tylko po `X`, a poziome tylko po `Y`
- przesunąć badge długości tak, aby nie zasłaniały midpointów
- zostawić edycję długości tylko dla badge outline
- wprowadzić jednolite skalowanie outline + holes względem absolutnego `(0, 0)`
- użyć jednego helpera uniform-scale zarówno dla `_confirm_post_draw_editor()`, jak i `_prompt_scale_polygon()`
- zachować istniejący lokalny undo/redo canvasa

Najbardziej prawdopodobnie dotykane pliki:

- `core/app_settings.py`
- `ui/dialogs/settings_dialog.py`
- `ui/drawing_canvas.py`
- `tests/test_app_settings.py`
- `tests/test_mainwindow_ui_contract.py`
- `tests/test_drawing_canvas.py`

Testy minimalne:

- `uv run pytest tests/test_drawing_canvas.py -q`
- `uv run pytest tests/test_app_settings.py -q`
- `uv run pytest tests/test_mainwindow_ui_contract.py -q`
- `uv run pytest tests/test_workspace.py -q`
- potem `uv run pytest`

## Rollout 3

Zakres:

- nie zmieniać formatu serializacji `layout_bands`
- naprawić split engine dla partial cutout przez dokładniejszą dekompozycję band/segmentów
- doprowadzić do tego, aby każdy wynikowy segment nadal miał najwyżej jedno `partial_cut_line_y_cm`
- poprawić wcześniejsze grupowanie band pieces i granice segmentów
- traktować `ui/canvas/sheet_geometry.py` jako konsument renderingu, a nie główne miejsce naprawy
- ewentualne zmiany mają siedzieć głównie w `core/layout_engine.py` i tylko pomocniczo w `core/project_state.py`
- dodać regresje dla skośnych i częściowych wycinków wpływających tylko na część szerokości pasa

Najbardziej prawdopodobnie dotykane pliki:

- `core/layout_engine.py`
- `core/project_state.py`
- `ui/canvas/sheet_geometry.py`
- `tests/test_layout_engine.py`
- `tests/test_models_and_state.py`
- `tests/test_drawing_canvas.py`

Testy minimalne:

- `uv run pytest tests/test_layout_engine.py -q`
- `uv run pytest tests/test_models_and_state.py -q`
- `uv run pytest tests/test_drawing_canvas.py -q`
- potem `uv run pytest`

## Czy rollout 2 i 3 robić razem

Rekomendacja:

- nie robić rollout 2 i 3 w jednym mieszanym przebiegu
- nie odpalać ich równolegle jako dwóch niezależnych agentów na tym samym worktree
- najlepiej zrobić je w dwóch osobnych sesjach albo w jednej sesji, ale sekwencyjnie i z twardym checkpointem po rollout 2

Powód:

- rollout 2 zmienia semantykę edycji canvasa i testy UI
- rollout 3 zmienia logikę layout engine i regresje domenowe
- zmieszanie obu zakresów bardzo utrudni diagnostykę, gdy coś padnie w `tests/test_drawing_canvas.py`

Praktyczny wariant:

1. Nowa sesja: tylko rollout 2.
2. Zielone testy rollout 2 + pełny `uv run pytest`.
3. Druga nowa sesja: rollout 3 na bazie kodu po rollout 2.

## Co było przygotowane pod kolejne rollouty

Jawne przygotowanie wykonane w rollout 1:

- `edge_drag_mode` został celowo zostawiony w kodzie, żeby jego usunięcie zrobić dopiero w rollout 2
- toggle `Snap to Grid` został rozdzielony od `Pokaż siatkę`, więc rollout 2 nie powinien już mieszać tych pojęć

Nie było dodatkowego ukrytego scaffoldu pod rollout 3.

## Uwaga o worktree

W repo są też inne zmiany w `docs/` i plikach niepowiązanych z tym zadaniem.

Przy kontynuacji:

- nie porządkować tych plików przy rollout 2 lub 3
- zawęzić pracę do kodu i testów związanych z canvas/layout

## Jak rozpocząć nową sesję

Najbezpieczniej:

1. Otworzyć nową sesję.
2. W pierwszej wiadomości kazać agentowi przeczytać:
   - `AGENTS.md`
   - ten plik: `_TODO/13_CANVAS_ROLLOUT_2_3_HANDOFF_2026-05-05.md`
3. Dopiero potem zlecić konkretnie `Rollout 2` albo `Rollout 3`.

## Gotowy prompt do nowej sesji

### Start Rollout 2

```text
Przeczytaj AGENTS.md oraz _TODO/13_CANVAS_ROLLOUT_2_3_HANDOFF_2026-05-05.md.
Wdrażaj wyłącznie Rollout 2 z tego handoffu.
Nie dotykaj rollout 3 ani nie porządkuj docs/.
Najpierw potwierdź live baseline w repo, potem zrób zmiany i zweryfikuj je wskazanymi testami.
```

### Start Rollout 3

```text
Przeczytaj AGENTS.md oraz _TODO/13_CANVAS_ROLLOUT_2_3_HANDOFF_2026-05-05.md.
Wdrażaj wyłącznie Rollout 3 z tego handoffu.
Załóż, że Rollout 1 jest już wykonany; przed zmianami sprawdź live stan repo.
Nie zmieniaj formatu serializacji layout_bands.
Najpierw odtwórz regresję testem, potem napraw i zweryfikuj wskazanymi testami.
```

## Załączniki w nowej sesji

Jeśli interfejs pozwala dołączyć plik, dołącz:

- przede wszystkim ten plik z `_TODO/`

Opcjonalnie jako drugi materiał referencyjny:

- `docs/plan-zmian-canvas-ustawienia-toolbar-2026-05-04.md`

Nie trzeba startować od "build". Lepiej startować od planu/handoffu i odczytu live repo.
