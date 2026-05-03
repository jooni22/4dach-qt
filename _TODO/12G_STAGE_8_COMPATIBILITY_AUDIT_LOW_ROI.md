# Stage 8: audit kompatybilności i niski ROI

## Planowanie wymagane

TAK.

Na początku pracy agent ma krótko wskazać, które drobne cleanupy są rzeczywiście test-backed i behavior-preserving, a które należy zostawić, bo nie mają ROI albo wymagają decyzji produktowej.

## Cel

Domknąć tylko niskoryzykowne porządki kompatybilnościowe po wcześniejszych etapach.

## Zakres

Dotyczy wyłącznie test-backed, behavior-preserving cleanupu dla:

- `core/geometry.py`
- `core/models.py`
- `ui/toolbar.py`

Kontrakty do zachowania:

- aliasy `build_*_outline`
- kontrakt hole containment
- dual-key compatibility

## Poza zakresem

- `make_triangle()` zostaje bez zmian, dopóki nie ma decyzji produktowej
- toolbar index-coupling ruszać dopiero po dodaniu testów kontraktowych
- brak cleanupu bez wyraźnego ROI i bez osłony testowej

## Testy automatyczne

Dobrać testy do dotkniętego obszaru, a na końcu zawsze uruchomić:

```bash
uv run pytest -q
```

## Jak testować manualnie

1. Uruchomić aplikację:

```bash
uv run python3 __main__.py
```

2. Otworzyć istniejący projekt zapisany starszym formatem i sprawdzić, że nadal się ładuje poprawnie.
3. Przejść przez podstawowe akcje toolbaru i upewnić się, że przypisanie indeksów/akcji nie zmieniło zachowania UI.
4. Dodać obrys i wycinek, a potem sprawdzić, że reguły containment oraz kompatybilność importów/aliasów nie zostały naruszone.
5. Zapisać i ponownie otworzyć projekt, żeby potwierdzić dual-key compatibility i brak regresji serializacyjnych.

## Warunek zakończenia

- wykonane zostały tylko cleanupy z niskim ryzykiem i realnym ROI
- kompatybilność legacy została zachowana
- pełny suite jest zielony

## Next stage

Brak. To etap domykający tę roadmapę.
