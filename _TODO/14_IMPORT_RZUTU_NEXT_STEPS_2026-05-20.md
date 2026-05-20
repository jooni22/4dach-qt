# Import rzutu - kolejne kroki

Data: 2026-05-20

## Stan po wdrożeniu

- `Kształt -> Importuj z rzutu...` otwiera tymczasową kartę `Import rzutu` w głównym workspace zamiast modala.
- Karta importu nie jest połacią: ma `plane_id=None`, osobny typ zakładki i zamykanie wywołuje anulowanie importu.
- Canvas importu przechowuje crop i punkty szkiców w współrzędnych obrazu.
- Zamknięty szkic od razu trafia do listy draftów i jest widoczny jako półprzezroczysty polygon na obrazie.
- `Importuj` dodaje wszystkie połacie jako nowe zakładki w jednej operacji undo.
- Zdjęcie pozostaje stanem tymczasowym UI i nie trafia do pliku projektu.

## Zweryfikowane komendy

```bash
uv run pytest tests/test_roof_plan_import.py tests/test_roof_plan_import_dialog.py tests/test_workspace.py tests/test_mainwindow_ui_contract.py -q
uv run ruff check ui/dialogs/roof_plan_import_dialog.py ui/dialogs/__init__.py ui/workspace.py ui/main_window.py tests/test_roof_plan_import_dialog.py tests/test_workspace.py tests/test_mainwindow_ui_contract.py
uv run pytest
```

Wynik ostatniego pełnego przebiegu: `399 passed`.

## Następne kroki

1. Otworzyć aplikację przez `uv run python __main__.py` i ręcznie sprawdzić import na realnym rzucie: wybór pliku, rysowanie kilku połaci, wpisywanie wymiarów, import, undo.
2. Dopolerować przełącznik trybu `Kadruj` / `Rysuj`, jeśli użytkownicy mają często kadrować obraz; obecnie jest prosty i funkcjonalny, ale bez stanu wizualnego aktywnego trybu.
3. Rozważyć panowanie obrazu przy zoomie manualnym, jeśli `100%` lub `+` będzie ucinać duże rzuty poza widocznym obszarem.
4. Dodać screenshot albo krótkie nagranie do PR, bo zmiana dotyczy głównego przepływu UI.
5. Przy następnym rozszerzeniu nie dodawać OpenCV ani auto-detekcji linii bez osobnego briefu; obecny zakres to ręczny import.
