# Risky Refactor Agent Brief

## Cel

Ten plik jest briefem dla agenta, który ma "myśleć długo", planować ostrożnie i podejmować tylko te większe, bardziej ryzykowne obszary refaktoru, które zostały świadomie odłożone podczas wcześniejszych etapów cleanupu.

To nie jest kolejny mały etap cleanupu. To jest mapa obszarów wysokiego ryzyka wraz z warunkami bezpieczeństwa, wymaganym przygotowaniem testowym i sugerowaną kolejnością.

## Aktualny stan repo

- Branch: `fix/report-and-drawing-overlays`
- Branch status: lokalna gałąź jest `do przodu 4`
- Aktualny suite status:
  - `uv run pytest` -> `242 passed, 2 skipped`
- Znane skipy:
  - `tests/test_mainwindow_ui_contract.py:862`
  - `tests/test_mainwindow_ui_contract.py:893`
  - oba opisane jako `freehand snap origin — pending Package 1 implementation`

## Najważniejsze zasady dla agenta

Przed jakimkolwiek większym ruchem agent musi:

1. Przeczytać `AGENTS.md`
2. Przeczytać `docs/review-backlog.md`
3. Przeczytać `_TODO/CLEANUP_PLAN.md`
4. Sprawdzić aktualny `git status`
5. Traktować obecny zielony suite jako punkt odniesienia
6. Nie pracować przez duży rewrite bez testów charakteryzujących
7. Nie mieszać logiki Qt/UI do `core/`
8. Nie zmieniać formatu danych i kontraktów serializacji bez jawnej decyzji migracyjnej

## Jak użyć tego briefu z agentem

Agent powinien pracować według tego schematu:

1. Wybierz dokładnie jeden obszar z poniższej listy.
2. Najpierw wykonaj mapowanie odpowiedzialności i call-site'ów.
3. Wypisz aktualne ryzyka i test gaps.
4. Dodaj testy charakteryzujące przed zmianą produkcyjną, jeśli obszar nie jest już dobrze osłonięty.
5. Zaproponuj najmniejszy możliwy refaktor, który daje realny zysk.
6. Uruchom testy lokalne i pełne `uv run pytest`.
7. W raporcie końcowym podaj:
   - co zmieniłeś
   - jakie ryzyka zostały domknięte
   - jakie ryzyka nadal pozostają
   - czy obszar nadaje się na kolejny etap dekompozycji

## Sugerowana kolejność ryzykownych prac

### 1. `ui/drawing_canvas.py` — interakcje i odpowiedzialności

To jest najwyższy hotspot ryzyka w całym repo.

#### Dlaczego to ryzykowne

- plik ma ~4000+ linii
- miesza wiele odpowiedzialności w jednej klasie:
  - rendering
  - snapping
  - overlays
  - geometry editing
  - selection
  - sheet visualization
  - undo/history
  - event handling
- wcześniejsze awarie i flaky/functional problemy skupiały się właśnie tutaj

#### Co już zostało ustabilizowane

- render helper coverage / clipping tests zostały dodane
- origin-marker crash został naprawiony
- explicit snap priority nad inference snap została ustabilizowana
- `MODE_DRAW_OUTLINE` przestał używać istniejącej połaci do point snap, ale nadal może używać jej do inferencji po krawędziach

#### Najbardziej ryzykowne podobszary `DrawingCanvas`

##### 1A. Snapping / freehand draw

Obejmuje m.in.:

- `_resolve_draw_preview_endpoint()`
- `_resolve_inference_snap()`
- `_resolve_axis_snap()`
- `_resolve_angular_snap()`
- `_resolve_point_snap()`
- `_resolve_grid_snap()`
- `_build_draw_inferences()`
- target selection for vertices/edges during draw modes

Ryzyko:

