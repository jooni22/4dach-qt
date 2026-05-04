# Plan zmian: canvas, ustawienia i toolbar

## Cel dokumentu

Spisać w jednym miejscu wszystkie zgłoszone przez użytkownika:

- błędy do naprawy,
- zmiany zachowania,
- zmiany domyślnych ustawień,
- zmiany UI/UX,
- miejsca w kodzie, które najpewniej trzeba ruszyć,
- pytania otwarte, które warto doprecyzować przed implementacją albo w trakcie review.

Dokument bazuje na opisie użytkownika z dnia `2026-05-04`, załączonych zrzutach ekranu oraz szybkim sprawdzeniu aktualnego kodu i istniejących nazw ustawień.

## Stan obecny potwierdzony w kodzie

### Ustawienia aplikacji

Aktualne źródło prawdy dla ustawień to `core/app_settings.py` (`AppSettings`) oraz `ui/dialogs/settings_dialog.py`.

Potwierdzone obecne defaulty:

- `partial_cutout_top_extra_cm = 15`
- `grid_size_cm = 10`
- `show_grid = True`
- `grid_major_cm = 100`
- `grid_minor_cm = 10`
- `show_crosshair = True`
- `snap_to_grid = True`
- `snap_to_axis = True`
- `snap_to_45deg = True`
- `snap_to_3060deg = False`
- `snap_to_points = True`
- `show_inferences = True`
- `live_angle_mode = absolute`
- `show_guide_lines = True`
- `edge_drag_mode = move_vertices`
- `show_edge_length_labels = True`
- `show_vertex_angle_labels = False`
- `label_always_visible = False`

To oznacza, że część oczekiwanych przez użytkownika defaultów już istnieje, ale co najmniej te pola są obecnie niezgodne z wymaganiem:

- `show_crosshair` jest obecnie `True`, a ma być `False`
- `snap_to_3060deg` jest obecnie `False`, a ma być `True`
- `label_always_visible` jest obecnie `False`, a ma być `True`

### Toolbar i widoczność arkuszy

Potwierdzone elementy w `ui/toolbar.py` i `ui/main_window.py`:

- istnieje osobny przycisk `material_button` z tooltipem `Wybór aktywnej blachy`
- istnieje `variant_combo` do wyboru materiału
- istnieje akcja `overlay_sheet` z etykietą `Pokaż arkusze`
- istnieje akcja `grid` z etykietą `Pokaż siatkę`
- nie ma osobnej ikony toolbarowej dla `snap_to_grid`

Potwierdzone obecne defaulty runtime:

- `MainWindow._sheets_visible = True`
- `Workspace._sheets_visible = True`

To jest niezgodne z wymaganiem użytkownika, który chce, aby `Pokaż arkusze` było domyślnie wyłączone.

### Edycja midpointów / białych kropek

Potwierdzone w `ui/drawing_canvas.py`:

- istnieje logika midpointów krawędzi,
- midpoint handle jest rysowany jako osobna kropka,
- `edge_drag_mode` obecnie rozdziela dwa tryby:
  - `move_vertices`
  - `insert_vertex`
- dla outline istnieje już ścieżka `insert_polygon_point(...)` przy trybie `insert_vertex`

To dobrze pokrywa technicznie obecny stan, ale jest niezgodne z nową regułą biznesową użytkownika:

- dla kształtów midpoint ma przesuwać całą krawędź,
- dla wycinków midpoint ma dodawać nowy wierzchołek,
- ta reguła ma być stała, a nie wybierana z ustawień.

## Zakres zmian zgłoszonych przez użytkownika

## 1. Ustawić nowe defaulty i dodać przycisk `Domyślne`

### Wymaganie

Jeżeli nie ma `config.json`, aplikacja ma ładować następujące wartości jako standardowe defaulty.

### Docelowe defaulty

#### Wycinki

- Zapas górnego odcinka dla częściowo przykrytego arkusza: `15 cm`

#### Siatka i przyciąganie

