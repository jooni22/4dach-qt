## Developer Tooling & CI/CD

Relevant source files

This page provides an overview of the development ecosystem for 4Dach, including the automated quality gates, the Python environment management strategy, and the structured pull request workflow. The project prioritizes reproducibility through `uv` and rigorous static analysis to manage the complexities of a geometry-heavy CAD application.

## Development Environment

The project strictly requires Python 3.11 and utilizes uv for dependency management and virtual environment isolation [AGENTS.md#4-5](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L4-L5) To ensure consistency across developer machines and CI environments, all commands are prefixed with `uv run` [AGENTS.md#13](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L13-L13)

### Tooling Stack

The project employs a multi-layered linting and analysis suite to maintain code health:

# Developer Tooling & CI/CD

|  Tool   |                         Purpose                          |                   Configuration                   |
|---------|----------------------------------------------------------|---------------------------------------------------|
|  Ruff   | All-in-one linter and formatter (replaces isort, flake8) |        `[tool.ruff]` in pyproject.toml#39-72        |
| Vulture |   Dead-code detection for unused functions and classes   |      `[tool.vulture]` in pyproject.toml#74-78       |
| deptry  | Dependency health (unused, missing, or transitive deps)  |       `[tool.deptry]` in pyproject.toml#80-86       |
| pytest  |       Test execution engine with `pytest-qt` for UI        | `[tool.pytest.ini_options]` in pyproject.toml#23-25 |

For details on tool configuration and local execution, see [Code Quality & Review Workflow](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#6.2).

## CI/CD Pipelines

Automated workflows are managed via GitHub Actions, split into quality verification and distribution builds.

### Lint & Test Pipeline (`lint.yml`)

This workflow triggers on every push and pull request to `main` or `master` [.github/workflows/lint.yml#4-7](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L4-L7) It executes the following sequence:

1.  Environment Setup: Installs Python 3.11 and `uv` [.github/workflows/lint.yml#15-21](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L15-L21)
2.  Dependency Sync: Uses `uv sync` to recreate the exact lockfile environment [.github/workflows/lint.yml#23-24](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L23-L24)
3.  Static Analysis: Runs `ruff` (lint + format check), `deptry`, and `vulture` [.github/workflows/lint.yml#26-33](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L26-L33)
4.  Test Suite: Executes the full `pytest` suite [.github/workflows/lint.yml#35-36](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L35-L36)

### Windows Build Pipeline (`build-windows.yml`)

A dedicated workflow for generating a standalone Windows executable using PyInstaller [.github/workflows/build-windows.yml#1-11](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml#L1-L11) It bundles the `config.json` schema, the `form.ui` definition, and the `core/` and `ui/` packages into a single-file distribution [.github/workflows/build-windows.yml#40-49](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml#L40-L49)

For details on pipeline steps and build artifacts, see [CI Pipelines & Build](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#6.1).

## Workflow & Code Quality

### Stacked PR Workflow

To handle sequential implementation stages, the project encourages a "stacked" workflow using `gh-stack` [AGENTS.md#67-79](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L67-L79) Developers create branches on top of previous stages rather than branching exclusively from `main`, allowing for granular reviews of complex features [AGENTS.md#72-76](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L72-L76)

### Review Backlog Process

Unresolved feedback and non-critical refactoring items are tracked in `docs/review-backlog.md` [AGENTS.md#120-122](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L120-L122) Before starting a task, developers are required to check this backlog for items assigned to their current stage [AGENTS.md#100-109](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L100-L109)

### Automation Diagram: Local to CI

The following diagram illustrates how local developer tools map to the automated GitHub Actions entities.

Development Lifecycle Mapping

Sources: [pyproject.toml#33-86](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L33-L86) [AGENTS.md#1-118](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L1-L118) [.github/workflows/lint.yml#1-37](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L1-L37) [.github/workflows/build-windows.yml#1-58](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml#L1-L58)

### Dependency and Environment Management

The project uses a strict dependency structure defined in `pyproject.toml`.

Dependency Categorization

Sources: [pyproject.toml#1-36](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L1-L36) [AGENTS.md#4-13](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L4-L13)

## Child Pages

-   [CI Pipelines & Build](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#6.1) — Detailed breakdown of GitHub Actions and PyInstaller bundling logic.
-   [Code Quality & Review Workflow](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#6.2) — Deep dive into Ruff/Vulture configs, pre-commit hooks, and the `review-backlog.md` protocol.