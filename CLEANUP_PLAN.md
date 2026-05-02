# Plan cleanupu repo `4dach` dla agenta edytującego kod

## Cel
Przeprowadzić dokładny cleanup repo po kodzie pisanym częściowo przez AI, ze szczególnym naciskiem na:
- semantyczne duplikacje logiki
- zbyt szerokie klasy/moduły
- powtarzalne wzorce mutacji stanu
- bezpieczne uproszczenie przepływów UI i core
- brak regresji funkcjonalnych

Plan ma być realizowany etapami, bez dużego jednorazowego przepisywania architektury.

## Kontekst projektu
- Python `3.11`
- środowisko uruchamiane przez `uv`
- GUI: `PySide6`
- testy: `pytest`, `pytest-qt`
- ważna zasada architektoniczna: nie mieszać logiki Qt/UI do `core/`
- repo ma istniejący proces review backlog; został sprawdzony
- `docs/review-backlog.md` nie zawiera obecnie otwartych pozycji, które blokują ten cleanup

## Zasady wykonania
1. Nie pracuj na `main` / `master`.
2. Rób cleanup etapami, najlepiej jako stack małych branchy / PR.
3. Każdy etap ma dotyczyć jednego logicznego obszaru.
4. Najpierw dodawaj testy charakteryzujące zachowanie tam, gdzie refaktor jest ryzykowny.
5. Nie usuwaj pozornej duplikacji, jeśli jest ona częścią kompatybilności formatu danych.
6. Nie przenoś logiki domenowej do UI ani zależności Qt do `core/`.
7. Po każdym etapie uruchamiaj testy przez:
   - `uv run pytest`

## Priorytety refaktoru

### Priorytet 1: szybkie, niskie ryzyko, wysoki zwrot
1. `ui/workspace.py`
2. małe lokalne deduplikacje w `ui/main_window.py`
3. lokalne helpery w `core/project_state.py`

### Priorytet 2: średnie ryzyko, duży zwrot
1. `core/layout_engine.py`
2. dalsze porządkowanie `ui/main_window.py`

### Priorytet 3: wysokie ryzyko, etap późniejszy
1. `ui/drawing_canvas.py`

## Zidentyfikowane hotspoty

### 1. `ui/main_window.py`
To jest główny hotspot długu technicznego.

Objawy:
- `MainWindow` ma ponad 100 metod
- jedna klasa obsługuje jednocześnie:
  - bootstrap aplikacji
  - konfigurację
  - theme
  - projekt i persistence
  - operacje na planes
  - refresh canvasów
  - obsługę dialogów
  - część command/undo flow
  - status bar / report refresh

Znalezione duplikacje / powtarzalne wzorce:
- powtarzany boilerplate podpinania sygnałów canvasu z `UniqueConnection`
- powtarzalne guardy:
  - `_active_or_warn`
  - `_active_with_outline_or_warn`
  - `_active_with_holes_or_warn`
- powtarzalne przepływy CRUD dla roof plane
- silne sprzężenie refreshu po edycji
- bezpośrednie używanie wewnętrznych pól `DrawingCanvas`

### 2. `core/project_state.py`
Drugi ważny hotspot.

Objawy:
- obiekt jest jednocześnie kontenerem stanu i serwisem domenowym
- dużo metod mutujących podobnym wzorcem
- powtarzane lookupy liniowe po `roof_planes` i `materials`

Znalezione duplikacje / powtarzalne wzorce:
- `require plane -> validate -> mutate -> mark dirty`
- podobna logika dla outline i holes
- powtarzane `next(... for ... in ...)`

### 3. `core/layout_engine.py`
Najważniejszy hotspot logiczny poza UI.

Objawy:
- bardzo duża, proceduralna `generate_layout()`
- kilka podobnych pętli generujących placementy i rejectiony
- historyczne łatki typu `Fix #...` wskazują na narastające poprawki lokalne

Znalezione semantyczne duplikacje:
- podobna logika w:
  - partial-cutout bottom
  - partial-cutout top
  - standard phase