- Rozmiar oczka siatki: `10 cm`
- Główna siatka: `100 cm`
- Pomocnicza siatka: `10 cm`
- Kursor / `Pokaż krzyżyk kursora`: `wyłączone`
- `Przyciągaj do siatki`: `włączone`
- `Przyciągaj do osi 0°/90°`: `włączone`
- `Przyciągaj do 45°`: `włączone`
- `Przyciągaj do 30°/60°`: `włączone`
- `Przyciągaj do punktów charakterystycznych`: `włączone`
- `Pokaż linie inferencji CAD`: `włączone`

#### Rysowanie na żywo

- Tryb kąta: `Kąt bezwzględny od osi X`
- `Pokaż subtelne linie pomocnicze aktywnego segmentu`: `włączone`

#### Edycja po rysowaniu

- `Pokaż etykiety długości krawędzi`: `włączone`
- `Pokaż etykiety kątów wierzchołków`: `wyłączone`
- `Pokazuj etykiety także bez zaznaczenia`: `włączone`

### Dodatkowa zmiana UI

W oknie ustawień trzeba dodać przycisk `Domyślne`, który przywraca te wartości w formularzu bez potrzeby ręcznego klikania każdej opcji.

### Uwaga projektowa

Pole `Środek krawędzi` nie powinno docelowo wrócić po kliknięciu `Domyślne`, bo zgodnie z dalszymi wymaganiami ma zostać usunięte całkowicie z ustawień.

### Moduły do ruszenia

- `core/app_settings.py`
- `ui/dialogs/settings_dialog.py`
- `tests/test_app_settings.py`

### Kryteria akceptacji

- brak `config.json` daje dokładnie powyższe wartości,
- przycisk `Domyślne` resetuje formularz ustawień do nowych defaultów,
- serializacja/deserializacja ustawień nadal działa,
- testy defaultów zostają zaktualizowane.

## 2. Naprawa podziału arkuszy przy wycinkach, które nie pokrywają całej szerokości

### Objaw

Aktualnie aplikacja automatycznie wyznacza linie podziału arkuszy w złych miejscach, gdy wycinek nie pokrywa całej szerokości arkusza/pasa.

Na pierwszym zrzucie użytkownik zaznaczył:

- pomarańczowe linie: obecne błędne przedziały,
- zielone linie: oczekiwane poprawne przedziały.

### Wymaganie

Na każdym wycinku ma automatycznie powstawać linia przedziału dokładnie w miejscu wynikającym z geometrii wycinka, tak jak na zielonych oznaczeniach.

Inaczej mówiąc:

- jeśli wycinek zmienia realny przebieg podziału pasa/arkusza,
- to granica przedziału musi zostać wprowadzona na wysokości wynikającej z tego wycinka,
- a nie tylko na podstawie obecnej uproszczonej heurystyki.

### Prawdopodobny obszar kodu

- `core/layout_engine.py`
- `core/project_state.py`
- `ui/canvas/sheet_geometry.py`
- testy layoutu i odbudowy splitów w:
  - `tests/test_models_and_state.py`
  - `tests/test_layout_engine.py`

### Ryzyko

To nie wygląda na czysto wizualny problem. Jest duża szansa, że trzeba poprawić sam model podziału segmentów/bandów, a nie tylko rendering.

### Kryteria akceptacji

- linie przedziałów pojawiają się na każdym wycinku tam, gdzie faktycznie zmienia się podział,
- widok canvasa i dane layoutu są ze sobą zgodne,
- raport i pozycje arkuszy nie rozjeżdżają się po przeliczeniu projektu,
- istniejące testy splitów nie regresują.

## 3. Usunięcie środkowej kulki przy przesuwaniu wycinka

### Objaw

Na drugim obrazie środkowa kulka nadal sugeruje osobny uchwyt do łapania i przesuwania wycinka.

### Problem

To jest teraz mylące, bo:

- przesuwanie wycinka działa już po kliknięciu wewnątrz wycinka,
- kulka nie jest już potrzebna jako affordance,
- dodatkowo źle wyznacza środek wizualny i wprowadza użytkownika w błąd.

