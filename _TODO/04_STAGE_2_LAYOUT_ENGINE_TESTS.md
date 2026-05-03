# Stage 2: Layout engine characterization tests
Skille załaduj:
/test-driven-development
```markdown
Wykonaj tylko etap testow charakteryzujacych dla `core/layout_engine.py` zgodnie z `_TODO/CLEANUP_PLAN.md`.

Dodaj testy obejmujace:
- partial-cutout bottom
- partial-cutout top
- standard placement flow
- warningi i rejectiony
- edge-case splity

Cel:
- zamrozic obecne zachowanie przed refaktorem
- jeszcze nie refaktoruj algorytmu, chyba ze drobna zmiana jest konieczna do testowalnosci

Wymagania:
- trzymaj scope na testach i minimalnych zmianach pomocniczych
- nie zmieniaj publicznego zachowania `layout_engine`
- uruchom `uv run pytest`

Na koncu podaj:
- jakie testy dodales
- jakie scenariusze sa juz zabezpieczone
- jakie obszary `generate_layout()` nadal sa slabo chronione testami
- wynik `uv run pytest`
```
