# Plan implementacji logiki i testów dla projektu 4Dach

## 1. Cel dokumentu
Ten dokument porządkuje wdrożenie właściwej logiki aplikacji dla kalkulacji rozkroju blachodachówki 2D w istniejącym projekcie PySide6. UI jest w dużej części już odtworzone, dlatego celem nie jest przebudowa interfejsu, tylko:
- wydzielenie poprawnej logiki domenowej,
- utrzymanie cienkiej warstwy UI w `mainwindow.py` i `dialogs.py`,
- przygotowanie testów, które potwierdzą zarówno zgodność UI, jak i poprawność implementacji po wdrożeniu.

## 2. Stan obecny projektu

### 2.1. Co już jest
- `mainwindow.py`
  - buduje menu, toolbar, zakładki, theme toggle i centralny obszar roboczy,
  - zawiera prosty `DrawingCanvas`,
  - obsługuje uruchamianie dialogów i zapis do `config.json`.
- `dialogs.py`
  - zawiera dialogi: kształty, dane firmy, katalog blach,
  - zawiera `load_config()` i `save_config()`.
- `form.ui` + `ui_form.py`
  - dostarczają scaffold głównego okna.
- `config.json`
  - przechowuje dane firmy, katalog blach i kilka parametrów kształtów.
- `DOC/ui-info.md`, `DOC/ui-okna.md`
  - dokumentują oczekiwany wygląd i układ UI.

### 2.2. Czego jeszcze nie ma
- modelu domenowego projektu i połaci,
- silnika geometrii 2D,
- silnika generowania arkuszy,
- kontrolera stanu zakładek/połaci,
- raportowania BOM/kosztów/odpadu,
- testów jednostkowych, integracyjnych i UI,
- formalnej dokumentacji kilku kluczowych zasad algorytmu.

## 3. Ocena Twojego planu
Plan jest dobry jako opis celu biznesowego i ogólnej procedury. Najważniejsze jego zalety:
- jasno definiuje, że pracujemy wyłącznie w 2D,
- narzuca pionowy kierunek pasów, co upraszcza geometrię,
- rozróżnia blachodachówkę modułową i blachę trapezową,
- zawiera sensowne scenariusze testowe,
- przewiduje ręczną korektę arkuszy.

Jednocześnie plan wymaga doprecyzowania w kilku miejscach, bo bez tego implementacja może być niespójna lub trudna do przetestowania.

## 4. Najważniejsze poprawki i usprawnienia do planu

### 4.1. Rozdzielić warstwy odpowiedzialności
Nie należy implementować silnika obliczeniowego bezpośrednio w `mainwindow.py`. To ma być tylko warstwa orkiestracji UI.

Rekomendowany podział:
- `mainwindow.py`
  - akcje menu/toolbar,
  - spinanie sygnałów,
  - przekazywanie poleceń do kontrolera,
  - odświeżanie widoków i status bara.
- `dialogs.py`
  - tylko formularze i pobieranie danych od użytkownika.
- nowy moduł `models.py`
  - dataclasses / struktury domenowe.
- nowy moduł `geometry.py`
  - operacje na poligonach, przecięcia, walidacje.
- nowy moduł `layout_engine.py`
  - generowanie pasów i arkuszy.
- nowy moduł `project_state.py`
  - stan projektu, aktywna połać, ręczne korekty, dirty state.
- nowy moduł `reporting.py`
  - BOM, powierzchnie, odpady, koszty.
- opcjonalnie nowy moduł `canvas_presenter.py`
  - transformacja danych domenowych na warstwę rysowaną przez canvas.

To jest nadal architektura lekka i zgodna z charakterem tego repo, ale dużo lepiej testowalna niż dokładanie wszystkiego do jednego pliku.

### 4.2. Wprowadzić jawny model danych
Obecny `config.json` przechowuje tylko część danych. Do implementacji potrzeba jawnego modelu domenowego.

