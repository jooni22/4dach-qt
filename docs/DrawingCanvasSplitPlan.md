# DrawingCanvas Split Plan

## Cel

Rozbić `ui/drawing_canvas.py` w taki sposob, zeby agenci i deweloperzy latwiej orientowali sie w strukturze pliku, bez wchodzenia od razu w duza wieloetapowa przebudowe architektury.

Najwazniejszy cel tej fazy to poprawa nawigacji i czytelnosci, a nie zmiana zachowania canvasa.

## Stan obecny

`ui/drawing_canvas.py` ma obecnie okolo `3866` linii i laczy w jednym miejscu kilka roznych odpowiedzialnosci:

- obsluge interakcji myszy i klawiatury,
- sesje rysowania i edycje odcinkow,
- logike pomocniczego edytora inline,
- rendering i wszystkie warstwy paintingu,
- snapping i inference,
- undo/redo,
- mapowanie geometrii i pomocnicze obliczenia widoku.

To powoduje, ze plik jest zbyt duzy jako jednostka kontekstu. Nawet jesli kod jest logicznie podzielony na klasy i mixiny, agenci gubia sie, bo musza utrzymac w pamieci zbyt wiele niezaleznych obszarow naraz.

## Wniosek

Samo dodanie komentarza na gorze pliku pomoze tylko troche.

Podzial na `2` pliki tez nie daje najlepszego efektu, bo nadal zostaje jeden bardzo duzy modul.

Najlepszy stosunek kosztu do zysku w pierwszym kroku daje podzial na `3` pliki.

## Zakres fazy 1

Pierwsza faza powinna byc celowo konserwatywna:

- bez zmiany zachowania,
- bez przepisywania algorytmow,
- bez glebokiej reorganizacji importow,
- bez dalszego rozdrabniania na wiele malych modulow.

Chodzi o czyste wyjecie duzych, naturalnych blokow odpowiedzialnosci do osobnych plikow.

## Docelowy podzial fazy 1

### 1. `ui/drawing_canvas.py`

Plik glowny powinien zostac odchudzony i pelnic role modulu integracyjnego.

Powinien zawierac glownie:

- `DrawingCanvas`,
- obecne stale i dataclassy, jesli ich ruszenie zwiekszaloby ryzyko,
- importy do wyciagnietych mixinow i widgetu pomocniczego.

W tej fazie nie trzeba jeszcze na sile wynosic wszystkiego z `DrawingCanvas`.

### 2. `ui/canvas/canvas_interaction.py`

Ten plik powinien przejac:

- `_InlineSegmentEditor`,
- `_DrawingCanvasInteractionMixin`,
- `_DrawingCanvasInlineEditorMixin`.

Powod:

Tak zwany "inline editor" nie jest tylko malym widgetem formularza. To w praktyce caly subsystem sesji wejscia i edycji:

- crosshair,
- preview segmentu,
- logika kata i dlugosci,
- parse/confirm/cancel,
- post-draw editing,
- obsluga przeplywu interakcji podczas rysowania.

Dlatego ten blok jest blizej interakcji niz paintingu.

### 3. `ui/canvas/canvas_painting.py`

Ten plik powinien przejac:

- `_DrawingCanvasPaintingMixin`.

Powod:

To najwiekszy i jednoczesnie najbardziej samodzielny blok w calym module. Wyjecie go do osobnego pliku daje najwiekszy zysk nawigacyjny praktycznie bez zmiany architektury.

## Dlaczego nie wiecej plikow na start

Pelniejszy docelowy podzial na:

- `constants.py`,
- `state_models.py`,
- osobne moduly paintingu,
- osobne moduly geometrii i snappingu,

ma sens jako kolejna faza, ale nie jako pierwszy ruch.

Na start byloby to zbyt szerokie i zwiekszaloby ryzyko:

- ukrytych zaleznosci,
- kolistych importow,
- niepotrzebnego dryfu zachowania,
- duzego diffu trudniejszego do review.

Faza 1 ma byc tania, praktyczna i bezpieczna.

## Proponowana kolejnosc wdrozenia

### Krok 1. Utworzyc `ui/canvas/canvas_interaction.py`

Przeniesc tam 1:1:

- `_InlineSegmentEditor`,
- `_DrawingCanvasInteractionMixin`,
- `_DrawingCanvasInlineEditorMixin`.

Na tym etapie nie porzadkowac logiki bardziej niz trzeba. Priorytetem jest zachowanie stabilnosci.

### Krok 2. Utworzyc `ui/canvas/canvas_painting.py`

