# Stage 3: wydzielenie tylko czysto-funkcyjnych helperów canvasa

## Planowanie wymagane

TAK.

Na początku pracy agent ma rozpisać krótki plan wydzielenia modułów i potwierdzić, które helpery są naprawdę stateless, a które nadal zależą od stanu widgetu.

## Cel

Wydzielić tylko czysto-funkcyjne helpery canvasa do `ui/canvas/`, bez zmiany publicznego API.

## Zakres

- wydzielić wewnętrzne moduły pod `ui/canvas/`
- zostawić `ui/drawing_canvas.py` jako publiczną fasadę
- rodzinę render/sheet geometry przenosić razem
- obejmuje to `_sheet_render_items()`, clipping polygonów, placement render polygons, path builders i helpery coverage
- statelessową matematykę snap/inference wydzielić osobno

## Poza zakresem

- nie rozdzielać hit-testu od geometrii renderu w tej iteracji
- stan widgetu, cache renderu, selection, undo/redo i origin drag zostają własnością `DrawingCanvas`
- brak większego splitu klasy przez mixiny

## Testy automatyczne

Najpierw gate lokalny:

```bash
uv run pytest tests/test_drawing_canvas.py tests/test_mainwindow_ui_contract.py -q
```

Potem pełny suite:

```bash
uv run pytest -q
```

## Jak testować manualnie

1. Uruchomić aplikację:

```bash
uv run python3 __main__.py
```

2. Otworzyć widok połaci z istniejącym layoutem i sprawdzić, że render arkuszy, clipping i coverage wyglądają tak samo jak przed zmianą.
3. Przejść przez rysowanie obrysu i wycinków oraz sprawdzić, że snapy nadal działają poprawnie.
4. Włączyć i wyłączyć warstwy pomocnicze, siatkę oraz liczniki modułów, żeby upewnić się, że rendering nie stracił synchronizacji.
5. Sprawdzić wybór arkuszy i geometrii po kliknięciu w kilka różnych miejsc canvasa.

## Warunek zakończenia

- helpery stateless są wydzielone
- `ui/drawing_canvas.py` pozostaje publiczną fasadą
- brak regresji w renderingu i snap/inference

## Next stage

`Stage 4 -> _TODO/12C_STAGE_4_DRAWING_CANVAS_INTERNAL_SPLIT.md`
