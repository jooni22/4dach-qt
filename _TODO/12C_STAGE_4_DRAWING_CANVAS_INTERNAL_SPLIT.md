# Stage 4: opcjonalny split wewnętrzny `DrawingCanvas`

## Planowanie wymagane

TAK.

Na początku pracy agent ma opisać docelowy podział mixinów i wskazać dokładnie, które grupy metod wchodzą do każdego wycinka. Bez tego nie zaczynać zmian.

## Warunek wejścia

Ten stage wolno rozpocząć dopiero po zielonym Stage 2 i Stage 3.

## Cel

Rozbić wnętrze klasy `DrawingCanvas` na mixiny, bez zmiany publicznej fasady.

## Zakres

- rozbijać wnętrze klasy przez mixiny, nie przez delegację
- zachować publiczny `DrawingCanvas`
- `ui/drawing_canvas.py` ma dalej re-eksportować co najmniej:
  - `DrawingCanvas`
  - `CommittedOutlineEdit`
  - używane stałe

Docelowy kierunek:

- mixiny dla `paint/_draw_*`
- mixiny dla interakcji `mouse/key/hit-test/drag`
- mixiny dla inline editor flow

## Poza zakresem

- brak zmiany publicznych importów
- brak redesignu flow eventów
- brak przenoszenia odpowiedzialności do delegatów/koordynatorów

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

2. Przejść pełny flow: rysowanie obrysu, dodawanie wycinku, edycja wierzchołka, drag ciała i inline edit długości.
3. Sprawdzić, że klawisze `Escape`, cyfry do inputu i modyfikatory snap zachowują się tak samo jak przed zmianą.
4. Zweryfikować, że zaznaczenie, uchwyty i overlaye pozostają aktywne po operacjach edycji.
5. Otworzyć projekt z istniejącym layoutem i sprawdzić rendering plus hit-testing arkuszy.

## Warunek zakończenia

- podział wewnętrzny istnieje
- publiczna fasada pozostała stabilna
- zachowanie canvasa nie zmieniło się funkcjonalnie

## Next stage

`Stage 5 -> _TODO/12D_STAGE_5_LAYOUT_ENGINE_REFACTOR.md`
