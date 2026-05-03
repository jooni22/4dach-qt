# Plan cleanupu UI i usunięcia martwego kodu

## Cel

Uprościć interfejs aplikacji przez usunięcie zbędnych pozycji menu, ikon toolbaru,
opcji w ustawieniach i pól w katalogu blach, a następnie posprzątać zależny martwy
kod bez naruszania działających ścieżek roboczych użytkownika.

## Potwierdzone wymagania

### Menu `Wycinki`

- usunąć `Przesuń wycinek...`, ale zachować samą funkcję przesuwania wycięcia na canvasie,
- usunąć `Usuń wycinek`, ponieważ wystarcza ikona kosza.

### `Katalog > Blachy > Dane Blachy`

- usunąć obsługę `dachówkowa` z UI i zostawić tylko `trapezowa`,
- usunąć pola:
  - `Zapas dolny`,
  - `Zapas górny`,
  - `Długość modułu`,
  - `Cena za m2`,
  - `Cena za m2 (gr)`,
- zostawić tylko:
  - `id=nazwa`,
  - `Szerokość efektywna arkusza`,
  - `Minimalna długość arkusza`,
  - `Maksymalna długość arkusza`.

### `Ustawienia > Ustawienia aplikacji`

- usunąć całkowicie z UI:
  - `Shift: swobodny ruch bez przyciągania`,
  - `pokaż wskaźnik osi x/y`,
  - `pokazuj długość z dokładnością do 0.1 cm`,
  - `skala overlayów`,
  - `pokaż referencje X/Y podczas rysowania`,
- usunąć możliwość przełączania z UI, ale zachować docelowe zachowanie aplikacji dla:
  - `blokada osi x/y co 1 cm`,
  - `pokaż siatkę roboczą` tylko jako ikona toolbaru,
  - `pokaż łuk kąta przy aktywnym wierzchołku`,
  - `zamykaj wielokąt prawym przyciskiem myszy`,
  - `undo` z domyślną głębokością `20`.

### Toolbar

Potwierdzone do usunięcia z UI:

- `minus` / `Odejmij / Minus`,
- `module_count` / `Włącz/wyłącz pokazywanie ilości modułów`,
- `zoom_out` / `Oddal / Pomniejsz`,
- `fit_view` / `Pokaż wszystko / Dopasuj do ekranu`,
- `broom` / `Wyczyść / Usuń wszystko`,
- `select_properties` / `Właściwości / Wybierz`,
- `from_base` / `Od bazy`.

### Zakładki workspace

- usunąć zakładkę `Raport`,
- zachować generowanie i drukowanie raportu, bez przełączania aplikacji na osobną zakładkę.

## Diagnoza techniczna

Najważniejsze miejsca zmian w kodzie:

- `ui/main_window.py`
  - budowa menu `Wycinki`,
  - wiązanie toolbaru do callbacków,
  - logika specjalnego traktowania zakładki `Raport`,
  - generowanie raportu i aktywacja zakładek po wygenerowaniu HTML,
- `ui/toolbar.py`
  - definicja wszystkich ikon toolbaru,
  - obecnie część akcji jest mapowana po indeksach, co jest największym ryzykiem zmian,
- `ui/workspace.py`
  - stałe dodawanie zakładki `Raport` w `sync()`,
  - pomocnicze metody `report_tab_index()` i `is_report_tab_index()`,
- `ui/dialogs/settings_dialog.py`
  - formularz ustawień, `_load_values()`, `get_values()`, `build_settings()`,
- `core/app_settings.py`
  - domyślne wartości i odczyt legacy ustawień,
- `ui/dialogs/material_dialog.py`
  - formularze i szczegóły materiałów,
- `core/models.py`
  - model materiału i kompatybilność wczytywania starych danych,
- `ui/drawing_canvas.py`
  - nadal zużywa część ustawień i pól materiału, które po uproszczeniu UI mogą stać się martwe.

## Najważniejsze ryzyka

### 1. Toolbar jest kruchy przez mapowanie po indeksach

Obecnie nazwane akcje są pobierane z `_toolbar_actions` po pozycjach, np.:

- `action_trash = self._toolbar_actions[9][0]`,
- `action_module_count = self._toolbar_actions[10][0]`,
- trailing actions są pobierane przez `self._toolbar_actions[-6:]`.

To oznacza, że zwykłe usunięcie ikon bez wcześniejszego ustabilizowania mapowania
może przepiąć złe akcje do złych callbacków.

### 2. `module_count` i `from_base` nie są dziś tylko dekoracją

- `module_count` ma aktywną logikę w `ui/main_window.py`, `ui/workspace.py`, `ui/drawing_canvas.py` i testach,
- `from_base` ma aktywną logikę w `ui/main_window.py`.

Usunięcie samych ikon jest proste, ale pełne usunięcie martwego kodu wymaga drugiego przejścia.

### 3. `Raport` jest dziś elementem kontraktu UI

- `ui/workspace.py` zawsze dodaje zakładkę `Raport`,
- `ui/main_window.py` ma kilka strażników specjalnie dla tej zakładki,
- `tests/test_mainwindow_ui_contract.py` zakłada, że `Raport` istnieje i jest ostatnią kartą.

Usunięcie tej zakładki wymaga spójnej zmiany workspace, main window i testów.

### 4. Uproszczenie UI materiałów nie jest równoznaczne z usunięciem pól z modelu

`module_length_cm` jest dziś używane w `ui/drawing_canvas.py`, więc pełne usunięcie z modelu
materiału w pierwszym kroku byłoby ryzykowne. Bezpieczniej najpierw usunąć pola z UI,
zostawiając kompatybilny model i odczyt danych.

