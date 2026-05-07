# Project Management Redesign Plan

## Cel

Przebudować przepływ tworzenia, otwierania, zapisywania i edycji projektów tak, aby:

1. startup panel działał przewidywalnie,
2. `Cancel` nie uruchamiał przypadkowego projektu,
3. nowy projekt zawsze dawał możliwość wpisania danych projektu przed utworzeniem pliku,
4. metadane projektu dało się edytować także po rozpoczęciu pracy,
5. lista projektów była czytelna i wyglądała profesjonalnie,
6. użytkownik mógł usuwać projekty z potwierdzeniem,
7. projekt zapisywał się automatycznie co 5 minut,
8. architektura dialogów była prostsza i mniej podatna na błędy niż obecny wielotrybowy `ProjectManagerDialog`.

## Ustalone decyzje

1. `Cancel` w startup panelu zamyka aplikację.
2. Zmiana nazwy projektu edytuje zawsze metadane projektu.
3. Zmiana nazwy projektu może dodatkowo zmienić nazwę pliku `.4dach`, ale tylko jeśli rename jest bezkolizyjny i bezpieczny.
4. Na tę iterację nie wprowadzamy obowiązkowego `project_id` jako nowego trwałego identyfikatora domenowego.
5. Format `project_meta` zostaje podstawowym źródłem prawdy dla danych projektu.

## Aktualne problemy w kodzie

### 1. Startup `Cancel`

Aktualnie `MainWindow` ładuje stan projektu przed pokazaniem startup dialogu. Jeśli startup dialog zwróci `Rejected`, okno zostaje otwarte z wcześniej wczytanym stanem, co użytkownik odbiera jako uruchomienie nie wiadomo jakiego projektu.

Dotknięte miejsca:

1. `ui/main_window.py:82-140`
2. `ui/main_window.py:617-640`

### 2. Dialog zarządzania projektami jest przeciążony trybami

Obecny `ProjectManagerDialog` obsługuje jednocześnie:

1. startup,
2. open,
3. new,
4. save as.

To prowadzi do:

1. ukrytych pól i niejednoznacznych przycisków,
2. błędów przepływu `Nowy`/`Cancel`,
3. trudności w profesjonalnym rozwijaniu UI.

Dotknięte miejsce:

1. `ui/dialogs/project_manager_dialog.py`

### 3. Nowy projekt tworzy się zbyt wcześnie

W trybie startup kliknięcie `Nowy` nie otwiera formularza danych projektu. Zamiast tego dialog akceptuje się z ukrytym `default_name="Nowy projekt"` i tworzy ścieżkę pliku od razu.

Dotknięte miejsca:

1. `ui/dialogs/project_manager_dialog.py:167-177`
2. `ui/dialogs/project_manager_dialog.py:245-252`
3. `ui/main_window.py:626-637`

### 4. Brak walidacji unikalności nazwy projektu

Plik projektu jest budowany bez iteracji nazwy przy kolizji.

Dotknięte miejsce:

1. `ui/dialogs/project_manager_dialog.py:250`

### 5. Brak edycji danych projektu po rozpoczęciu pracy

Istnieje edycja danych firmy (`company_data`), ale nie ma osobnego przepływu dla metadanych projektu.

Dotknięte miejsca:

1. `ui/main_window.py:1585-1595`
2. `ui/main_window.py:303-325`

### 6. Brak usuwania projektów z panelu

Brak akcji usuwania i potwierdzenia.

### 7. Brak autosave

Nie ma timera ani cichego autozapisu.

## Istniejące elementy, które warto zachować

1. `project_meta` już zawiera potrzebne pola:
   - `name`
   - `address`
   - `contact_name`
   - `phone`
   - `notes`
   - `created_at`
   - `modified_at`
2. `scan_projects_dir(...)` już sortuje projekty po `modified_at DESC`.
3. `save_config(...)` zapisuje atomowo.
4. `UserPreferences` już przechowuje `projects_dir` poza plikami projektów.

## Docelowy UX

### Startup / Open panel

Nowy dialog przeglądarki projektów powinien mieć układ 50/50.

#### Lewa część

Lista projektów:

1. nazwa projektu,
2. data ostatniej modyfikacji,
3. sortowanie malejąco po dacie modyfikacji.

#### Prawa część

Szczegóły zaznaczonego projektu:

1. nazwa projektu,
2. data utworzenia,
3. data ostatniej modyfikacji,
4. osoba kontaktowa,
5. telefon,
6. adres,
7. notatki,
8. powierzchnia netto,
9. liczba połaci.

#### Akcje

1. `Otwórz`
2. `Nowy`
3. `Usuń`
4. `Anuluj`

### Nowy projekt

Kliknięcie `Nowy` ma otwierać osobny formularz danych projektu.

Pola:

