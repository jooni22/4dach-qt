# Findings

## Struktura repozytorium
- `mainwindow.py`
  - buduje menu, toolbar, zakładki, canvasy i obsługuje akcje UI
  - zawiera tymczasowy `DrawingCanvas` oparty o `QWidget`
- `dialogs.py`
  - zawiera dialogi kształtów, danych firmy, katalogu blach
  - zawiera persystencję `config.json`
- `form.ui` / `ui_form.py`
  - tylko scaffold głównego okna
- `DOC/ui-info.md`, `DOC/ui-okna.md`
  - opisują oczekiwany UI i są dobrą bazą do testów zgodności UI

## Co już istnieje
- Wielozakładkowy workspace (`QTabWidget`) jest już obecny na poziomie UI.
- Katalog blach i dane firmy mają formularze oraz zapis do `config.json`.
- Toolbar i menu są zgodne z opisem UI i mogą stanowić obiekt testów smoke/UI.

## Czego brakuje
- Brak modelu domenowego: `RoofPlane`, `Material`, `SheetPlacement`, `Report`.
- Brak warstwy usług / silnika obliczeniowego.
- Brak kontrolera stanu projektu i stanu pojedynczej połaci.
- Brak trybów edycji geometrii: przesuwanie punktów, dodawanie punktów na krawędziach, obsługa wycinków.
- Brak raportowania, BOM, kosztorysu i wizualizacji arkuszy wynikowych.
- Brak testów jednostkowych, integracyjnych i UI.

## Wniosek architektoniczny
Nowa logika nie powinna trafić do `mainwindow.py` poza cienką warstwą orkiestracji akcji UI. Najlepszy kierunek to wydzielenie osobnych modułów dla:
- modeli domenowych,
- silnika geometrii i rozkroju,
- kontrolera stanu projektu,
- adaptera persystencji,
- warstwy rysowania / prezentera canvasa.

## Dokumentacja pomocna już teraz
- `DOC/ui-info.md` jako źródło prawdy dla menu i toolbaru.
- `DOC/ui-okna.md` jako źródło prawdy dla okien dialogowych.

## Dokumentacja brakująca
- Specyfikacja współrzędnych i orientacji osi w przestrzeni roboczej.
- Zasady domknięcia poligonu i walidacji samoprzecięć.
- Formalna definicja „globalnej linii bazowej” dla taktowania modułów.
- Zasady ręcznej korekty arkuszy i konfliktu z autogeneracją.
- Format docelowego raportu i model eksportu.
