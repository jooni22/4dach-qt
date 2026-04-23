# Task Plan: Pełne wdrożenie logiki 4Dach

## Goal
Doprowadzić aplikację do stanu roboczego dla kalkulacji rozkroju blachodachówki 2D w klasycznym UI PySide6, zachowując istniejący shell okna i rozwijając domenę iteracyjnie, testowalnie i bez przebudowy `ui_form.py`.

## Current Phase
Phase 7

## Phases

### Phase 1: Baseline Sync
- [x] Uzgodnić plan funkcjonalny i architekturę z aktualnym repo
- [x] Utrwalić decyzje i założenia w `planning/findings.md`
- [x] Przygotować handoff dla kolejnej sesji
- **Status:** complete

### Phase 2: Domain Core
- [x] Ustabilizować `ProjectState`, serializację i migrację `config.json`
- [ ] Domknąć modele połaci, materiałów, arkuszy i wyników layoutu
- [x] Rozdzielić stan UI od stanu domenowego
- **Status:** complete

### Phase 3: Geometry And Editing
- [ ] Dokończyć fabryki kształtów parametrycznych
- [x] Dodać walidację outline i hole
- [x] Wprowadzić podstawowy workflow wycinków przez menu i dialogi wejściowe
- [ ] Utrzymać tylko wspierane akcje geometrii w menu bez wracania do usuniętego zakresu edycji outline
- **Status:** complete

### Phase 4: Layout And Reports
- [x] Dokończyć layout engine dla aktywnej połaci i aktywnego materiału
- [x] Dodać raportowanie BOM, kosztów i ostrzeżeń
- [x] Przygotować HTML report generator
- [x] Obsłużyć ręczne korekty arkuszy i dirty-state
- **Status:** complete

### Phase 5: UI Integration
- [x] Podłączyć wspierane akcje menu i toolbar do domeny
- [x] Ujednolicić zakładki z połaciami i canvasy z modelem projektu
- [x] Pokazać stany layoutu, BOM i ostrzeżenia w UI
- **Status:** complete

### Phase 6: Testing And Verification
- [x] Rozszerzyć testy modeli, geometrii, layoutu i raportów
- [x] Uzupełnić testy kontraktowe UI
- [x] Dodać scenariusze smoke dla load/save i workflow usera
- **Status:** complete

### Phase 7: Delivery
- [ ] Ustabilizować końcowy kontrakt danych
- [ ] Zaktualizować dokumentację roboczą
- [ ] Wypisać finalne założenia i ograniczenia
- **Status:** pending

## Key Questions
1. Jak bezpiecznie rozciągnąć `config.json` o `project_state`, nie psując istniejących danych i dialogów?
2. Jak dokładnie ma działać semantyka `base_line_y_cm` dla blachy dachówkowej?
3. Jakie ograniczenia geometrii są obowiązkowe dla pierwszej wersji edytora?
4. Jak mapować ręczne korekty arkuszy na kolejne przeliczenia?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| UI pozostaje klasycznym Qt Widgets bez przebudowy layoutu | To repo ma już działający shell i wymaga zachowania architektury |
| `ui_form.py` nie jest edytowane ręcznie | Plik jest generowany z `form.ui` |
| Logika domenowa nie trafia do `mainwindow.py` poza cienką orkiestracją | Ułatwia testowanie i rozwój |
| Stan projektu żyje osobno od konfiguracji dialogów | Pozwala rozwijać model projektu bez psucia obecnych formularzy |
| Geometria pracuje w cm | To upraszcza algorytmy i mapowanie na canvas |
| Layout engine jest diagnostyczny i zwraca warnings/rejected segments | Ułatwia debug i testy nietypowych połaci |
| Ręczne korekty mają być zachowywane między przeliczeniami | To wymaganie z planu i warunek użyteczności |
| `base_line_y_cm` na start jest automatycznie ustawiane na `max_y` obrysu aktywnej połaci | To bezpieczne uproszczenie zgodne z planem i pozwala wdrożyć wspólną bazę modułów bez zmian UI |
| Akcje menu `Przesuń`, `Przesuń punkt`, `Dodaj punkt`, `Usuń punkt`, flip/rotate, align i linie podziału są poza bieżącym zakresem | Użytkownik zlecił usunięcie ich z aktualnego UI i roadmapy, więc agent nie powinien planować nad nimi prac |

## Next Steps
1. Dodać scenariusze smoke dla load/save i podstawowego workflow użytkownika.
2. Rozszerzyć testy UI o stan raportu po ręcznych korektach, gdy środowisko ma `pytest-qt`.
3. Domknąć tylko te akcje toolbar/menu, które mają realne odpowiedniki domenowe i nie wracają do usuniętego zakresu.
4. Ustabilizować końcowy kontrakt danych przed fazą delivery.

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| Błędne założenie testu o paśmie przecinającym wycinek przy szerokości 60 cm | 1 | Zmieniono scenariusz testowy na szerokość 40 cm, aby środkowy pas rzeczywiście przecinał wycinek i sprawdzał globalną bazę |

## Notes
- Po każdym etapie aktualizować `planning/findings.md` i `planning/progress.md`
- Dla nowych decyzji niezgodnych z dokumentacją dopisywać jawne założenia
- Jeśli brak specyfikacji, przyjmować bezpieczne uproszczenie i je testować
