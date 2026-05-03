## Workspace & Toolbar Controllers (ui/workspace.py, ui/toolbar.py)

Relevant source files

The Workspace and Toolbar controllers manage the primary interactive regions of the 4Dach application. The `WorkspaceController` orchestrates the multi-tab interface where each roof plane is edited, while the `ToolbarController` provides a centralized command interface for project actions, drawing modes, and view toggles.

## WorkspaceController (ui/workspace.py)

The `WorkspaceController` manages a `QTabWidget` where each tab (except the final report tab) represents a `RoofPlane` from the `ProjectState` [ui/workspace.py#1-7](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L1-L7) It is responsible for the lifecycle of `DrawingCanvas` instances and ensuring that UI state (like grid visibility) is synchronized across all open planes.

### Tab Lifecycle and Synchronization

The `sync()` method is the core lifecycle function. It clears existing tabs and rebuilds them based on the current `ProjectState` [ui/workspace.py#55-60](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L55-L60)

# Workspace & Toolbar Controllers (ui/workspace.py, ui/toolbar.py)

-   Plane Tabs: For every `RoofPlane` in the project, a tab is created containing a `DrawingCanvas` [ui/workspace.py#65-68](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L65-L68)
-   Dirty Indicators: If a plane has a `layout_dirty_reason`, its tab title is appended with an asterisk `*` [ui/workspace.py#67-68](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L67-L68)
-   Report Tab: A permanent "Raport" tab is appended at the end of the list [ui/workspace.py#79](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L79-L79) This tab contains a `QTextBrowser` for displaying generated HTML reports [ui/workspace.py#35-41](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L35-L41)
-   Active Tracking: The controller tracks the `primary_canvas`, which corresponds to the `active_plane_id` in the `ProjectState` [ui/workspace.py#69-70](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L69-L70)

### Per-Canvas Fan-out

The controller implements a "fan-out" pattern to propagate global UI toggles to every individual canvas. This is handled by the `_for_each_canvas` helper [ui/workspace.py#113-118](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L113-L118)

|           Method            |                                    Description                                     |
|-----------------------------|------------------------------------------------------------------------------------|
|    `toggle_grid(enabled)`     |        Toggles the background grid on all canvases ui/workspace.py#120-121         |
| `set_sheet_visibility(visible)` | Shows or hides the calculated sheet layout on all canvases ui/workspace.py#126-128 |
| `toggle_module_count(enabled)`  |   Toggles the display of module indices on all canvases ui/workspace.py#130-131    |
|     `update_all_canvases()`     |            Triggers a `repaint()` on every canvas ui/workspace.py#139-140            |

### Workspace Data Flow

The following diagram illustrates how the `WorkspaceController` bridges the `ProjectState` to the individual `DrawingCanvas` views.

Workspace Entity Mapping

Sources: [ui/workspace.py#18-46](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L18-L46) [ui/workspace.py#55-86](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L55-L86) [ui/workspace.py#146-158](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L146-L158)

## ToolbarController (ui/toolbar.py)

The `ToolbarController` constructs the `QToolBar` and manages `QAction` objects. It serves as the primary entry point for user commands, routing interactions to the `MainWindow`.

### Action Construction & Management

Actions are defined in a structured list `icon_rows` and instantiated via `_add_action` [ui/toolbar.py#88-103](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L88-L103) This helper ensures that every action has:

1.  A consistent icon from `app_icons.py` [ui/toolbar.py#34](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L34-L34)
2.  A tooltip and status tip [ui/toolbar.py#64-65](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L64-L65)
3.  A connection to the status bar to show feedback [ui/toolbar.py#70-72](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L70-L72)

### Icon Theming

The controller supports dynamic icon recoloring via `refresh_icons(foreground, accent, muted)` [ui/toolbar.py#30-34](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L30-L34)

-   Accent Icons: `base_point_toggle`, `sun`, `moon` [ui/toolbar.py#78-79](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L78-L79)
-   Muted Icons: `grid`, `broom`, `module_count` [ui/toolbar.py#80-81](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L80-L81)
-   Standard Icons: All other actions use the primary foreground color [ui/toolbar.py#82](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L82-L82)

### Specialized Widgets

Beyond standard buttons, the toolbar contains complex widgets:

-   Material Selector: A combination of a `QToolButton` ("A") and a `QComboBox` (`variant_combo`) used to select the active material for the current plane [ui/toolbar.py#124-148](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L124-L148)
-   Layout Direction: Toggles for `action_from_left` and `action_from_right` to control the sheet placement origin [ui/toolbar.py#160-161](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L160-L161)

### Toolbar Action Mapping

This diagram maps UI concepts to the specific `QAction` references maintained by the controller.

Toolbar Action References

Sources: [ui/toolbar.py#17-25](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L17-L25) [ui/toolbar.py#111-122](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L111-L122) [ui/toolbar.py#30-34](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L30-L34)

## Key Interactions

### Canvas Mode Synchronization

When the user clicks `action_draw_outline` in the toolbar, the `MainWindow` typically reacts by changing the `mode` of the `primary_canvas` in the `WorkspaceController`. The toolbar maintains the "Checked" state of toggle buttons (like the grid or base point toggle) to reflect the current editor state [ui/toolbar.py#115-116](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L115-L116)

### Material Selection Flow

1.  User selects a material in `variant_combo` [ui/toolbar.py#139](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L139-L139)
2.  `MainWindow` receives the change signal.
3.  `MainWindow` updates the `ProjectState` for the active plane.
4.  `MainWindow` calls `workspace.update_all_canvases()` to refresh the rendering with new sheet dimensions [ui/workspace.py#139-140](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L139-L140)

|        Feature         |     File Reference      |                                              Implementation Detail                                               |
|------------------------|-------------------------|------------------------------------------------------------------------------------------------------------------|
|    Tab Context Menu    |   ui/workspace.py#31    |                                      Enabled via `CustomContextMenu` policy.                                       |
| Report Tab Protection  |  ui/workspace.py#80-82  |                            Close buttons are explicitly removed from the report tab.                             |
|      Icon Sizing       |    ui/toolbar.py#45     |                                          Standardized at 18x18 pixels.                                           |
| Primary First Contract | ui/workspace.py#113-118 | `_for_each_canvas` always processes the `primary_canvas` before others to ensure responsive feedback in the active tab. |

Sources:

-   `WorkspaceController` logic: [ui/workspace.py#18-169](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/workspace.py#L18-L169)
-   `ToolbarController` construction: [ui/toolbar.py#17-165](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/toolbar.py#L17-L165)
-   Canvas propagation tests: [tests/test\_workspace.py#44-74](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_workspace.py#L44-L74)