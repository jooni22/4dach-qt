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
│   ├── models.py            # Modele domenowe (RoofPlane, Material, SheetPlacement)
│   ├── geometry.py           # Operacje geometryczne (Polygon2D, Bounds2D)
│   ├── layout_engine.py      # Silnik generowania rozkładu arkuszy
│   ├── project_state.py     # Stan projektu, zarządzanie połaciami
│   └── reporting.py         # Generowanie raportów HTML/BOM
├── ui/
│   ├── main_window.py       # Główne okno aplikacji
│   ├── drawing_canvas.py    # Canvas do rysowania geometrii
│   ├── workspace.py         # Kontroler zakładek dla połaci
│   ├── dialogs.py           # Dialogi (kształty, blachy, dane firmy)
│   └── theme_manager.py     # Obsługa jasnego/ciemnego motywu
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

- `core/models.py` — definicje modeli danych
- `core/geometry.py` — klasa Polygon2D i operacje geometryczne
- `core/layout_engine.py` — logika generowania rozkładu arkuszy
- `core/project_state.py` — zarządzanie stanem projektu
- `ui/main_window.py` — główne okno Qt
- `ui/drawing_canvas.py` — canvas do rysowania

## Referencje

Dokumentacja algorytmu i testów: `docs/knowledge/plan-logiki-i-testow.md`
