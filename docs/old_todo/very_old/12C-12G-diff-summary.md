# Podsumowanie Diffów 12C-12G

Zakres: od `81f560c` do `69b903d`

## Commity

- `ca52c8e` `refactor: split drawing canvas internals into mixins`
- `c41132f` `refactor: harden and simplify layout engine control flow`
- `835260c` `refactor: extract main window refresh helpers`
- `3003b4e` `refactor: unify project state mutation lifecycle`
- `69b903d` `refactor: apply low-risk compatibility cleanups`

## Statystyka

- 11 plikow zmienionych
- 3779 linii dodanych
- 3376 linii usunietych

Najwieksze zmiany:

- `ui/drawing_canvas.py` - 6368 linii ruchu/refaktoru
- `core/layout_engine.py` - 256 linii
- `ui/main_window.py` - 101 linii
- `tests/test_models_and_state.py` - 93 linii
- `ui/main_window_refresh.py` - nowy plik, 66 linii
- `tests/test_layout_engine.py` - 61 linii
- `tests/test_mainwindow_ui_contract.py` - 56 linii
- `core/project_state.py` - 54 linii
- `ui/main_window_dialogs.py` - nowy plik, 36 linii
- `core/models.py` - 37 linii
- `tests/test_drawing_canvas.py` - 27 linii

## Zmienione pliki

- `M core/layout_engine.py`
- `M core/models.py`
- `M core/project_state.py`
- `M tests/test_drawing_canvas.py`
- `M tests/test_layout_engine.py`
- `M tests/test_mainwindow_ui_contract.py`
- `M tests/test_models_and_state.py`
- `M ui/drawing_canvas.py`
- `M ui/main_window.py`
- `A ui/main_window_dialogs.py`
- `A ui/main_window_refresh.py`

## Podsumowanie Funkcjonalne

Z perspektywy uzytkownika koncowego zakres `12C`-`12G` nie byl nowa funkcja, tylko porzadkowaniem i utwardzaniem istniejacego zachowania.

Najwazniejsze skutki praktyczne:

- Edycja i rysowanie na canvasie powinny dzialac tak jak wczesniej, ale kod odpowiedzialny za render, interakcje i edytory inline jest teraz lepiej rozdzielony.
- Generowanie ukladu arkuszy powinno zachowywac sie tak samo, ale obsluga segmentow i przypadkow granicznych jest mniej podatna na bledy przy dalszych zmianach.
- Odswiezanie glownego okna po zmianach stanu projektu jest bardziej przewidywalne: odswiezenie materialow, czyszczenie cache raportu, odswiezenie canvasa oraz ustawienie dirty/saved state sa teraz spiete jednym kontraktem zamiast rozproszonych flag.
- Operacje zmieniajace geometrie polaci i otworow przechodza jedna wspolna sciezka mutacji, wiec trudniej o niespojnosc typu: zmiana geometrii bez invalidacji layoutu, zmiana bez bumpa rewizji albo zmiana z innym cyklem walidacji niz reszta.
- Poprawiona zostala kompatybilnosc wczytywania materialow: jesli payload miesza nowe i stare klucze, a nowy klucz istnieje, ale ma `None`, system poprawnie spada do legacy pola zamiast wywalic sie na `float(None)`.

W praktyce jedyna bardziej zauwazalna zmiana zachowania dla uzytkownika to ostatni punkt z `12G`: starsze lub mieszane dane materialow sa bezpieczniej parsowane.

## Podsumowanie Techniczne

### 12C

- `ui/drawing_canvas.py` zostalo przebudowane wewnetrznie na uklad mixinow.
- Rozdzielone zostaly odpowiedzialnosci:
  - render,
  - interakcje,
  - inline/post-draw edit flow.
- Publiczny entrypoint pozostal ten sam: `DrawingCanvas` nadal jest fasada.

To oznacza, ze nie zmienil sie publiczny punkt integracji, ale logika wewnatrz klasy przestala byc jednym duzym monolitem.

### 12D

- `core/layout_engine.py` dostal refaktor sterowania przeplywem generowania rzedow.
- Wyciagnieto helpery typu:
  - fazy segmentu,
  - append dla pojedynczej fazy,
  - append dla calego segmentu,
  - liczenie extra dla terminal row,
  - warning dla invalid max sheet length.
- Efekt: wczesniejsze zduplikowane petle i warunki zostaly skupione w bardziej przewidywalne helpery.

### 12E

- Z `ui/main_window.py` wyciagnieto dwa obszary pomocnicze:
  - `ui/main_window_refresh.py`
  - `ui/main_window_dialogs.py`
- `ui/main_window_refresh.py` przejal logike kontraktowego odswiezania po zmianie stanu.
- `ui/main_window_dialogs.py` przejal helpery dialogowe i pomocnicza logike typu centered hole.
- `ui/main_window.py` zostal uproszczony i bardziej skupiony na orkiestracji niz na detalach implementacyjnych.

### 12F

- `core/project_state.py` ujednolicil mutacje geometrii przez `_set_plane_geometry(...)`.
- Operacje:
  - `move_roof_plane(...)`
  - `add_hole_to_plane(...)`
  - `set_hole_polygon(...)`
  - `delete_hole_from_plane(...)`
  zostaly przepiete na wspolny lifecycle.
- Usunieto prywatny helper `_mark_plane_geometry_changed(...)`.
- `validate_geometry` w `_set_plane_geometry(...)` rozszerzono tak, by przyjmowal takze `Callable`, co pozwolilo wstrzyknac walidacje do wspolnej sciezki.

To jest wazne, bo wczesniej czesc operacji robila reczne mutacje plus reczne oznaczanie zmian, a teraz wszystko przechodzi jednym kanalem.

### 12G

- `core/models.py` dostal maly helper `_first_non_none(...)`.
- `MaterialDefinition.from_dict()` uzywa go do fallbacku pomiedzy nowymi i legacy kluczami.
- Dotyczy to pol:
  - `effective_width_cm`
  - `min_sheet_length_cm`
  - `max_sheet_length_cm`
  - `top_allowance_cm`
  - `bottom_allowance_cm`
  - `module_length_cm`
  - `price_per_m2`
- Dodano regresje w `tests/test_models_and_state.py` dla payloadu, gdzie nowe klucze sa obecne, ale maja `None`.

## Najwazniejszy Efekt Architektoniczny

- UI zostalo bardziej modulowe:
  - canvas rozdzielony logicznie,
  - main window ma wyciagniete helpery,
  - czystszy przeplyw refresh/state.
- Core ma bardziej spojne sciezki:
  - layout engine z mniejsza duplikacja,
  - project state z jedna sciezka mutacji geometrii,
  - model materialu odporniejszy na stare payloady.

## Ryzyko I Charakter Zmian

- To glownie refaktor porzadkujacy i wzmacniajacy testy, nie duza zmiana funkcjonalna.
- Najwyzsze ryzyko techniczne bylo w `ui/drawing_canvas.py`, ale zostalo oslonięte testami.
- `12G` bylo swiadomie minimalne.
