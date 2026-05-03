## UI & Canvas Tests

Relevant source files

The UI and Canvas test suite ensures the integrity of the graphical interaction layer, coordinate transformations, and the synchronization between the `ProjectState` and the `MainWindow`. These tests utilize `pytest-qt` to simulate user input and verify the rendering pipeline.

## Drawing Canvas Interaction & Rendering

`test_drawing_canvas.py` validates the complex state machine within `DrawingCanvas`. It covers vertex manipulation, edge splitting, and the visual feedback systems (snapping/inferences).

### Interaction Modes & State Transitions

The canvas operates in several modes (e.g., `MODE_DRAW_OUTLINE`, `MODE_EDIT`, `MODE_MOVE`). Tests verify that mouse events trigger correct state transitions and coordinate mapping via `CanvasMapper` [tests/test\_drawing\_canvas.py#33-35](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_drawing_canvas.py#L33-L35)

|            Test Case             |               Scenario                |                                  Expected Behavior                                   |
|----------------------------------|---------------------------------------|--------------------------------------------------------------------------------------|
| `test_canvas_selects_vertex_handle...` |     Left click on existing vertex     |     Enters `MODE_EDIT`, sets `_active_vertex_index` tests/test_drawing_canvas.py#113-123      |
|  `test_canvas_clicking_midpoint...`  | Click edge with `insert_vertex` setting |    Splitting of edge, insertion of new `Point2D` tests/test_drawing_canvas.py#174-188    |
| `test_crosshair_axis_uses_dominant...` |    Mouse move during freehand draw    | `_crosshair_axis` locks to "x" or "y" based on delta tests/test_drawing_canvas.py#156-172 |

### Snapping & Inference Engine

Tests ensure that the snapping engine correctly identifies target vertices and edges to provide visual guides (`InferenceLine`).

-   Grid Visibility: `test_grid_minor_visibility_follows_mapper_scale` verifies that minor grid lines are only drawn when the `CanvasMapper` scale exceeds a specific threshold [tests/test\_drawing\_canvas.py#141-154](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_drawing_canvas.py#L141-L154)
-   Axis Snapping: `test_snap_helpers_resolve_axis_snap_returns_locked_point_and_label` validates the pure math behind locking a point to a specific angle (e.g., 0°, 90°) [tests/test\_canvas\_pure\_helpers.py#69-80](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_canvas_pure_helpers.py#L69-L80)

### Drawing Canvas Logic Flow

The following diagram illustrates how user input is processed into a committed geometry change.

User Interaction to Geometry Commitment

Sources: [tests/test\_drawing\_canvas.py#33-55](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_drawing_canvas.py#L33-L55) [tests/test\_drawing\_canvas.py#113-123](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_drawing_canvas.py#L113-L123) [tests/test\_drawing\_canvas.py#190-205](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_drawing_canvas.py#L190-L205)

## MainWindow UI Contract

`test_mainwindow_ui_contract.py` verifies the high-level orchestration of the application, ensuring that menu actions, toolbar buttons, and the project lifecycle are correctly wired.

### Signal Contracts & Persistence

# UI & Canvas Tests

-   Workspace Sync: `test_mainwindow_refreshes_active_plane_on_primary_canvas` ensures that when `ProjectState` changes, the `WorkspaceController` updates the `primary_canvas` with the correct `RoofPlane` [tests/test\_mainwindow\_ui\_contract.py#81-94](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_mainwindow_ui_contract.py#L81-L94)
-   Persistence Round-trips: Tests mock `save_config` to verify that UI actions trigger the persistence layer without actual disk I/O during testing [tests/test\_mainwindow\_ui\_contract.py#30-33](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_mainwindow_ui_contract.py#L30-L33)
-   Undo Stack: Verification of the `_HistoryEntry` pattern where every mutation (e.g., adding a plane, moving a vertex) is pushed to the `_undo_stack` [tests/test\_mainwindow\_ui\_contract.py#155-177](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_mainwindow_ui_contract.py#L155-L177)

### Tab Management

The `WorkspaceController` manages the `QTabWidget` representing different roof planes.

-   Plane Lifecycle: `test_mainwindow_adds_renames_and_deletes_roof_plane_tabs` covers the full lifecycle of a tab, including the dirty-state indicator (`*` suffix on tab text) [tests/test\_mainwindow\_ui\_contract.py#122-153](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_mainwindow_ui_contract.py#L122-L153)

MainWindow Component Sync

Sources: [tests/test\_mainwindow\_ui\_contract.py#44-68](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_mainwindow_ui_contract.py#L44-L68) [tests/test\_mainwindow\_ui\_contract.py#96-120](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_mainwindow_ui_contract.py#L96-L120) [tests/test\_workspace.py#33-41](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_workspace.py#L33-L41)

## Coordinate Mapping & Helpers

### CanvasMapper

`test_canvas_mapper.py` validates the bidirectional transformation between domain coordinates (cm) and screen pixels (px).

-   Fit-by-Width/Height: `test_mapper_scales_and_offsets_correctly` verifies the `min(scale_x, scale_y)` logic that preserves aspect ratios while fitting the geometry into the `canvas_rect` [tests/test\_canvas\_mapper.py#13-28](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_canvas_mapper.py#L13-L28)
-   Margins: Verification that `margin_x` and `margin_y` are respected to prevent geometry from touching the widget edges [tests/test\_canvas\_mapper.py#40-49](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_canvas_mapper.py#L40-L49)

### Sheet Rendering Pipeline

`test_canvas_pure_helpers.py` tests the logic for preparing sheet geometry for the `QPainter`.

-   Vertical Clipping: `clip_polygon_to_vertical_span` is tested to ensure sheets are trimmed exactly to the roof plane boundaries [tests/test\_canvas\_pure\_helpers.py#8-18](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_canvas_pure_helpers.py#L8-L18)
-   Z-Ordering: `build_sheet_render_items` ensures that "auto" placements and "manual" overrides are sorted correctly for consistent rendering [tests/test\_canvas\_pure\_helpers.py#21-53](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_canvas_pure_helpers.py#L21-L53)

## Workspace Controller Fan-out

The `WorkspaceController` is responsible for propagating global UI toggles (like grid visibility) to all canvases, not just the active one.

|      Function      |                                              Logic Verified                                               |
|--------------------|-----------------------------------------------------------------------------------------------------------|
|    `toggle_grid`     | Propagates `enabled` state to all `DrawingCanvas` instances in `_plane_tab_canvases` tests/test_workspace.py#44-63 |
| `update_all_canvases`  |         Triggers `update()` on every cached canvas to force a repaint tests/test_workspace.py#67-74         |
| `set_sheet_visibility` |          Updates internal `_sheets_visible` state and notifies canvases tests/test_workspace.py#76-82          |

Sources:

-   `tests/test_drawing_canvas.py`
-   `tests/test_mainwindow_ui_contract.py`
-   `tests/test_workspace.py`
-   `tests/test_canvas_mapper.py`
-   `tests/test_canvas_pure_helpers.py`
-   `core/canvas_mapper.py`