Minimalny model:
- `ProjectState`
  - `roof_planes: list[RoofPlane]`
  - `active_plane_id`
  - `company_data`
  - `material_catalog`
- `RoofPlane`
  - `id`
  - `name`
  - `outline: Polygon2D`
  - `holes: list[Polygon2D]`
  - `selected_material_id`
  - `generation_settings`
  - `auto_sheet_placements`
  - `manual_sheet_placements`
  - `layout_revision`
- `Material`
  - `id`
  - `type` (`dachowkowa` / `trapezowa`)
  - `effective_width_cm`
  - `module_length_cm`
  - `bottom_margin_cm`
  - `top_margin_cm`
  - `min_sheet_length_cm`
  - `max_sheet_length_cm`
  - `price_per_m2`
- `SheetPlacement`
  - `id`
  - `band_index`
  - `x_left_cm`
  - `x_right_cm`
  - `y_top_cm`
  - `y_bottom_cm`
  - `raw_length_cm`
  - `final_length_cm`
  - `source` (`auto` / `manual`)
  - `split_reason`
- `Report`
  - `net_roof_area_m2`
  - `gross_sheet_area_m2`
  - `waste_percent`
  - `total_cost`
  - `bom_rows`

### 4.3. Doprecyzować reprezentację geometrii
W planie warto jawnie ustalić:
- wszystkie współrzędne robocze liczymy w cm,
- geometria domenowa ma być niezależna od pikseli canvasa,
- canvas tylko mapuje cm <-> px,
- poligon zewnętrzny powinien być prosty, bez samoprzecięć,
- wycinek musi leżeć w całości wewnątrz obrysu,
- wycinki nie powinny nachodzić na siebie bez jawnej obsługi.

To jest ważne, bo obecny `DrawingCanvas` operuje na pozycjach myszy w pikselach, a nie na geometrii domenowej.

### 4.4. Oddzielić tryby pracy użytkownika
Plan powinien wprost opisać tryby interakcji:
- rysowanie obrysu,
- rysowanie wycinku,
- edycja punktu,
- dodawanie punktu na krawędzi,
- usuwanie punktu,
- przesuwanie całej połaci,
- ręczna edycja arkuszy.

Bez jawnego `editor_mode` logika w canvasie szybko stanie się trudna do utrzymania.

### 4.5. Uściślić algorytm generowania pasów
Obecny plan jest dobry, ale należy dopisać kilka zasad:
- pasy generujemy od `min_x` do `max_x` co `effective_width_cm`,
- dla każdego pasa analizujemy jego część wspólną z połacią netto,
- wynik dla jednego pasa może dać 0, 1 lub wiele segmentów pionowych,
- każdy segment pionowy jest kandydatem na osobny arkusz,
- po kontakcie z wycinkiem nie robimy „wyjątku specjalnego”, tylko traktujemy to jako naturalny wynik przecięcia pasa z geometrią netto,
- długość surowa wynika z geometrii, a dopiero potem jest normalizowana do reguł materiału.

To uprości implementację i testy: silnik nie myśli kategorią „okno”, tylko kategorią „segmenty netto w pasie”.

### 4.6. Lepiej zdefiniować taktowanie modułów
To jest najważniejszy fragment algorytmu i musi być zapisany precyzyjniej.

Dla blachodachówki:
- trzeba przyjąć wspólną globalną linię bazową `base_y_cm`,
- długość efektywna arkusza nie może być zaokrąglana niezależnie od lokalnego segmentu,
- finalne cięcia muszą respektować wspólną siatkę modułową względem `base_y_cm`,
- należy określić, czy `base_y_cm` oznacza:
  - największe `y` w geometrii,
  - czy użytkownik może ten punkt/linię ustawić ręcznie,
  - czy przełącznik toolbaru „Od bazy” ma wpływ na tę regułę.