- powtarzane konstrukcje:
  - `SheetPlacement(...)`
  - `RejectedSegment(...)`
  - `LayoutWarning(...)`

### 4. `ui/workspace.py`
Dobry kandydat na szybki cleanup.

Objawy:
- kilka metod powtarza ten sam fan-out po wszystkich canvasach

Powtarzające się wzorce:
- `toggle_grid`
- `set_snap_to_grid_enabled`
- `set_sheet_visibility`
- `toggle_module_count`
- `update_all_canvases`

### 5. `ui/drawing_canvas.py`
Moduł bardzo duży i ryzykowny.

Objawy:
- ok. 4000+ linii
- mieszanie wielu odpowiedzialności:
  - rendering
  - interaction state
  - snapping
  - overlays
  - edycja geometrii
  - selection
  - sheet visualization
  - undo

Wniosek:
- nie robić dużego rozbijania na początku
- najpierw testy charakteryzujące i izolacja punktów wejścia
- pełniejszy podział dopiero po ustabilizowaniu innych modułów

### 6. `core/models.py`
Uwaga: nie każda duplikacja jest zła.

Istotne:
- `MaterialDefinition` ma aliasy i kompatybilność legacy
- `to_dict()` / `from_dict()` obsługują celowo więcej niż jeden format kluczy

Wniosek:
- nie upraszczać tego bez świadomej migracji formatu danych
- traktować jako świadomą kompatybilność, nie zwykły duplication smell

### 7. `core/geometry.py`
Uwaga na zachowanie krytyczne.

Istotne:
- aliasy typu `build_*_outline` delegują do `make_*`
- `validate_hole_polygon()` ma krytyczny kontrakt
- istnieje regresyjny test:
  - `tests/test_geometry.py::test_validate_hole_polygon_outside_outline`

Wniosek:
- nie ruszać walidacji bez testów
- aliasy można uprościć tylko po sprawdzeniu call-site'ów i publicznego API

### 8. `ui/toolbar.py`
Mniejszy temat.

Objawy:
- znaczenie akcji zależy od indeksów w liście `_toolbar_actions`

Wniosek:
- cleanup możliwy, ale niższy priorytet

## Proponowany plan etapów

## Etap 0: baseline i zabezpieczenie
Przed edycją:
1. Przeczytaj:
   - `AGENTS.md`
   - `docs/review-backlog.md`
2. Sprawdź stan repo i aktualną gałąź.
3. Uruchom pełne testy:
   - `uv run pytest`
4. Zanotuj:
   - które testy już istnieją dla `geometry`, `layout_engine`, `project_state`
   - czy są obecne GUI testy dla `MainWindow` / `WorkspaceController`

Rezultat:
- czysta baza porównawcza przed refaktorem

## Etap 1: szybkie deduplikacje o niskim ryzyku
### 1A. `ui/workspace.py`
Cel:
- wyciągnąć prywatny helper iterujący po wszystkich canvasach

Przykładowy kierunek:
- helper typu `_for_each_canvas(...)` albo iterator zwracający wszystkie canvasy
- zredukować powtórzony fan-out do jednego wzorca

Akceptacja:
- brak zmiany zachowania
- kod krótszy i czytelniejszy
- testy przechodzą

### 1B. `ui/main_window.py`
Cel:
- zrobić tylko małe, lokalne deduplikacje, bez pełnego rozbijania klasy

Zrób:
- wyciągnij helper do bezpiecznego podpinania sygnałów canvasu
- ujednolić active-plane guardy w bardziej centralny mechanizm
- ograniczyć powtórzenia w prostych flow CRUD dla plane'ów
- nie zmieniać jeszcze publicznego przepływu okna

Nie rób jeszcze:
- pełnego rozbijania `MainWindow` na wiele nowych klas
- dużej zmiany lifecycle aplikacji

Akceptacja:
- mniej boilerplate
- mniej powtórzeń
- zachowanie bez zmian

### 1C. `core/project_state.py`
Cel:
- zlikwidować lokalne duplikacje bez zmiany modelu domeny

