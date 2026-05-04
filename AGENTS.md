# Repository Guidelines

## Project Structure & Module Organization
The application is a PySide6 desktop app. Root files contain entrypoints and assets such as `__main__.py`, `mainwindow.py`, `form.ui`, `config.json`, `app_icons.py`, and `persistence.py`. Put domain logic in `core/` (`geometry.py`, `layout_engine.py`, `models.py`, `project_state.py`, `reporting.py`, `canvas_mapper.py`). Keep Qt Widgets code in `ui/`, with dialog classes under `ui/dialogs/` and canvas helpers under `ui/canvas/`. Tests live in `tests/`. Reference material and active plans are under `docs/documentations/`, `docs/latest_todo/`, and `_TODO/`.

## Build, Test, and Development Commands
Use `uv` for the local environment.

- `uv sync` or `make install`: install runtime and dev dependencies into `.venv`.
- `uv run python __main__.py` or `make run`: start the desktop app.
- `uv run pytest` or `make test`: run the full suite.
- `uv run pytest tests/test_models_and_state.py -q`: fast non-UI regression pass.
- `uv run pytest tests/test_mainwindow_ui_contract.py -q`: focused Qt/UI contract test.
- `uv run python scripts/review_and_run_tests.py -q`: print test expectations, then run tests.
- `uv run ruff check .` and `uv run ruff format .`: lint and format Python code.

Prefer direct `pytest` paths for focused runs; they are more reliable than older Makefile shortcuts.

## Coding Style & Naming Conventions
Target Python 3.11. Use 4-space indentation, double quotes, and keep lines within Ruff’s `100`-character limit. Follow existing naming: `snake_case` for modules/functions, `PascalCase` for classes, descriptive test names starting with `test_`. Keep geometry and layout logic in `core/`; keep pixel mapping, painting, and widget behavior in `ui/`. Preserve compatibility shims and public import surfaces when refactoring.

## Testing Guidelines
The suite uses `pytest` with `pytest-qt`; `tests/conftest.py` sets `QT_QPA_PLATFORM=offscreen`, so UI tests run headless. Add or update tests with every behavior change, especially for `ui/drawing_canvas.py` and `ui/main_window.py`. Mirror the existing split: pure logic in files like `test_geometry.py`, UI behavior in files like `test_drawing_canvas.py`.

## Commit & Pull Request Guidelines
Recent commits favor short imperative subjects with prefixes such as `fix:`, `refactor:`, `docs:`, and `test:`. Keep each commit scoped to one concern. For pull requests, summarize the user-visible change, list the verification commands you ran, and include screenshots or short recordings for canvas or window-level UI changes. If a change touches Qt wiring, mention any signal/slot or persistence risk explicitly.
