<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# /github

rzut-obrys.jpg czyli 1 zdjęcie to uproszczony rzut całego dachu
prawdziwy-rzuyt-2.jpg to jest rzut który zazwyczaj tak wygląda, z którego rysuje się połaci w aplikacji.
Chciałbym do aplikacji dodać nowa funkcje, która umożliwi załadowanie zdjęcia rzutu (użytkownik zrobi sobie skan rzutu lub załączy jpg czy png), wtedy po uruchomieniu tej opcji, wyświetla się nowe okno, w którym użytkownik ma coś ala wizard, czyli proces przez który aplikacja go łatwo przeprowadzi aby poprawnie utworzyć połacie w aplikacji. W tym wizard wymyśliłem, że użytkownik widzi zdjęcie które załączył i po kolei aplikacja przeprowadza go przez kroki opisane niżej (twoim zadaniem jest sprawdzenie, czy taka implementacja będzie trudna, czy coś z tych kroków jest niejasne/problematyczne, jeżeli widzisz łątwiejszą metode to od razu o niej napisz, pamiętaj interfejs musi być mega prosty):

1. użytkownik ma napis, wybierz obszar roboczy (czyli obszar na zdjęciu na którym są rozmieszczone wszystkie połacie czyli obrys całego dachu), po zaznaczeniu pojawia się opcja dalej
2. użytkownik ma możliwość (przez cały wizard, wyboru przezroczystości obrazu oraz jego nowo utworzonych linii, coś jak w gimp przezroczystość warstwy)
3. Tutaj trzeba zdecydować co będzie prostszym rozwiazaniem, czy użytkownik ma możliwość zaznaczenie linii (wcześniej rozpoznane z obrazu linie i kursorem zaznaczamy linie już rozpoznane), czy lepiej dać narzędzie prostych linii i kursorem rysuje to co chce dodać na połać (rysuje po widocznych liniach a dokładnie zaznacza punkty i linie się rysują po kolei od punktu do punktu, z możliwością cofnięcia ostatnich ruchów). W tym trybie ma na początku możliwość ile połaci chce z tego obrazu narysować i dodawać konkretne figury jako osobne połacie.
4. Użytkownik wybrał np 3 połacie i je narysowal, normalizujemy wtedy kąty i prostujemy linie aby było symetryczne wszystko. Następnie użytkownik wprowadza długości rozpoznanych figur (tutaj musimy zweryfikować które długości są kluczowe aby dopasować finalny rozmiar połaci czyli narysowanych figur)
5. Wyświetlamy podsumowanie i możliwość poprawy albo akceptacji i umieszczenie w programie narysowanych przez użytkownika połaci.

Mam pełny obraz zarówno zdjęć, jak i kodu. Oto kompleksowa analiza.

***

## Ocena ogólna

Pomysł jest dobry i wykonalny w Qt — masz już 80% potrzebnej infrastruktury w `DrawingCanvas`, `CanvasMapper` i silniku snappingu.  Żaden krok nie wymaga zewnętrznych bibliotek ML do rozpoznawania linii. Poniżej idę przez każdy krok i wskazuję co jest proste, co jest problematyczne i jak to uprościć.

***

## Analiza krok po kroku

### Krok 1 — Wybór obszaru roboczego

**Trudność: niska.** To standardowe zaznaczenie prostokątem rubber-band (`QRubberBand`) — Qt ma to out-of-the-box.  Po zaznaczeniu aplikacja wyznacza bounding box i wszystkie późniejsze operacje działają w tym układzie współrzędnych.

**Jeden problem:** Jeżeli rzut jest obrócony (skan pod kątem), guma prostokątna da zły obszar. Rozwiązanie — dodaj przycisk „wyrównaj/wyprostuj obraz" na tym samym ekranie (prosta rotacja przez `QTransform` na pixmapie).

***

### Krok 2 — Kontrola przezroczystości przez cały wizard

**Trudność: bardzo niska.** `QPixmap` rysuje się na `QGraphicsView` lub bezpośrednio w `paintEvent` z `painter.setOpacity(value)`, gdzie `value` pochodzi ze slidera.  To dosłownie jedna linia. Warto też dodać toggle „pokaż/ukryj tło" — szybsze niż suwak.

