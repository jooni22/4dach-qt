## Getting Started

Relevant source files

This page provides a step-by-step guide for setting up the development environment, running the 4Dach application, executing the test suite, and building the Windows executable. 4Dach is a Python-based CAD application for roof sheet layout, built using PySide6.

## Environment Requirements

The project has strict environment constraints to ensure stability across development and CI environments.

-   Python Version: Strictly requires Python 3.11 [pyproject.toml#5](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L5-L5) [AGENTS.md#4](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L4-L4)
-   Package Manager: Uses uv for dependency management and virtual environment isolation [AGENTS.md#4](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L4-L4)
-   Operating System: Cross-platform (Linux/Windows/macOS) for development, with specialized CI for Windows builds [Makefile#11-23](https://github.com/jooni22/4dach-qt/blob/81f560ca/Makefile#L11-L23) [.github/workflows/build-windows.yml#11](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml#L11-L11)

Sources: [pyproject.toml#5](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L5-L5) [AGENTS.md#4](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L4-L4) [.github/workflows/build-windows.yml#11](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml#L11-L11)

## Development Setup

The project uses `uv` to manage a virtual environment located in `.venv` [AGENTS.md#11](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L11-L11)

1.  Install uv: If not already installed, install the `uv` package manager.
2.  Synchronize Dependencies: Run the following command to create the virtual environment and install all dependencies (including dev tools): _Note: This is equivalent to `make install` [Makefile#79-82](https://github.com/jooni22/4dach-qt/blob/81f560ca/Makefile#L79-L82)_
3.  Activation: You can activate the environment via `source .venv/bin/activate` or use the `uv run` prefix for all commands to guarantee the correct interpreter is used [AGENTS.md#13](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L13-L13) [AGENTS.md#27-29](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L27-L29)

### Tooling Configuration

The environment is pre-configured with several code quality tools defined in `pyproject.toml`:

-   Ruff: Handles linting (rules F, E, W, I, UP, B, C4, SIM) and formatting [pyproject.toml#39-72](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L39-L72)
-   Vulture: Detects dead code with a minimum confidence of 80% [pyproject.toml#74-77](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L74-L77)
-   deptry: Monitors dependency health and identifies unused or missing packages [pyproject.toml#80-86](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L80-L86)

Sources: [pyproject.toml#39-86](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L39-L86) [AGENTS.md#11-29](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L11-L29) [Makefile#79-82](https://github.com/jooni22/4dach-qt/blob/81f560ca/Makefile#L79-L82)

## Running the Application

To start the application, use the `uv run` command targeting the main entry point:

Alternatively, use the provided `Makefile` target:

### Application Bootstrapping Flow

The following diagram illustrates the transition from the command line into the Python code entities.

Entry Point Data Flow

Sources: [Makefile#51-53](https://github.com/jooni22/4dach-qt/blob/81f560ca/Makefile#L51-L53) [pyproject.toml#11-21](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L11-L21) [.github/workflows/build-windows.yml#40-49](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml#L40-L49)

## Executing the Test Suite

The project uses `pytest` along with `pytest-qt` for handling the PySide6 event loop during UI testing [pyproject.toml#31-33](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L31-L33)

### Test Commands

|                     Command                      |               Description                | Makefile Target  |
|--------------------------------------------------|------------------------------------------|------------------|
|                  `uv run pytest`                   | Runs the full test suite AGENTS.md#40-41 |    `make test`     |
|    `uv run pytest tests/test_models_and_state.py`    |       Runs core unit tests (No UI)       |  `make test-unit`  |
| `uv run pytest tests/test_mainwindow_ui_contract.py` |   Runs integration tests requiring Qt    |   `make test-ui`   |
|   `uv run python3 scripts/review_and_run_tests.py`   |   Prints expectations then runs tests    | `make test-review` |

### Testing Infrastructure

Tests are categorized into Core/Geometry (pure logic) and UI/Canvas (interaction-heavy). The `scripts/print_test_expectations.py` file contains a registry of `Expectation` dataclasses that document the intended behavior for complex geometric edge cases [scripts/print\_test\_expectations.py#14-100](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/print_test_expectations.py#L14-L100)

Sources: [pyproject.toml#31-33](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L31-L33) [Makefile#26-49](https://github.com/jooni22/4dach-qt/blob/81f560ca/Makefile#L26-L49) [AGENTS.md#40-48](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L40-L48) [scripts/print\_test\_expectations.py#14-100](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/print_test_expectations.py#L14-L100)

## CI/CD Workflows

The project utilizes GitHub Actions for continuous integration and distribution.

### 1\. Lint & Dependency Health (`lint.yml`)

Triggered on every push or PR to `main`/`master` [.github/workflows/lint.yml#4-7](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L4-L7)

-   Environment: Ubuntu-latest, Python 3.11 [.github/workflows/lint.yml#11-18](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L11-L18)
-   Steps:
    1.  `uv sync` dependencies [.github/workflows/lint.yml#24](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L24-L24)
    2.  `ruff check` and `ruff format --check` [.github/workflows/lint.yml#27](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L27-L27)
    3.  `deptry` check [.github/workflows/lint.yml#30](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L30-L30)
    4.  `vulture` dead-code scan [.github/workflows/lint.yml#33](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L33-L33)
    5.  `pytest` execution [.github/workflows/lint.yml#36](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L36-L36)

### 2\. Build Windows Executable (`build-windows.yml`)

Generates a standalone `.exe` using PyInstaller [.github/workflows/build-windows.yml#40-49](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml#L40-L49)

This workflow is not part of the default `main`/`master` CI path. It runs only when triggered manually with `workflow_dispatch` or when code is pushed to the `cutout-fix` branch.

-   Packaging Strategy: Uses `--onefile` and `--windowed` modes [.github/workflows/build-windows.yml#41-42](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml#L41-L42)
-   Data Bundling: Explicitly includes `config.json`, `form.ui`, and the `core/` and `ui/` packages via `--add-data` [.github/workflows/build-windows.yml#44-47](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml#L44-L47)
-   Artifacts: The resulting binary is uploaded as `4dach-windows-exe` [.github/workflows/build-windows.yml#53-57](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml#L53-L57)

Sources: [.github/workflows/lint.yml#1-37](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L1-L37) [.github/workflows/build-windows.yml#1-58](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml#L1-L58)

## Development Workflow: Stacked PRs

This repository follows a stage-based workflow and supports stacked pull requests via `gh-stack` [AGENTS.md#67-79](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L67-L79)

### Rules for Implementation

# Getting Started

2.  Branching: Never work directly on `main`. Each stage must have its own branch [AGENTS.md#72-73](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L72-L73)
3.  Sequential Stages: If Stage B depends on Stage A, branch Stage B from Stage A's branch, not from `main` [AGENTS.md#76](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L76-L76)
4.  Review Backlog: Before starting, check `docs/review-backlog.md` for unresolved items assigned to the current stage [AGENTS.md#100-104](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L100-L104)
5.  Cleanup Protocol: Follow the "Python Project Cleanup Protocol" (SKILL.md) when refactoring, ensuring that `_rc` (resource) files and signal/slot connections are not accidentally removed by automated tools [docs/SKILL.md#122-166](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/SKILL.md?plain=1#L122-L166)

Codebase Cleanup Hierarchy

Sources: [AGENTS.md#67-110](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L67-L110) [docs/SKILL.md#1-19](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/SKILL.md?plain=1#L1-L19) [\_TODO.md#1-110](https://github.com/jooni22/4dach-qt/blob/81f560ca/_TODO.md?plain=1#L1-L110) [.pre-commit-config.yaml#1-31](https://github.com/jooni22/4dach-qt/blob/81f560ca/.pre-commit-config.yaml#L1-L31)
