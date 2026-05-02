# Stage 0: Baseline i mapowanie testow

```markdown
Pracujesz w repo `4dach`. Przeczytaj najpierw:
- `AGENTS.md`
- `docs/review-backlog.md` jesli istnieje
- `_TODO/CLEANUP_PLAN.md`

Cel: przygotowac bezpieczny punkt startowy do cleanupu zgodnie z planem, bez rozpoczynania jeszcze duzych refaktorow.

Zasady:
- nie pracuj na `main` / `master`
- nie rozszerzaj zakresu poza Stage 0
- jeszcze nie wykonuj duzych refaktorow
- pracuj zgodnie z AGENTS.md
- uzywaj `uv run` dla polecen Python/testow

Wykonaj tylko Stage 0:
1. Sprawdz aktualny branch i worktree.
2. Przeczytaj `AGENTS.md`, `docs/review-backlog.md` i `_TODO/CLEANUP_PLAN.md`.
3. Uruchom pelne testy przez `uv run pytest`.
4. Podsumuj istniejace testy dla:
   - `core/geometry.py`
   - `core/layout_engine.py`
   - `core/project_state.py`
   - `ui/workspace.py`
   - `ui/main_window.py`
5. Wskaz, gdzie sa najwieksze luki testowe przed cleanupem.
6. Zaproponuj dokladny pierwszy etap implementacyjny zgodny z planem.

Na koncu podaj:
- wynik testow
- stan brancha/worktree
- najblizszy rekomendowany etap
- ryzyka, ktore trzeba zabezpieczyc testami przed dalszym refaktorem
```
