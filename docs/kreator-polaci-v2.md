Masz wdrożyć poprawki w widoku wyboru połaci oraz w powiązanym widoku podglądu w aplikacji Qt. Nie twórz nowej koncepcji, nie proponuj alternatywnych kierunków i nie wracaj do etapu planowania. Masz wdrożyć ustalony kierunek na podstawie poniższych wymagań.

To jest redesign wdrożeniowy, nie brainstorming.

GŁÓWNY CEL
Usprawnij wizualnie i funkcjonalnie widok wyboru połaci oraz podgląd geometrii, zachowując prostotę, minimalizm i układ bardzo zbliżony do referencji:
- lewe okno = wybór figur,
- prawe okno = duży podgląd,
- pod oknami więcej miejsca na inputboxy i funkcje odbicia lustrzanego.

KLUCZOWE OGRANICZENIA — OBOWIĄZUJĄCE
1. Zachowaj wygląd i ogólny podział podobny do referencji: całe okno ma być wizualnie podzielone na dwie główne części.
2. Po lewej stronie ma być biblioteka figur.
3. Po prawej stronie ma być duży podgląd wybranej połaci.
4. Nie dodawaj siatki pomocniczej.
5. Nie zmieniaj tła podglądu.
6. Zachowaj minimalistyczny wygląd podglądu.
7. Wymiary mają być wpisywane wyłącznie przez inputboxy / spinboxy.
8. Nie wolno dodawać przeciągania boków połaci.
9. Jeżeli w tym flow występują wycinki / lukarny, przeciągać na podglądzie można wyłącznie je.
10. W tym widoku nie implementuj walidacji, komunikatów walidacyjnych ani informacji o błędach.
11. Nie implementujemy połaci 10, 11, 12, 13.
12. Dzięki usunięciu połaci 10–13 skróć lewy panel z biblioteką i wykorzystaj odzyskane miejsce pod lewym i prawym panelem na sekcję parametrów oraz funkcje odbicia lustrzanego.

FIGURY MUSZĄ BYĆ DOKŁADNIE TAKIE I W TAKIEJ KOLEJNOŚCI
Użyj dokładnie tych figur od Połać 1 do Połać 9 i dopilnuj, aby miniatura, podgląd oraz mapowanie do geometrii były ze sobą zgodne:

- Połać 1: prostokąt.
- Połać 2: trójkąt równoramienny.
- Połać 3: trapez równoramienny z krótszą górną podstawą.
- Połać 4: równoległobok pochylony w prawo.
- Połać 5: równoległobok pochylony w lewo.
- Połać 6: trapez z prawym bokiem pionowym i lewym bokiem pochyłym.
- Połać 7: trapez z lewym bokiem pionowym i prawym bokiem pochyłym.
- Połać 8: pięciokąt typu „domek”.
- Połać 9: sześciokąt z ściętymi górnymi narożnikami.

Bardzo ważne:
- wcześniej były pomieszane miniatury i mapowanie figur, szczególnie w zakresie 4–9,
- teraz masz to poprawić tak, aby biblioteka miniatur dokładnie odpowiadała rzeczywistej geometrii rysowanej po prawej stronie,
- nie dodawaj połaci 10–13,
- lewy panel ma pokazywać tylko połać 1–9.

UKŁAD OKNA
Zaprojektuj i opisz finalny układ tak, aby:
- okno było wyraźnie podzielone mniej więcej na dwie połowy,
- lewa połowa zawierała bibliotekę figur,
- prawa połowa zawierała duży podgląd,
- sekcja z inputboxami była pod panelem lewym i prawym, z większą ilością miejsca niż obecnie,
- sekcja funkcji odbicia lustrzanego również była umieszczona w dolnej części, a nie jako mało widoczne checkboxy upchnięte przy podglądzie,
- przyciski akcji typu Zatwierdź / Anuluj pozostały czytelne, ale nie dominowały nad podglądem.