Zrób:
- wyciągnij helpery lookupów
- wyciągnij helper/abstrakcję dla wzorca:
  - pobierz plane
  - zwaliduj
  - zmutuj
  - oznacz dirty
- ujednolić mutacje outline/hole tam, gdzie to bezpieczne

Akceptacja:
- mniej powtórzonego kodu
- brak zmian w serializacji
- brak zmian w zewnętrznym API jeśli niepotrzebne

## Etap 2: testy charakteryzujące dla ryzykownych obszarów
Przed dużym refaktorem dodaj testy dla:

### 2A. `core/layout_engine.py`
Dodaj testy dla:
- partial-cutout bottom
- partial-cutout top
- standard placement flow
- ostrzeżeń i odrzuceń
- edge-case splitów

Cel:
- zamrozić aktualne zachowanie przed deduplikacją pętli

### 2B. `core/project_state.py`
Dodaj testy dla:
- mutacji outline
- mutacji holes
- dirty-state
- lookupów aktywnego plane/material

### 2C. `ui/workspace.py` / `ui.main_window.py`
Jeśli sensowne i tanie:
- małe testy `pytest-qt` dla wybranych helperów i podstawowych flow
- jeśli pełne testy GUI są zbyt drogie, opisz manual QA dla tych ścieżek

### 2D. `core/geometry.py`
Upewnij się, że istniejące testy chronią:
- walidację otworu względem outline
- brak regresji w `validate_hole_polygon()`

## Etap 3: refaktor `core/layout_engine.py`
To powinien być osobny etap/branch.

Cel:
- deduplikacja semantyczna `generate_layout()` bez zmiany wyników

Zrób:
- wyciągnij wspólny helper dla budowania placement/rejection
- odseparuj logikę wspólną dla:
  - bottom partial cutout
  - top partial cutout
  - standard placement
- ogranicz liczbę lokalnych warunków w jednej funkcji
- jeśli potrzebne, wprowadź małe prywatne struktury pomocnicze, ale bez przesadnej abstrakcji

Nie rób:
- pełnego przeprojektowania algorytmu
- zmiany publicznego kontraktu `LayoutResult`, jeśli nie jest to konieczne

Akceptacja:
- testy z Etapu 2 przechodzą bez zmian
- mniej powtórzeń
- `generate_layout()` wyraźnie czytelniejsza

## Etap 4: dalsze porządkowanie `ui/main_window.py`
Dopiero po Etapach 1-3.

Cel:
- ograniczyć rozmiar i odpowiedzialność `MainWindow`

Kierunek:
- wyodrębniaj małe koordynatory lub helpery wokół:
  - refresh/report/status flow
  - plane action flow
  - dialog flow
  - canvas wiring

Ważne:
- nie twórz zbyt wielu sztucznych klas
- preferuj małe, praktyczne ekstrakcje zamiast wielkiego redesignu
- nie rozbijaj na siłę, jeśli wystarczy kilka wewnętrznych helperów lub małych controllerów

Akceptacja:
- mniej odpowiedzialności w jednej klasie
- mniejsze metody
- łatwiejsze śledzenie przepływu akcji użytkownika

## Etap 5: ostrożny przegląd `ui/drawing_canvas.py`
Ten etap ma być opcjonalny lub późniejszy.

Cel:
- przygotować grunt pod przyszły podział, a nie robić wielkiej rewolucji od razu

Najpierw:
- zidentyfikuj logiczne segmenty:
  - rendering
  - snapping
  - overlays
  - geometry editing
  - selection
  - undo
- dodaj testy charakteryzujące tam, gdzie możliwe
- wyciągnij tylko najbardziej izolowalne helpery

Nie rób:
- wielkiego splitu modułu bez silnego pokrycia testami
- zmiany zachowań interakcji canvasu na ślepo

## Etap 6: cleanup niskiego priorytetu
### `ui/toolbar.py`
- zastąp logikę zależną od indeksów bardziej jawną konstrukcją akcji

