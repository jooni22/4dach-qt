# Plan implementacji GUI – rysowanie, obliczenia i raporty w 4Dach

Implementacja kodu UI w PySide6, który spięty z istniejącą warstwą `core/` pozwoli użytkownikowi rysować połacie 2D, generować pokrycie blachą (pasy/arkusze), przeglądać wynik na canvasie i wyświetlać raport końcowy z BOM.

---

## Stan obecny (co już działa)

- `mainwindow.py` – menu, toolbar, zakładki `workspace_tabs`, `DrawingCanvas`, `QTextBrowser` raportu.
- `dialogs.py` – dialogi kształtów, blach, danych firmy.
- `core/models.py`, `geometry.py`, `layout_engine.py`, `project_state.py`, `reporting.py` – pełny model domenowy, silnik geometrii i rozkroju.
- `tests/` – testy jednostkowe geometrii i kontraktowe UI.

## Co jeszcze brakuje w UI

1. **Canvas nie rysuje wygenerowanych arkuszy** – widzi tylko obrys i wycinki.
2. **Brak trybów edycji** – użytkownik nie może przesuwać punktów obrysu ani zaznaczać arkuszy myszką.
3. **Callbacki generowania layoutu są puste** – `Arkusze → Przelicz aktywną połać` (F5) i toolbar „Nakładanie blachy” nic nie robią.
4. **Raport w `QTextBrowser` jest tekstowo-HTML bez graficznego rzutu** – brak wizualizacji arkuszy w eksporcie.
5. **Brak ręcznej korekty arkuszy w canvasie** – menu `Dodaj arkusz / Usuń arkusz` nie ma implementacji.
6. **Toolbar przełączniki `Od prawej` / `Od bazy`** nie wpływają na `GenerationSettings`.

---

## Faza 1 – Canvas: obrys + arkusze + moduły

### Task 1.1 – Wydzielić mapper `CanvasCoordinateMapper`
- **Plik:** `mainwindow.py` (lub nowy `core/canvas_mapper.py`)
- **Zmiana:** Przenieść logikę skalowania cm↔px z `_draw_roof_plane` do osobnej klasy `CanvasCoordinateMapper(bounds, canvas_rect)`.
- **Cel:** Wielokrotne użycie w rysowaniu obrysu, arkuszy, punktów edycji i później w raporcie SVG.

### Task 1.2 – Rozszerzyć `DrawingCanvas._draw_roof_plane` o arkusze
- **Plik:** `mainwindow.py`
- **Zmiana:** Po narysowaniu obrysu i wycinków iterować po `plane.auto_sheet_placements + plane.manual_sheet_placements`.
  - Rysować każdy arkusz jako prostokąt (`QRectF`) w kolorze wypełnienia zależnym od `source` (auto/manual).
  - Dla `material.type == "dachówkowa"` i `module_length_cm > 0` rysować linie poziome co moduł.
  - Wyświetlać etykietę z `final_length_cm` w środku arkusza (opcjonalnie liczbę modułów).
- **Cel:** Użytkownik widzi pasy pokrycia natychmiast po generacji.

### Task 1.3 – Uchwyty wierzchołków obrysu
- **Plik:** `mainwindow.py`
- **Zmiana:** W `_draw_roof_plane` po narysowaniu obrysu narysować małe kwadraty/kółka w każdym wierzchołku `outline.points`.
- **Cel:** Wizualna podstawa pod późniejszą edycję punktów.

### Task 1.4 – Tryb edycji w `DrawingCanvas`
- **Plik:** `mainwindow.py`
- **Zmiana:** Dodać enum `CanvasMode { VIEW, DRAW_OUTLINE, DRAW_HOLE, EDIT_POINTS, MOVE_PLANE, SELECT_SHEET }` oraz setter `set_mode()`.
- **Zmiana:** W zależności od trybu zmienić kursor i obsługę `mousePressEvent` (zamiast bezwarunkowego `user_points.append`).
- **Cel:** Oddzielenie oglądania od edycji – zgodnie z `DOC/plan-logiki-i-testow.md` sekcja 4.4.

---

