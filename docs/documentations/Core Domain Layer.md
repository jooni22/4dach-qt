## Core Domain Layer

Relevant source files

-   [core/\_\_init\_\_.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/__init__.py)
-   [core/app\_settings.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py)
-   [core/geometry.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py)
-   [core/layout\_engine.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py)
-   [core/models.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py)
-   [core/project\_state.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py)
-   [tests/test\_geometry.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_geometry.py)
-   [tests/test\_layout\_engine.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_layout_engine.py)

The `core/` package contains the business logic, geometric algorithms, and state management systems of the 4Dach application. It is designed to be independent of the UI layer, ensuring that calculations for roof layouts and material estimates are deterministic and testable.

## Architecture Overview

The domain layer is structured into several specialized subsystems that interact through the `ProjectState` container.

### Data Flow and Entity Mapping

The following diagram illustrates how natural language concepts (like "Roof" or "Cutout") map to specific code entities within the `core/` package.

Domain Entity Mapping

Sources: [core/models.py#12-121](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L12-L121) [core/project\_state.py#32-40](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L32-L40) [core/layout\_engine.py#164-168](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L164-L168)

___

## Subsystems

### 2.1 [Domain Models (core/models.py)](https://github.com/jooni22/4dach-qt/blob/81f560ca/Domain%20Models%20(core/models.py))

Defines the foundational data structures used throughout the application. This includes geometric primitives like `Point2D` and `Polygon2D`, as well as business entities like `MaterialDefinition` and `RoofPlane`. It handles the "compact" serialization format used in `config.json` to minimize file size.

# Core Domain Layer

-   Key Entities: `Point2D`, `Polygon2D`, `MaterialDefinition`, `RoofPlane`, `SheetPlacement`.
-   For details, see [Domain Models (core/models.py)](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#2.1).

Sources: [core/models.py#12-200](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L12-L200)

### 2.2 [Geometry Engine (core/geometry.py)](https://github.com/jooni22/4dach-qt/blob/81f560ca/Geometry%20Engine%20(core/geometry.py))

A pure-Python geometry library providing polygon operations without external dependencies like GEOS or Shapely. It includes factory functions for standard roof shapes (rectangles, trapezoids, triangles) and critical validation logic to ensure cutouts stay within roof boundaries.

-   Key Functions: `make_trapezoid`, `validate_polygon`, `polygon_is_inside_polygon`, `vertical_segments_for_band`.
-   For details, see [Geometry Engine (core/geometry.py)](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#2.2).

Sources: [core/geometry.py#15-192](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L15-L192) [tests/test\_geometry.py#65-78](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_geometry.py#L65-L78)

### 2.3 [Layout Engine (core/layout\_engine.py)](https://github.com/jooni22/4dach-qt/blob/81f560ca/Layout%20Engine%20(core/layout_engine.py))

The core algorithm that tiles a `RoofPlane` with sheets of a specific `Material`. It decomposes the roof into vertical bands, handles complex intersections with cutouts (holes), and applies business rules such as `top_extra_cm` for partial sheets.

-   Key Functions: `generate_layout`, `_build_band_segments`, `_detect_cutout_interaction`.
-   For details, see [Layout Engine (core/layout\_engine.py)](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#2.3).

Sources: [core/layout\_engine.py#164-220](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L164-L220) [tests/test\_layout\_engine.py#24-62](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_layout_engine.py#L24-L62)

### 2.4 [Project State Management (core/project\_state.py)](https://github.com/jooni22/4dach-qt/blob/81f560ca/Project%20State%20Management%20(core/project_state.py))

Acts as the "Single Source of Truth" for the current project. `ProjectState` manages the lifecycle of roof planes and materials, tracks "dirty" states to trigger layout recalculations, and provides methods for merging manual user overrides with automated layouts.

-   Key Methods: `upsert_material`, `add_roof_plane`, `_mark_layout_inputs_changed`, `to_config_fragment`.
-   For details, see [Project State Management (core/project\_state.py)](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#2.4).

Sources: [core/project\_state.py#32-158](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L32-L158)

### 2.5 [Application Settings (core/app\_settings.py)](https://github.com/jooni22/4dach-qt/blob/81f560ca/Application%20Settings%20(core/app_settings.py))

Manages global user preferences that affect both the UI behavior (snapping, grid size) and the layout algorithm (default allowances). Settings are snapshotted during layout generation to ensure that changing a global setting doesn't unexpectedly alter existing project calculations.

-   Key Entities: `AppSettings` dataclass.
-   For details, see [Application Settings (core/app\_settings.py)](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#2.5).

Sources: [core/app\_settings.py#36-150](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L36-L150)

### 2.6 [Reporting Engine (core/reporting.py)](https://github.com/jooni22/4dach-qt/blob/81f560ca/Reporting%20Engine%20(core/reporting.py))

Transforms the geometric `LayoutResult` into human-readable Bill of Materials (BOM) and HTML/SVG reports. It calculates total area, waste percentages, and costs based on the material definitions.

-   Key Functions: `build_project_report`, `build_project_report_html`.
-   For details, see [Reporting Engine (core/reporting.py)](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#2.6).

___

## Core System Interactions

The interaction between the geometry engine, layout engine, and state management is highly decoupled. The `ProjectState` coordinates the flow of data.

Layout Generation Sequence

Sources: [core/project\_state.py#284-310](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L284-L310) [core/layout\_engine.py#164-200](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L164-L200)