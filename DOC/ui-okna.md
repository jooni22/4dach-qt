
### 1. Okna wywoływane z menu KSZTAŁT

Służą one do parametrycznego, precyzyjnego generowania bazowych obrysów dachu. We wszystkich tych oknach na dole znajdują się dwa przyciski akcji: **[X Anuluj]** oraz **[OK]** (z ikoną zielonego ptaszka).

#### A. Kształt -> Prostokąt 
*   **Tytuł okna:** Prostokąt
*   **Zawartość:**
    *   `Szerokość`: pole liczbowe z suwakiem (strzałki góra/dół). Jednostka: **cm**. Wartość na filmie: 300.
    *   `Wysokość`: pole liczbowe z suwakiem. Jednostka: **cm**. Wartość na filmie: 300.

#### B. Kształt -> Trójkąt 
*   **Tytuł okna:** Trójkąt
*   **Zawartość:**
    *   Opcje wyboru (Radio buttons) określające typ trójkąta:
        *   `równoramienny` (zaznaczony domyślnie)
        *   `prostokątny`
        *   `dowolny`
    *   `Podstawa`: pole liczbowe z suwakiem. Jednostka: **cm**. Wartość na filmie: 300.
    *   `Wysokość`: pole liczbowe z suwakiem. Jednostka: **cm**. Wartość na filmie: 300.
    *   `[ ] Ramię`: pole wyboru (checkbox) z przypisanym polem liczbowym. Jednostka: **cm**. Wartość na filmie: 400. *(Zauważ: gdy wybrany jest trójkąt równoramienny, pole wprowadzania "Ramię" jest wyszarzone/nieaktywne).*

#### C. Kształt -> Trapez   
*   **Tytuł okna:** Trapez
*   **Zawartość:**
    *   Opcje wyboru (Radio buttons) określające typ trapezu:
        *   `równoramienny` (zaznaczony domyślnie)
        *   `prostokątny`
    *   `Podstawa dolna`: pole liczbowe z suwakiem. Jednostka: **cm**. Wartość na filmie: 500.
    *   `górna` (opisane zaraz obok pola 'Podstawa dolna'): pole liczbowe z suwakiem. Jednostka: **cm**. Wartość na filmie: 300.
    *   `Wysokość`: pole liczbowe z suwakiem. Jednostka: **cm**. Wartość na filmie: 300.

---

### 2. Okna wywoływane z menu KATALOG

Służą do konfiguracji parametrów globalnych projektu oraz zarządzania biblioteką materiałów.

#### A. Katalog -> Dane firmy... 
Okno służące do wprowadzania danych wykonawcy/firmy, które następnie zaczytywane są do generowanego raportu.
*   **Tytuł okna:** Dane firmy
*   **Zawartość:**
    *   `Nazwa firmy:` pole tekstowe. Wartość: *Super Dach Bis Jerzy Zimnoch* 
    *   `NIP:` pole tekstowe (obok nazwy firmy). Wartość: *542-030-52-23*.
    *   `Adres:` duże pole tekstowe (wielolinijkowe). Wartość: *Ogrodniki ul. Rubinowa 10 16-002 Dobrzyniewo Duże*.
    *   `Adres strony WWW:` pole tekstowe. Wartość: *superdachbis.pl*.
    *   `Logo firmy:` pole tekstowe (prawdopodobnie na wpisanie nazwy pliku lub ścieżki). Wartość: *test*.
*   **Przyciski:** **[X Anuluj]** oraz **[OK]**.

#### B. Katalog -> Blachy... 
Jest to moduł zarządzania materiałami, składający się z okna głównego ("Blachy") oraz okna edycji ("Dane blachy").

**Okno Główne: "Blachy"**
*   **Tytuł okna:** Blachy
*   **Z lewej strony:** Puste pole w formie listy, na której widnieje jeden element: `PD510` (zaznaczony).
*   **Z prawej strony (podgląd parametrów wybranego elementu):**
    *   Szerokość efektywna arkusza: 51 cm
    *   Maks. długość arkusza: 900 cm
    *   Zapas dolny: 10 cm
    *   Zapas górny: 80 cm
    *   Min. długość arkusza: 0 cm
    *   Odległość między łatami: 0 cm
    *   Odległość między kontrłatami: 0 cm
    *   Moduły: (puste białe pole w formie listy)
    *   Cena za m2: 10,00 zł
*   **Przyciski akcji (pod parametrami):** **[+ Dodaj]**, **[Edycja]**, **[- Usuń]**.
*   **Przycisk zamykania (na samym dole):** **[X Zamknij]**.

**Okno Edycji: "Dane blachy" (Otwiera się po kliknięciu "Edycja" lub "Dodaj")**
*   **Tytuł okna:** Dane blachy
*   **Typ blachy (radio buttons):** `dachówkowa` (zaznaczone) lub `trapezowa`.
*   **Pola wprowadzania parametrów (wartości z filmu dla edycji 'PD510'):**
    *   `Nazwa:` [test / PD510]
    *   `Szerokość efektywna arkusza:` [51] cm
    *   `Długość modułu:` [25] cm
    *   `Zapas dolny:` [10] cm
    *   `Zapas górny:` [80] cm
    *   `Minimalna długość arkusza:` [20] cm
    *   `Odległość między łatami:` [10] cm
    *   `Odległość między kontrłatami:` [0] cm
*   **Sekcja "moduły":**
    *   Rozwijana lista z suwakiem (widoczna wartość `1`).
    *   Przyciski **[+]** i **[-]** (do dodawania/usuwania zdefiniowanych długości modułów).
    *   Białe, puste pole listy poniżej.
*   **Sekcja cenowa:**
    *   `Cena za` -> Radio buttons: `m2` (zaznaczone) lub `mb`.
    *   Pole na złotówki: [10] `zł`.
    *   Pole na grosze: [0] `gr`.
*   **Przyciski:** **[X Anuluj]** oraz **[OK]**.

---

### 3. Okna dialogowe systemu / Pop-upy

#### A. Ostrzeżenie przy czyszczeniu połaci 
Pojawia się po wywołaniu opcji "Wyczyść aktywną połać" (wywoływanej z menu ikona szczotki).
*   **Tytuł okna:** Ostrzeżenie
*   **Ikona:** Żółty trójkąt z wykrzyknikiem.
*   **Treść komunikatu:** *Czy na pewno wyczyścić aktywną połać?*
*   **Przyciski:** **[X Anuluj]** oraz **[OK]**.