### Wymaganie

Usunąć środkową kulkę dla wycinków w trybie przesuwania/edycji.

### Zakres

To jest zmiana UI/renderingu w `ui/drawing_canvas.py`.

### Kryteria akceptacji

- środkowa kulka nie jest rysowana dla wycinków,
- nadal da się przesuwać wycinek przez kliknięcie i drag wewnątrz jego obszaru,
- brak regresji selekcji wycinków.

## 4. Białe kropki: brak na wycinkach, zasłanianie przez badge, nowa stała reguła działania

### Objawy

Na trzecim obrazie użytkownik zgłasza dwa problemy:

- na wycinkach brakuje białych kropek,
- boczne białe kropki są zasłaniane przez badge z wymiarami.

### Wymaganie ogólne

Trzeba:

- dodać białe kropki do wycinków,
- przesunąć badge wyżej lub niżej tak, aby nigdy nie zasłaniały białych kropek,
- usunąć z ustawień opcję `Ustawienia > Edycja po rysowaniu > Środek krawędzi`,
- zastąpić ją stałą zasadą zależną od typu geometrii.

### Nowa stała reguła midpointów

#### Dla kształtów / głównego obrysu

Biała kropka na krawędzi ma powodować przesuwanie tej krawędzi, czyli:

- przesuwamy jedną linię, na której leży kropka,
- długości dwóch przylegających linii na końcach zmieniają się odpowiednio,
- zachowanie ma odpowiadać przesuwaniu całej krawędzi, a nie dodawaniu nowego punktu.

#### Dla wycinków

Biała kropka na krawędzi ma powodować dodanie nowego wierzchołka.

### Powiązany bug geometryczny

Użytkownik wskazał dodatkowo błąd na piątym obrazie:

- gdy łapiemy boczne białe kropki w kształcie,
- a górna linia ma inną długość niż dolna,
- to zamiast zmieniać pozycję względem osi `X`, pojawia się też niechciane przesunięcie względem osi `Y`.

To oznacza, że drag bocznej krawędzi nie zachowuje się czysto osiowo i najpewniej miesza przesunięcie normalne z przesunięciem po skosie lub z midpointem liczonym w złym układzie odniesienia.

### Docelowe zachowanie

- drag pionowej/bocznej krawędzi zmienia szerokość zgodnie z osią `X`,
- drag poziomej krawędzi zmienia wysokość zgodnie z osią `Y`,
- brak dodatkowego dryfu na drugiej osi,
- dla wycinków midpoint nie przesuwa całej krawędzi, tylko rozcina ją i dodaje nowy punkt.

### Konsekwencja w ustawieniach

Opcję `Środek krawędzi` trzeba usunąć z:

- modelu ustawień,
- dialogu ustawień,
- serializacji/deserializacji,
- testów,
- ewentualnych dokumentacji.

### Moduły do ruszenia

- `ui/drawing_canvas.py`
- `ui/dialogs/settings_dialog.py`
- `core/app_settings.py`
- `tests/test_drawing_canvas.py`
- `tests/test_app_settings.py`

### Kryteria akceptacji

- wycinki mają białe kropki na krawędziach,
- badge z długością nigdy nie zasłaniają midpointów,
- midpoint kształtu przesuwa krawędź,
- midpoint wycinka dodaje nowy wierzchołek,
- opcja `Środek krawędzi` znika z ustawień i konfiguracji,
- boczne przeciąganie nie wprowadza błędnego przesunięcia po osi `Y`.

## 5. Zmiana długości boku przez badge ma skalować całą geometrię proporcjonalnie

### Objaw

Na czwartym obrazie użytkownik opisuje, że po kliknięciu białego badge długości i wpisaniu nowej wartości:

- obecnie zmienia się długość tylko jednej linii,
- a oczekiwane jest skalowanie całego kształtu w tym samym stosunku.

### Wymaganie