Przeniesc tam 1:1 caly `_DrawingCanvasPaintingMixin`.

To powinno byc mozliwie mechaniczne przeniesienie, bez mieszania odpowiedzialnosci.

### Krok 3. Uproscic `ui/drawing_canvas.py`

W pliku glownym:

- zostawic `DrawingCanvas`,
- zostawic stale i dataclassy, jesli ich wynoszenie nie jest niezbedne,
- dodac importy z nowych modulow,
- upewnic sie, ze kolejnosc dziedziczenia pozostaje bez zmian.

### Krok 4. Dodac lekkie komentarze nawigacyjne

Po podziale nadal warto dodac krotkie komentarze i docstringi, ale juz w nowych, mniejszych modulach.

Przyklad:

- `"""Interaction and input-session helpers for DrawingCanvas."""`
- `"""Painting helpers for DrawingCanvas."""`

W samym `DrawingCanvas` mozna zostawic krotkie sekcje typu:

- `# Public API`
- `# History and selection`
- `# Geometry and view helpers`

## Zasady importow

Zeby nie wprowadzic problemow podczas wyciecia kodu:

- unikac importowania `DrawingCanvas` do nowych modulow,
- nowe moduly powinny zawierac tylko mixiny i pomocniczy widget,
- jesli potrzebne sa typy tylko do anotacji, uzyc `TYPE_CHECKING` lub string annotations,
- zachowac obecne zaleznosci pomocnicze z `ui.canvas.snap_helpers` i `ui.canvas.sheet_geometry` bez dodatkowej przebudowy.

## Główne ryzyka

### 1. Koliste importy

Najwieksze ryzyko pojawi sie, jesli nowe moduly zaczna importowac `DrawingCanvas` zamiast dzialac przez `self` i istniejace importy pomocnicze.

### 2. Ukryte zaleznosci miedzy blokami

Niektore metody interaction, inline editing i painting moga korzystac ze wspolnego stanu ustawianego w `DrawingCanvas.__init__`. Przy przenoszeniu trzeba zachowac identyczne nazwy pol i identyczny przeplyw inicjalizacji.

### 3. Zbyt ambitne porzadki przy okazji

Najlatwiej zepsuc taki refaktor wtedy, gdy oprocz przenoszenia zacznie sie od razu poprawiac style, nazwy i strukture pomocnicza. W tej fazie nalezy tego unikac.

## Checklista weryfikacyjna

Po wykonaniu podzialu trzeba sprawdzic co najmniej:

- czy canvas otwiera sie bez bledow importu,
- czy rysowanie obrysu nadal dziala,
- czy zamykanie poligonu nadal dziala,
- czy drag wierzcholkow i krawedzi nadal dziala,
- czy inline editing dlugosci i kata nadal dziala,
- czy painting siatki, overlayow i zaznaczen nadal dziala,
- czy undo/redo nadal dziala,
- czy snapping i inference nadal dzialaja,
- czy testy dotyczace canvasa nadal przechodza.

## Kryteria akceptacji

Faza 1 jest zakonczona, jezeli:

- `ui/drawing_canvas.py` jest wyraznie mniejszy,
- interakcja i painting sa w osobnych plikach,
- nie ma regresji zachowania,
- agenci moga czytac kazdy z glownych obszarow osobno,
- diff pozostaje na tyle prosty, zeby review bylo latwe.

## Oczekiwany efekt

Po tej zmianie:

- glowny plik przestanie byc jedynym ogromnym punktem wejscia,
- painting bedzie odseparowany od interakcji,
- subsystem wejscia i inline editingu bedzie czytelniejszy,
- kolejne fazy porzadkowania beda latwiejsze i bezpieczniejsze.

## Faza 2 opcjonalnie

Dopiero po stabilnym wdrozeniu fazy 1 warto rozważyć dalsze kroki:

- wyniesienie stalych do `ui/canvas/constants.py`,
- wyniesienie dataclass do `ui/canvas/state_models.py`,
- dalszy podzial paintingu na mniejsze moduly,
- wydzielenie geometrii i snappingu z `DrawingCanvas`.

## Rekomendacja koncowa

Najbardziej praktyczny pierwszy ruch to:

1. podzielic `ui/drawing_canvas.py` na `3` pliki,
2. zrobic to mozliwie mechanicznie,
3. dopiero potem dodac lekkie komentarze nawigacyjne,
4. nie zaczynac od duzej wielomodulowej przebudowy.

To da realna poprawe dla agentow bez niepotrzebnego ryzyka refaktoru.
