# Plan wdrożenia: trwałe raporty projektu i przycisk „Raport” w browserze

## Cel

Dodać trwałe, łatwo dostępne raporty HTML powiązane z projektem oraz udostępnić ich otwieranie bezpośrednio z browsera projektów.

## Założenie wejściowe

1. Wszystkie stare projekty testowe zostały usunięte.
2. Możemy bezpiecznie zmienić model przechowywania projektów bez zachowywania kompatybilności wstecz.
3. Nie musimy obsługiwać starego płaskiego formatu `*.4dach` w katalogu głównym `projects_dir`.

## Nowy model przechowywania projektu

Zamiast pojedynczego pliku:

```text
<projects_dir>/Projekt.4dach
```

wprowadzamy kontener projektu jako katalog:

```text
<projects_dir>/
  <slug-projektu>/
    project.4dach
    report.html
```

### Zasady

1. `project.4dach` jest stałą nazwą pliku konfiguracyjnego projektu.
2. `report.html` jest trwałym, ostatnio wygenerowanym raportem projektu.
3. Nazwa wyświetlana projektu nadal pochodzi z `project_meta.name`.
4. Nazwa katalogu projektu powstaje z bezpiecznego slugu wygenerowanego z nazwy projektu.
5. Kolizje nazw katalogów rozwiązujemy iteracją:
   - `projekt-a`
   - `projekt-a-2`
   - `projekt-a-3`

## Docelowy UX

## Browser projektów

W panelu szczegółów zaznaczonego projektu dodajemy przycisk:

1. `Raport`

### Zachowanie przycisku `Raport`

1. Jeśli `report.html` istnieje:
   - przycisk jest aktywny
   - kliknięcie otwiera raport w domyślnej przeglądarce
2. Jeśli `report.html` nie istnieje:
   - przycisk jest wyszarzony
3. Na tym etapie aktywność przycisku zależy tylko od istnienia pliku.
4. Nie blokujemy otwierania „starego” raportu, jeśli projekt był później edytowany.
   - Opcjonalny status „raport może być nieaktualny” można dodać później jako rozszerzenie.

## Generowanie raportu

1. Każde wygenerowanie raportu zapisuje `report.html` w katalogu projektu.
2. `open_external=True` otwiera właśnie ten trwały plik.
3. Wewnętrzny podgląd raportu w aplikacji pozostaje bez zmian.
4. Kolejne wygenerowanie raportu nadpisuje poprzedni plik `report.html`.

## Edycja nazwy projektu

Ponieważ folder projektu ma być nazwany wg projektu, ta zmiana dotyka też rename flow.

### Rekomendowane zachowanie

1. Zmiana nazwy zawsze aktualizuje `project_meta.name`.
2. Jeśli rename katalogu projektu jest bezkolizyjny i bezpieczny:
   - zmieniamy nazwę katalogu projektu
   - `_project_file_path` wskazuje dalej na:
     - `nowy-katalog/project.4dach`
3. Jeśli rename katalogu się nie uda:
   - zachowujemy stary katalog
   - zapisujemy tylko metadane
   - pokazujemy jasną informację w stylu:
     - „Nazwa projektu została zmieniona, ale nazwa katalogu pozostała bez zmian.”

To jest odpowiednik wcześniejszego rename pliku, tylko na poziomie katalogu projektu.

## Zakres techniczny

## 1. Warstwa ścieżek projektu

Dodać wspólne helpery do pracy z katalogiem projektu.

### Rekomendowane helpery

1. `slugify_project_name(name: str) -> str`
2. `project_dir_from_name(projects_dir: Path, project_name: str) -> Path`
3. `resolve_unique_project_dir(projects_dir: Path, project_name: str, current_dir: Path | None = None) -> Path`
4. `project_config_path(project_dir: Path) -> Path`
5. `project_report_path(project_dir: Path) -> Path`
6. `project_dir_from_config_path(config_path: Path) -> Path`

### Lokalizacja helperów

Najczyściej:
1. nowy moduł Qt-free, np. `project_files.py`

Alternatywnie:
1. rozszerzyć `persistence.py`

Rekomenduję osobny moduł, bo to logika storage/path, a nie sam zapis JSON.

## 2. Zmiana create/save-as/edit

### `ProjectDetailsDialog`

Zmienić dialog tak, by:
1. zwracał docelową ścieżkę:
   - `<project_dir>/project.4dach`
2. rozwiązywał kolizje na poziomie katalogu projektu, nie pliku `.4dach`
3. w trybie edycji znał:
   - bieżący katalog projektu
   - bieżący plik `project.4dach`

### `MainWindow`

Dostosować:
1. `_create_new_project()`
2. `_save_project_as()`
3. `_edit_project_meta()`
4. `_save_project_from_dialog(...)`

Tak, aby wszystkie te ścieżki działały na nowym modelu katalogowym.

## 3. Zmiana browsera projektów

### `ProjectMeta`

Rozszerzyć model o:

1. `project_dir: Path`
2. `config_path: Path`
3. `report_path: Path`
4. `has_report: bool`

Można zachować istniejące `path`, ale docelowo lepiej jasno rozdzielić:
1. `config_path`
2. `project_dir`

### Skanowanie projektów

Zamiast:

```python
root.glob("*.4dach")
```

browser powinien:
1. iterować po katalogach w `projects_dir`
2. szukać w nich `project.4dach`
3. czytać metadane z:
   - `<dir>/project.4dach`