***

### Krok 3 — Rysowanie połaci: zaznaczanie vs. rysowanie ręczne

**Tu jest kluczowy wybór architektoniczny.** Moja rekomendacja: **porzuć całkowicie opcję automatycznego rozpoznawania linii z obrazu** — to jest Twój krok 3a (zaznaczanie rozpoznanych linii). [Certainty 97%]

Dlaczego:

- Rzuty budowlane (patrz `prawdziwy-rzut-2.jpg`) mają kreskowania, wymiary, linie pomocnicze, schody, opisy — detekcja linii (Hough transform, OpenCV) zwróci 200+ fałszywych krawędzi [Certainty 96%]
- Rzut uproszczony (`rzut-obrys.jpg`) byłby wykrywalny, ale użytkownicy będą wgrywać oba typy
- Obsługa błędów i korygowanie złych wyników byłoby trudniejsze do UX niż samo rysowanie

**Zostaw tylko opcję B: ręczne klikanie punktów** — ale wzbogacone o mechanizm który już masz:

Istniejący `DrawingCanvas` ma już:

- tryb `MODE_DRAW_OUTLINE` z `user_points`, rubber-band i snap-to-vertex
- `_InlineSegmentEditor` do ręcznego wpisywania długości segmentu
- undo stack per-wierzchołek
- snapping ortogonalny i 45°

Wizard po prostu uruchamia **nową instancję** `DrawingCanvas` z załadowaną pixmapą jako tło warstwy 0, wyłączoną siatką i włączonym trybem `MODE_DRAW_OUTLINE`. Nie musisz pisać nowego silnika rysowania.

**Liczba połaci na wejściu kroku 3:** Pytanie „ile połaci?" na początku kroku jest OK, ale lepiej zrobić je jako **przyciski „Dodaj następną połać"** po narysowaniu każdej — użytkownik nie zawsze wie z góry ile ich będzie, dopóki nie narysuje pierwszej.

***

### Krok 4 — Normalizacja kątów + wprowadzanie wymiarów

To jest **najtrudniejszy krok** i ma dwa oddzielne problemy.

#### 4a — Normalizacja (prostowanie linii i symetria)

**Trudność: średnia.** Masz już snapping 45°/90°, ale normalizacja po fakcie (korekcja już narysowanego poligonu) to coś innego.

Najprostsze podejście bez uczenia maszynowego:

- dla każdego boku poligonu oblicz kąt,
- jeśli kąt mieści się w tolerancji np. ±8° od 0°/90°/45°/135° → „snap" go do tej wartości,
- ponownie oblicz wierzchołki tak, żeby sąsiednie odcinki się przecinały po korekcji.

To jest algorytm iteracyjny (każda zmiana kąta jednego boku przesuwa dwa wierzchołki), ale dla poligonów dachowych z 4–10 wierzchołkami działa stabilnie. [Certainty 90%]

Symetria: **nie rób automatycznej symetrii** — dachy są często niesymetryczne (jak widać na Twoim rzucie). Daj użytkownikowi checkbox „wymuś symetrię wzdłuż osi X/Y" per połać.

#### 4b — Wprowadzanie wymiarów i skalowanie

To jest **problematyczne w projekcie** — i warto poświęcić chwilę, bo jest kilka podejść:


| Podejście | Zalety | Wady |
| :-- | :-- | :-- |
| Użytkownik wprowadza jeden wymiar referencyjny (np. długość jednego boku) | Mega proste, jeden QDoubleSpinBox | Wymaga żeby użytkownik wiedział który bok i ile cm |
| Użytkownik kliknął dwa punkty na zdjęciu i wpisał odległość między nimi w cm (kalibracja skali) | Działa dla każdego rzutu, bardzo intuicyjne | Krok extra przed rysowaniem |
| Aplikacja prosi o wszystkie kluczowe wymiary każdego boku | Najdokładniej | Zbyt dużo formularzy |

