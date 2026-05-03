## 4Dach — Project Overview

Relevant source files

-   [AGENTS.md](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1)
-   [README-perplexity.md](https://github.com/jooni22/4dach-qt/blob/81f560ca/README-perplexity.md?plain=1)
-   [\_TODO.md](https://github.com/jooni22/4dach-qt/blob/81f560ca/_TODO.md?plain=1)
-   [\_\_main\_\_.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/__main__.py)
-   [config.json](https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json)
-   [core/canvas\_mapper.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py)
-   [docs/test-e2e.md](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/test-e2e.md?plain=1)
-   [mainwindow.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/mainwindow.py)
-   [pyproject.toml](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml)
-   [tests/test\_canvas\_mapper.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_canvas_mapper.py)

4Dach is a professional desktop application designed for calculating the cutting layout of metal roofing sheets (tile and trapezoidal) on roof planes. It provides a comprehensive workflow from defining complex roof geometries to generating automated sheet placements and detailed Bill of Materials (BOM) reports.

The application is targeted at roofing contractors and distributors who need to minimize material waste through precise geometric layout calculations.

### Core Capabilities

# 4Dach — Project Overview

-   Geometric Modeling: Define roof planes using parametric shapes (rectangles, triangles, trapezoids) or freehand polygons [README-perplexity.md#5-6](https://github.com/jooni22/4dach-qt/blob/81f560ca/README-perplexity.md?plain=1#L5-L6)
-   Obstacle Handling: Support for internal cutouts such as chimneys and skylights [README-perplexity.md#7](https://github.com/jooni22/4dach-qt/blob/81f560ca/README-perplexity.md?plain=1#L7-L7)
-   Automated Layout Engine: Generates sheet distributions based on material properties like effective width, module length, and overlap allowances [README-perplexity.md#8-9](https://github.com/jooni22/4dach-qt/blob/81f560ca/README-perplexity.md?plain=1#L8-L9)
-   Reporting: Produces HTML and BOM reports including waste calculations and cost estimates [README-perplexity.md#11](https://github.com/jooni22/4dach-qt/blob/81f560ca/README-perplexity.md?plain=1#L11-L11)
-   Interactive Editing: Real-time adjustment of layout origins, sheet lengths, and geometric vertices [README-perplexity.md#10](https://github.com/jooni22/4dach-qt/blob/81f560ca/README-perplexity.md?plain=1#L10-L10)

### Technology Stack

The project is built on a modern Python stack with a focus on type safety and robust desktop performance:

-   Language: Python 3.11+ [pyproject.toml#5](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L5-L5)
-   GUI Framework: PySide6 (Qt for Python) [pyproject.toml#7](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L7-L7)
-   Environment Management: `uv` for reproducible builds and dependency isolation [AGENTS.md#4](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L4-L4)
-   Testing: `pytest` and `pytest-qt` for unit and GUI integration testing [pyproject.toml#31-33](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L31-L33)
-   Code Quality: Ruff (linting/formatting), Vulture (dead-code detection), and deptry (dependency health) [pyproject.toml#34-36](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L34-L36)

___

### System Architecture

4Dach follows a layered architecture that separates core domain logic from the user interface. This ensures that geometric calculations and layout algorithms remain testable in headless environments.

#### High-Level Component Interaction

The following diagram illustrates how the major subsystems interact to transform a geometric definition into a final report.

System Component Data Flow

Sources: [README-perplexity.md#23-37](https://github.com/jooni22/4dach-qt/blob/81f560ca/README-perplexity.md?plain=1#L23-L37) [ui/main\_window.py#4](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L4-L4) [core/project\_state.py#17](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L17-L17) [core/canvas\_mapper.py#8](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py#L8-L8)

___

### Major Subsystems

#### 1\. Core Domain (`core/`)

The core layer contains the "brain" of the application. It is strictly separated from Qt dependencies to allow for fast unit testing.

-   Models: Defines `RoofPlane`, `Material`, and `SheetPlacement` [core/models.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py)
-   Geometry Engine: Handles polygon validation, clipping, and segment calculations [core/geometry.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py)
-   Layout Engine: The primary algorithm that slices roof planes into vertical bands and places sheets [core/layout\_engine.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py)
-   Project State: Acts as the single source of truth, managing the collection of roof planes and the undo/redo history [core/project\_state.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py)

For details, see [Core Domain Layer](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#2).

#### 2\. User Interface (`ui/`)

The UI layer is built with PySide6 and handles user interaction, rendering, and tool management.

-   Main Window: Orchestrates the application lifecycle, file I/O, and high-level commands [ui/main\_window.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py)
-   Drawing Canvas: A complex widget for interactive geometry editing, featuring a snapping engine and real-time sheet previews [ui/drawing\_canvas.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py)
-   Workspace: Manages multiple roof planes via a tabbed interface [ui/workspace.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py)

For details, see [User Interface Layer](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#3).

#### 3\. Persistence & Configuration

The application uses a JSON-based format for saving project data. The `config.json` file stores company information, material catalogs, application settings, and the full state of all roof planes [config.json#1](https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json#L1-L1)

Data Serialization Mapping

Sources: [config.json#1](https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json#L1-L1) [core/project\_state.py#17](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L17-L17) [core/models.py#27](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L27-L27)

For details, see [Persistence & Configuration](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#4).

___

### Child Pages

-   [Getting Started](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#1.1): Step-by-step guide for setting up the development environment using `uv`, running the application via `__main__.py`, and understanding the build process [AGENTS.md#19-24](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L19-L24)
-   [Architecture Overview](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#1.2): Deep dive into the data flow, the `ProjectState` lifecycle, and the signal/slot patterns used to keep the UI in sync with the domain model.

___

Sources:

-   [README-perplexity.md#1-97](https://github.com/jooni22/4dach-qt/blob/81f560ca/README-perplexity.md?plain=1#L1-L97)
-   [pyproject.toml#1-86](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L1-L86)
-   [AGENTS.md#1-191](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L1-L191)
-   [\_\_main\_\_.py#1-25](https://github.com/jooni22/4dach-qt/blob/81f560ca/__main__.py#L1-L25)
-   [config.json#1](https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json#L1-L1)