## Application Settings (core/app\_settings.py)

Relevant source files

The `AppSettings` module defines the global configuration state for the 4Dach application. Unlike per-plane geometry settings, these parameters represent business rules, UI preferences, and editing behaviors that apply across the entire application workspace [core/app\_settings.py#1-10](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L1-L10)

## The AppSettings Dataclass

The `AppSettings` class is a central dataclass that stores all user-configurable parameters. It is designed to be decoupled from the project geometry to allow users to change UI preferences without affecting the underlying data structures, though certain "business rule" fields are snapshotted during layout generation to ensure reproducibility [core/app\_settings.py#6-10](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L6-L10)

### Configuration Categories

The current `AppSettings` dataclass exposes 29 persisted fields. The groups below reflect runtime responsibility rather than declaration order in the source file.

#### Business Rules

| Field | Default | Purpose |
|-------|---------|---------|
| `partial_cutout_top_extra_cm` | `15.0` | Extra sheet allowance added above a partial cutout so layout/report output stays reproducible. |

#### Grid & Snap

| Field | Default | Purpose |
|-------|---------|---------|
| `grid_size_cm` | `10.0` | Base editing-grid square size expressed in domain centimetres. |
| `show_grid` | `True` | Toggles visibility of the canvas grid overlay. |
| `grid_major_cm` | `100` | Interval for stronger major-grid markings. |
| `grid_minor_cm` | `10` | Interval for lighter minor-grid markings. |
| `snap_to_grid` | `True` | Enables snapping geometry edits to the configured grid. |
| `snap_to_axis` | `True` | Enables horizontal/vertical axis snapping. |
| `snap_to_45deg` | `True` | Enables 45-degree snapping when drawing or editing. |
| `snap_to_3060deg` | `False` | Enables additional 30/60-degree snapping modes. |
| `snap_to_points` | `True` | Enables snapping to existing outline, hole, and sheet points. |
| `show_inferences` | `True` | Shows inference and snap-hint feedback while the cursor moves. |
| `snap_axis_threshold_deg` | `3.0` | Angular tolerance used for axis snapping. |
| `snap_45_threshold_deg` | `2.5` | Angular tolerance used for 45-degree snapping. |
| `snap_radius_px` | `12` | Pixel radius used to detect nearby snap candidates. |

#### Visuals

| Field | Default | Purpose |
|-------|---------|---------|
| `show_axis_overlay` | `True` | Displays the axis/origin overlay on the canvas. |
| `show_crosshair` | `True` | Displays a cursor crosshair during interactive editing. |
| `show_xy_references_during_draw` | `True` | Shows transient X/Y helper references while drawing segments. |
| `show_decimal_cm` | `False` | Switches dimension labels from integer-style output to decimal centimetres. |
| `show_angle_arc` | `True` | Shows the live angle arc while drawing/editing segments. |
| `show_guide_lines` | `True` | Displays guideline overlays that assist cursor alignment. |
| `ui_element_scale` | `1.6` | Global scaling factor for canvas UI affordances and handles. |
| `show_edge_length_labels` | `True` | Displays edge-length annotations on the geometry. |
| `show_vertex_angle_labels` | `False` | Displays per-vertex angle labels on the geometry. |
| `label_always_visible` | `False` | Keeps labels visible instead of only showing them contextually. |

#### Interaction

| Field | Default | Purpose |
|-------|---------|---------|
| `shift_drag_behavior` | `free_move` | Controls whether Shift bypasses snapping or locks movement orthogonally. |
| `live_angle_mode` | `absolute` | Chooses whether live angles are measured from the X axis or from the previous segment. |
| `close_on_rmb` | `True` | Allows right mouse button to close the active freehand sketch. |
| `edge_drag_mode` | `move_vertices` | Chooses whether edge interaction moves existing vertices or inserts a new one. |

#### History

| Field | Default | Purpose |
|-------|---------|---------|
| `undo_stack_depth` | `50` | Maximum number of snapshot entries kept in the undo/redo history. |

Sources: `core/app_settings.py`, `tests/test_app_settings.py`

___

## Data Flow and Persistence

Application settings are persisted within the `config.json` file under the `app_settings` key [core/app\_settings.py#3](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L3-L3) The system uses a robust validation pattern in `from_dict` to ensure that corrupt or missing configuration keys do not crash the application.

### Validation and Clamping Logic

The `from_dict` method implements strict type checking and value clamping:

1.  Type Safety: Raw values from JSON are cast to `float`, `int`, or `bool`. If casting fails, hardcoded defaults are used [core/app\_settings.py#84-92](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L84-L92)
2.  Domain Constraints: Values like `grid_size_cm` or `undo_stack_depth` are checked against non-positive values and reset to defaults if invalid [core/app\_settings.py#93-149](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L93-L149)
3.  Enum Validation: String-based modes (e.g., `shift_drag_behavior`) are checked against sets of valid constants like `_VALID_SHIFT_DRAG_BEHAVIORS` [core/app\_settings.py#17-97](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L17-L97)

### Persistence Lifecycle Diagram

This diagram shows how `AppSettings` moves between the disk and the runtime objects.

Sources: [core/app\_settings.py#81-174](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L81-L174) [config.json#1](https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json#L1-L1)

___

## Snapshotting Mechanism

A critical architectural feature is the decoupling of global settings from layout results. Because `partial_cutout_top_extra_cm` affects the physical length of sheets generated, changing this setting globally should not retroactively alter existing layouts in a saved project [core/app\_settings.py#6-10](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L6-L10)

When the `layout_engine.py` computes a layout, it "snapshots" the relevant `AppSettings` fields into the `LayoutResult`. This ensures that even if the user later changes their global preferences, the report and the visual representation of that specific plane remain consistent with the parameters used at the time of generation.

`core/reporting.py` also tolerates an optional `round_sheet_length_to_int` attribute via `getattr(settings, "round_sheet_length_to_int", False)` when selecting report precision for sheet lengths. That flag is not part of the current `AppSettings` dataclass, so its absence is expected and defaults reporting to one decimal place.

### Snapshotted Parameters Association

This diagram bridges the settings definitions to their usage in the layout generation process.

Sources: [core/app\_settings.py#6-10](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L6-L10) [core/app\_settings.py#50-51](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L50-L51)

___

## Behavior Modes

The module defines several constants that govern UI interaction logic.

### Shift-Drag Behaviors

-   `SHIFT_DRAG_BEHAVIOR_FREE_MOVE`: Holding Shift disables all snapping, allowing pixel-perfect placement [core/app\_settings.py#15-47](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L15-L47)
-   `SHIFT_DRAG_BEHAVIOR_ORTHOGONAL_LOCK`: Holding Shift constrains movement to the X or Y axis and snaps to 1cm increments [core/app\_settings.py#16-48](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L16-L48)

### Angle Display Modes

-   `LIVE_ANGLE_MODE_ABSOLUTE`: Angles are displayed relative to the horizontal X-axis [core/app\_settings.py#21-59](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L21-L59)
-   `LIVE_ANGLE_MODE_RELATIVE_TO_PREV`: Angles are displayed relative to the previous segment drawn [core/app\_settings.py#22-59](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L22-L59)

### Edge Manipulation

-   `EDGE_DRAG_MODE_MOVE_VERTICES`: Dragging an edge moves both connected vertices [core/app\_settings.py#27-74](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L27-L74)
-   `EDGE_DRAG_MODE_INSERT_VERTEX`: Clicking/Dragging an edge inserts a new vertex at that position [core/app\_settings.py#28-74](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L28-L74)

Sources: [core/app\_settings.py#15-32](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L15-L32) [tests/test\_app\_settings.py#154-168](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_app_settings.py#L154-L168)
