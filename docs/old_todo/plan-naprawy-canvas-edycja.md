# Plan naprawy canvasu edycji

## Cel

Naprawić błędy prezentacji i edycji w `DrawingCanvas`, tak aby:
- etykiety długości boków były widoczne dla obrysu i wycięć,
- etykiety współrzędnych `X/Y` były stale widoczne dla narożników względem punktu `0,0`,
- mały widget osi `X/Y` przy marginesie został usunięty,
- siatka była rysowana konsekwentnie na całym canvasie, jeśli jest włączona.

## Ustalone wymagania

- Etykiety `X/Y` mają być widoczne stale, nie tylko podczas przeciągania.
- Podczas przeciągania całej krawędzi ma być pokazywany jeden punkt referencyjny `X/Y`.
- Mały widget osi `X/Y` przy marginesie ma zostać usunięty.
- Logiczny punkt `0,0` ma pozostać i nadal być podstawą obliczania współrzędnych.
- Siatka ma być widoczna na całym canvasie przez cały czas, jeśli użytkownik ma ją włączoną.

## Diagnoza techniczna

Najbardziej prawdopodobne źródła problemu znajdują się w `ui/drawing_canvas.py`:

- `_draw_roof_plane(...)`
  - obecnie rysuje pomiary krawędzi dla `outline`, ale nie dla `holes`, co tłumaczy brak etykiet długości na wycięciach,
- `_coordinate_overlay_labels(...)`
  - obecnie zwraca etykiety tylko dla aktywnego punktu i wybranych stanów drag, więc nie spełnia wymagania stałej widoczności `X/Y`,
- `_draw_freehand_axis_overlay(...)` oraz `_draw_axis_indicator_at(...)`
  - odpowiadają za mały widget osi przy marginesie, który ma zostać usunięty,
- `_grid_bounds_for_current_paint(...)`, `_grid_context(...)` i `paintEvent(...)`
  - odpowiadają za niespójne zachowanie siatki między stanem spoczynku a edycją,
- `_draw_vertex_axis_projections(...)`
  - już rysuje linie odniesienia osi dla wierzchołków w trybie edycji, ale tylko w ograniczonych warunkach i bez pełnego systemu stałych etykiet współrzędnych.

Istotne zachowania już obecne w kodzie:

- `_default_origin_point(...)` ustawia origin w lewym dolnym rogu obrysu,
- `_relative_coordinate_point(...)` liczy współrzędne względem `0,0`,
- test `test_canvas_origin_defaults_to_outline_bottom_left_corner` potwierdza ten kontrakt.

## Zakres prac

### In

- `ui/drawing_canvas.py`
- testy regresyjne w `tests/test_drawing_canvas.py`
- warstwa renderowania overlayów, etykiet i siatki

### Out

- `core/layout_engine.py`
- zmiany w modelu danych i serializacji
- szeroki refaktor architektury canvasu

## Plan implementacji

1. Dodać testy charakteryzujące dla zgłoszonych błędów w `tests/test_drawing_canvas.py`.
2. Rozszerzyć `_draw_roof_plane(...)`, aby rysował etykiety długości także dla wszystkich `holes`.
3. Zweryfikować `_edge_label_regions(...)` dla wycięć i dopracować offsety etykiet tam, gdzie wycięcia mają ciasne segmenty lub długie poziome odcinki.
4. Zmienić logikę `_coordinate_overlay_labels(...)`, aby generowała stałe etykiety `X/Y` dla narożników w trybie edycji, nie tylko dla aktywnie przeciąganego punktu.
5. Ustalić jeden punkt referencyjny `X/Y` dla przeciąganej krawędzi i wprost opisać ten kontrakt w testach.
6. Oprzeć etykiety współrzędnych wyłącznie o `_origin_point()` i `_relative_coordinate_point(...)`, bez zależności od dekoracyjnego widgetu osi.
7. Usunąć z renderowania mały widget osi przy marginesie przez zmianę `_draw_freehand_axis_overlay(...)` i/lub `_draw_axis_indicator(...)`, bez naruszania logicznego punktu `0,0`.
8. Ujednolicić zachowanie siatki przez zmianę `_grid_bounds_for_current_paint(...)`, tak aby przy aktywnym `show_grid` siatka była liczona dla całego obszaru canvasu także podczas edycji.
9. Uprościć kolejność rysowania w `paintEvent(...)`, tak aby siatka nie zmieniała warstwy ani zakresu tylko dlatego, że trwa drag origin albo drag wierzchołka.
10. Zweryfikować końcowy efekt ręcznie na scenariuszach ze zrzutów oraz przez pełny zestaw testów canvasu.

## Testy do dodania lub rozszerzenia

- Test: etykiety długości są rysowane dla `holes`, nie tylko dla `outline`.
- Test: etykiety `X/Y` są dostępne stale dla narożników w trybie edycji.
- Test: dla przeciąganej krawędzi widoczny jest jeden punkt referencyjny `X/Y`.
- Test: mały widget osi przy marginesie nie jest rysowany.
- Test: siatka przy `show_grid=True` obejmuje cały canvas zarówno w spoczynku, jak i podczas przeciągania.
- Test: istniejący kontrakt origin w lewym dolnym rogu pozostaje bez zmian.

## Kryteria akceptacji

- Na głównym obrysie i na każdym wycięciu widoczne są etykiety długości boków.
- W trybie edycji użytkownik widzi stale współrzędne `X/Y` narożników względem `0,0`.
- Podczas przeciągania całej krawędzi wyświetlany jest jeden punkt referencyjny `X/Y`.
- Mały widget osi `X/Y` przy lewym marginesie nie jest widoczny.
- Punkt `0,0` nadal istnieje i poprawnie wyznacza współrzędne względne.
- Siatka, jeśli włączona, jest widoczna na całym canvasie zarówno przed edycją, jak i podczas przeciągania.
- Dotychczasowe testy canvasu przechodzą, a nowe testy regresyjne zabezpieczają zgłoszone przypadki.

## Uwagi wdrożeniowe

- Zmiany powinny pozostać możliwie małe i lokalne dla `ui/drawing_canvas.py`.
- Nie należy zmieniać semantyki geometrii ani kolejności zapisu punktów bez osobnej potrzeby.
- Najpierw warto ustabilizować testy i kontrakty renderowania, a dopiero potem poprawiać szczegóły pozycji badge'y i overlayów.