## Faza 2 – Generowanie pokrycia i reakcja UI

### Task 2.1 – Implementacja `MainWindow._open_recalculate_active_plane`
- **Plik:** `mainwindow.py`
- **Zmiana:**
  1. Pobrać aktywną połać i materiał (`project_state.active_roof_plane()`, `material_by_id`).
  2. Wywołać `project_state.generate_layout_for_active_plane()`.
  3. Jeśli `LayoutResult.warnings` niepuste – `QMessageBox.warning` z listą.
  4. Wywołać `build_report()` + `build_report_html()` i zapisać w `self._latest_report_*`.
  5. Odświeżyć `primary_canvas.update()` oraz `_refresh_report_view()`.
- **Cel:** Menu `Arkusze → Przelicz aktywną połać` (F5) działa end-to-end.

### Task 2.2 – Toolbar „Nakładanie blachy na powierzchnie” jako trigger generacji
- **Plik:** `mainwindow.py`
- **Zmiana:** Połączyć akcję toolbaru (ikona dokumentu z czerwoną warstwą) z `_open_recalculate_active_plane`.
- **Cel:** Zgodność z UI opisanym w `DOC/ui-info.md`.

### Task 2.3 – Podłączyć `Od prawej` i `Od bazy`
- **Plik:** `mainwindow.py`
- **Zmiana:**
  - `Od prawej` – toggle `QAction.setCheckable(True)`; przy zmianie ustawiać `plane.generation_settings.layout_origin = "right"/"left"` i oznaczać layout jako dirty.
  - `Od bazy` – toggle; przy zmianie ustawiać `base_line_y_cm` na `bounds.max_y` (auto) lub `None` (wyłączone) i dirty.
- **Cel:** Użytkownik może sterować kierunkiem pasów i linią bazową modułów.

### Task 2.4 – Wizualna sygnalizacja stanu „nieaktualny layout”
- **Plik:** `mainwindow.py`
- **Zmiana:** Gdy `plane.layout_dirty_reason` nie jest `None`, zmienić tekst zakładki połaci (np. dodając `*`) lub pokazać ikonę/tekst w status barze.
- **Cel:** Użytkownik widzi, że po zmianie geometrii lub materiału wynik wymaga przeliczenia.

---

## Faza 3 – Raporty i ręczna korekta arkuszy

### Task 3.1 – Graficzny rzut połaci w eksporcie raportu HTML
- **Plik:** `core/reporting.py`
- **Zmiana:** W `build_report_html` wygenerować inline SVG z:
  - obrysem połaci,
  - wycinkami (przerywana linia),
  - arkuszami (pasy z etykietami długości).
- **Wymagane:** Użycie `CanvasCoordinateMapper` (lub analogicznej funkcji) do transformacji cm→px w SVG.
- **Cel:** Raport HTML zgodny z opisem w `DOC/ui-info.md`: „graficzny rzut zaprojektowanej połaci z naniesionym podziałem na arkusze”.

### Task 3.2 – Callbacki menu Plik → Drukuj raport / raport ciągły / skrócony
- **Plik:** `mainwindow.py`
- **Zmiana:**
  - `_open_standard_report_preview` – wygenerować pełny HTML (`build_report_html(include_bom=True)`), zapisać do temp, otworzyć w przeglądarce (`QDesktopServices.openUrl`).
  - `_open_continuous_report_preview` – raport ze wszystkimi połaciami połączonymi w jeden HTML.
  - `_open_short_report_preview` – raport bez BOM (lub ze skróconym), zgodnie z `DOC/ui-info.md`.
- **Cel:** Menu `Plik → Drukuj raport*` działa i produkuje pliki HTML.

### Task 3.3 – Tryb zaznaczania i ręczna edycja arkuszy na canvasie
- **Plik:** `mainwindow.py`
- **Zmiana:**
  - W trybie `SELECT_SHEET` (`mousePressEvent`) wykrywać kliknięcie w prostokąt arkusza (hit-test po `x_left_cm`, `x_right_cm`, `y_top_cm`, `y_bottom_cm`).
  - Zaznaczony arkusz podświetlić (grubsza obwódka, inny kolor).
  - Przekazać `selected_sheet_id` do `MainWindow`, żeby menu `Usuń arkusz` (Delete) wiedziało co usuwać.