### `core/geometry.py`
- aliasy `build_*_outline` rozważ tylko po sprawdzeniu użyć
- nie ruszaj walidacji bez pełnej ochrony testowej

### `core/models.py`
- nie upraszczaj aliasów serializacji bez planu migracji danych

## Konkretne duplikacje do usunięcia

### A. Powtarzalne fan-out operations
Plik:
- `ui/workspace.py`

Zamień wiele podobnych metod na wspólny mechanizm iteracji po canvasach.

### B. Powtarzalne signal wiring
Plik:
- `ui/main_window.py`

Zamień wiele bloków:
- `try`
- `connect(... UniqueConnection)`
- `except TypeError`
na wspólny helper.

### C. Powtarzalne guardy aktywnego plane
Plik:
- `ui/main_window.py`

Ujednolić pobieranie:
- aktywnego plane
- aktywnego plane z outline
- aktywnego plane z holes

### D. Powtarzalne mutacje stanu i dirty marking
Plik:
- `core/project_state.py`

Ujednolić wzorzec:
- lookup
- validate
- mutate
- mark dirty

### E. Powtarzalne tworzenie placement/rejection/warning
Plik:
- `core/layout_engine.py`

Wyciągnąć wspólny mechanizm dla podobnych pętli w `generate_layout()`.

## Czego nie usuwać pochopnie
1. Kompatybilności formatu w `core/models.py`
2. Krytycznej walidacji geometrii w `core/geometry.py`
3. Zachowania layout engine bez testów charakteryzujących
4. Zachowań GUI canvasu bez testów lub przynajmniej manual QA

## Zalecany układ branchy / stage'y
Rekomendowany stack:

1. `cleanup/workspace-dedup`
2. `cleanup/project-state-dedup`
3. `cleanup/layout-engine-tests`
4. `cleanup/layout-engine-dedup`
5. `cleanup/main-window-helpers`
6. `cleanup/main-window-decomposition`
7. `cleanup/drawing-canvas-prep`

Jeśli stack jest za duży, minimum:
1. `cleanup/workspace-and-mainwindow-lowrisk`
2. `cleanup/project-state-and-layout-tests`
3. `cleanup/layout-engine-refactor`

## Wymagane testy i weryfikacja
Po każdym etapie:
1. `uv run pytest`

Dodatkowo:
- jeśli zmieniasz `layout_engine`, dodaj/uruchom testy regresyjne dla layoutów
- jeśli zmieniasz `project_state`, dodaj testy mutacji stanu i dirty flag
- jeśli zmieniasz `MainWindow` lub `WorkspaceController`, wykonaj manual QA:
  - przełączanie plane'ów
  - dodawanie/usuwanie/duplikowanie plane
  - odświeżanie canvasa
  - zaznaczanie elementów
  - grid/snap/module count visibility
  - podstawowe flow zapisu/odczytu projektu

## Definition of Done
Cleanup uznaj za poprawny tylko jeśli:
1. `uv run pytest` przechodzi
2. nie ma regresji w geometrii i layoutach
3. nie zepsuto kompatybilności serializacji projektu
4. nie dodano zależności Qt do `core/`
5. zredukowano realne duplikacje, a nie tylko przemianowano kod
6. największe hotspoty mają mniejszy boilerplate i czytelniejszy przepływ
7. każdy etap pozostaje reviewowalny i możliwy do cofnięcia osobno

## Oczekiwany rezultat końcowy
Po wykonaniu planu repo powinno mieć:
- mniej semantycznych duplikacji
- prostsze flow mutacji stanu
- bardziej czytelny `layout_engine`
- mniej boilerplate w `MainWindow` i `WorkspaceController`
- lepsze zabezpieczenie testami dla krytycznych obszarów
- przygotowany grunt pod późniejsze bezpieczne rozbijanie `DrawingCanvas`

## Ważna uwaga końcowa
Największy błąd byłby próbować "posprzątać wszystko naraz". Ten cleanup ma być:
- iteracyjny
- test-first dla ryzykownych miejsc
- mały na PR
- bez naruszania kompatybilności danych i zachowania GUI