Rekomendacja:
- na start przyjąć automatyczną bazę zdefiniowaną jako skrajna dolna wartość połaci netto,
- ale zaprojektować model tak, aby później można było dodać ręczne ustawienie bazy.

### 4.7. Zdefiniować politykę dla arkuszy poza zakresem min/max
W planie trzeba rozdzielić dwa przypadki:
- `final_length_cm < min_sheet_length_cm`
  - arkusz pomijamy,
  - ale raportujemy ten fakt jako odrzucony segment, jeśli to ważne diagnostycznie,
- `final_length_cm > max_sheet_length_cm`
  - silnik nie powinien tylko zwrócić błędu tekstowego,
  - powinien zwrócić wynik walidacji typu `requires_transverse_split=True`,
  - implementacja fazy 1 może jedynie oznaczać konieczność podziału poprzecznego bez automatycznego dzielenia,
  - automatyczny podział można zaplanować jako fazę 2.

### 4.8. Jawnie opisać ręczną korektę arkuszy
To wymaganie jest bardzo ważne i ma konsekwencje architektoniczne.

Rekomendowana zasada:
- wynik automatu jest zapisywany osobno,
- ręczne zmiany użytkownika są przechowywane jako zestaw poprawek delta,
- ponowne automatyczne przeliczenie nie nadpisuje ręcznych zmian bez wyraźnej decyzji użytkownika,
- po zmianie geometrii lub materiału stan powinien być oznaczony jako „wynik nieaktualny”.

Minimalny model korekt:
- `manually_added_sheet_ids`
- `manually_removed_auto_sheet_ids`
- `manual_sheet_placements`
- `layout_dirty_reason`

### 4.9. Rozszerzyć raportowanie o warstwę diagnostyczną
Raport końcowy to nie tylko BOM i koszt.

Silnik powinien zwracać także:
- ostrzeżenia walidacyjne,
- listę odrzuconych segmentów,
- flagę wymagającą podziału poprzecznego,
- metryki pomocnicze do debugowania.

To bardzo pomaga w testach i w diagnozie błędów na nietypowych połaciach.

## 5. Gdzie przypisać daną funkcję w obecnym projekcie

### 5.1. `mainwindow.py`
Tu powinno zostać:
- budowanie menu i toolbarów,
- przełączanie trybów edycji,
- aktywacja zakładki / połaci,
- otwieranie dialogów,
- wywołanie polecenia „przelicz”,
- przekazanie wyniku do widoku,
- status bar i komunikaty.

Tu nie powinno trafić:
- geometria poligonów,
- liczenie przecięć,
- logika modułów,
- BOM, odpady i kosztorys.

### 5.2. `dialogs.py`
Tu powinno zostać:
- edycja parametrów materiałów,
- formularze kształtów bazowych,
- dane firmy,
- w przyszłości ewentualnie dialog ustawień generowania.

Tu nie powinno trafić:
- logika liczenia rozkroju,
- logika walidacji geometrii poza prostą walidacją formularza.

### 5.3. Nowe moduły domenowe
Najbardziej naturalny, prosty i bezpieczny podział dla tego repo:
- `models.py`
- `geometry.py`
- `layout_engine.py`
- `project_state.py`
- `reporting.py`

Nie ma potrzeby robić od razu rozbudowanego wielopoziomowego frameworka katalogów. Ważniejsze jest czytelne oddzielenie logiki od UI.

## 6. Proponowana kolejność wdrożenia

### Faza 1. Fundament domeny
- wprowadzić `models.py`,
- znormalizować nazwy pól materiału i projektu,
- przygotować adapter odczytu/zapisu `config.json` do nowych modeli.

### Faza 2. Geometria wejściowa
- walidacja prostego poligonu,
- walidacja wycinków,
- operacje pomocnicze: bbox, pole powierzchni, segmenty przecięć.

