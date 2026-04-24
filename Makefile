.PHONY: test test-ui run lint clean install help

# Domyślny target
.DEFAULT_GOAL := help

# Zmienne
PYTHON := python3.11
PIP := pip3
PYTEST := pytest

# Target: help - wyświetla dostępne targety
help:
	@echo "Dostępne targety:"
	@echo "  make test       - uruchamia wszystkie testy"
	@echo "  make test-ui    - uruchamia tylko testy UI (wymaga PySide6)"
	@echo "  make test-unit  - uruchamia tylko testy jednostkowe (bez UI)"
	@echo "  make run        - uruchamia aplikację"
	@echo "  make lint       - uruchamia lintowanie (jeśli dostępne)"
	@echo "  make clean      - czyści pliki tymczasowe i cache"
	@echo "  make install    - instaluje zależności"
	@echo "  make help       - wyświetla tę pomoc"

# Target: test - uruchamia wszystkie testy
test:
	@echo "Uruchamianie wszystkich testów..."
	$(PYTHON) -m pytest tests/ -v

# Target: test-ui - uruchamia testy UI
test-ui:
	@echo "Uruchamianie testów UI (wymaga PySide6)..."
	$(PYTHON) -m pytest tests/test_mainwindow_ui_contract.py -v

# Target: test-unit - uruchamia testy jednostkowe bez UI
test-unit:
	@echo "Uruchamianie testów jednostkowych (bez UI)..."
	$(PYTHON) -m pytest tests/test_models_and_state.py tests/test_geometry.py tests/test_reporting.py tests/test_layout.py -v

# Target: run - uruchamia aplikację
run:
	@echo "Uruchamianie aplikacji..."
	$(PYTHON) mainwindow.py

# Target: lint - uruchamia lintowanie
lint:
	@echo "Próba uruchomienia lintowania..."
	@if command -v ruff >/dev/null 2>&1; then \
		echo "Używanie ruff..."; \
		ruff check .; \
	elif command -v pylint >/dev/null 2>&1; then \
		echo "Używanie pylint..."; \
		pylint core/ tests/ mainwindow.py dialogs.py; \
	else \
		echo "Nie znaleziono ruff ani pylint. Zainstaluj jeden z nich."; \
	fi

# Target: clean - czyści pliki tymczasowe
clean:
	@echo "Czyszczenie plików tymczasowych..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Czyszczenie zakończone."

# Target: install - instaluje zależności
install:
	@echo "Instalowanie zależności..."
	$(PIP) install -r requirements.txt
	@echo "Instalacja zakończona."