Zmiana długości przez badge ma działać jako jednolite skalowanie geometrii, a nie lokalna edycja jednej krawędzi.

### Przykład

Jeżeli mamy kwadrat, gdzie każda z `4` linii ma długość `100`, to po zmianie jednej z wartości z `100` na `500` wynik ma być taki:

- nadal kwadrat,
- każda linia ma `500`.

### Dodatkowe wymaganie dotyczące wycinków

Użytkownik doprecyzował, że wycinki mają być skalowane dokładnie tym samym współczynnikiem co outline. Oznacza to, że:

- skalowanie outline musi zachować spójny współczynnik dla całego obiektu,
- wycinki należące do tej geometrii również muszą zostać przeskalowane tym samym współczynnikiem,
- tak aby zachować proporcje całego układu outline + holes.

### Doprecyzowany punkt odniesienia skalowania

Użytkownik doprecyzował, że skalowanie ma odbywać się względem punktu `x:0, y:0` używanego już przy gotowym kształcie.

Praktyczna interpretacja implementacyjna tego wymagania:

- badge pojawiają się dopiero wtedy, gdy istnieje gotowy kształt,
- w tym stanie punkt `0,0` jest punktem odniesienia geometrii ustawionym przy lewej dolnej bazie kształtu,
- skalowanie ma startować właśnie od tego punktu `0,0`,
- po skalowaniu lewa dolna baza referencyjna nadal ma mieć `x:0, y:0`,
- outline i wszystkie wycinki mają zachować wspólny współczynnik skali względem tego samego origin.

To wyklucza skalowanie względem:

- środka bounding boxa,
- środka figury,
- lokalnego midpointu wybranej krawędzi,
- dowolnego pivotu zależnego od aktualnie klikniętego badge.

### Moduły do ruszenia

- `ui/drawing_canvas.py`
- możliwe wsparcie w `core/geometry.py`
- testy regresyjne w `tests/test_drawing_canvas.py`

### Kryteria akceptacji

- edycja długości przez badge skaluje cały outline proporcjonalnie,
- powiązane wycinki skalują się w tym samym stosunku,
- pivot skalowania to punkt `0,0` geometrii używany dla gotowego kształtu,
- po skalowaniu lewa dolna baza referencyjna nadal ma `x:0, y:0`,
- kształt zachowuje klasę podobieństwa,
- nie dochodzi do lokalnego „rozciągania” tylko jednej krawędzi.

## 6. Toolbar: usunąć ikonę wyboru aktywnej blachy, zmienić defaulty i dodać ikonę `snap_to_grid`

### Obecny stan

W toolbarze istnieją obecnie:

- osobna ikonka/przycisk `Wybór aktywnej blachy` (`material_button`),
- pole `variant_combo`,
- `Pokaż arkusze`,
- `Pokaż siatkę`,
- `Układaj od lewej`,
- `Od prawej`.

### Wymagania

#### 6.1. Usunąć ikonę `Wybór aktywnej blachy`

Powód:

- aktywna blacha i tak ustawia się automatycznie po wyborze innej blachy,
- osobna ikonka jest zbędna.

Najbardziej naturalne odczytanie wymagania:

- usunąć sam `material_button`,
- zostawić `variant_combo` jako właściwy kontroler wyboru.

#### 6.2. Zmienić domyślne stany toolbaru

Aktualnie domyślnie zaznaczone są:

- `Pokaż arkusze`
- `Pokaż siatkę`
- `Układaj od lewej`

Docelowo:

- `Pokaż arkusze` ma być domyślnie odznaczone,
- `Pokaż siatkę` pozostaje domyślnie włączone,
- `Układaj od lewej` pozostaje domyślnie włączone.

#### 6.3. Dodać nową ikonę obok `Pokaż siatkę`

Nowa ikona ma reprezentować:

- `Przyciągaj do siatki`

czyli toolbarowy skrót do opcji, która obecnie jest tylko w ustawieniach.

Wymagania szczegółowe:

- ikona typu magnes lub wizualnie równoważna,
- ma być obok `Pokaż siatkę`,
- ma być domyślnie włączona,
- ma sterować tym samym stanem co `app_settings.snap_to_grid`.

### Moduły do ruszenia

- `ui/toolbar.py`
- `ui/main_window.py`
- `ui/workspace.py`
- ewentualnie `app_icons.py`
- testy UI kontraktu i workspace:
  - `tests/test_mainwindow_ui_contract.py`
  - `tests/test_workspace.py`

### Kryteria akceptacji

- `material_button` znika z toolbaru,
- wybór materiału nadal działa przez `variant_combo`,
- `Pokaż arkusze` jest domyślnie wyłączone,
- nowa ikona `snap_to_grid` działa i synchronizuje się z ustawieniami,
- brak rozjazdu między stanem toolbaru, `MainWindow` i canvasem.

## 7. Menu `Plik`: uprościć opcje drukowania raportu

### Obecny stan

W `ui/main_window.py` w menu `Plik` istnieją obecnie trzy akcje:

- `Drukuj raport`
- `Drukuj raport ciągły`
- `Drukuj raport skrócony`

### Wymaganie

Trzeba usunąć z menu `Plik` następujące opcje:

- `Drukuj raport ciągły`
- `Drukuj raport skrócony`

Ma zostać tylko jedna opcja:

- `Drukuj raport`

### Zakres

Na tym etapie plan obejmuje uproszczenie menu użytkownika. Nie zakładamy jeszcze zmian wewnętrznej logiki generowania raportów, dopóki nie okaże się to konieczne podczas implementacji.

### Prawdopodobny obszar kodu

- `ui/main_window.py`
- ewentualnie `tests/test_mainwindow_ui_contract.py`

### Kryteria akceptacji

- w menu `Plik` widoczna jest tylko akcja `Drukuj raport`,
- akcje `Drukuj raport ciągły` i `Drukuj raport skrócony` nie są już dostępne z UI,
- pozostała akcja `Drukuj raport` nadal działa bez regresji.

## Lista issue do naprawy

1. Niezgodne defaulty `AppSettings` względem oczekiwań użytkownika.
2. Brak przycisku `Domyślne` w dialogu ustawień.
3. Błędny podział arkuszy przy wycinkach częściowo pokrywających szerokość pasa.
4. Środkowa kulka wycinka jest zbędna i myląca.
5. Brak midpointów na wycinkach.
6. Badge zasłaniają boczne midpointy.
7. `edge_drag_mode` jako opcja ustawień jest niezgodne z nową docelową regułą biznesową.
8. Drag bocznych midpointów kształtu powoduje niechciany dryf po osi `Y`.
9. Edycja długości przez badge modyfikuje tylko jedną krawędź zamiast skalować całość.
10. Skalowanie przez badge musi obejmować także wycinki.
11. Zbędna ikonka `Wybór aktywnej blachy` w toolbarze.
12. `Pokaż arkusze` ma zły domyślny stan (`True` zamiast `False`).
13. Brak toolbarowej akcji `snap_to_grid`.
14. W menu `Plik` są zbędne akcje `Drukuj raport ciągły` i `Drukuj raport skrócony`.

## Proponowany podział na etapy implementacyjne

### Etap 1. Ustawienia i toolbar

- poprawa defaultów w `AppSettings`,
- dodanie przycisku `Domyślne`,
- usunięcie `material_button`,
- dodanie toolbarowego `snap_to_grid`,
- wyłączenie `Pokaż arkusze` domyślnie.

### Etap 2. Midpointy i edycja geometrii

- usunięcie środkowej kulki wycinka,
- dodanie midpointów do wycinków,
- stała reguła: outline przesuwa krawędź, wycinek dodaje wierzchołek,
- usunięcie `edge_drag_mode` z ustawień,
- naprawa driftu `Y` przy przeciąganiu bocznej krawędzi.

### Etap 3. Badge i skalowanie