1. `Nazwa projektu` - wymagane,
2. `Adres` - opcjonalne,
3. `Osoba kontaktowa` - opcjonalne,
4. `Telefon` - opcjonalne,
5. `Notatki` - opcjonalne.

Zachowanie:

1. użytkownik może wpisać tylko nazwę i zacząć pracę,
2. pozostałe dane może uzupełnić później.

### Edycja projektu po starcie

Nowa pozycja menu:

1. `Plik > Edytuj projekt...`

To ma otwierać ten sam formularz co tworzenie projektu, ale z danymi bieżącego projektu.

### Usuwanie projektu

1. tylko z potwierdzeniem,
2. komunikat ma zawierać nazwę projektu,
3. nie wolno usuwać aktualnie otwartego projektu bez dodatkowego, świadomego flow.

### Autosave

1. co 5 minut,
2. tylko jeśli są niezapisane zmiany,
3. tylko jeśli projekt ma przypisaną ścieżkę pliku,
4. zapis cichy,
5. status bar informuje o autozapisie,
6. błędy nie mogą spamować użytkownika modalami przy każdym cyklu.

## Docelowa architektura

## Dialogi

Zalecane rozdzielenie obecnego `ProjectManagerDialog` na dwa osobne komponenty:

1. `ProjectBrowserDialog`
2. `ProjectDetailsDialog`

### `ProjectBrowserDialog`

Odpowiedzialność:

1. przeglądanie projektów,
2. wybór projektu do otwarcia,
3. uruchomienie tworzenia nowego projektu,
4. usuwanie projektu,
5. prezentacja szczegółów.

### `ProjectDetailsDialog`

Odpowiedzialność:

1. tworzenie nowego projektu,
2. `Zapisz jako...`,
3. edycja metadanych bieżącego projektu.

## Dane projektu

Na tę iterację utrzymujemy `project_meta` jako główne źródło prawdy.

Potencjalne przyszłe rozszerzenie:

1. dodać `project_meta.id` jako niewidoczne UUID,
2. użyć go dopiero wtedy, gdy pojawi się realna potrzeba stabilnej tożsamości niezależnej od nazwy i ścieżki.

Nie jest to wymagane do obecnej przebudowy.

## Rename pliku przy zmianie nazwy projektu

Rekomendowane zachowanie:

1. zmiana nazwy zawsze aktualizuje `project_meta.name`,
2. jeśli nowa nazwa daje bezkolizyjną ścieżkę pliku w tym samym katalogu, próbujemy przemianować plik `.4dach`,
3. jeśli rename się nie uda albo ścieżka koliduje, zostawiamy istniejący plik i zapisujemy tylko metadane,
4. w razie kolizji użytkownik dostaje jasną informację, że nazwa projektu została zmieniona, ale nazwa pliku pozostała bez zmian; pełne przeniesienie może zrobić przez `Zapisz jako...`.

## Etapy implementacji

### Etap 1. Naprawa krytycznego flow

Cel: usunąć najbardziej rażące błędy UX bez pełnej przebudowy wszystkiego naraz.

Zakres:

1. `Cancel` w startup panelu zamyka aplikację.
2. `Nowy projekt` nie może już tworzyć od razu `Nowy projekt.4dach` bez formularza.
3. nazwa projektu musi być walidowana i iterowana przy kolizji.

Dotknięte pliki:

1. `ui/main_window.py`
2. `ui/dialogs/project_manager_dialog.py` lub nowe dialogi, jeśli rozdzielenie nastąpi od razu
3. `tests/test_mainwindow_ui_contract.py`
4. `tests/test_project_manager_dialog.py`

### Etap 2. Przebudowa UI przeglądarki projektów

Cel: czytelny i profesjonalny panel otwierania projektów.

Zakres:

1. `QSplitter` 50/50,
2. lewa lista projektów,
3. prawa sekcja szczegółów,
4. czytelny model wyświetlania nazwy i daty,
5. statystyki projektu w szczegółach.

Dotknięte pliki:

1. `ui/dialogs/project_browser_dialog.py` lub refactor `project_manager_dialog.py`
2. `tests/test_project_manager_dialog.py`

### Etap 3. Formularz danych projektu

Cel: jeden spójny formularz dla create/save as/edit.

Zakres:

1. walidacja nazwy,
2. iteracja nazw przy kolizji,
3. wypełnianie domyślnych wartości przy edycji,
4. wspólna ścieżka odczytu/zapisu metadanych.

Dotknięte pliki:

1. nowy `ui/dialogs/project_details_dialog.py`
2. `ui/main_window.py`
3. testy dialogów i main window

### Etap 4. `Plik > Edytuj projekt...`

Cel: użytkownik może uzupełniać dane projektu w dowolnym momencie.

Zakres:

