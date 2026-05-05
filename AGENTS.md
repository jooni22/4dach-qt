# Repository Guidelines

## Project Structure & Module Organization
The application is a PySide6 desktop app. Root files contain entrypoints and assets such as `__main__.py`, `mainwindow.py`, `form.ui`, `config.json`, `app_icons.py`, and `persistence.py`. Put domain logic in `core/` (`geometry.py`, `layout_engine.py`, `models.py`, `project_state.py`, `reporting.py`, `canvas_mapper.py`). Keep Qt Widgets code in `ui/`, with dialog classes under `ui/dialogs/` and canvas helpers under `ui/canvas/`. Tests live in `tests/`. Local reference material may exist under `docs/`; treat `_TODO/` and user-linked briefs as the primary handoff sources.

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

## Work Modes
Default to the lightest process that safely fits the task.

### Fast Path
Use this for local, low-risk changes:

- one file or one narrow behavior
- no serialization or persistence changes
- no startup/save/open flow changes
- no modal-dialog behavior changes
- no changes to `ui/drawing_canvas.py`, `ui/main_window.py`, `core/project_state.py`, `core/layout_engine.py`, or `persistence.py`

Workflow:

- read only the directly relevant files
- make the minimal correct change
- run only the most relevant tests
- lint only touched files
- do not run the full test suite by default

### Standard Path
Use this for moderate scoped changes:

- 2-5 touched files
- normal UI wiring or module-level logic
- regression risk is local but not trivial

Workflow:

- read the relevant implementation and nearby tests
- update or add targeted tests when behavior changes
- run targeted tests for touched areas
- lint only touched files
- run full `uv run pytest` only if the change looks broader or targeted runs suggest spillover

### Deep Path
Use this for high-risk or cross-cutting changes:

- touches `persistence.py`, `core/project_state.py`, `core/layout_engine.py`, `ui/drawing_canvas.py`, or startup/save/open flows in `ui/main_window.py`
- changes project file format, migrations, or serialization
- broad refactor or more than 5 touched files
- explicit user request for high-confidence validation

Workflow:

- broader code reading is allowed
- targeted tests first, then full `uv run pytest`
- lint touched files
- repo-wide checks only when needed by the task or explicitly requested

## Coding Style & Naming Conventions
Target Python 3.11. Use 4-space indentation, double quotes, and keep lines within Ruff’s `100`-character limit. Follow existing naming: `snake_case` for modules/functions, `PascalCase` for classes, descriptive test names starting with `test_`. Keep geometry and layout logic in `core/`; keep pixel mapping, painting, and widget behavior in `ui/`. Preserve compatibility shims and public import surfaces when refactoring.

## Testing Guidelines
The suite uses `pytest` with `pytest-qt`; `tests/conftest.py` sets `QT_QPA_PLATFORM=offscreen`, so UI tests run headless. Add or update tests with every behavior change, especially for `ui/drawing_canvas.py` and `ui/main_window.py`. Mirror the existing split: pure logic in files like `test_geometry.py`, UI behavior in files like `test_drawing_canvas.py`.

## Verification Policy
- Default to targeted verification first.
- Use direct `pytest` paths for the touched area.
- Run full `uv run pytest` for Deep Path tasks, when the user asks for full verification, or when targeted runs indicate wider fallout.
- Run `uv run ruff check` on touched files by default.
- Do not run repo-wide `ruff check .`, `ruff format .`, `deptry .`, or `vulture .` unless the task is cleanup/tooling/CI-related or the user explicitly asks for it.

## Boundary Cases
If the task sits between a quick patch and a deeper validation pass, ask one short question before proceeding.

Offer:

- quick change: minimal analysis, minimal patch, targeted verification
- fuller pass: broader analysis, more tests, deeper validation

Unless the user prefers otherwise, choose:

- Fast Path for local fixes
- Deep Path for persistence, serialization, startup/save/open, modal-dialog flows, or broad UI contract changes

## Instruction Priority
For agent behavior, treat `AGENTS.md` as the process source of truth for this repo.

Priority order:

1. direct user request
2. `AGENTS.md`
3. task-specific brief or handoff explicitly referenced by the user
4. code and tests
5. reference documentation
6. historical plans, TODOs, and workflow logs

Historical plans and workflow transcripts are reference-only unless the user explicitly points to them.

## Commit & Pull Request Guidelines
Recent commits favor short imperative subjects with prefixes such as `fix:`, `refactor:`, `docs:`, and `test:`. Keep each commit scoped to one concern. For pull requests, summarize the user-visible change, list the verification commands you ran, and include screenshots or short recordings for canvas or window-level UI changes. If a change touches Qt wiring, mention any signal/slot or persistence risk explicitly.