4. oznaczać raport jako dostępny, jeśli istnieje:
   - `<dir>/report.html`

## 4. Dodanie przycisku `Raport`

W `ProjectManagerDialog`:

1. dodać przycisk `Raport` w panelu szczegółów projektu
2. aktualizować jego stan po każdej zmianie zaznaczenia
3. po kliknięciu:
   - jeśli `report.html` istnieje:
     - `QDesktopServices.openUrl(QUrl.fromLocalFile(...))`
   - jeśli nie istnieje:
     - nic albo przycisk disabled

### Rekomendowane umiejscowienie

Najbardziej naturalne:
1. po prawej stronie, w panelu szczegółów, pod danymi lub obok nagłówka „Szczegóły projektu”

Nie rekomenduję wrzucania go tylko do dolnego `QDialogButtonBox`, bo to akcja kontekstowa dla zaznaczonego projektu, nie główny flow dialogu.

## 5. Trwały zapis raportu

### `MainWindow._gen_report(...)`

Zmienić tak, by:

1. po wygenerowaniu HTML zawsze zapisywać go do:
   - `project_report_path(project_dir_from_config_path(self._project_file_path))`
2. przy `open_external=True` otwierać właśnie ten zapisany plik
3. przy braku `_project_file_path`:
   - nie tworzyć raportu w temp
   - zachować obecne zachowanie albo wyświetlić komunikat, że projekt musi być zapisany
   - rekomendacja: jeśli projekt nie ma ścieżki, nie zapisujemy raportu trwałego i nadal pokazujemy go tylko w aplikacji

### Rekomendowane zachowanie dla niezapisanej sesji

1. Raport wewnętrzny nadal można wygenerować
2. Trwały `report.html` zapisujemy tylko wtedy, gdy projekt ma `_project_file_path`
3. Browser `Raport` działa tylko dla projektów zapisanych na dysku

## 6. Delete projektu

### `ProjectManagerDialog._delete_selected_project()`

Zmienić usuwanie tak, by:
1. usuwało cały katalog projektu
2. nie tylko `project.4dach`

Rekomendacja:
1. użyć `shutil.rmtree(project.project_dir)`

### Blokada dla aktywnego projektu

Porównanie powinno działać na config path albo project dir:
1. najlepiej na `config_path`
2. ewentualnie na `project_dir`

## 7. Testy

## Dialog browsera

Dodać testy:

1. browser skanuje katalogi projektu zawierające `project.4dach`
2. `has_report=False` gdy `report.html` nie istnieje
3. `has_report=True` gdy `report.html` istnieje
4. przycisk `Raport` jest disabled bez pliku
5. przycisk `Raport` jest enabled z plikiem
6. kliknięcie `Raport` otwiera poprawny plik lokalny
7. delete usuwa cały katalog projektu
8. po delete lista i preview odświeżają się poprawnie

## Project details / create / save-as

1. nowy projekt tworzy:
   - katalog projektu
   - `project.4dach` w środku
2. `save as` zapisuje do nowego katalogu projektu
3. kolizja nazwy iteruje nazwę katalogu
4. edycja nazwy projektu może zmienić katalog projektu, jeśli rename jest bezkolizyjny

## MainWindow / raport

1. `_gen_report(..., open_external=False)` zapisuje `report.html`, jeśli projekt ma ścieżkę
2. `_gen_report(..., open_external=True)` otwiera trwały `report.html`
3. ponowna generacja nadpisuje raport
4. niezapisana sesja nie zapisuje raportu na dysk
5. po otwarciu projektu browser poprawnie widzi istnienie raportu

## Ryzyka

1. To jest zmiana modelu przechowywania projektu, więc dotyka wielu flow jednocześnie.
2. Trzeba dopilnować, by `_project_file_path` zawsze wskazywał na `project.4dach`, a nie katalog projektu.
3. Rename katalogu projektu przy edycji nazwy może generować kolizje lub błędy systemowe.
4. Delete katalogu projektu musi być ostrożny i działać tylko na ścieżkach wewnątrz `projects_dir`.
5. Raport może istnieć, ale być nieaktualny względem nowszego stanu projektu.
   - Na ten etap to akceptujemy.

## Rekomendowana kolejność implementacji

## Commit 1
Wprowadzenie nowego modelu ścieżek projektu:
1. helpery storage/path
2. `ProjectDetailsDialog` i `MainWindow` zapisujące do `<dir>/project.4dach`

## Commit 2
Browser projektów czytający katalogi projektów:
1. skan katalogów
2. `ProjectMeta` z `has_report`
3. dostosowanie delete do katalogów

## Commit 3
Trwały raport:
1. zapis `report.html`
2. otwieranie trwałego raportu z `MainWindow._gen_report(...)`

## Commit 4
Przycisk `Raport` w browserze:
1. aktywacja/dezaktywacja
2. otwieranie `report.html`
3. testy UI

## Definicja ukończenia

Zmiana jest gotowa, gdy:

1. nowy projekt zapisuje się jako katalog projektu
2. config projektu jest w `project.4dach`
3. wygenerowany raport zapisuje się jako `report.html`
4. browser projektu pokazuje aktywny przycisk `Raport`, jeśli raport istnieje
5. kliknięcie `Raport` otwiera trwały plik HTML
6. delete usuwa cały katalog projektu
7. testy dla create/open/browser/delete/report przechodzą stabilnie