### Faza 3. Silnik rozkroju
- generacja pionowych pasów,
- przecięcie pasa z połacią netto,
- budowa segmentów pionowych,
- normalizacja długości według materiału,
- walidacja min/max,
- zwrot wyniku z ostrzeżeniami.

### Faza 4. Agregacja i raport
- BOM według długości,
- powierzchnia netto i brutto,
- procent odpadu,
- koszt całkowity.

### Faza 5. Integracja z UI
- spięcie zakładek z `ProjectState`,
- wyświetlanie połaci netto i wynikowych arkuszy,
- sygnalizacja stanu nieaktualnych wyników,
- obsługa ręcznych korekt.

### Faza 6. Testy i stabilizacja
- testy jednostkowe geometrii,
- testy silnika rozkroju,
- testy integracyjne stanu projektu,
- testy UI kontraktowe.

## 7. Strategia testów

## 7.1. Zasada ogólna
Testy należy podzielić na dwie niezależne warstwy:
- testy logiki domenowej,
- testy kontraktu UI.

To ważne, bo sam test UI nie potwierdzi poprawności silnika obliczeniowego, a same testy silnika nie potwierdzą zgodności istniejącego interfejsu z dokumentacją.

### 7.2. Rekomendowany stack testowy
Rekomendacja:
- `pytest`
- `pytest-qt`
- opcjonalnie `pytest-cov`

Powód:
- `pytest-qt` dobrze nadaje się do tworzenia `QApplication`, otwierania okien, klikania akcji i weryfikacji widgetów bez ręcznego pisania wielu helperów.

### 7.3. Testy logiki domenowej
Proponowane pliki:
- `tests/test_geometry.py`
- `tests/test_layout_engine.py`
- `tests/test_reporting.py`
- `tests/test_project_state.py`

Minimalne przypadki:
- walidacja poligonu bez samoprzecięć,
- wykrywanie niepoprawnego wycinka,
- generacja pasów dla prostokąta,
- trójkąt ze schodkowaniem modułowym,
- połać z oknem dająca dwa segmenty w jednym paśmie,
- zmiana materiału z modułowego na ciągły,
- przypadek poniżej minimum długości,
- przypadek powyżej maksimum długości,
- BOM i koszt z poprawnymi sumami.

### 7.4. Testy UI kontraktowe
Proponowane pliki:
- `tests/test_mainwindow_ui.py`
- `tests/test_dialogs_ui.py`

Te testy mają sprawdzać zgodność z `DOC/ui-info.md` i `DOC/ui-okna.md`, a nie logikę algorytmu.

Zakres testów UI:
- obecność menu: `Plik`, `Kształt`, `Wycinki`, `Katalog`, `Arkusze`,
- obecność i kolejność akcji w menu,
- obecność i kolejność głównych akcji toolbaru,
- obecność `workspace_tabs`,
- obecność canvasa w zakładkach,
- otwieranie dialogów `Prostokąt`, `Trójkąt`, `Trapez`, `Dane firmy`, `Blachy`,
- poprawne etykiety i typy kontrolek w dialogach,
- poprawne domyślne wartości z `config.json`.

### 7.5. Ważne usprawnienie pod testy UI
Aby testy UI były stabilne, trzeba dodać lub ujednolicić `objectName` dla:
- głównych akcji menu,
- przycisków toolbaru,
- najważniejszych pól dialogów,
- canvasów,
- przycisku wyboru materiału,
- comboboxu wariantu.

Bez tego testy będą oparte głównie o teksty widoczne i kolejność, co jest bardziej kruche.

### 7.6. Test akceptacyjny po wdrożeniu logiki
Powinien istnieć co najmniej jeden test end-to-end na poziomie desktopowego UI:
- otwórz aplikację,
- wybierz materiał,
- ustaw kształt testowy,
- uruchom generację pokrycia,
- sprawdź, że na aktywnej połaci pojawiły się oczekiwane arkusze,
- sprawdź, że raport danych agregowanych jest spójny z wynikiem silnika.

