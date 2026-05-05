# Faza 1 `AddPolacDialog` — repo-true MVP z baseline repo

## Cel
Wdrożyć mały, wdrażalny wizard `AddPolacDialog` jako nowy entrypoint w menu `Kształt`, bez naruszania obecnych dialogów `Prostokąt...`, `Trójkąt...`, `Trapez...`, `Dowolny` i menu `Wycinki`. Faza 1 ma być zgodna z aktualnym repo, a nie z hipotetycznym API z `docs/plan_ksztalt-wycinek-v2.md`.

## Stan repo będący źródłem prawdy
- `ProjectState.set_roof_plane_geometry(...)` już potrafi zapisać obrys i listę wycinków atomowo.
- `MainWindow` obsługuje shape-dialogi i undo/redo przez jedną komendę `_edit(...)`.
- `config["ksztalty"]` jest istniejącym cache dla trzech legacy flow i pozostaje jedynym miejscem pamiętania ich wartości między sesjami.
- Repo-root `config.json` jest fixture danych aplikacji i testów, więc jego przywrócenie należy do zakresu fazy 1.

## Zakres MVP

### Krok 1 — obrys połaci
- Obsługiwane są dokładnie trzy flow:
  - `prostokat`: `szerokosc`, `wysokosc`
  - `trojkat`: `typ`, `podstawa`, `wysokosc`, opcjonalne `ramie`
  - `trapez`: `typ`, `podstawa_dolna`, `podstawa_gorna`, `wysokosc`
- Wynik dialogu jest lokalnym `@dataclass(slots=True)` w `ui/dialogs/add_polac_dialog.py`.
- Nie ma żadnych zmian w `core.models`.
- `Flip H` i `Flip V` są niezależne i działają na gotowej geometrii obrysu przez lokalny pure helper oparty o `Polygon2D.bounds()`.

### Krok 2 — wycinek
- Obsługiwane są tylko opcje:
  - `Bez wycinka`
  - `Wycinek prostokątny`
- Dla wycinka prostokątnego dostępne są wyłącznie pola `szerokosc` i `wysokosc`.
- Obowiązuje decyzja `repo-true`: wizard nie dodaje własnej walidacji containment ponad to, co już robi `ProjectState`.

## Integracja
- `AddPolacDialog` jest eksportowany przez `ui.dialogs`.
- W `ui/main_window.py` dochodzi:
  - akcja `Kreator połaci...` jako pierwszy wpis menu `Kształt`
  - metoda `MainWindow._dlg_add_polac()`
- `_dlg_add_polac()` wykonuje jedną komendę `_edit(...)`:
  - jeśli aktywna połać istnieje, ustawia jej obrys i opcjonalny wycinek przez `set_roof_plane_geometry(...)`
  - jeśli aktywnej połaci nie ma, w tej samej komendzie tworzy nową połacię, a następnie ustawia jej pełną geometrię
- Nie ma integracji przez `add_roof_plane(RoofPlane)` ani dodawania nowych metod do domeny tylko pod ten wizard.

## Cache i trwałość
- Do `config["ksztalty"]` trafiają wyłącznie legacy shape-value dla:
  - `prostokat`
  - `trojkat`
  - `trapez`
- Nie dodajemy kluczy wizard-only.
- Nie persystujemy między sesjami:
  - wyboru kroku wycinka
  - stanu `Flip H`
  - stanu `Flip V`

## Baseline repo
- `config.json` w root repo jest częścią tej fazy i musi wrócić do używalnego stanu testowego.
- Baseline powinien zawierać:
  - `company_data.name = "Super Dach Bis Jerzy Zimnoch"`
  - materiał `PD510`
  - `project_state` zgodny z aktualnym loaderem
  - taką liczbę startowych połaci, by kontrakt startowy `MainWindow` i testy działały po świeżym starcie

## Testy akceptacyjne
- Nowy plik `tests/test_add_polac_dialog.py` pokrywa:
  - wybór kafla i odbudowę formularza
  - mapowanie legacy pól dla trójkąta i trapezu
  - niezależność `Flip H` i `Flip V`
  - przejście krok 1 → krok 2
  - `get_result()` dla `none` i `rectangle`
  - anulowanie bez wyniku
- `tests/test_mainwindow_ui_contract.py` pokrywa:
  - obecność `Kreator połaci...` w menu `Kształt`
  - brak regresji starych `Prostokąt...`, `Trójkąt...`, `Trapez...`, `Dowolny` i menu `Wycinki`
  - ustawienie geometrii aktywnej pustej połaci bez tworzenia nowej zakładki
  - utworzenie nowej połaci, gdy aktywnej nie ma
  - zapis obrys + wycinek jako jeden wpis undo/redo
- Zielony baseline tej fazy:
  - `uv run pytest tests/test_add_polac_dialog.py -q`
  - `uv run pytest tests/test_mainwindow_ui_contract.py -q`
  - `uv run pytest tests/test_models_and_state.py -q`
  - `uv run pytest`

## Poza zakresem fazy 1
- `9` kształtów połaci z planu `v2`
- `3` typy wycinków z planu `v2`
- nowe typy publiczne w domenie
- nowy top-level cache wizarda
- zmiana semantyki toolbaru, `Plik > Nowa połać`, `Dowolny` albo ręcznych wycinków