- repozycjonowanie badge tak, aby nie zasłaniały midpointów,
- przebudowa edycji długości przez badge na jednolite skalowanie,
- testy outline + cutout scaling.

### Etap 4. Layout / split arkuszy

- analiza algorytmu splitów,
- poprawa generowania przedziałów przy częściowych wycinkach,
- testy layoutu i renderingu arkuszy.

### Etap 5. Uproszczenie menu raportów

- usunięcie z menu `Plik` akcji `Drukuj raport ciągły`,
- usunięcie z menu `Plik` akcji `Drukuj raport skrócony`,
- pozostawienie tylko `Drukuj raport`,
- aktualizacja testów kontraktu menu, jeśli istnieją.

## Szczegółowa kolejność implementacji na małe taski

### Etap 1. Ustawienia i toolbar

1. Zmienić default `show_crosshair` z `True` na `False` w `core/app_settings.py`.
2. Zmienić default `snap_to_3060deg` z `False` na `True` w `core/app_settings.py`.
3. Zmienić default `label_always_visible` z `False` na `True` w `core/app_settings.py`.
4. Zaktualizować `AppSettings.from_dict(...)`, aby brakujące klucze ładowały nowe defaulty.
5. Zaktualizować `tests/test_app_settings.py` pod nowe wartości domyślne.
6. Dodać przycisk `Domyślne` w `ui/dialogs/settings_dialog.py`.
7. Dodać metodę pomocniczą resetującą pola dialogu do domyślnych wartości `AppSettings()`.
8. Upewnić się, że reset `Domyślne` nie przywraca opcji `Środek krawędzi`, jeśli ta opcja zostanie już usunięta w dalszym etapie.
9. Usunąć `material_button` z `ui/toolbar.py`.
10. Zachować `variant_combo` jako jedyny kontroler wyboru aktywnej blachy.
11. Dodać nową akcję toolbarową dla `snap_to_grid` obok `Pokaż siatkę`.
12. Podłączyć nową akcję toolbarową do `MainWindow` i `Workspace`, tak aby sterowała tym samym stanem co `app_settings.snap_to_grid`.
13. Zmienić runtime default `_sheets_visible` na `False` w `ui/main_window.py` i `ui/workspace.py`.
14. Zaktualizować testy kontraktu UI i workspace pod nowy toolbar i nowe defaulty.

### Etap 2. Midpointy i reguły edycji po rysowaniu

15. Zidentyfikować w `ui/drawing_canvas.py` kod rysujący środkową kulkę wycinka.
16. Usunąć rendering środkowej kulki wycinka bez naruszania dragowania wnętrza wycinka.
17. Dodać midpoint handles do krawędzi wycinków.
18. Rozdzielić zachowanie midpointów po typie geometrii:
19. Dla outline midpoint ma przesuwać całą krawędź.
20. Dla wycinka midpoint ma dodawać nowy wierzchołek.
21. Usunąć `edge_drag_mode` z `core/app_settings.py`.
22. Usunąć `edge_drag_mode` z `ui/dialogs/settings_dialog.py`.
23. Usunąć testy i serializację powiązane z `edge_drag_mode`.
24. Dodać test regresyjny potwierdzający insert vertex dla wycinka po kliknięciu białej kropki.
25. Dodać test regresyjny potwierdzający drag całej krawędzi outline po kliknięciu midpointu.
26. Naprawić błąd driftu osi `Y` przy przeciąganiu bocznej krawędzi outline.
27. Dodać test regresyjny dla przypadku, w którym górna i dolna krawędź mają różne długości, ale boczny drag nadal pozostaje osiowy.

### Etap 3. Badge i skalowanie proporcjonalne

