# Stage 7: `core/project_state.py` jako osobny cleanup po `main_window`

## Planowanie wymagane

TAK.

Na początku pracy agent ma zmapować wszystkie publiczne mutatory outline/hole/geometry i wskazać, które już używają wspólnego lifecycle, a które jeszcze obchodzą go boczną ścieżką.

## Cel

Ujednolicić lifecycle mutacji outline/hole/geometry wokół jednej ścieżki.

## Zakres

Ta ścieżka ma obejmować:

- walidację
- mutację stanu
- invalidację layoutu
- bump revision

## Poza zakresem

- brak zmian formatu serializacji
- brak zmian permissiveness geometrii
- brak zmian logiki katalogu materiałów
- helpery `_serialize_*` i `_deserialize_*` zostają w pliku

## Testy automatyczne

Najpierw gate lokalny:

```bash
uv run pytest tests/test_models_and_state.py tests/test_geometry.py tests/test_layout_engine.py -q
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

2. Dodać połać, edytować obrys, dodać i przesunąć wycinek, a potem sprawdzić, że layout oznacza się jako wymagający odświeżenia dokładnie wtedy, kiedy powinien.
3. Cofnąć i ponowić kilka zmian, żeby potwierdzić spójność revision/dirty flow.
4. Zmienić geometrię po wygenerowanym layoutcie i sprawdzić, że stary layout nie zostaje błędnie uznany za aktualny.
5. Zapisać projekt i ponownie go otworzyć, żeby upewnić się, że cleanup mutatorów nie naruszył serializacji.

## Warunek zakończenia

- outline/hole/geometry używają jednego czytelnego lifecycle mutacji
- layout invalidation i revision bump są spójne
- serializacja i permissive behavior pozostały bez zmian

## Next stage

`Stage 8 -> _TODO/12G_STAGE_8_COMPATIBILITY_AUDIT_LOW_ROI.md`
