# SKILL: Python Project Cleanup Protocol

> Role: Senior DevOps & Python Automation Engineer
> Task: Refaktoryzacja i "sprzątanie" projektów Python, ze szczególnym uwzględnieniem aplikacji Desktop GUI (PyQt / PySide6).
> Ten dokument służy jako instrukcja techniczna dla agentów AI. Przed każdym sprzątaniem przeczytaj go w całości.

---

## 1. Mapowanie problemów na narzędzia

| Problem | Narzędzie | Autofix? | Uwagi |
|---|---|---|---|
| Nieposortowane / zbędne importy | **Ruff** (`I`, `F401`) | **TAK** (`--fix`) | Zastępuje autoflake, isort, flake8 |
| Martwy kod (nieużywane funkcje, klasy, zmienne) | **Vulture** | **NIE** (tylko raport) | Dużo false-positives w GUI — patrz sekcja 4 |
| Nieuzużywane / brakujące / błędne zależności w `pyproject.toml` | **deptry** | **NIE** (tylko raport) | Wymaga zainstalowanego venv |
| Przestarzała składnia Pythona | **Ruff** (`UP`) | **TAK** (`--fix`) | np. `list()` zamiast `[]` |
| Proste bug patterny | **Ruff** (`B`, `C4`, `SIM`) | **TAK** (`--fix`) | |

**Rekomendacja**: Ruff to podstawa. Vulture i deptry to uzupełnienie. **Nigdy nie uruchamiaj Vulture bez wcześniejszego Ruff** — Ruff usuwa zbędne importy, co zmniejsza szum w Vulture.

---

## 2. Konfiguracja standardowa

### `pyproject.toml` — sekcje [tool.*]

```toml
# === Ruff: all-in-one linter & formatter ===================================
[tool.ruff]
target-version = "py311"
line-length = 100
exclude = [
    "ui_form.py",        # wygenerowany przez uic
    "app_icons.py",      # duże statyczne dane
    "*_rc.py",           # zasoby Qt
    ".venv", "__pycache__", "build", "dist",
]

[tool.ruff.lint]
select = ["F", "E", "W", "I", "UP", "B", "C4", "SIM"]
ignore = ["E501"]
fixable = ["F", "I", "UP", "B", "C4", "SIM"]

[tool.ruff.lint.isort]
known-first-party = ["core"]   # dostosuj do nazwy projektu

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

# === Vulture: dead-code detection ==========================================
[tool.vulture]
exclude = ["ui/", "ui_form.py", "tests/", ".venv/", "build/", "dist/"]
min_confidence = 80
paths = ["."]

# === deptry: dependency health ===============================================
[tool.deptry]
exclude = [".venv", "build", "dist", ".codex"]

[tool.deptry.per_rule_ignores]
DEP002 = ["pillow", "pytest-image-snapshot", "pytest-qt", "ruff", "vulture", "deptry"]
```

---

## 3. Procedura bezpiecznego wykonania (Safety & Workflow)

> **Złota zasada**: Każde narzędzie / typ zmiany = osobny branch. Nigdy nie sprzątaj bezpośrednio na `main`.

### Krok 1 — Izolacja brancha
```bash
git checkout -b fix/cleanup-<tool-name>   # np. fix/cleanup-imports-ruff
```

### Krok 2 — Dry-run (opcjonalnie, szczególnie dla Vulture)
```bash
# Ruff — pokaż co zmieni, ale nie zapisuj
ruff check . --diff

# deptry — tylko raport
deptry .

# Vulture — tylko raport
vulture .
```

### Krok 3 — Wykonanie
```bash
# Ruff (autofix)
ruff check . --fix
ruff format .

# deptry — ręczna naprawa na podstawie raportu
# Vulture — ręczna naprawa na podstawie raportu + whitelist
```

### Krok 4 — Weryfikacja (obowiązkowa!)
```bash
pytest
```
Jeśli testy nie przechodzą — **cofnij zmiany** (`git restore`) i zbadaj który import / kod był używany dynamicznie.

### Krok 5 — Commit atomowy
```bash
git add -p
git commit -m "refactor: remove unused imports using Ruff"
# lub
# git commit -m "refactor: remove dead code identified by Vulture"
# lub
# git commit -m "chore: fix dependency declarations (deptry)"
```

### Krok 6 — Pull Request (agent NIE merguje!)
```bash
gh pr create --title "cleanup: Ruff import & format pass" \
  --body "Tool: Ruff vX.Y.Z\nScope: auto-fix unused imports + format\nTests: pytest passed\nPyQt/PySide6 verification: checked for signal/slot connections and .ui files"
```

---

## 4. Pułapki PyQt / PySide6 — CRITICAL

### 4.1 Vulture: metody łączone sygnałami (slots / `connect()`)

**Problem**: Vulture może oznaczyć metodę `on_button_clicked` lub `slot_method` jako "martwy kod", bo nie widzi dynamicznego połączenia przez `.connect(self.method)`.