28. Zlokalizować kod odpowiedzialny za pozycjonowanie badge długości w `ui/drawing_canvas.py`.
29. Zmienić pozycjonowanie badge tak, aby midpoint handle miał priorytet widoczności.
30. Dodać test lub pomocniczy kontrakt renderingu potwierdzający brak overlapu midpoint/badge.
31. Zlokalizować kod inline editora długości, który dziś zmienia tylko jedną krawędź.
32. Zastąpić lokalną edycję jednej krawędzi logiką jednolitego skalowania całego outline.
33. Przyjąć punkt `0,0` geometrii jako jedyny pivot skalowania.
34. Utrzymać po skalowaniu lewą dolną bazę referencyjną kształtu na `x:0, y:0`.
35. Skalować wszystkie wycinki dokładnie tym samym współczynnikiem co outline.
36. Dodać test dla prostokąta/kwadratu, w którym zmiana jednej długości badge skaluje wszystkie krawędzie.
37. Dodać test potwierdzający, że outline i holes zachowują wspólny współczynnik skali.
38. Dodać test potwierdzający, że pivot `0,0` pozostaje stabilny po skalowaniu.

### Etap 4. Split arkuszy i logika layoutu

39. Odtworzyć przypadek z częściowym wycinkiem w testach layoutu lub project state.
40. Zidentyfikować, czy błąd wynika z `core/layout_engine.py`, czy z późniejszego mapowania/renderingu.
41. Naprawić generowanie przedziałów dla wycinków niepokrywających całej szerokości pasa.
42. Zweryfikować, czy `split_reason == "partial_cutout_top"` nadal wystarcza, czy potrzebne są dodatkowe rozróżnienia segmentów.
43. Dodać testy regresyjne dla kilku układów wycinków z zielonymi liniami podziału opisanymi przez użytkownika.
44. Zweryfikować zgodność: layout engine, project state, canvas rendering i raport muszą pokazywać ten sam podział.
45. Przejść pełen zestaw testów związanych z layoutem, canvasem i ustawieniami.

### Etap 5. Uproszczenie menu raportów

46. Usunąć z definicji menu `Plik` akcję `Drukuj raport ciągły` w `ui/main_window.py`.
47. Usunąć z definicji menu `Plik` akcję `Drukuj raport skrócony` w `ui/main_window.py`.
48. Upewnić się, że pozostaje tylko akcja `Drukuj raport`.
49. Zaktualizować testy kontraktu UI/menu, jeśli asercje obejmują te akcje.

## Pytania otwarte i założenia robocze

### Pytanie 1. Pozycjonowanie badge względem midpointów

Użytkownik podał wymaganie funkcjonalne (`nie mogą zasłaniać`), ale nie podał jednej preferowanej strony.

Założenie robocze:

- wybierać automatycznie offset góra/dół lub lewo/prawo tak, aby priorytetem było niezachodzenie na midpoint handle.

## Rekomendacja implementacyjna

Najpierw zrobić zmiany o niskim ryzyku i wysokiej czytelności:

1. ustawienia i toolbar,
2. midpointy i usunięcie starej opcji `Środek krawędzi`,
3. skalowanie przez badge,
4. na końcu algorytm splitów arkuszy.

Powód:

- zmiany `AppSettings` i toolbaru są dobrze odizolowane,
- midpointy i badge są lokalne dla `DrawingCanvas`,
- split arkuszy ma największe ryzyko wpływu na logikę layoutu i raportowania.

## Minimalny zestaw testów regresyjnych

- `tests/test_app_settings.py`
  - nowe defaulty,
  - brak `edge_drag_mode`,
  - reset do `Domyślne`.
- `tests/test_workspace.py`
  - synchronizacja `snap_to_grid` i widoczności arkuszy.
- `tests/test_mainwindow_ui_contract.py`
  - obecność nowej akcji toolbarowej,
  - brak starego `material_button`.
- `tests/test_drawing_canvas.py`
  - brak środkowej kulki wycinka,
  - midpointy na wycinkach,
  - przesuwanie krawędzi outline bez driftu `Y`,
  - insert vertex dla wycinka,
  - skalowanie outline + wycinków przez badge,
  - brak overlapu midpoint/badge.
- `tests/test_models_and_state.py` oraz/lub `tests/test_layout_engine.py`
  - poprawne splity dla częściowych wycinków.