Ten test nie musi być bardzo rozbudowany na start, ale powinien spinać całą ścieżkę użytkownika.

## 8. Brakujące informacje, które warto doprecyzować przed implementacją
Poniższe punkty są naprawdę istotne. Bez nich część decyzji trzeba będzie arbitralnie założyć.

### 8.1. Geometria i współrzędne
- Czy oś `Y` rośnie w dół jak na ekranie, czy w górę jak w klasycznej geometrii?
- Czy geometria domenowa ma być przechowywana w układzie matematycznym, a dopiero canvas odwracać osie?
- Czy dopuszczalne są punkty współliniowe i zerowej długości krawędzie?

### 8.2. Reguły wycinków
- Czy wycinek może dotykać obrysu zewnętrznego?
- Czy dwa wycinki mogą się stykać krawędzią lub wierzchołkiem?
- Czy wycinki mogą być dowolnymi poligonami, czy w praktyce wystarczą prostokąty?

### 8.3. Reguły materiałowe
- Skąd bierze się `max_sheet_length_cm`, skoro obecny dialog pokazuje ją jako stałe 900 cm, ale nie zapisuje jawnie do modelu?
- Czy lista `moduly` ma tylko charakter informacyjny, czy ogranicza dozwolone długości?
- Czy cena zawsze ma być liczona po `m2`, czy dla `mb` też ma być wspierana pełna kalkulacja?

### 8.4. Reguły rozkroju
- Czy pasy mają startować zawsze od lewej krawędzi bbox, czy od bazy użytkownika?
- Jak dokładnie ma działać przełącznik `Od prawej`?
- Jak dokładnie ma działać przełącznik `Od bazy`?
- Czy półotwarte skrajne pasy przy prawej granicy mają być przycinane do mniejszej szerokości, czy odrzucane?

### 8.5. Ręczne poprawki
- Czy ręcznie dodany arkusz może częściowo wyjść poza połać netto?
- Czy ręczne usunięcie auto-arkusza jest blokadą trwałą do kolejnego „pełnego odświeżenia”? 
- Jak użytkownik ma rozpoznawać, że widzi wynik automatyczny z ręcznymi nadpisaniami?

### 8.6. Raport i eksport
- Jaki ma być docelowy format raportu: HTML, PDF, wydruk Qt, czy kilka opcji?
- Czy BOM grupujemy po długości finalnej, po liczbie modułów, czy po obu?
- Jak zaokrąglać pola powierzchni i kwoty w raporcie?

## 9. Minimalna dokumentacja, której jeszcze brakuje
Przed właściwą implementacją warto dopisać trzy krótkie dokumenty techniczne:
- `DOC/domain-model.md`
  - definicje modeli i relacji,
- `DOC/layout-algorithm.md`
  - dokładne zasady generacji pasów i taktowania modułów,
- `DOC/test-plan.md`
  - lista scenariuszy testowych i kryteria akceptacji.

Jeśli chcesz ograniczyć zakres, minimum absolutne to jeden dokument zawierający:
- definicję `RoofPlane`, `Material`, `SheetPlacement`,
- formalny opis globalnej linii bazowej,
- zasady ręcznej korekty wyników.

## 10. Ostateczna rekomendacja
Najbezpieczniejszy kierunek dla tego repo to:
- pozostawić `mainwindow.py` i `dialogs.py` jako warstwę UI,
- wprowadzić lekkie wydzielenie modułów domenowych,
- zacząć od testów jednostkowych silnika i kontraktowych testów UI,
- dopiero potem spinać wszystko w pełny workflow interaktywny.

To pozwoli rozwijać logikę obliczeniową bez psucia istniejącego UI i jednocześnie zbuduje solidną podstawę pod dalsze funkcje, takie jak ręczne poprawki, raporty i zaawansowane scenariusze rozkroju.