- **Cel:** Podstawa pod ręczne poprawki bez opuszczania canvasu.

### Task 3.4 – Dialogi obsługi arkuszy
- **Plik:** `dialogs.py` + `mainwindow.py`
- **Zmiana:**
  - `Podgląd arkuszy` (`Ctrl+A`) – nowy dialog z tabelą: pas, x-left, x-right, długość surowa, długość finalna, źródło (auto/manual).
  - `Aktywne arkusze` – lista z checkboxami do chwilowego ukrywania (opcjonalnie, może być wersja uproszczona).
  - `Dodaj arkusz` – dialog z polami: pas, szerokość, długość, pozycja Y; walidacja min/max z materiału.
- **Zmiana w `MainWindow`:** `_open_add_sheet_dialog`, `_open_remove_sheet_dialog`, `_open_sheet_preview_dialog` muszą wywoływać odpowiednie metody `ProjectState` (`add_manual_sheet_placement`, `remove_sheet_placement`) i odświeżać canvas.
- **Cel:** Pełna obsługa menu `Arkusze` zgodnie z `DOC/ui-info.md`.

### Task 3.5 – Rysowanie „siatki” i „ilości modułów”
- **Plik:** `mainwindow.py`
- **Zmiana:**
  - Toolbar `Siatka` – toggle rysowania siatki pomocniczej na canvasie (co 50/100 cm).
  - Toolbar `Włącz/wyłącz pokazywanie ilości modułów` – toggle wyświetlania liczby modułów na arkuszach zamiast tylko długości.
- **Cel:** Zgodność z toolbarem opisanym w `DOC/ui-info.md`.

---

## Kolejność i zależności

| Kolejność | Task | Zależy od |
|-----------|------|-----------|
| 1 | 1.1 Mapper | – |
| 2 | 1.2 Arkusze na canvasie | 1.1 |
| 3 | 1.3 Uchwyty wierzchołków | 1.1 |
| 4 | 1.4 Tryby canvasa | 1.3 |
| 5 | 2.1 Przelicz aktywną połać | 1.2 |
| 6 | 2.2 Toolbar nakładanie | 2.1 |
| 7 | 2.3 Od prawej / Od bazy | 2.1 |
| 8 | 2.4 Sygnalizacja dirty | 2.1 |
| 9 | 3.1 SVG w raporcie | 1.1, 1.2 |
| 10 | 3.2 Drukuj raport | 3.1 |
| 11 | 3.3 Zaznaczanie arkuszy | 1.2, 1.4 |
| 12 | 3.4 Dialogi arkuszy | 3.3 |
| 13 | 3.5 Siatka / moduły | 1.2 |

---

## Testy do dodania / zaktualizowania

- `tests/test_mainwindow_ui_contract.py` – dodać asercje na obecność akcji toolbaru (`Od prawej`, `Od bazy`, `Nakładanie blachy`) i ich checkable state.
- `tests/test_canvas_rendering.py` (nowy plik) – test jednostkowy `DrawingCanvas` z mockiem `QPainter` sprawdzający, że dla połaci z 3 arkuszami wywołane jest `drawRect` ≥ 3 razy.
- `tests/test_report_html.py` – test sprawdzający, że `build_report_html` zawiera `<svg>` i elementy `<rect>` dla arkuszy.
- `tests/test_models_and_state.py` – rozszerzyć o test ręcznego dodawania/usuwania arkusza przez `ProjectState` z weryfikacją dirty state.

---

## Minimalny zakres MVP (jeśli trzeba skrócić)

Jeśli priorytetem jest pokazanie działania aplikacji end-to-end, wystarczy zaimplementować:
1. **Task 1.1 + 1.2** – canvas rysuje arkusze.
2. **Task 2.1** – F5 generuje pokrycie i odświeża canvas.
3. **Task 3.1 + 3.2** – raport HTML z graficznym rzutem otwierany w przeglądarce.

Reszta (tryby edycji, ręczne poprawki, siatka) to faza 2.
