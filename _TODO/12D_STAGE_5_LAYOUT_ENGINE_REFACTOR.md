# Stage 5: `core/layout_engine.py` po rozbudowie testów

## Planowanie wymagane

TAK.

Na początku pracy agent ma wskazać, które ścieżki `generate_layout()` są objęte nowymi testami i które helpery control-flow wolno konsolidować bez zmiany algorytmu.

## Cel

Uprościć `core/layout_engine.py` dopiero po rozszerzeniu osłony testowej dla trudnych przypadków geometrii i warning paths.

## Zakres

Najpierw dopisać testy dla:

- `zero_sheet_height`
- multi-cutout/skewed geometry
- `partial_cutout_top`
- `top_extra_cm`
- warning/rejection paths

Potem zrobić refaktor ograniczony do:

- konsolidacji control flow
- helperów outcome-building

## Poza zakresem

- bez redesignu algorytmu
- bez przenoszenia `_UnionFind`
- bez przenoszenia `_unique_sorted()`
- bez zmian schematu `layout_bands`

## Testy automatyczne

Najpierw gate lokalny:

```bash
uv run pytest tests/test_layout_engine.py tests/test_drawing_canvas.py tests/test_reporting.py -q
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

2. Wczytać lub utworzyć kilka połaci:
   - prostą
   - skośną
   - z wieloma wycinkami
   - z przypadkiem partial cutout
3. Wygenerować layout i sprawdzić, że liczba arkuszy, warningi i odrzucone segmenty są sensowne oraz stabilne.
4. Dla przypadku skrajnego sprawdzić, że brak wysokości arkusza daje właściwe warningi zamiast awarii.
5. Wygenerować raport po layoutcie i sprawdzić, że wynik nadal zgadza się z tym, co widać na canvasie.

## Warunek zakończenia

- trudne przypadki mają testy
- control flow jest uproszczony bez zmiany semantyki
- layouty i warningi pozostają zgodne z baseline

## Next stage

`Stage 6 -> _TODO/12E_STAGE_6_MAIN_WINDOW_CLEANUP.md`
