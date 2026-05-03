# Stage 4: MainWindow dalsze porzadkowanie
Skills:
codebase-cleanup-tech-debt, pyside6-reviewer
```markdown
Wykonaj tylko etap dalszego porzadkowania `ui/main_window.py` zgodnie z `_TODO/CLEANUP_PLAN.md`.

Cel:
- ograniczyc rozmiar i odpowiedzialnosc `MainWindow`
- wyodrebnic male, praktyczne helpery lub koordynatory wokol:
  - refresh/report/status flow
  - plane action flow
  - dialog flow
  - canvas wiring

Nie rob:
- wielkiego redesignu architektury
- sztucznego mnozenia klas bez realnej korzysci
- zmian w `DrawingCanvas`, jesli nie sa absolutnie konieczne

Wymagania:
- preferuj male, reviewowalne kroki
- jesli pojawia sie ryzyko regresji GUI, dodaj test lub przynajmniej przygotuj manual QA checklist
- po zmianach uruchom `uv run pytest`

Na koncu podaj:
- co zostalo wydzielone lub uproszczone
- jakie odpowiedzialnosci zostaly odciazone z `MainWindow`
- jakie testy uruchomiles
- krotka manual QA checklist
```