BIBLIOTEKA FIGUR — LEWA STRONA
Wymagania:
- pokaż tylko figury Połać 1–9,
- ułóż je w zwartej, czytelnej siatce,
- nie zostawiaj pustej dużej przestrzeni po usunięciu pozycji 10–13,
- zaznaczenie aktywnej figury ma być wyraźne, ale proste,
- miniatury mają być czytelne i poprawne geometrycznie,
- podpisy mają pozostać w formie Połać 1, Połać 2 itd., zgodnie z kolejnością,
- możesz dodać wewnętrzne techniczne nazwy typów w kodzie, ale użytkownik w UI nadal ma widzieć numerację Połać 1–9.

PODGLĄD — PRAWA STRONA
Wymagania:
- podgląd ma być większy niż obecnie i ma pełnić rolę głównego obszaru roboczego,
- bez siatki,
- bez zmiany tła,
- bez efektów dekoracyjnych,
- figura ma być rysowana czytelnie, z dobrym wykorzystaniem przestrzeni,
- podgląd ma natychmiast reagować na zmianę wartości w inputboxach,
- jeśli w danym widoku występuje wycinek / lukarna, jego pozycję można przesuwać na podglądzie,
- nie wolno dodać przeciągania boków połaci.

OZNACZENIA WYMIARÓW
Dodaj czytelne oznaczenia wymiarów bezpośrednio na podglądzie.
Wymagania:
- pokazuj oznaczenia takie jak A, B, C, H, H1, E — zależnie od typu figury,
- oznaczenia mają być umieszczone przy odpowiednich bokach lub wysokościach,
- mają być subtelne i funkcjonalne,
- mają wzmacniać czytelność inputów,
- po focusie na konkretnym inputboxie można wizualnie podkreślić odpowiadający mu wymiar na podglądzie,
- nadal bez siatki i bez przeładowania widoku.

INPUTBOXY
Wymagania:
- inputboxy / spinboxy pozostają jedyną metodą zmiany wymiarów połaci,
- trzeba przeznaczyć na nie więcej miejsca pod głównymi panelami,
- układ pól ma być prosty i czytelny,
- nazwy pól mają odpowiadać oznaczeniom na podglądzie,
- zmiana wartości ma natychmiast odświeżać rysunek,
- w tym widoku nie pokazuj walidacji i nie projektuj komunikatów walidacyjnych.

ODBIECIE LUSTRZANE
Funkcje Flip H i Flip V mają zostać przebudowane.
Wymagania:
- nie jako niepozorne checkboxy,
- potraktuj je jak czytelne narzędzia geometrii,
- umieść je w dolnej sekcji razem z parametrami lub obok nich,
- ich stan ma być jednoznaczny wizualnie,
- kliknięcie ma natychmiast aktualizować podgląd.

ZAKRES IMPLEMENTACJI
Masz przygotować wdrożenie dla:
- widoku wyboru połaci,
- dużego podglądu po prawej stronie,
- dolnej sekcji parametrów,
- funkcji odbicia lustrzanego,
- poprawionych miniaturek Połać 1–9,
- spójnego zachowania podglądu i inputów.

Nie implementuj w tym zadaniu:
- połaci 10,
- połaci 11,
- połaci 12,
- połaci 13,
- siatki,
- zmiany tła podglądu,
- walidacji,
- komunikatów walidacyjnych,
- przeciągania boków połaci.

FORMAT ODPOWIEDZI
Przygotuj odpowiedź wdrożeniową, nie koncepcyjną.
Chcę dostać:

1. Krótki opis finalnego układu okna.
2. Finalny opis lewej części okna.
3. Finalny opis prawej części okna.
4. Finalny opis dolnej sekcji z inputboxami i odbiciem lustrzanym.
5. Dokładną listę figur Połać 1–9 i ich poprawnego mapowania.
6. Listę konkretnych zmian do wdrożenia w Qt.
7. Listę widgetów / klas / obszarów UI do zmiany.
8. Kolejność implementacji krok po kroku.
9. Krótką checklistę QA, ale tylko pod kątem zgodności figur, układu, inputów, podglądu i odbicia lustrzanego.

WAŻNE
- Nie analizuj wariantów.
- Nie proponuj innych układów niż układ lewa strona wybór / prawa strona podgląd.
- Nie dodawaj nowych połaci ponad 1–9.
- Nie dodawaj walidacji.
- Nie opisuj „co można rozważyć”.
- Masz opisać i wdrożyć dokładnie ten kierunek.
