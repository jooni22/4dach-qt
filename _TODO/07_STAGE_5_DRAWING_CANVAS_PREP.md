# Stage 5: DrawingCanvas prep only

```markdown
Wykonaj tylko ostrozny etap przygotowawczy dla `ui/drawing_canvas.py` zgodnie z `_TODO/CLEANUP_PLAN.md`.

Cel:
- przygotowac grunt pod przyszly podzial, bez wielkiej rewolucji

Najpierw:
- zidentyfikuj i uporzadkuj logiczne segmenty odpowiedzialnosci:
  - rendering
  - snapping
  - overlays
  - geometry editing
  - selection
  - undo
- dodaj testy charakteryzujace tam, gdzie to praktyczne
- wyciagnij tylko najbardziej izolowalne helpery, jesli sa bezpieczne

Nie rob:
- duzego splitu modulu bez silnego pokrycia testami
- zmiany zachowan interakcji canvasu na slepo
- zmian w innych modulach, jesli nie sa konieczne

Wymagania:
- zachowanie GUI ma pozostac bez zmian
- po zmianach uruchom `uv run pytest`

Na koncu podaj:
- co udalo sie bezpiecznie wydzielic lub uporzadkowac
- jakie obszary nadal sa zbyt ryzykowne na wiekszy refaktor
- jakie testy uruchomiles
- manual QA checklist dla `DrawingCanvas`
```
