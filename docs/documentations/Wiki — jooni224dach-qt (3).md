## Architecture Overview

Relevant source files

The 4Dach application is built using a layered architecture that strictly separates domain logic from the user interface. It utilizes a Controller-View pattern facilitated by Qt's signal/slot mechanism, with a central ProjectState serving as the single source of truth for all data.

## Layered Structure

The codebase is organized into three primary layers, ensuring that geometric and business logic can be tested independently of the GUI.

|    Layer    |                                  Responsibility                                  | Key Packages/Files |
|-------------|----------------------------------------------------------------------------------|--------------------|
|  UI Layer   |     Orchestrates user interaction, canvas rendering, and window management.      | `ui/`, `app_icons.py`  |
| Core Domain | Handles geometry calculations, sheet placement algorithms, and state management. |       `core/`        |
| Persistence |                 Manages atomic I/O operations for project files.                 |   `persistence.py`   |

### System Entity Map

The following diagram bridges the conceptual "Natural Language" requirements to the concrete Python classes and files.

Diagram: Entity Mapping

Sources: [core/models.py#18-26](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L18-L26) [core/project\_state.py#33-40](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L33-L40) [core/layout\_engine.py#164-168](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L164-L168) [ui/main\_window.py#53-56](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L53-L56)

___

## Data Flow & Interaction

The application follows a unidirectional flow for data updates, while using signals for UI synchronization.

# Architecture Overview

2.  User Interaction: The user performs an action on the `DrawingCanvas` (e.g., moving a point) or via a dialog.
3.  Command Execution: `MainWindow` executes a command (e.g., `_perform_command`), which captures a snapshot of the current `ProjectState`.
4.  State Mutation: The `ProjectState` is updated. If geometry changes, it marks the affected `RoofPlane` as "dirty" via `layout_dirty_reason`.
5.  Layout Generation: When a dirty plane is viewed, `core.layout_engine.generate_layout` is triggered to recompute sheet placements.
6.  View Refresh: The `WorkspaceController` detects state changes and calls `sync()`, which updates the `DrawingCanvas` and `ReportController`.

Diagram: User Interaction to Layout Generation

Sources: [ui/main\_window.py#41](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L41-L41) [ui/main\_window.py#534-550](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L534-L550) [core/project\_state.py#173-185](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L173-L185) [core/layout\_engine.py#164-175](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L164-L175)

___

## Key Architectural Components

### Core Domain Logic (`core/`)

The core contains no references to PySide6/Qt, making it highly portable.

-   Models: Dataclasses like `Point2D`, `Polygon2D`, and `Material` define the data structures [core/models.py#18-30](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L18-L30)
-   ProjectState: Manages the collection of roof planes and materials. It handles "hard" and "soft" dirty tracking to determine when a layout needs re-calculation [core/project\_state.py#33-100](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L33-L100)
-   Layout Engine: A pure-functional engine that takes a `RoofPlane` and `Material` and returns a `LayoutResult` containing `SheetPlacement` objects [core/layout\_engine.py#88-94](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L88-L94)

### UI Layer (`ui/`)

-   MainWindow: The central controller. It manages the `QUndoStack` logic via `_HistoryEntry` and coordinates between the toolbar, workspace, and persistence [ui/main\_window.py#59-110](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L59-L110)
-   DrawingCanvas: A complex widget that handles coordinate transformations via `CanvasMapper` and provides interactive modes for drawing outlines and cutouts [ui/drawing\_canvas.py#41](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L41-L41) [core/canvas\_mapper.py#8-15](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py#L8-L15)
-   WorkspaceController: Manages the `QTabWidget` where each tab represents a different `RoofPlane` [ui/workspace.py#44](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L44-L44)

### Persistence

Persistence is handled by `persistence.py`, which implements atomic writes using `tempfile.NamedTemporaryFile`. This prevents file corruption if the application crashes during a save operation [persistence.py#30-49](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L30-L49)

Diagram: Persistence and State Restoration

Sources: [persistence.py#15-27](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L15-L27) [core/project\_state.py#42-48](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L42-L48) [ui/main\_window.py#62-63](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L62-L63)

___

## Design Patterns

### Controller-View Pattern

The `MainWindow` acts as the controller, holding the `ProjectState`. UI components like `DrawingCanvas` are views that emit signals when user actions occur. The controller handles these signals, modifies the state, and tells the views to refresh.

### Signal/Slot Communication

Extensive use of Qt signals decouples components. For example, when a material is edited in the `BlachyDialog`, it doesn't directly update the canvas; it updates the `ProjectState`, which then triggers a cascade of refreshes across the UI [ui/main\_window.py#34-40](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L34-L40) [core/project\_state.py#114-146](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L114-L146)

### Dirty-Tracking

To optimize performance, the system avoids re-calculating layouts on every frame. `RoofPlane` objects track why they are dirty (e.g., `geometry_changed`, `material_changed`). The `LayoutEngine` is only invoked if the `layout_dirty_reason` is non-null [core/project\_state.py#157-158](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L157-L158) [core/layout\_engine.py#164-175](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L164-L175)

Sources: `ui/main_window.py`, `core/project_state.py`, `core/layout_engine.py`, `persistence.py`, `core/canvas_mapper.py`.