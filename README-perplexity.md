# 4Dach — Kalkulator Rozkroju Blachodachówki

## Opis projektu

**4Dach** to desktopowa aplikacja do kalkulacji rozkroju blachodachówki na dachy. Program umożliwia:
- Definiowanie kształtów połaci dachowych (prostokąt, trójkąt, trapez, dowolny wielobok)
- Dodawanie wycinków (okien dachowych, kominów)
- Generowanie automatycznego rozkładu arkuszy blachy z uwzględnieniem modułów
- Obsługę dwóch typów materiałów: **dachówkowa** i **trapezowa**
- Ręczną edycję i korektę wygenerowanych arkuszy
- Generowanie raportów (BOM, koszty, odpady)
- Zapis/odczyt projektu do formatu JSON

## Stack technologiczny

- **Python 3.11+**
- **PySide6** (Qt for Python) — GUI
- **uv** — menedżer pakietów i środowisk
- **pytest** + **pytest-qt** — testowanie (w tym GUI)

## Struktura projektu

```
4dach/
├── __main__.py              # Punkt wejścia aplikacji
├── core/
...
├── ui/
...
├── tests/                   # Testy jednostkowe i integracyjne
├── docs/knowledge/          # Dokumentacja techniczna
├── AGENTS.md                # Instrukcje dla agentów AI
└── pyproject.toml           # Konfiguracja projektu
```

## Instrukcje

### Uruchomienie aplikacji

```bash
uv run python3 __main__.py
```

### Uruchomienie testów

```bash
uv run pytest
```

### Dodawanie pakietów

```bash
uv add nazwa_pakietu
uv add --dev nazwa_pakietu_dev
```

## Kluczowe koncepcje

### Model danych
- **RoofPlane** — połać dachowa z obrysem, wycinkami, materiałem i ustawieniami generacji
- **Material** — definicja blachy (szerokość efektywna, długości min/max, moduły, cena)
- **SheetPlacement** — pojedynczy arkusz z pozycją, wymiarami i źródłem (auto/manual)

### Silnik rozkroju
Generuje pionowe pasy na podstawie `effective_width_cm` materiału, przecina je z geometrią połaci netto, tworzy segmenty pionowe, normalizuje długości zgodnie z regułami materiału (moduły dla dachówkowej, ciągłe dla trapezowej).

### Tryby pracy
- **rysowanie obrysu** — definiowanie kształtu połaci
- **rysowanie wycinku** — dodawanie otworów w połaci
- **edycja punktów** — modyfikacja geometrii
- **ustawianie punktu zerowego** — konfiguracja początku układu współrzędnych

### Kierunek układania
- **od lewej** / **od prawej** — kierunek generacji pasów
- **od bazy** — linia bazowa dla modułowego taktowania

## Pliki do załączenia


## Referencje

Dokumentacja algorytmu i testów: `docs/knowledge/plan-logiki-i-testow.md`
