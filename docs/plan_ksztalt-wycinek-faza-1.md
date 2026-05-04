# Plan implementacji fazy 1 — `AddPolacDialog` MVP

## Cel
Wprowadzić nowy, dwuetapowy kreator `AddPolacDialog` jako dodatkowy entrypoint w menu `Kształt`, bez usuwania obecnych dialogów `Prostokąt...`, `Trójkąt...`, `Trapez...`. Faza 1 ma dać stabilny MVP, który da się wdrożyć i przetestować bez przebudowy architektury repo.

## Stan wyjściowy repo
- `Plik > Nowa połać` oraz toolbarowe `Nowa połać` tworzą pustą zakładkę połaci.
- Menu `Kształt` ustawia geometrię aktywnej połaci przez `_dlg_prostokat`, `_dlg_trojkat`, `_dlg_trapez`, albo tworzy pierwszą połacię, jeśli żadna jeszcze nie istnieje.
- Cache formularzy shape-dialogów jest dziś trzymany w `config["ksztalty"]`.
- `ProjectState.set_roof_plane_geometry(...)` już istnieje i pozwala zapisać obrys i listę wycinków atomowo.

## Zakres funkcjonalny fazy 1
- Dodać akcję `Kreator połaci...` jako pierwszy wpis menu `Kształt`.
- Zachować stare trzy akcje shape-dialogów bez zmian.
- Kreator ma działać na aktywnej połaci. Jeśli aktywnej połaci nie ma, ma utworzyć pierwszą połacię dokładnie tak jak obecne `_dlg_*`.
- Krok 1 kreatora:
  - wybór jednego z trzech kształtów: `prostokąt`, `trójkąt`, `trapez`,
  - dynamiczny formularz zgodny z obecnymi dialogami,
  - podgląd kształtu,
  - dwa niezależne przełączniki `Flip H` i `Flip V`.
- Krok 2 kreatora:
  - wybór `Bez wycinka` albo `Wycinek prostokątny`,
  - dla wycinka pola `szerokość` i `wysokość`,
  - podgląd obrysu z opcjonalnym wycinkiem.
- Zatwierdzenie ma zapisać obrys i opcjonalny wycinek jako jedną operację undo/redo.

## Decyzje architektoniczne
- Nie dodawać nowych typów do `core.models`. Wynik kreatora ma być lokalnym `@dataclass(slots=True)` w `ui/dialogs/add_polac_dialog.py`.
- Nie przenosić logiki generowania domenowego `Polygon2D` do widoku. Dialog zwraca wynik wejściowy, a integracja buduje geometrię przed zapisem do `ProjectState`.
- Nie zmieniać semantyki `Plik > Nowa połać`, toolbarowego `Nowa połać`, `Dowolny`, ani menu `Wycinki`.
- Nie robić migracji `config.json`. W fazie 1 utrzymać istniejące `config["ksztalty"]`.
- W fazie 1 nie persystować między sesjami stanu `Flip H`, `Flip V` ani formularza wycinka. Te wartości mają być sesyjne.

## Zmiany implementacyjne

### 1. Nowy dialog
- Dodać `ui/dialogs/add_polac_dialog.py`.
- W pliku umieścić:
  - lokalny `AddPolacResult`,
  - katalog trzech kształtów MVP,
  - widget galerii kształtów,
  - widget preview,
  - dynamiczny formularz wymiarów,
  - krok wycinka z opcją `none` / `rectangle`,
  - `get_result() -> AddPolacResult | None`.
- Preview ma używać `QPainter` tylko w `paintEvent`, a miniatury mogą być renderowane do `QPixmap`.

### 2. Integracja z menu i `MainWindow`
- Dodać eksport `AddPolacDialog` do `ui/dialogs/__init__.py`.
- W `ui/main_window.py`:
  - dodać import `AddPolacDialog`,
  - dodać nową akcję `Kreator połaci...` w menu `Kształt`,
  - dodać metodę `_dlg_add_polac()`.
- `_dlg_add_polac()` ma:
  - otworzyć dialog,
  - zbudować `Polygon2D` dla wybranego kształtu,
  - zastosować flipy na poziomie punktów,
  - opcjonalnie zbudować centralnie osadzony prostokątny wycinek,
  - zapisać wynik przez jedną komendę `_edit(...)`.
- Jeśli aktywna połać istnieje, kreator ma użyć `ProjectState.set_roof_plane_geometry(...)`.
- Jeśli aktywnej połaci nie ma, kreator ma utworzyć nową połacię z obrysem i ewentualnym wycinkiem w tej samej komendzie `_edit(...)`.

### 3. Reuse istniejących helperów
- Reuse `make_rectangle`, `make_triangle`, `make_trapezoid` z `core.geometry`.
- Reuse wzorca helperów z `ui/main_window_dialogs.py`; tam można dodać małe funkcje pomocnicze dla budowy geometrii kreatora.
- Nie dodawać nowych metod do `ProjectState`, jeśli obecne `add_roof_plane(...)`, `set_roof_plane_geometry(...)` i walidacja wycinków wystarczą.

### 4. Cache formularzy
- Dla `prostokąt`, `trójkąt`, `trapez` zapisywać tylko dane zgodne z obecnym legacy formatem `config["ksztalty"]`.
- Dla `trójkąt` zachować pola `typ`, `podstawa`, `wysokość`, `ramię`, `ramie_enabled`.
- Dla `trapez` zachować pola `typ`, `podstawa_dolna`, `podstawa_górna`, `wysokość`.
- Nie dokładać do `config["ksztalty"]` nowych kluczy wizard-only.

## Testy
- Dodać nowy plik testów dialogu, np. `tests/test_add_polac_dialog.py`.
- Pokryć:
  - zmianę wybranego kafla i odbudowę formularza,
  - niezależność `Flip H` i `Flip V`,
  - przejście z kroku 1 do kroku 2,
  - payload z `get_result()`,
  - anulowanie bez wyniku.
- Rozszerzyć `tests/test_mainwindow_ui_contract.py` o:
  - obecność akcji `Kreator połaci...` w menu `Kształt`,
  - ustawienie geometrii aktywnej pustej połaci bez tworzenia dodatkowej zakładki,
  - utworzenie pierwszej połaci, jeśli żadna nie istnieje,
  - dodanie prostokątnego wycinka,
  - jeden wpis undo/redo dla całej operacji,
  - brak regresji starych `_dlg_prostokat`, `_dlg_trojkat`, `_dlg_trapez`.

## Kryteria akceptacji
- Menu `Kształt` zawiera nową akcję `Kreator połaci...`, a stare akcje nadal działają.
- Kreator potrafi ustawić obrys aktywnej połaci dla trzech shape-flow legacy.
- Kreator potrafi opcjonalnie dodać prostokątny wycinek w tej samej operacji zapisu.
- Cofnięcie jednej komendy usuwa jednocześnie obrys i dodany przez kreator wycinek.
- `uv run pytest` przechodzi po wdrożeniu.

## Poza zakresem fazy 1
- Pełna galeria `9` kształtów.
- Pełna galeria `3` typów wycinka.
- Nowy top-level cache wizarda w `config.json`.
- Usuwanie starych akcji `Prostokąt...`, `Trójkąt...`, `Trapez...`.