- małe zmiany kolejności resolverów zmieniają zachowanie użytkownika
- łatwo rozjechać klasyfikację `_draw_snap_state.kind`
- free-draw i normalny plane/cutout drawing używają podobnych, ale nie identycznych semantyk
- obszar ma silny wpływ na UX i testy GUI

Warunki wejścia:

- utrzymać obecne zielone testy `tests/test_drawing_canvas.py`
- przed większą dekompozycją dodać brakujące testy wokół:
  - multi-step freehand draw
  - inference precedence vs point snap
  - origin/grid interactions w freehand flows

Co agent może zrobić bezpiecznie:

- rozdzielić czysto logiczne helpery decyzyjne od state mutation
- wyodrębnić mały moduł/helper tylko dla "snap candidate selection"
- najpierw zrobić refaktor wewnętrzny bez zmiany publicznego flow eventów

##### 1B. Inline segment editor

Ryzyko:

- wcześniej był jednym z failing obszarów
- ma mieszankę geometrii, edycji tekstowej i event flow
- łatwo uszkodzić commit/cancel semantics i pozycjonowanie wierzchołków

Warunki wejścia:

- najpierw dodać więcej testów charakteryzujących dla confirm/cancel/placement mapping
- nie zaczynać od dużej dekompozycji UI

##### 1C. Geometry edit / drag flow

Obejmuje m.in.:

- `_start_outline_drag`
- `_start_outline_edge_split_drag`
- `_start_plane_body_drag`
- `_start_hole_drag`
- `_start_hole_center_drag`
- `_update_geometry_drag`
- `_commit_geometry_drag`
- `_cancel_geometry_drag`
- origin drag flow

Ryzyko:

- silne sprzężenie z mapperem, selekcją, overlayami i undo
- łatwo rozwalić kolejność sygnałów / commit flow
- część zachowania jest GUI-owo złożona i trudna do odtworzenia samym unit testem

Warunki wejścia:

- dodać testy charakteryzujące dla drag begin/update/commit/cancel
- przygotować checklistę manual QA

##### 1D. Selection / hit testing

Ryzyko:

- już istnieje deferred item z review backlog:
  - `stage-7-pr9-001`
  - sheet hit-testing może wybierać obiekt wizualnie ukryty lub nieobecny w dziurze/cutout
- selection jest spleciona z geometrią, renderem i overlay labels

Warunki wejścia:

- dodać testy dla overlapping sheet shapes / hit targets / hole gaps

##### 1E. Undo / history inside `DrawingCanvas`

Ryzyko:

- history/snapshoty łatwo rozjechać z drag flows
- duplikacja może kusić do dużego refaktoru, ale regressions są kosztowne

Warunki wejścia:

- przed przebudową dopisać testy dla snapshot/restore/undo/redo dla różnych trybów interakcji

##### 1F. Duży split `DrawingCanvas`

To jest osobny, najwyższy poziom ryzyka.

Nie robić na ślepo:

- rozbijania na moduły/koordynatory/renderery/controller-y bez wcześniejszego pokrycia testowego
- wynoszenia połowy klasy naraz do nowych plików

Minimalna bezpieczna ścieżka:

1. Najpierw zbudować testy dla poszczególnych responsibility slices.
2. Potem wydzielać po jednym pionowym wycinku, np.:
   - render helpers
   - snap candidate logic
   - drag session state
3. Każdy wydzielony wycinek musi zachować zielony suite.

### 2. `core/layout_engine.py` — głębszy refaktor algorytmu

Wczesne etapy usunęły lokalne duplikacje, ale to nadal logiczny hotspot.

#### Dlaczego to ryzykowne

- `generate_layout()` nadal ma złożony control flow
- partial cutout i band segmentation są semantycznie kruche
- istnieją historyczne poprawki typu `Fix #...`, co sugeruje warstwowe narastanie wyjątków

#### Obszary szczególnego ryzyka

##### 2A. Partial-cutout semantics

