## Testing

Relevant source files

The 4Dach test suite provides comprehensive coverage across the entire stack, from low-level geometric primitives to complex UI interactions. The suite is designed to ensure mathematical correctness in layout generation while maintaining a stable user experience through automated UI contract testing.

### Test Strategy and Environment

The project utilizes `pytest` as the primary test runner. Because the application is built on PySide6, many tests require a Qt event loop. To allow these tests to run in headless environments (such as GitHub Actions CI), the suite is configured to use the offscreen platform.

# Testing

-   Configuration: The `QT_QPA_PLATFORM` is set to `offscreen` in the global test configuration [tests/conftest.py#7](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/conftest.py#L7-L7)
-   Tooling:
    -   `pytest-qt`: Used for simulating user interactions (mouse clicks, drags) and managing the Qt event loop.
    -   `uv`: Used for dependency synchronization and executing tests within a consistent virtual environment.
-   Automation: Tests are automatically executed on every Pull Request and push to the `main` branch via the `Lint & Dependency Health` workflow [.github/workflows/lint.yml#35-36](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L35-L36)

### Test Categories

The suite is logically divided into two main categories:

|     Category     |             Scope             |                               Key Modules                               |
|------------------|-------------------------------|-------------------------------------------------------------------------|
|    Unit Tests    |    Logic, Geometry, Models    |       `test_geometry.py`, `test_layout_engine.py`, `test_models_and_state.py`       |
| UI & Integration | Canvas, MainWindow, Workspace | `test_drawing_canvas.py`, `test_mainwindow_ui_contract.py`, `test_canvas_mapper.py` |

### System Mapping: Test Entrypoints

The following diagram maps the high-level testing commands to the specific scripts and test files they execute within the codebase.

Diagram: Test Execution Flow

Sources: [Makefile#25-39](https://github.com/jooni22/4dach-qt/blob/81f560ca/Makefile#L25-L39) [scripts/review\_and\_run\_tests.py#15-26](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/review_and_run_tests.py#L15-L26) [tests/conftest.py#1-12](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/conftest.py#L1-L12)

___

### Core & Geometry Tests

This category focuses on the "Headless" logic of the application. It ensures that the mathematical foundations of the roof geometry and the sheet placement algorithms remain robust against regressions.

-   Geometry Validation: Tests for self-intersection detection and hole-inside-outline constraints [scripts/print\_test\_expectations.py#15-24](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/print_test_expectations.py#L15-L24)
-   Layout Determinism: Verification that the layout engine generates consistent `LayoutBand` and `SheetPlacement` objects for complex polygons [scripts/print\_test\_expectations.py#56-74](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/print_test_expectations.py#L56-L74)
-   State Serialization: Round-trip testing for `ProjectState` to ensure data integrity during save/load operations.

For details, see [Core & Geometry Tests](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#5.1).

### UI & Canvas Tests

These tests exercise the `DrawingCanvas` and `MainWindow` using `pytest-qt`. They simulate real-world user behavior to verify that the UI responds correctly to mouse inputs and maintains synchronization with the underlying data models.

-   Interaction Modes: Testing vertex dragging, edge snapping, and coordinate transformation via `CanvasMapper` [scripts/print\_test\_expectations.py#106-119](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/print_test_expectations.py#L106-L119)
-   Signal Contracts: Ensuring `MainWindow` correctly handles signals like `outline_edit_committed` and updates the undo stack [scripts/print\_test\_expectations.py#116-119](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/print_test_expectations.py#L116-L119)
-   Coordinate Mapping: Validation of `fit-by-width` vs `fit-by-height` scaling in the canvas view [scripts/print\_test\_expectations.py#36-54](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/print_test_expectations.py#L36-L54)

For details, see [UI & Canvas Tests](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#5.2).

### Developer Workflow: Test Expectations

To aid in debugging complex geometric results, the project includes a "Review" system. The script `scripts/print_test_expectations.py` provides a human-readable summary of what each test is verifying (e.g., specific point coordinates or the number of expected layout bands) [scripts/print\_test\_expectations.py#14-105](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/print_test_expectations.py#L14-L105)

Developers are encouraged to run `make test-review` before submitting a PR to verify that their changes align with the documented functional expectations [Makefile#40-44](https://github.com/jooni22/4dach-qt/blob/81f560ca/Makefile#L40-L44)

Diagram: Code Entity Association

Sources: [tests/conftest.py#7](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/conftest.py#L7-L7) [scripts/print\_test\_expectations.py#14-15](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/print_test_expectations.py#L14-L15) [Makefile#25-39](https://github.com/jooni22/4dach-qt/blob/81f560ca/Makefile#L25-L39)