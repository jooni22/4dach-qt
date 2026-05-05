# Plan implementacji fazy 2 — pełny rollout `AddPolacDialog`

## Cel
Rozszerzyć `AddPolacDialog` z MVP do pełnego kreatora docelowego: galeria `9` kształtów połaci, galeria `3` typów wycinka, osobny cache wizarda w `config.json` oraz zastąpienie starych akcji `Prostokąt...`, `Trójkąt...`, `Trapez...` w menu `Kształt`.

## Założenie wejściowe
Faza 2 zakłada, że faza 1 została już wdrożona i działa:
- istnieje `AddPolacDialog`,
- dialog jest spięty z `MainWindow`,
- kreator działa na aktywnej połaci,
- operacja obrys + wycinek jest atomowa dla undo/redo.

## Decyzje docelowe fazy 2
- `Kreator połaci...` staje się głównym entrypointem menu `Kształt`.
- Z menu `Kształt` usunąć akcje `Prostokąt...`, `Trójkąt...`, `Trapez...`.
- Stare klasy dialogowe mogą tymczasowo zostać w kodzie, ale nie mają już być odsłaniane użytkownikowi w menu.
- Dodać nowy top-level cache `config["add_polac_dialog"]`.
- Nie migrować starego `config["ksztalty"]` do nowego formatu. Legacy klucz zostaje tylko jako źródło seedowania początkowych wartości dla kształtów MVP.

## Docelowy katalog kształtów
Pełna galeria ma zawierać dokładnie te identyfikatory:
- `prostokat`
- `trojkat`
- `trapez_row`
- `trapez_prl`
- `trapez_l`
- `trapez6`
- `trapez7`
- `pieciokat`
- `pieciokat2`

Każdy kafel ma mieć:
- `shape_id`,
- etykietę użytkową,
- znormalizowany kontur do preview,
- schemat pól formularza,
- funkcję budowy `Polygon2D`.

## Docelowy katalog wycinków
Krok 2 ma zawierać dokładnie:
- `none`
- `lukarna1`
- `lukarna2`
- `lukarna3`

Schemat pól:
- `none`: bez formularza,
- `lukarna1`: `A`, `H1`,
- `lukarna2`: `A`, `H`,
- `lukarna3`: `A`, `H1`, `H`.

Wycinek ma być osadzany centralnie względem `outline.bounds()` i walidowany przez istniejącą walidację wycinków.

## Format nowego cache w `config.json`
Wprowadzić nowy klucz:

```json
{
  "add_polac_dialog": {
    "last_shape": "prostokat",
    "last_cutout": "none",
    "flip_h": false,
    "flip_v": false,
    "shapes": {
      "prostokat": {"A": 800, "B": 300},
      "trojkat": {"A": 800, "B": 300},
      "trapez_row": {"A": 800, "C": 500, "B": 300},
      "trapez_prl": {"A": 800, "C": 500, "B": 300},
      "trapez_l": {"A": 800, "C": 500, "B": 300},
      "trapez6": {"A": 800, "C": 500, "B": 300},
      "trapez7": {"A": 800, "C": 500, "B": 300},
      "pieciokat": {"A": 800, "B": 300},
      "pieciokat2": {"A": 800, "B": 300}
    },
    "cutouts": {
      "lukarna1": {"A": 80, "H1": 60},
      "lukarna2": {"A": 80, "H": 60},
      "lukarna3": {"A": 80, "H1": 60, "H": 60}
    }
  }
}
```

## Zasady kompatybilności config
- Przy pierwszym otwarciu wizarda:
  - jeśli istnieje `config["add_polac_dialog"]`, użyć go wprost,
  - jeśli nie istnieje, zseedować `prostokat`, `trojkat`, `trapez_row` z obecnego `config["ksztalty"]`,
  - brakujące shape/cache wypełnić wartościami domyślnymi.
- Po wdrożeniu fazy 2 zapisywać stan wizarda wyłącznie do `config["add_polac_dialog"]`.
- Nie nadpisywać już `config["ksztalty"]` przy użyciu nowego wizarda.

## Zmiany implementacyjne

### 1. Rozdzielenie katalogów od widoku
- Wydzielić dane galerii i schematy formularzy do pomocniczego modułu przy wizardzie, np. `ui/dialogs/add_polac_catalog.py`.
- Trzymać tam:
  - definicje shape tiles,
  - definicje cutout tiles,
  - domyślne wartości formularzy,
  - znormalizowane kontury do preview.
- Sam `AddPolacDialog` ma odpowiadać za UI i nawigację, nie za opis katalogu danych.

### 2. Rozszerzenie `AddPolacDialog`
- Rozszerzyć galerię do `9` kształtów i `3` typów wycinka.
- Utrzymać dwa kroki dialogu z `QStackedWidget`.
- Dla wszystkich nowych shape/cutout entries preview ma działać bez dodatkowych decyzji implementacyjnych.
- `Flip H` i `Flip V` pozostają globalne dla wybranego kształtu.
- Krok 2 ma dostać preview aktualnego obrysu po flipach, nie surowego konturu przed transformacją.

### 3. Budowa geometrii
- `prostokat` i `trojkat` budować bezpośrednio z pól `A`, `B`.
- `trapez_*` budować z pól `A`, `C`, `B`, zgodnie z definicją konkretnego szablonu.
- `pieciokat*` budować z pól `A`, `B` przez skalowanie znormalizowanego konturu.
- Flipy stosować na końcowej liście punktów obrysu przed budową `Polygon2D`.
- `lukarna1`, `lukarna2`, `lukarna3` budować jako `Polygon2D` wycinka względem środka bounding boxa połaci.

### 4. Integracja z `MainWindow`
- Zostawić `Dowolny` i istniejące ręczne wycinki w obecnym miejscu.
- Usunąć tylko trzy stare shape-entrypointy z menu `Kształt`.
- `MainWindow` dalej ma zapisywać geometrię przez jedną komendę `_edit(...)`.
- Nie zmieniać workflow pustych zakładek połaci ani toolbarowego `Nowa połać`.

## Testy
- Rozszerzyć testy dialogu o pełną galerię `9` i `3`.
- Dodać testy cache `config["add_polac_dialog"]`:
  - odczyt istniejącego cache,
  - seed z legacy `config["ksztalty"]`,
  - zapis nowych wartości po akceptacji.
- Rozszerzyć `tests/test_mainwindow_ui_contract.py`:
  - brak akcji `Prostokąt...`, `Trójkąt...`, `Trapez...` w menu `Kształt`,
  - obecność `Kreator połaci...`,
  - poprawne budowanie nowych kształtów i wycinków,
  - brak regresji `Dowolny` i `Wycinki`.
- Dodać test round-trip `load_config/save_config`, który potwierdza, że nowy klucz `add_polac_dialog` przechodzi przez persistence bez mutacji.

## Kryteria akceptacji
- Menu `Kształt` używa już wyłącznie `Kreator połaci...` i `Dowolny`.
- Wizard obsługuje pełny katalog `9` kształtów i `3` wycinków.
- Stan wizarda jest pamiętany w `config["add_polac_dialog"]`.
- Dla brakującego nowego cache kreator seeduje wartości z `config["ksztalty"]` tylko raz, jako fallback kompatybilności.
- `uv run pytest` przechodzi po wdrożeniu.

## Poza zakresem fazy 2
- Usuwanie legacy klas dialogowych z kodu źródłowego.
- Zmiana semantyki `Plik > Nowa połać` i toolbarowego `Nowa połać`.
- Refaktor `ProjectState`, `WorkspaceController` albo `DrawingCanvas` niezwiązany bezpośrednio z wizardem.