- bottom phase
- top phase
- `partial_cutout_top`
- `top_extra_cm`
- `coverage_polygons`
- `placement_id` selection for top sheet

Ryzyko:

- drobna zmiana może dać poprawnie wyglądający wynik dla prostych przypadków, ale zły dla edge-case'ów

##### 2B. Band segmentation / slab merging

- `_build_band_segments()`
- `_band_pieces_for_range()`
- union/grouping logic
- representative sampled cross-section assumptions

Ryzyko:

- regresje pojawiają się głównie na nieregularnych/skewed geometriach

##### 2C. Warning/rejection paths

- `invalid_max_sheet_length`
- `zero_sheet_height`
- short tail / rejected segment behavior

Ryzyko:

- część ścieżek jest trudna do osiągnięcia i słabo reprezentowana w codziennej pracy użytkownika

#### Warunki wejścia

- zachować Stage 2 characterization tests
- jeśli agent planuje większy redesign, najpierw dopisać brakujące testy wokół:
  - `zero_sheet_height`
  - coverage extension semantics
  - multi-cutout/skewed edge cases

### 3. `core/project_state.py` — większa przebudowa modelu odpowiedzialności

Wcześniejsze etapy zrobiły bezpieczny cleanup lokalny. Nadal ryzykowne byłoby ruszanie głębiej.

#### Dlaczego to ryzykowne

- obiekt łączy rolę kontenera stanu i serwisu domenowego
- mutacje geometrii, dirty-state i layout invalidation są semantycznie ważne
- część aktualnych zachowań jest celowo permisywna

#### Konkretne ryzyka

- zmiana semantyki `layout_dirty_reason`
- zmiana zachowania manual sheet overrides podczas zmian geometrii/materialu
- zmiana obecnie dopuszczalnych przypadków typu holes outside outline
- większa zmiana lookup/model flow może zepsuć round-trip stanu projektu

#### Warunki wejścia

- przed większym redesignem dopisać jeszcze bardziej bezpośrednie testy dla:
  - material replacement / ordering
  - dirty-state mutation matrix
  - interaction między outline/hole changes a layout rebuild

### 4. `ui/main_window.py` — głębsza dekompozycja lifecycle i dialog flows

Wcześniej wykonano tylko lokalne deduplikacje i lekkie extraction helpers.

#### Dlaczego to ryzykowne

- `MainWindow` nadal jest centralnym koordynatorem aplikacji
- obejmuje bootstrap, project flow, dialogs, canvas refresh, report flow, undo-ish orchestration, status bar
- większa dekompozycja może łatwo zepsuć kolejność odświeżeń lub wiring sygnałów

#### Ryzykowne podobszary

- startup lifecycle
- refresh/report/status flow
- dialog action flow jako grupa
- przenoszenie canvas signal management bliżej lifecycle obiektów
- dalsze rozbijanie plane CRUD i command orchestration

#### Warunki wejścia

- zachować istniejące GUI regression tests
- przed większą dekompozycją przygotować odpowiedź na pytanie:
  - czy chcemy wydzielać koordynatory flow,
  - czy tylko helper modules,
  - czy zmieniać ownership stanu i sygnałów

### 5. `core/geometry.py` — walidacja i kontrakty geometrii

#### Dlaczego to ryzykowne

- `validate_hole_polygon()` ma krytyczny kontrakt
- geometry helpers są fundamentem dla `project_state` i `drawing_canvas`
- pozorna duplikacja aliasów może być częścią publicznego API

#### Ryzykowne obszary

- walidacja hole containment
- triangle semantics (`make_triangle()` ambiguity z backlogu)
- uproszczenie aliasów `build_*_outline` / `make_*`

#### Warunki wejścia

- konieczne dodatkowe testy call-site / public API
- żadnych zmian bez sprawdzenia realnych zależności

### 6. `core/models.py` — kompatybilność serializacji

#### Dlaczego to ryzykowne