1. dodać akcję menu,
2. podpiąć dialog danych projektu,
3. aktualizować `project_meta`,
4. odświeżać tytuł okna,
5. oznaczać projekt jako dirty,
6. opcjonalnie próbować rename pliku.

Dotknięte pliki:

1. `ui/main_window.py`
2. testy UI contract

### Etap 5. Usuwanie projektów

Cel: pełna obsługa delete z potwierdzeniem.

Zakres:

1. przycisk `Usuń`,
2. potwierdzenie `QMessageBox`,
3. blokada dla aktualnie otwartego projektu,
4. odświeżenie listy i szczegółów.

Dotknięte pliki:

1. browser dialog,
2. testy dialogu.

### Etap 6. Autosave

Cel: bezpieczny, cichy autozapis co 5 minut.

Zakres:

1. `QTimer` w `MainWindow`,
2. warunek: `_has_unsaved_changes` i `_project_file_path is not None`,
3. cichy zapis bez pełnej ścieżki interakcyjnej `Save As`,
4. czytelny komunikat w status barze,
5. tłumienie powtarzalnych błędów.

Dotknięte pliki:

1. `ui/main_window.py`
2. testy `test_mainwindow_ui_contract.py`

## Minimalne API pomocnicze do dodania

### W warstwie dialogów

1. helper generujący bezkolizyjną nazwę projektu,
2. helper budujący docelową ścieżkę pliku z nazwy,
3. helper odczytu szczegółów projektu do panelu preview.

### W `MainWindow`

1. `_edit_project_meta()`
2. `_attempt_rename_project_file(...)`
3. `_start_autosave_timer()`
4. `_autosave_project_if_needed()`
5. `_close_after_startup_cancel()` lub prostszy równoważnik

## Proponowana kolejność commitów

### Commit 1

Naprawa startup `Cancel` + przygotowanie flow nowego projektu.

### Commit 2

Nowy formularz `ProjectDetailsDialog` i walidacja/iteracja nazwy.

### Commit 3

Przebudowa browsera projektów na split 50/50.

### Commit 4

`Plik > Edytuj projekt...` + aktualizacja metadanych i tytułu.

### Commit 5

Usuwanie projektów z potwierdzeniem.

### Commit 6

Autosave co 5 minut + testy regresyjne.

## Test plan

### Dialogi / browser

1. startup `Cancel` zamyka aplikację,
2. `Nowy` otwiera formularz danych projektu,
3. brak automatycznego tworzenia `Nowy projekt.4dach`,
4. pusta nazwa jest blokowana,
5. kolizja nazw iteruje `Projekt 2`, `Projekt 3`, ...,
6. lista sortuje po `modified_at DESC`,
7. preview pokazuje poprawne dane,
8. delete wymaga potwierdzenia,
9. delete aktualnie otwartego projektu jest blokowany.

### Main window

1. `Nowy projekt` czyści połacie i ładuje pusty stan,
2. `Edytuj projekt...` aktualizuje `project_meta`,
3. rename pliku działa tylko gdy bezpieczny,
4. przy kolizji rename pliku jest pomijany bez utraty metadanych,
5. autosave zapisuje tylko dirty projekt ze ścieżką,
6. autosave nic nie robi dla nowej, niezapisanej sesji,
7. autosave nie niszczy stanu dirty/saved,
8. `modified_at` aktualizuje się po autozapisie.

## Ryzyka

1. Startup close flow w Qt może wymagać zamknięcia okna po zakończeniu konstruktora, a nie bezpośrednio w środku `__init__`.
2. Rename aktywnego pliku projektu musi być atomowy i dobrze obsłużyć kolizje oraz `OSError`.
3. Autosave nie może używać flow z modalnym `Save As`, bo to zepsuje UX.
4. Przebudowa dialogów dotknie wielu testów monkeypatchujących obecny `ProjectManagerDialog`.

## Rekomendacje implementacyjne

1. Najpierw naprawić flow i dodać testy bezpieczeństwa.
2. Potem dopiero robić ładny browser i preview.
3. Autosave wdrażać dopiero po ustabilizowaniu ścieżki `new/open/save/edit`, żeby nie debugować kilku przepływów naraz.
4. Nie dokładać teraz `project_id`, chyba że w trakcie implementacji rename pliku okaże się istotnie problematyczny.

## Definicja ukończenia

Przebudowa będzie gotowa, gdy:

1. startup `Cancel` zawsze zamknie aplikację,
2. nowy projekt zawsze zacznie się od formularza danych projektu,
3. użytkownik będzie mógł później edytować metadane projektu,
4. panel projektów będzie miał czytelną listę i panel szczegółów,
5. usuwanie będzie działało z potwierdzeniem,
6. autosave będzie działał co 5 minut,
7. testy dla tych przepływów będą przechodziły stabilnie.
