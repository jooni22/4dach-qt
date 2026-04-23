# Plan zadania

## Cel
Przeanalizować istniejący projekt PySide6 pod kątem nowej implementacji logiki aplikacji dla kalkulacji rozkroju blachodachówki 2D, wskazać właściwe miejsca odpowiedzialności w kodzie, ocenić kompletność wymagań oraz przygotować ulepszony plan implementacji i testów.

## Fazy
- [x] Zmapować istniejącą strukturę aplikacji, UI shell, dialogi, persystencję i aktualny stan testowalności.
- [x] Zweryfikować plan domenowy względem obecnej architektury oraz wskazać luki, ryzyka i brakującą dokumentację.
- [x] Opracować docelowy plan wdrożenia logiki, architekturę modułów i strategię testów automatycznych UI/logiki.
- [x] Zapisać końcowy plan do pliku Markdown w repozytorium.

## Ustalenia robocze
- Repo ma obecnie strukturę klasycznego desktopowego Qt Widgets z logiką UI w `mainwindow.py`.
- `dialogs.py` zawiera formularze oraz `load_config()` / `save_config()` dla `config.json`.
- `ui_form.py` jest generowany z `form.ui` i nie powinien być ręcznie edytowany.
- Brak wydzielonego silnika obliczeniowego i brak testów automatycznych.

## Ryzyka
- Wciśnięcie logiki domenowej do `mainwindow.py` utrudni testowanie i dalszy rozwój.
- Obecny model danych w `config.json` jest zbyt płaski dla pełnego modelu połaci, arkuszy i raportów.
- Brakuje formalnej specyfikacji kilku zasad geometrycznych i algorytmicznych.

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| `code_search` called with file URI instead of absolute path | 1 | Re-run with `/data/...` absolute path |
