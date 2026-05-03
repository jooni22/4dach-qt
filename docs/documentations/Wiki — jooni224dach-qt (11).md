## User Interface Layer

Relevant source files

-   [ui/\_\_init\_\_.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/__init__.py)
-   [ui/dialogs/company\_dialog.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/company_dialog.py)
-   [ui/dialogs/shape\_dialogs.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/shape_dialogs.py)
-   [ui/main\_window.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py)
-   [ui/report\_view.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/report_view.py)
-   [ui/theme\_manager.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py)
-   [ui/toolbar.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py)
-   [ui/workspace.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py)

The User Interface Layer (the `ui/` package) is responsible for the visual representation of the project, user interaction handling, and coordinating data flow between the user and the [Core Domain Layer](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#2). It is built using PySide6 and follows a controller-view pattern where specialized controller classes manage complex widgets like the toolbar and workspace.

### System Orchestration

The UI is centered around the `MainWindow` class, which serves as the top-level controller. It orchestrates the lifecycle of the project, manages the global undo/redo stack, and wires signals between the `WorkspaceController` (managing tabs) and the `ProjectState` (the domain model).

#### UI Component Relationship

This diagram illustrates how the primary UI entities interact with the core domain.

Sources: [ui/main\_window.py#59-102](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L59-L102) [ui/workspace.py#18-46](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L18-L46) [ui/toolbar.py#17-25](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L17-L25)

___

### Key Components

#### [Main Window (ui/main\_window.py)](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#3.1)

The `MainWindow` [ui/main\_window.py#59](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L59-L59) handles high-level application logic:

# User Interface Layer

-   Project Lifecycle: Methods like `_new_project`, `_open_project`, and `_save_project` manage persistence [ui/main\_window.py#144-147](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L144-L147)
-   Command Pattern: Most mutations are routed through `_perform_command` to ensure the undo/redo stack (`_HistoryEntry`) is updated [ui/main\_window.py#52-57](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L52-L57)
-   Signal Wiring: It connects canvas signals (e.g., `outline_edit_committed`) to project state updates [ui/main\_window.py#41](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L41-L41)

#### [Drawing Canvas (ui/drawing\_canvas.py)](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#3.2)

The `DrawingCanvas` is the primary interactive area for geometry editing.

-   Interaction Modes: It supports multiple modes including `MODE_DRAW_OUTLINE`, `MODE_DRAW_CUTOUT`, and `MODE_EDIT` [ui/drawing\_canvas.py#41](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L41-L41)
-   Rendering Pipeline: It draws the grid, roof body, and sheets in a layered fashion using a `CanvasMapper` for coordinate transformations.
-   Snapping: A dedicated snapping engine assists in precise point placement.

#### [Workspace & Toolbar Controllers (ui/workspace.py, ui/toolbar.py)](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#3.3)

These controllers offload logic from the `MainWindow`:

-   WorkspaceController: Manages the `QTabWidget` (`workspace_tabs`), mapping each tab to a specific `RoofPlane` via `DrawingCanvas` instances [ui/workspace.py#18-32](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L18-L32)
-   ToolbarController: Constructs `QAction` objects, manages icon theming via `refresh_icons`, and handles the material selection combo box [ui/toolbar.py#17-35](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L17-L35)

#### [Dialogs (ui/dialogs/)](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#3.4)

The application uses specialized dialogs for data entry:

-   Parametric Shapes: `ProstokatDialog`, `TrojkatDialog`, and `TrapezDialog` allow users to enter dimensions for standard roof shapes [ui/dialogs/shape\_dialogs.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/shape_dialogs.py)
-   Configuration: `BlachyDialog` (materials) and `DaneFirmyDialog` (company data) provide interfaces for editing global settings [ui/dialogs/company\_dialog.py#14](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/company_dialog.py#L14-L14)

#### [Theming & Icons (ui/theme\_manager.py, app\_icons.py)](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#3.5)

The `ThemeManager` provides a centralized system for light and dark modes:

-   Tokens: Defines `_ThemeTokens` for colors, borders, and palettes [ui/theme\_manager.py#16-35](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L16-L35)
-   Persistence: Stores the user's theme preference in `QSettings` [ui/theme\_manager.py#120-129](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L120-L129)
-   Icons: The `app_icons.py` module works with the `ToolbarController` to re-render SVG icons dynamically when the theme changes [ui/toolbar.py#30-34](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L30-L34)

___

### Data Flow: User Interaction to Model Update

The following diagram maps user actions in the UI to the underlying code entities and domain updates.

Sources: [ui/main\_window.py#144](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L144-L144) [ui/toolbar.py#89](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L89-L89) [ui/drawing\_canvas.py#41](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L41-L41) [core/project\_state.py#31](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L31-L31)

___

### Report View

The `ReportController` [ui/report\_view.py#7](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/report_view.py#L7-L7) manages a `QTextBrowser` (`report_view`) located in the final tab of the workspace [ui/workspace.py#35-41](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L35-L41) It displays the generated HTML reports and handles placeholder states when a layout is "dirty" or hasn't been calculated yet [ui/report\_view.py#16-42](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/report_view.py#L16-L42)

Sources:

-   `ui/main_window.py`
-   `ui/workspace.py`
-   `ui/toolbar.py`
-   `ui/report_view.py`
-   `ui/theme_manager.py`
-   `ui/dialogs/shape_dialogs.py`
-   `ui/dialogs/company_dialog.py`