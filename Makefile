.PHONY: test test-ui test-unit test-review test-expectations run lint clean install help

# Domyślny target
.DEFAULT_GOAL := help

# Zmienne
PYTHON := uv run python3
UV := uv
PYTEST := uv run pytest

# Target: help - wyświetla dostępne targety
help:
	@echo "Dostępne targety:"
	@echo "  make test              - uruchamia wszystkie testy"
	@echo "  make test-ui          - uruchamia tylko testy UI (wymaga PySide6)"
	@echo "  make test-unit        - uruchamia tylko testy jednostkowe (bez UI)"
	@echo "  make test-review      - pokazuje oczekiwania testów i uruchamia wszystkie testy"
	@echo "  make test-expectations - pokazuje tylko oczekiwane dane/wyniki wszystkich testów"
	@echo "  make run              - uruchamia aplikację"
	@echo "  make lint             - uruchamia lintowanie (jeśli dostępne)"
	@echo "  make clean            - czyści pliki tymczasowe i cache"
	@echo "  make install          - instaluje zależności"
	@echo "  make help             - wyświetla tę pomoc"

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

# Target: test-review - pokazuje oczekiwania testów i uruchamia wszystkie testy
test-review:
	@echo "=== Przeglad oczekiwan testow + uruchomienie ==="
	$(PYTHON) scripts/review_and_run_tests.py -q

# Target: test-expectations - pokazuje tylko oczekiwane dane/wyniki wszystkich testów
test-expectations:
	@echo "=== Oczekiwane dane i wyniki wszystkich testow ==="
	$(PYTHON) scripts/print_test_expectations.py

# Target: run - uruchamia aplikację
run:
	@echo "Uruchamianie aplikacji..."
	$(PYTHON) __main__.py

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
	$(UV) sync
	@echo "Instalacja zakończona."
