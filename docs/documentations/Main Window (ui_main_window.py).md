## Main Window (ui/main\_window.py)

Relevant source files

The `MainWindow` class serves as the central orchestrator of the 4Dach application. It manages the application lifecycle, coordinates data flow between the `ProjectState` and the UI components, and maintains the global undo/redo history. It acts as the top-level controller for the `WorkspaceController`, `ToolbarController`, and various dialogs.

The repo-root `mainwindow.py` file is only a compatibility shim: it re-exports `ui.main_window.MainWindow` for legacy imports and does not contain a separate window implementation.

### Project Lifecycle and Persistence

The `MainWindow` handles project-level operations including creation, loading, and saving. It utilizes the `persistence.py` module for atomic file operations.

# Main Window (ui/main\_window.py)

-   New Project: `_new_project` resets the `ProjectState` and clears the workspace [ui/main\_window.py#284-301](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L284-L301)
-   Open Project: `_open_project` invokes `QFileDialog` to select a `.json` file, loads it via `load_config`, and re-initializes the `ProjectState` [ui/main\_window.py#303-324](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L303-L324)
-   Save Project: `_save_project` persists the current state to the last known path. If no path exists, it triggers `_save_project_as` [ui/main\_window.py#326-340](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L326-L340)
-   Dirty State: The window tracks unsaved changes by comparing the current state signature against `_saved_snapshot_signature` [ui/main\_window.py#70-73](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L70-L73) Unsaved planes are indicated with an asterisk (`*`) in the tab title [ui/main\_window.py#1146-1161](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L1146-L1161)

Project Data Flow

Sources: [ui/main\_window.py#59-110](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L59-L110) [ui/main\_window.py#303-356](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L303-L356) [persistence.py#15-61](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L15-L61)

### Undo/Redo Mechanism

The application implements a snapshot-based undo/redo system. The `MainWindow` maintains two `deque` objects containing `_HistoryEntry` objects, which store the state of the project before and after a command.

-   \_HistoryEntry: A dataclass storing a label and serialized dictionaries of the project state [ui/main\_window.py#52-57](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L52-L57)
-   \_push\_history: Captures the "before" state, executes a callback, captures the "after" state, and pushes the entry onto the `_undo_stack` while clearing the `_redo_stack` [ui/main\_window.py#387-408](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L387-L408)
-   \_perform\_command: A wrapper used to encapsulate logic that should be undoable. It ensures that the workspace and UI are refreshed after the state change [ui/main\_window.py#365-385](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L365-L385)
-   \_undo / \_redo: Pops a snapshot from the respective stack and re-applies it to the `ProjectState` via `from_config` [ui/main\_window.py#410-438](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L410-L438)

Sources: [ui/main\_window.py#52-57](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L52-L57) [ui/main\_window.py#68-69](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L68-L69) [ui/main\_window.py#365-438](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L365-L438)

### Signal Wiring and DrawingCanvas Interaction

`MainWindow` connects UI signals to the `DrawingCanvas` through the `WorkspaceController`. This allows user interactions in the canvas to propagate back to the domain model.

|    Signal / Event    |   MainWindow Handler    |                                    Purpose                                    |
|----------------------|-------------------------|-------------------------------------------------------------------------------|
| `outline_edit_committed` | `_on_outline_edit_committed` |     Updates the roof plane's boundary polygon ui/main_window.py#1113-1122     |
|  `hole_edit_committed`   |  `_on_hole_edit_committed`   | Adds or updates a cutout/hole in the active plane ui/main_window.py#1124-1133 |
| `origin_edit_committed`  | `_on_origin_edit_committed`  |   Sets the layout start point (manual override) ui/main_window.py#1135-1144   |
|     `mode_changed`     |  `_on_canvas_mode_changed`   |        Updates the status bar "Mode" label ui/main_window.py#1106-1111        |

Interaction Pattern

Sources: [ui/main\_window.py#1106-1144](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L1106-L1144) [ui/drawing\_canvas.py#41](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L41-L41)

### Layout Generation and Reporting

Layout generation is triggered automatically whenever geometry or material settings change. The `MainWindow` manages the transition from design to reporting.

-   Layout Triggers: Commands like `_recalculate_active_plane` [ui/main\_window.py#925-931](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L925-L931) or changing materials via the toolbar [ui/main\_window.py#848-864](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L848-L864) force a layout recalculation in `ProjectState`.
-   Report Pipeline:
    1.  `_gen_report` is called with a specific mode ("standard", "continuous", "short") [ui/main\_window.py#1004-1017](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L1004-L1017)
    2.  `build_project_report` aggregates data from all planes into a `LayoutReport` [core/reporting.py#360-394](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L360-L394)
    3.  `build_project_report_html` converts the report data into an HTML string [core/reporting.py#440-451](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L440-L451)
    4.  The `ReportController` loads the HTML into the `QWebEngineView` [ui/report\_view.py#38-46](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/report_view.py#L38-L46)

Sources: [ui/main\_window.py#1004-1052](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L1004-L1052) [core/reporting.py#360-451](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L360-L451) [ui/report\_view.py#38-46](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/report_view.py#L38-L46)

### UI Components and Chrome

The window "chrome" consists of the menu bar, toolbars, and status bar.

-   Theme Management: `ThemeManager` handles switching between light and dark modes. `MainWindow` reacts to the `_theme_toggle` to apply stylesheets and refresh SVG icons via `app_icons.py` [ui/main\_window.py#122-128](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L122-L128) [ui/main\_window.py#1072-1087](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L1072-L1087)
-   Toolbar: The `ToolbarController` (stored in `_tb_ctrl`) manages actions for drawing modes, layout directions, and material selection [ui/main\_window.py#96](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L96-L96)
-   Workspace: Managed by `WorkspaceController`, it contains a `QTabWidget` where each tab represents a `RoofPlane` or the global `Report` [ui/main\_window.py#85-92](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L85-L92)

Sources: [ui/main\_window.py#84-102](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L84-L102) [ui/theme\_manager.py#15-30](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L15-L30) [app\_icons.py#5-28](https://github.com/jooni22/4dach-qt/blob/81f560ca/app_icons.py#L5-L28)