## Zakres prac

### In

- `ui/main_window.py`
- `ui/toolbar.py`
- `ui/workspace.py`
- `ui/dialogs/settings_dialog.py`
- `core/app_settings.py`
- `ui/dialogs/material_dialog.py`
- aktualizacja testów UI, settingsów, workspace i canvasu
- sweep martwego kodu po uproszczeniach

### Out

- przebudowa silnika raportowania i drukowania raportu,
- szerokie zmiany w geometrii/layout engine,
- pochopne usuwanie pól z modelu materiałów, jeśli nadal są używane runtime,
- migracje danych wykraczające poza bezpieczny odczyt legacy kluczy.

## Plan implementacji

1. Ustabilizować budowę toolbaru w `ui/toolbar.py`, tak aby akcje były przypinane po stabilnych nazwach, a nie po indeksach.
2. Usunąć z `ui/main_window.py` pozycje `Przesuń wycinek...` i `Usuń wycinek` z menu `Wycinki`, bez ruszania działających callbacków canvasu.
3. Usunąć z `ui/toolbar.py` ikony `minus`, `zoom_out`, `fit_view`, `broom`, `select_properties`, które dziś wyglądają na czysto UI-owe.
4. Usunąć z toolbaru także `module_count` i `from_base`, ale na tym etapie zostawić ich logikę runtime do drugiego przeglądu.
5. Uprościć `ui/dialogs/material_dialog.py`, aby formularz i widok szczegółów obsługiwały tylko `trapezowa` i tylko cztery pola biznesowe.
6. Zachować kompatybilny odczyt materiałów w `core/models.py`, ale przestać eksponować usunięte pola w UI.
7. Uprościć `ui/dialogs/settings_dialog.py` przez usunięcie wskazanych kontrolek i przez wymuszenie docelowych zachowań zamiast przełączników.
8. Zaktualizować `core/app_settings.py`, ustawiając docelowe defaulty: `orthogonal_lock`, `show_angle_arc=True`, `close_on_rmb=True`, `undo_stack_depth=20`, oraz pozostawić bezpieczny odczyt legacy konfiguracji.
9. Usunąć zakładkę `Raport` z `ui/workspace.py` i przepisać `ui/main_window.py`, aby generowanie raportu nie zależało od aktywacji osobnej karty.
10. Zaktualizować testy kontraktowe i regresyjne, zwłaszcza `tests/test_mainwindow_ui_contract.py`, `tests/test_app_settings.py`, `tests/test_workspace.py` i odpowiednie testy canvasu.
11. Wykonać drugi sweep martwego kodu po zmianach UI i testów, usuwając nieużywane callbacki, flagi settingsów, ścieżki `module_count`, `from_base` i inne osierocone gałęzie.

## Kolejność wdrożenia

### Faza 1. Niskie ryzyko

- zapisać i ustabilizować toolbar,
- usunąć pozycje z menu `Wycinki`,
- usunąć proste ikony toolbaru bez aktywnej logiki,
- uprościć `Dane Blachy`,
- uprościć `Ustawienia aplikacji`.

### Faza 2. Średnie ryzyko

- zmienić `AppSettings` i kompatybilność odczytu,
- usunąć zakładkę `Raport`,
- przepisać przepływ raportowania w `main_window`.

### Faza 3. Sweep końcowy

- przejrzeć `module_count`, `from_base`, stare flagi settingsów i osierocone testy,
- usunąć martwy kod dopiero po przejściu testów po zmianach UI.

## Testy do aktualizacji lub dodania

- testy menu w `tests/test_mainwindow_ui_contract.py` dla nowego menu `Wycinki`,
- testy toolbaru dla nowego zestawu akcji i stabilnego mapowania bez zależności od indeksów,
- testy workspace i `main_window` po usunięciu zakładki `Raport`,
- testy settingsów dla nowych defaultów i uproszczonego dialogu,
- testy wczytywania legacy configów w `tests/test_app_settings.py`,
- testy materiałów dla formularza tylko `trapezowa`,
- testy canvasu, jeśli po zmianach settingsów lub materiałów powstaną nowe stałe ścieżki zachowania.

## Kryteria akceptacji

- menu `Wycinki` nie zawiera `Przesuń wycinek...` ani `Usuń wycinek`,
- toolbar nie zawiera potwierdzonych ikon do usunięcia,
- zakładka `Raport` nie istnieje, ale generowanie i drukowanie raportu nadal działają,
- `Dane Blachy` obsługuje tylko `trapezowa` i uproszczony zestaw pól,
- `Ustawienia aplikacji` nie pokazują usuniętych opcji i wymuszają docelowe zachowania produktu,
- stare konfiguracje i stare materiały nadal dają się bezpiecznie wczytać,
- testy UI i settingsów przechodzą po aktualizacji,
- po drugim sweepie nie zostaje martwy kod po usuniętych ikonach, zakładce i opcjach.

## Uwagi wdrożeniowe

- Najpierw usuwać elementy z UI i testów, a dopiero później ścinać logikę, która może być jeszcze potrzebna do kompatybilności.
- Nie łączyć w jednym kroku uproszczenia UI materiałów z agresywną zmianą modelu domenowego materiałów.
- Przy usuwaniu `Raport` trzeba zachować `self._latest_report_html` i ścieżkę drukowania raportu.
- Przy usuwaniu ikon z toolbaru trzeba pilnować, aby żadna akcja nie zmieniła znaczenia przez przesunięcie indeksów.