- wcześniejsze etapy traktowały duplikacje w `to_dict()` / `from_dict()` jako świadomą kompatybilność legacy, nie zwykły smell
- łatwo "posprzątać" kod i przypadkowo usunąć zgodność formatów

#### Ryzykowne obszary

- dual-key migration patterns
- persistence backward compatibility
- rounding / serialization rules dla materiałów i ustawień

#### Warunki wejścia

- tylko z jawnym planem migracji albo decyzją o utrzymaniu kompatybilności

### 7. `ui/toolbar.py` — akcje zależne od indeksów

To nie jest najwyższe ryzyko funkcjonalne, ale jest to obszar zdradliwy.

#### Dlaczego to ryzykowne

- znaczenie akcji zależy od indeksów w `_toolbar_actions`
- możliwe są ciche regresje UI bez natychmiastowych wyjątków

#### Warunki wejścia

- najpierw testy kontraktowe toolbaru / akcji / kolejności / mapowania

## Znane ryzykowne tematy z backlogu i wcześniejszych etapów

Poniższe rzeczy nie są koniecznie "następnym krokiem", ale wiadomo, że są ryzykowne lub delikatne:

1. `ui/drawing_canvas.py` sheet hit-testing dla overlapów i hole gaps
   - deferred item `stage-7-pr9-001`
2. `ui/drawing_canvas.py` performance-oriented pomysł unikania `validate_polygon()` w `paintEvent()`
   - deferred item `stage-3-pr5-003`
3. `core/project_state.py` dalsze upraszczanie `replace_materials()` / `upsert_material()`
   - deferred jako maintainability/efficiency only
4. `core/layout_engine.py` przeniesienie `_UnionFind` i `_unique_sorted()` do shared utility
   - deferred, ale to nadal ruch architektoniczny który może rozlać zależności
5. `ui/main_window.py` przeniesienie signal connection management bliżej lifecycle canvasów
   - sensowne, ale ryzykowne bez precyzyjnego planu ownership

## Co agent powinien dostarczyć przed jakąkolwiek większą zmianą

Zanim agent ruszy którykolwiek z wysokich hotspotów, powinien przygotować:

1. Krótką mapę odpowiedzialności badanego modułu.
2. Listę testów już istniejących dla tego obszaru.
3. Listę brakujących testów osłonowych.
4. Propozycję najmniejszego sensownego refaktoru.
5. Listę rzeczy, których świadomie NIE rusza w tej iteracji.

## Najbardziej rekomendowany następny duży temat dla agenta

Jeśli agent ma wziąć jeden duży, "myślący" temat, najlepsza kolejność startu jest taka:

1. `ui/drawing_canvas.py` — ale tylko jako plan/test-first decomposition roadmap, nie jako ślepy rewrite.
2. `core/layout_engine.py` — tylko jeśli agent chce pogłębić testy i dopiero potem ruszać głębszy algorytm.
3. `ui/main_window.py` — dopiero gdy agent ma konkretną strategię lifecycle/flow decomposition.

## Proponowany prompt startowy dla agenta

```text
Pracujesz na repo 4dach. Masz działać bardzo ostrożnie i planować długo przed zmianami.

Przeczytaj kolejno:
1. AGENTS.md
2. docs/review-backlog.md
3. _TODO/CLEANUP_PLAN.md
4. _TODO/10_RISKY_REFACTOR_AGENT_BRIEF.md

Następnie:
- wybierz jeden obszar wysokiego ryzyka
- wypisz odpowiedzialności tego obszaru
- zinwentaryzuj istniejące testy i test gaps
- zaproponuj minimalny plan refaktoru w 2-5 krokach
- wskaż, czego nie należy ruszać w tej iteracji
- nie implementuj od razu dużego rewrite'u bez dodatkowych testów charakteryzujących

Traktuj obecny zielony wynik `uv run pytest` jako baseline, którego nie wolno zepsuć.
```
