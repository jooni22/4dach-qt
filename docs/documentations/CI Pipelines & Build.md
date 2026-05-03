## CI Pipelines & Build

Relevant source files

-   [.github/workflows/build-windows.yml](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml)
-   [.github/workflows/lint.yml](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml)
-   [.pre-commit-config.yaml](https://github.com/jooni22/4dach-qt/blob/81f560ca/.pre-commit-config.yaml)
-   [docs/SKILL.md](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/SKILL.md?plain=1)
-   [pyproject.toml](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml)

The 4Dach project utilizes GitHub Actions to automate code quality enforcement and binary distribution. The CI/CD strategy is built around the `uv` package manager for reproducible environments and includes comprehensive linting, dead-code detection, dependency auditing, and automated Windows executable builds.

## CI Workflow: Lint & Dependency Health

The `lint.yml` workflow is the primary gatekeeper for code quality. It executes on every push to the `main` or `master` branches and for all pull requests targeting these branches [.github/workflows/lint.yml#3-7](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L3-L7)

### Workflow Steps

The workflow runs on `ubuntu-latest` and follows a strict sequence to ensure the environment matches the developer setup [.github/workflows/lint.yml#11-37](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L11-L37):

# CI Pipelines & Build

2.  Environment Setup: Initializes Python 3.11 and installs the `uv` package manager [.github/workflows/lint.yml#15-21](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L15-L21)
3.  Dependency Sync: Executes `uv sync` to install all production and development dependencies defined in `pyproject.toml` [.github/workflows/lint.yml#23-24](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L23-L24)
4.  Ruff Check: Performs both a linting pass (`ruff check .`) and a formatting verification (`ruff format --check .`) [.github/workflows/lint.yml#26-27](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L26-L27)
5.  Dependency Audit: Runs `deptry .` to find unused, missing, or transitive dependencies [.github/workflows/lint.yml#29-30](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L29-L30)
6.  Dead-Code Scanning: Executes `vulture .` to identify potentially unused functions, classes, or variables [.github/workflows/lint.yml#32-33](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L32-L33)
7.  Test Suite: Runs the full `pytest` suite as the final verification step [.github/workflows/lint.yml#35-36](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L35-L36)

### Static Analysis Configuration

The tools are configured within `pyproject.toml` to handle the specific needs of a PySide6 application:

-   Ruff: Targets Python 3.11 with a line length of 100. It is configured to ignore `E501` (relying on the formatter) and specifically excludes generated files like `ui_form.py` and large data files like `app_icons.py` [pyproject.toml#39-50](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L39-L50)
-   Vulture: Set to a minimum confidence of 80% to reduce noise. It excludes the `ui/` directory and `tests/` to avoid false positives common in GUI signal/slot connections [pyproject.toml#74-77](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L74-L77)
-   deptry: Configured to ignore specific dev-tools (like `ruff`, `vulture`, and `pytest-qt`) that are necessary for the pipeline but not imported in the source code [pyproject.toml#83-85](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L83-L85)

### Data Flow: Linting Pipeline

The following diagram illustrates how the CI pipeline processes the codebase through various specialized tools.

CI Pipeline Logic (lint.yml)

Sources: [.github/workflows/lint.yml#23-37](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L23-L37) [pyproject.toml#39-86](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L39-L86)

___

## Build Workflow: Windows Executable

The `build-windows.yml` workflow automates the creation of a standalone Windows executable. This allows stakeholders to test the application without a Python environment.

Triggering is intentionally narrow: the workflow runs on manual `workflow_dispatch` and on `push` events to the `cutout-fix` branch only. It does not build automatically for pushes to `main` or `master`; those branches are covered by `lint.yml`.

### Bundling Strategy

The build uses `PyInstaller` with a specific bundling strategy to ensure all UI resources and core logic are available at runtime. The command utilizes several flags to create a portable "one-file" distribution [.github/workflows/build-windows.yml#37-49](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml#L37-L49):

-   `--onefile`: Packages the entire application into a single `.exe`.
-   `--windowed`: Suppresses the console window when the GUI starts.
-   `--add-data`: Explicitly bundles non-python files and subpackages:
    -   `config.json`: The default configuration template.
    -   `form.ui`: The XML layout for the main window.
    -   `core`: The core domain logic package.
    -   `ui`: The user interface package.
-   `--collect-all PySide6`: Ensures all dynamic libraries and plugins for the Qt framework are included.

### Build Pipeline (build-windows.yml)

The build runs on `windows-latest` to ensure binary compatibility [.github/workflows/build-windows.yml#11](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml#L11-L11)

Build to Artifact Mapping

Sources: [.github/workflows/build-windows.yml#37-57](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/build-windows.yml#L37-L57)

___

## Local Development Hooks

To maintain parity with the CI environment, the project includes a `.pre-commit-config.yaml` file. This allows developers to run the same checks locally before committing code.

-   Ruff: Configured with `--fix` to automatically resolve import sorting and simple lint errors during the pre-commit stage [.pre-commit-config.yaml#11-12](https://github.com/jooni22/4dach-qt/blob/81f560ca/.pre-commit-config.yaml#L11-L12)
-   deptry & Vulture: Integrated as hooks to prevent the introduction of unused dependencies or dead code [.pre-commit-config.yaml#18-30](https://github.com/jooni22/4dach-qt/blob/81f560ca/.pre-commit-config.yaml#L18-L30)

Developers can initialize these hooks using `uvx pre-commit install` [.pre-commit-config.yaml#2](https://github.com/jooni22/4dach-qt/blob/81f560ca/.pre-commit-config.yaml#L2-L2)

Sources: [.pre-commit-config.yaml#1-31](https://github.com/jooni22/4dach-qt/blob/81f560ca/.pre-commit-config.yaml#L1-L31) [docs/SKILL.md#187-195](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/SKILL.md?plain=1#L187-L195)
