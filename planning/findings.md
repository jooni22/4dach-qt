# Findings & Decisions

## Requirements
- Zachować istniejącą architekturę Qt Widgets: `form.ui` / `ui_form.py` jako scaffold, `mainwindow.py` jako shell, `dialogs.py` jako dialogi.
- Nie przenosić logiki domenowej do `mainwindow.py` poza cienką orkiestracją.
- Rozwijać aplikację od rdzenia domenowego do layoutu, raportów i dopiero potem UI.
- Nie psuć obecnego UI i nie przebudowywać go bez potrzeby.
- Dodać lokalnie uruchamialne testy dla domeny i głównego okna.

## Research Findings
- Repo już ma odtworzony shell UI: menu, toolbar, zakładki, status bar i dwa canvasy.
- `form.ui` jest minimalne; większość realnego UI powstaje programowo w `mainwindow.py`.
- `config.json` przechowuje dane firmy, katalog blach i domyślne parametry dialogów kształtów, ale nie przechowuje jeszcze projektu połaci.
- `DrawingCanvas` jest obecnie demonstracyjny i rysuje szkic użytkownika w pikselach, bez modelu domenowego.
- `BlachyDialog` i `DaneFirmyDialog` już stanowią działającą granicę dla konfiguracji materiałów oraz danych firmy.
- Rdzeń domenowy został wydzielony do pakietu `core/`, a pliki planowania przeniesiono do `planning/`.
- Bieżące środowisko uruchomieniowe miało `pytest`, ale nie miało zainstalowanych `PySide6` i `pytest-qt`, więc test UI został przygotowany, lecz nie wykonał się tutaj automatycznie.
- Da się już poprowadzić pierwszy realny przepływ danych: dialog kształtu -> obrys geometryczny -> `ProjectState` -> zapis do `config.json` -> render aktywnej połaci na canvasie.
- Aktualny plan docelowy obejmuje pełny workflow: domena, geometria, wycinki, layout, raporty, UI i testy.
- Da się już poprowadzić pierwszy realny workflow domenowy dla wycinka: połać -> walidowany wycinek -> przesunięcie wycinka -> przeliczenie layoutu -> serializacja `auto_sheet_placements` i `layout_revision`.
- `ProjectState` obsługuje już walidowaną edycję obrysu połaci: przesunięcie całej połaci, przesunięcie punktu, wstawienie punktu i usunięcie punktu.
- Menu `Kształt` i `Wycinki` ma już pierwszy działający workflow oparty o `QInputDialog`, bez przebudowy canvasa i bez przenoszenia logiki domenowej do UI.
- Reguła `base_line_y_cm` została dopięta do aktualnej geometrii obrysu, więc po zmianach outline bazuje na bieżącym `max_y` połaci.
- Na żądanie użytkownika usunięto z bieżącego zakresu UI i roadmapy akcje edycji outline połaci, flip/rotate, align oraz linie podziału, więc kolejny agent nie powinien planować prac nad nimi.
- `core/reporting.py` agreguje już BOM według długości arkusza, liczy koszt, odpady i scala ostrzeżenia z layoutu oraz odrzuconych segmentów.
- `mainwindow.py` podłącza już akcje `Drukuj raport`, `Drukuj raport ciągły` i `Drukuj raport skrócony` do rzeczywistego przeliczenia layoutu oraz renderu HTML raportu.
- Druga zakładka przestała pełnić funkcję pustego drugiego canvasa i służy teraz jako wbudowany podgląd raportu HTML dla aktywnej połaci.
- `ProjectState` obsługuje już ręczne korekty arkuszy przez `manual_sheet_placements`, `manually_removed_auto_sheet_ids` i scalony widok `active_sheet_placements_for_plane()`.
- Zmiana geometrii lub materiału oznacza połać przez `layout_dirty_reason`, czyści wynik auto-layoutu i zostawia ręczne arkusze do jawnego ponownego przeliczenia.
- Menu `Arkusze` ma już działający prosty workflow przez `QInputDialog`: dodanie ręcznego arkusza, usunięcie aktywnego arkusza, podgląd arkuszy, podsumowanie aktywnych arkuszy i zmianę materiału dla aktywnej połaci.
- `core/reporting.py` liczy raport na podstawie aktywnych arkuszy (`auto` po odjęciu ręcznie ukrytych + `manual`), dzięki czemu BOM i koszt odzwierciedlają korekty użytkownika.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Wprowadzić dataclasses dla punktów, poligonów, materiałów, połaci i arkuszy | Dają czytelny, testowalny model bez ciężkiej infrastruktury |
| Utrzymać osobno konfigurację UI i stan projektu domenowego | Obecne dialogi nadal korzystają z `config.json`, a nowa domena może rozwijać się iteracyjnie |
| Dać `ProjectState` z metodami fabrycznymi `from_config` / `to_config_fragment` | Umożliwia płynną integrację z istniejącymi danymi i dalszą migrację |
| Layout engine ma zwracać wynik diagnostyczny, nie tylko listę arkuszy | To przygotowuje grunt pod późniejsze walidacje i raportowanie |
| UI test ma sprawdzać kontrakt strukturalny zamiast szczegółów wizualnych | Taki test jest stabilniejszy i zgodny z obecnym etapem aplikacji |
| W pierwszym milestone długość arkusza dla blachy dachówkowej jest normalizowana przez zaokrąglenie całkowitej długości do modułu | To świadomie uproszczona wersja przed wdrożeniem pełnej globalnej linii bazowej |
| Segmenty powstają przez próbkowanie pionowego pasa w jego środku | To lekki algorytm startowy, wystarczający dla pierwszych testów i łatwy do wymiany później |
| Aktywna połać jest renderowana tylko na głównym canvasie | To wystarczy na start i nie wymaga przebudowy struktury zakładek |
| `project_state` jest persystowany jako osobny fragment w tym samym `config.json` | Zachowuje zgodność z istniejącą persystencją repo |
| Kształty parametryczne generują nowe połacie | Użytkownik zyskuje pierwszy działający workflow bez ryzykownego edytowania istniejącej geometrii |
| `base_line_y_cm` jest tymczasowo rozumiane jako dolna krawędź obrysu (`max_y`) w aktualnym układzie współrzędnych | Pozwala wdrożyć wspólną bazę modułów dla blachy dachówkowej bez zmian UI |
| Zmiana geometrii wycinka czyści tylko `auto_sheet_placements`, podnosi `layout_revision` i zostawia miejsce na przyszłe ręczne korekty | To bezpieczny pierwszy krok przed wdrożeniem pełnego dirty-state i nadpisań manualnych |
| Proste operacje edycji geometrii są na razie zbierane przez `QInputDialog` | To pozwala odblokować prawdziwy workflow użytkownika i testy bez budowy pełnego edytora bezpośrednio na canvasie |
| Zmiana geometrii obrysu również przelicza automatyczną bazę `base_line_y_cm` | Dzięki temu normalizacja modułów pozostaje spójna po edycji połaci |
| W pełnej implementacji ręczne korekty mają przetrwać kolejne przeliczenia | To kluczowy wymóg użyteczności systemu rozkroju |
| Raport HTML może być na początku prosty, ale musi zawierać dane firmy, materiał, BOM i ostrzeżenia | To wystarczy jako pierwsza użyteczna wersja bez nadmiarowej złożoności |
| Rdzeń i planowanie trzymamy w osobnych katalogach | To porządkuje repo bez naruszania klasycznej architektury UI |
| Usunięte akcje edycji outline i linii podziału nie wracają do planu bez nowej decyzji użytkownika | To chroni repo przed przypadkowym wznowieniem odłożonego zakresu |
| Podgląd raportu jest osadzony w drugiej zakładce jako `QTextBrowser` zamiast budować osobne okno drukowania | To najprostszy bezpieczny sposób pokazania BOM, kosztów i ostrzeżeń w istniejącym shellu Qt |
| Zmiana geometrii, materiału lub danych firmy czyści ostatni wygenerowany raport | Chroni UI przed pokazywaniem nieaktualnego BOM lub ostrzeżeń |
| Ręczne usunięcie auto-arkusza jest przechowywane jako delta po `id`, a ręczny arkusz jako osobny `SheetPlacement` ze źródłem `manual` | To pozwala raportować i przeliczać aktywny zestaw arkuszy bez mieszania danych wejściowych i korekt użytkownika |
| Po zmianie geometrii lub materiału system oznacza layout jako nieaktualny zamiast po cichu wyliczać nowy wynik | To zachowuje kontrolę użytkownika nad momentem ponownego przeliczenia i chroni ręczne korekty |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| Istniejące pliki planowania zawierały wcześniejszą analizę, ale nie aktualny plan implementacji | Zastępuję je planem operacyjnym dla pierwszego milestone'u |
| `pytest` zgłaszał ostrzeżenie o `qt_api` bez zainstalowanego pluginu `pytest-qt` | Usunięto ten wpis z konfiguracji `pyproject.toml` |
| Specyfikacja nie definiuje jednoznacznie geometrii dla trójkąta `dowolny` | Przyjęto jawne uproszczenie i zapisano je jako założenie implementacyjne |
| Zakres pełnego workflow nie był wcześniej zapisany w jednym miejscu | Zapisano go teraz w `planning/task_plan.md` i `planning/NEXT_SESSION_PROMPT.md` |
| Pierwszy test globalnej bazy modułów nie przecinał wycinka, więc dawał błędne oczekiwania | Zmieniono szerokość pasa testowego, aby środkowy pas rzeczywiście przecinał otwór i sprawdzał bazę globalną |
| Pierwszy scenariusz testu edycji outline wstawiał punkt powodujący samoprzecięcie | Zmieniono dane testowe tak, by sprawdzały poprawną edycję bez łamania walidacji poligonu |

## Resources
- `DOC/plan-logiki-i-testow.md`
- `DOC/ui-info.md`
- `DOC/ui-okna.md`
- `mainwindow.py`
- `dialogs.py`
- `config.json`
- `core/models.py`
- `core/project_state.py`
- `core/geometry.py`
- `core/layout_engine.py`
- `core/reporting.py`
- `/home/stankiem/.agents/skills/pyside6-classic-desktop/references/repo-profile.md`

## Visual/Browser Findings
- Menu i toolbar są budowane w `mainwindow.py`, a nie w `form.ui`.
- Główne okno posiada `QTabWidget` z zakładką canvasa i zakładką raportu; pomocnicza instancja `DrawingCanvas` nadal istnieje, ale nie jest eksponowana jako aktywny panel UI.
- Status bar już pełni funkcję lekkiego feedbacku dla akcji użytkownika.
- Obecny stan repo nadaje się do przejęcia przez kolejnego agenta implementacyjnego bez dodatkowego researchu.
