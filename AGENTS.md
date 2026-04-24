# Instrukcje dla Agentów AI i Programistów (AGENTS.md)

Ten projekt korzysta z narzędzia **uv** do zarządzania środowiskiem oraz ściśle wymaga języka **Python w wersji 3.11**. Aby zapobiec problemom z zależnościami i wersjami Pythona, zawsze stosuj poniższe reguły.

## 1. Środowisko i wersja Pythona
- Środowisko wirtualne znajduje się w katalogu `.venv`.
- Jeśli system lub terminal na to pozwala (np. za pomocą `direnv`), środowisko aktywowane jest automatycznie (patrz plik `.envrc`).
- Jeśli środowisko nie zostało aktywowane automatycznie, **zawsze używaj przedrostka `uv run`**. Zagwarantuje to użycie poprawnego Pythona 3.11.

## 2. Uruchamianie projektu
Aby uruchomić aplikację lub główny skrypt, użyj:
```bash
uv run python3 __main__.py
```
*(Wykonywanie samego `python3` zadziała poprawnie tylko, jeśli wcześniej użyto `source .venv/bin/activate`)*.

## 3. Uruchamianie testów
W projekcie skonfigurowano środowisko do testowania GUI (PySide6) używając `pytest` oraz `pytest-qt`. Aby odpalić wszystkie testy:
```bash
uv run pytest
```

## 4. Dodawanie zależności
Zależności projektu zarządzane są przez `uv`. Zamiast standardowego `pip install`, dodawaj nowe pakiety w ten sposób:
```bash
uv add nazwa_pakietu
uv add --dev nazwa_pakietu_dev
```

Trzymając się komendy `uv run` masz pewność, że wykonujesz kod we właściwie odizolowanym i spójnym środowisku.