**Rekomendacja:** zrób kalibrację skali jako osobny krok **między krokiem 1 a 3**: użytkownik klika dwa punkty na zdjęciu i wpisuje ile cm to wynosi. Raz skalibrowane → wszystkie połacie dziedziczą ten sam przelicznik px→cm. Potem w kroku 4 wyświetlasz wyliczone wymiary boków z możliwością korekty tylko tych, które „nie pasują" (zaznaczone na czerwono jeśli odchylają się od symetrii o więcej niż 5%). [Certainty 95%]

**Które wymiary są kluczowe:** długość najdłuższego boku każdej połaci (czyli kalenica lub okap) + jeden wymiar prostopadły (szerokość połaci). Reszta wynika z geometrii, o ile kąty zostały znormalizowane. [Certainty 97%]

***

### Krok 5 — Podsumowanie i import do projektu

**Trudność: niska.** Masz już `ProjectState` z API do dodawania `RoofPlane` . Wizard tworzy obiekty `RoofPlane` ze skonwertowanymi współrzędnymi (px→cm przez CanvasMapper) i dodaje je do stanu projektu. Podsumowanie to read-only widok z miniaturkami każdej narysowanej połaci.

Jeden ważny szczegół: po imporcie **wyczyść tło z pixmapą** — obiekty `RoofPlane` trafiają do głównego `DrawingCanvas` bez obrazu tła.

***

## Proponowana uproszczona kolejność kroków

Zamiast Twojego planu 5-krokowego proponuję przeprojektowanie na **6 prostszych kroków** — każdy jednoekranowy, bez przeciążenia kognitywnego:

```
Krok 0  →  Wgraj obraz (drag&drop lub przycisk)
Krok 1  →  Kalibracja skali: kliknij 2 punkty → wpisz cm
Krok 2  →  Zaznacz obszar roboczy (rubber-band)
Krok 3  →  Narysuj połaci jedną po drugiej (klik→klik→klik→close)
           [suwak opacity, undo, snap, przycisk "Dodaj kolejną"]
Krok 4  →  Normalizuj + zatwierdź wymiary (edytowalny widok)
Krok 5  →  Podsumowanie → "Importuj do projektu"
```

Krok 0 i 1 to nowe elementy względem Twojego planu — bez nich krok 4 nie ma skąd wziąć skali. [Certainty 99%]

***

## Co należy zaimplementować od nowa

Absolutnie minimalna nowa klasa to `ImportWizardDialog` (podklasa `QDialog` lub `QWizard`) zawierająca:

- `QStackedWidget` do przełączania kroków,
- `QGraphicsView` + `QGraphicsScene` z `QGraphicsPixmapItem` (tło) + `QGraphicsLineItem` i `QGraphicsEllipseItem` (rysowane wierzchołki/boki),
- `QSlider` dla opacity tła,
- `QPushButton` Cofnij, Dalej, Dodaj połać, Importuj,
- po stronie core: przelicznik skali px→cm i uproszczony normalizator kątów.

Istniejący `DrawingCanvas`, `CanvasMapper`, `ProjectState` i snap engine możesz wykorzystać bezpośrednio lub jako wzorzec — nie ma potrzeby duplikowania logiki.

***

## Podsumowanie ryzyk

| Ryzyko | Poziom | Mitygacja |
| :-- | :-- | :-- |
| Rozpoznawanie linii z obrazu | 🔴 Wysokie | Porzuć, zastąp ręcznym rysowaniem |
| Normalizacja kątów po narysowaniu | 🟡 Średnie | Iteracyjny snap per-bok, bez automatycznej symetrii |
| Brak kalibracji skali | 🔴 Wysokie | Dodaj krok kalibracji przed rysowaniem |
| Liczba połaci z góry | 🟡 Średnie | Zastąp dynamicznym "Dodaj kolejną" |
| Złożoność UX wizarda | 🟢 Niskie | QWizard + QStackedWidget → gotowy w Qt |

END
<span style="display:none">[^1][^2]</span>

<div align="center">⁂</div>

[^1]: rzut-obrys.jpg

[^2]: prawdziwy-rzut-2.jpg