**Instrukcja dla Agenta**:
- Przed usunięciem **jakiejkolwiek metody** w klasach dziedziczących po `QWidget`, `QMainWindow` lub `QObject`:
  1. Przeszukaj cały projekt pod kątek tekstowych odwołań do tej nazwy (np. w `connect()`, `QUiLoader`, plikach `.ui` XML).
  2. Jeśli znajdziesz odwołanie w `.ui` lub `connect()` — **nie usuwaj**. Dodaj do `whitelist.py`.

**Tworzenie whitelisty**:
```bash
vulture . --make-whitelist > whitelist.py
```
Następnie zaimportuj `whitelist.py` w Vulture config (`pyproject.toml`):
```toml
[tool.vulture]
paths = [".", "whitelist.py"]
```

### 4.2 Ruff / autoflake: importy zasobów Qt (`_rc`)

**Problem**: W aplikacjach GUI często importuje się zasoby (np. `import resources_rc`) lub moduły inicjalizujące style, które nie są wywoływane bezpośrednio w kodzie. Ruff zgłosi je jako `F401` (unused import).

**Instrukcja dla Agenta**:
- **NIGDY** nie usuwaj importów kończących się na `_rc` (zasoby Qt).
- **NIGDY** nie usuwaj importów modułów rejestrujących wtyczki / sterowniki Qt, nawet jeśli linter zgłasza nieużycie.
- Jeśli Ruff chce usunąć taki import, dodaj **w kodzie źródłowym** komentarz:
  ```python
  import resources_rc  # noqa: F401
  ```

**Ruff config — globalne wykluczenia**:
W `pyproject.toml` już wykluczone zostały `*_rc.py` oraz `ui_form.py`. Jeśli pojawią się nowe pliki generowane — dodaj je do `exclude`.

### 4.3 Pliki `.ui` → `.py` (uic)

**Problem**: Narzędzia statyczne (Ruff, Vulture) nie widzą kodu generowanego z plików `.ui` przez `pyside6-uic`. Jeśli metoda jest wywoływana tylko z wygenerowanego `ui_form.py`, Vulture może uznać ją za martwą.

**Instrukcja dla Agenta**:
- Pliki `ui_form.py` (generowane) powinny być **wykluczone** z analizy (Ruff: `exclude`, Vulture: `exclude`).
- Jeśli narzędzie sugeruje usunięcie metody w klasie GUI — agent musi najpierw przeszukać cały projekt pod kątek tekstowych odwołań (również w plikach `.ui` XML).
- W PR description wymień: *"Zweryfikowano pod kątek powiązań Signal/Slot oraz plików zasobów Qt"*.

---

## 5. Komendy CLI — ściągawka

```bash
# Ruff — lint + auto-fix
ruff check . --fix

# Ruff — format
ruff format .

# Ruff — sprawdź bez zmian (dry-run)
ruff check . --diff

# Vulture — martwy kod (raport)
vulture .

# Vulture — wygeneruj whitelistę
vulture . --make-whitelist > whitelist.py

# deptry — zdrowie zależności
deptry .

# Pre-commit — uruchom wszystkie hooki
uvx pre-commit run --all-files

# Testy — obowiązkowe po sprzątaniu
pytest
```

---

## 6. Pre-commit & CI

### `.pre-commit-config.yaml`
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.12
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/fpgmaas/deptry
    rev: 0.25.1
    hooks:
      - id: deptry

  - repo: https://github.com/jendrikseipp/vulture
    rev: v2.16
    hooks:
      - id: vulture
```

### GitHub Actions (minimalny workflow)
```yaml
name: Lint & Dependency Health
on:
  pull_request:
    branches: [main, master]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install uv
      - run: uv sync
      - run: uv run ruff check . && uv run ruff format --check .
      - run: uv run deptry .
      - run: uv run vulture .
      - run: uv run pytest
```

---

## 7. Smoke Test dla GUI (dodatkowy krok bezpieczeństwa)

Jeśli środowisko pozwala (headless / xvfb dla Linux, lokalnie dla Windows/Mac):

```bash
# Po sprzątaniu GUI — uruchom aplikację i sprawdź,
# czy nie wyrzuca AttributeError przy inicjalizacji okien
uv run python __main__.py --smoke-test
```

Typowe skutki zbyt agresywnego sprzątania w Qt:
- `AttributeError: 'MainWindow' object has no attribute 'on_action_triggered'`
- Brak ikon / stylów (usunięty import `resources_rc`)
- Crash przy otwieraniu dialogu (usunięta metoda slotu)

---

## 8. Checklist przed zakończeniem sesji sprzątania

- [ ] Każde narzędzie na osobnym branchu (`fix/cleanup-*`)
- [ ] Atomowe commity z jasnym opisem narzędzia
- [ ] `pytest` przechodzi po każdym sprzątaniu
- [ ] Sprawdzono sygnały/sloty i pliki `.ui`
- [ ] Sprawdzono importy `_rc` i zasobów Qt
- [ ] PR otwarty, **nie** mergowany bezpośrednio do `main`
- [ ] W opisie PR wymieniono zweryfikowane komponenty UI
