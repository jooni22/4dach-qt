# Stage 2: test-first hardening dla `DrawingCanvas`

## Planowanie wymagane

NIE.

Ten stage ma być wykonany test-first, ale bez osobnej rundy dużego planowania. Wolno dopisać tylko małe helpery potrzebne do testowalności.

## Cel

Domknąć charakteryzację najbardziej ryzykownych zachowań `DrawingCanvas` przed większym cleanupem.

## Zakres

Najpierw dopisać testy charakteryzujące dla:

- snap precedence
- multi-step freehand draw
- origin/grid interactions
- drag begin/update/commit/cancel
- inline editor confirm/cancel
- sheet overlap i hole-gap hit-testing

## Poza zakresem

- brak większych przenosin kodu
- brak splitu plików
- brak refaktoru architektury canvasa

## Backlog review

- `stage-7-pr9-001` i `stage-3-pr5-003` nie są automatycznie do zrobienia
- wolno w nie wejść tylko wtedy, gdy wynikają wprost z tego stage i mają własne testy

## Testy automatyczne

Minimalny gate:

```bash
uv run pytest tests/test_drawing_canvas.py tests/test_mainwindow_ui_contract.py -q
```

Jeśli canvas suite daje teardown noise:

```bash
uv run pytest tests/test_drawing_canvas.py -vv
```

## Jak testować manualnie

1. Uruchomić aplikację:

```bash
uv run python3 __main__.py
```

2. W trybie rysowania obrysu sprawdzić, że snap point/axis/grid działa w tej samej kolejności co przed zmianą.
3. Narysować freehand wieloetapowo i upewnić się, że kolejne segmenty oraz domknięcie działają bez gubienia punktów.
4. Włączyć siatkę, zmienić origin i sprawdzić, że interakcje origin/grid nie zmieniają innych zachowań rysowania.
5. Przeciągnąć wierzchołek, krawędź, ciało obrysu i wycinek; sprawdzić begin/update/commit/cancel.
6. Otworzyć inline editor długości segmentu i sprawdzić confirm oraz cancel.
7. Kliknąć na nachodzące na siebie arkusze i w obszary dziur, żeby potwierdzić stabilność hit-testu.

## Warunek zakończenia

- nowe testy istnieją i przechodzą
- zachowanie użytkowe canvasa pozostaje bez regresji
- brak większego refaktoru produkcyjnego poza lokalnymi helperami testowalności

## Next stage

`Stage 3 -> _TODO/12B_STAGE_3_CANVAS_PURE_HELPERS_EXTRACTION.md`
