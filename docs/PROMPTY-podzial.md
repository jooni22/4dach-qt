# Podział `docs/PROMPTY.txt` na grupy i etapy

Źródło: `docs/PROMPTY.txt`.

Cel tego dokumentu: krótko uporządkować zawartość źródła i wskazać, co jest właściwym promptem wykonawczym, a co tylko komentarzem organizacyjnym.

Uwaga: wzmianki o cleanupie są artefaktem starszej wersji tekstu i nie są częścią właściwego planu realizacji poniższej serii promptów.

## Grupa 1: Meta-instrukcje i rekomendacja kolejności

Ta grupa obejmuje wyłącznie komentarze organizacyjne z początku i końca pliku, a nie zadania implementacyjne.

### Trzy uwagi analityczne

1. Kolejność cleanupu A -> B -> C została opisana jako logiczna, ale nie stanowi części tej serii wdrożeniowej.
2. `undo_stack_depth` istnieje już w `AppSettings`, ale według analizy nie jest używany w logice `DrawingCanvas`.
3. Cleanup i poprawki freehand zostały jawnie rozdzielone na dwie osobne serie prac i nie powinny być mieszane w jednym branchu.

### Rekomendacja

Najpierw należy wykonać serię promptów korekcyjnych freehand, a dopiero później ewentualny cleanup w osobnym branchu.

### Kolejność wysyłania

Źródło wskazuje następującą kolejność:

1. Najpierw `Prompt A`.
2. Następnie `Prompt B`.

## Grupa 2: Seria promptów korekcyjnych freehand

### Etap 1 / Prompt A

**Cel**

Podłączyć istniejące ustawienia renderingu i inferencji w `DrawingCanvas`, tak aby były faktycznie respektowane podczas rysowania i edycji.

**Zakres**

- `show_decimal_cm`
- `show_edge_length_labels`
- brakująca inferencja typu `edge_extension`

**Pliki**

- `ui/drawing_canvas.py`

**Zależności**

Brak zależności od innych etapów wykonawczych; to pierwszy krok zalecany przed większą zmianą undo/redo.

**Ryzyko**

Małe, lokalne poprawki renderingu i inferencji; niskie ryzyko regresji przy zachowaniu obecnej architektury.

**Kryteria akceptacji**

- Ustawienie `show_decimal_cm` wpływa na format etykiet długości.
- Ustawienie `show_edge_length_labels` faktycznie steruje widocznością etykiet krawędzi.
- Inferencja `edge_extension` pojawia się podczas rysowania zgodnie z istniejącą logiką inferencji.
- Zmiany respektują istniejący przełącznik `show_inferences`.

### Etap 2 / Prompt B

**Cel**

Dodać lokalny stos undo/redo dla zakończonych zmian geometrii, bez przenoszenia odpowiedzialności poza `DrawingCanvas`.

**Zakres**

- undo/redo geometrii po zakończeniu rysowania

**Pliki**

- głównie `ui/drawing_canvas.py`
- opcjonalnie `ui/main_window.py`, tylko jeśli skróty klawiaturowe wymagałyby dodatkowego podłączenia

**Zależności**

Etap zależny od stabilnego stanu po `Prompt A`; źródło rekomenduje wykonać go dopiero po wcześniejszych małych poprawkach freehand.

**Ryzyko**

Większa, ale nadal lokalna zmiana w obszarze edycji geometrii; wyższe ryzyko niż w Etapie 1 z uwagi na stan, skróty i cofanie operacji.

**Kryteria akceptacji**

- Istnieje stos undo/redo dla edycji geometrii po zakończeniu rysowania.
- Cofanie i ponawianie działa dla typowych mutacji geometrii opisanych w promptcie.
- Skróty klawiaturowe działają bez naruszenia obecnego undo szkicu w trybie aktywnego freehand.
- Załadowanie nowej połaci czyści stos undo/redo.

## Sekwencja realizacji

1. Prompt A
2. Prompt B

Bez cleanupu.

Bez mieszania obu serii prac w jednym opisie.
