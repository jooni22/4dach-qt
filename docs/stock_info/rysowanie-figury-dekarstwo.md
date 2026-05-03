To świetne podejście UX – tzw. predictive snapping (przewidujące przyciąganie) znacznie przyspiesza pracę w CAD-zie. Aby Twój algorytm rozpoznawał intencje, musisz uwzględnić fakt, że dekarstwo to w 95% przypadków geometria oparta na równoległości i prostopadłości względem okapu (linii startowej).
Oto kompletna lista figur (wycinków), które Twój program powinien "mieć w głowie", aby poprawnie podpowiadać prowadnice:
## 1. Figury Podstawowe (90% przypadków)

* Prostokąt / Kwadrat: Najprostszy wycinek (np. dach dwuspadowy, okno, komin).
* Logika podpowiedzi: Jeśli 1. i 2. punkt tworzą linię poziomą, a kursor idzie w górę pod kątem 90°, wymuszaj prostokąt.
* Trapez Równoramienny: Typowa główna połać dachu kopertowego.
* Logika podpowiedzi: Po narysowaniu podstawy, jeśli kursor idzie do środka pod kątem (zazwyczaj 30°, 45°, 60°), szukaj lustrzanego punktu po drugiej stronie.
* Trójkąt Równoramienny: Ścianka boczna (namiotowa) dachu.
* Logika podpowiedzi: Kursor dąży do przecięcia się dwóch skosów dokładnie nad środkiem podstawy.

## 2. Figury Specjalistyczne (Wymagają inteligentnego snapowania)

* Trapez Prostokątny: Występuje, gdy dach łączy się ze ścianą wyższego budynku (ogniomurem). Jedna strona pionowa (90°), druga skośna (np. kosz).
* Równoległobok: Bardzo częsty przy tzw. "połaciach przechodnich" lub nowoczesnych stodołach z przesuniętą kalenicą.
* L-kształt / Poligony wklęsłe: Wycięcie narożne, np. gdy w rogu dachu jest taras lub uskok muru.
* Wyzwanie dla CAD: Musisz snapować do kątów 90° i 270° (kąty wewnętrzne).

## 3. Figury "Trudne" (Krzywoliniowe aproksymowane)
W dekarstwie rzadko rysuje się łuki "z ręki", zazwyczaj to zbiór krótkich odcinków:

* Wycinek koła / Elipsy (Wole Oko): Jeśli użytkownik stawia 3 punkty blisko siebie, które nie tworzą linii prostej, Twój program mógłby sugerować przejście w tryb łuku (Spline) lub aproksymację wielobokiem.
* Wycinek pierścienia kołowego: Widok z góry na dachy wieżyczek lub półokrągłe apsydy.

## 4. Specyficzne "Wycinki-Otwory" (Holes)
Oprócz kształtów zewnętrznych, Twój system snapowania musi rozpoznawać relację do krawędzi zewnętrznej:

* Wcięcie krawędziowe (U-shape): Wycięcie "kęsa" z brzegu połaci (np. pod komin, który stoi na skraju).
* Otwór wewnętrzny (Donut): Klasyczne okno/komin – tutaj snapowanie powinno sugerować równoległość do najbliższej krawędzi połaci (zazwyczaj okna montuje się równolegle do krokwi).

## Jakie kąty "zaszyć" w miękkim snapie?
Dekarze pracują na konkretnych nachyleniach. Twoje prowadnice powinny priorytetyzować:

   1. 0° / 90° / 180° / 270° – absolutna podstawa.
   2. 45° – najczęstszy kąt w koszach i grzbietach przy dachach o tym samym nachyleniu.
   3. 30° i 60° – bardzo częste w lukarnach i architekturze tradycyjnej.

Rada techniczna: Przy tworzeniu bazy danych, każdą z tych figur traktuj jako zamknięty poligon (listę punktów Vector2). Dodaj do każdej figury flagę isConvex (czy wypukła) – figury wklęsłe (L-kształtne) wymagają innej logiki przy automatycznym wyliczaniu powierzchni krycia materiałem.
Czy Twój program ma już zaimplementowaną logikę wykrywania kolizji (np. żeby użytkownik nie narysował komina "wiszącego" poza dachem)?

