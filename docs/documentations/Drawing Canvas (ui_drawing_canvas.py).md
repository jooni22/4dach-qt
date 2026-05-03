## Drawing Canvas (ui/drawing\_canvas.py)

Relevant source files

The `DrawingCanvas` class is the primary interactive `QWidget` for visualizing and manipulating roof planes [ui/drawing\_canvas.py#1-20](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L1-L20) It handles complex geometric interactions, including freehand drawing of outlines and cutouts, vertex manipulation, and high-fidelity rendering of sheet layouts.

## Interaction Modes

The canvas operates in several distinct modes that dictate how mouse and keyboard events are interpreted.

# Drawing Canvas (ui/drawing\_canvas.py)

|  Mode Constant  |                                      Description                                      |
|-----------------|---------------------------------------------------------------------------------------|
|    `MODE_IDLE`    |            Passive display of the active roof plane ui/drawing_canvas.py#5            |
| `MODE_DRAW_OUTLINE` |        Freehand drawing mode to create a new roof plane ui/drawing_canvas.py#6        |
| `MODE_DRAW_CUTOUT`  | Freehand drawing mode to create a hole within the active plane ui/drawing_canvas.py#7 |
|    `MODE_EDIT`    |      Vertex and edge manipulation of existing geometry ui/drawing_canvas.py#122       |
|    `MODE_MOVE`    |         Dragging the entire plane or specific elements ui/drawing_canvas.py#8         |

### Drawing Logic

In drawing modes, left-clicks add vertices to a `user_points` list [ui/drawing\_canvas.py#12](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L12-L12) The canvas provides visual feedback via a "rubber band" line and a snap indicator when the cursor is near the starting vertex to close the polygon [ui/drawing\_canvas.py#13-15](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L13-L15)

Sources: [ui/drawing\_canvas.py#1-20](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L1-L20) [ui/drawing\_canvas.py#113-124](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L113-L124)

## Rendering Pipeline

The `paintEvent` executes a layered rendering pipeline to ensure that the grid, geometry, and technical overlays are displayed in the correct order.

### Rendering Layers

1.  Grid: Draws major and minor grid lines based on `AppSettings` [ui/drawing\_canvas.py#141-155](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L141-L155)
2.  Roof Body: Renders the `Polygon2D` outline and holes of the `RoofPlane`.
3.  Sheets: Visualizes the calculated `SheetPlacement` items. This layer is optimized using `_render_items_cache` [ui/drawing\_canvas.py#61-62](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L61-L62)
4.  Overlays: Draws vertex handles, edge labels, snap indicators, and the `_InlineSegmentEditor` [ui/drawing\_canvas.py#102-105](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L102-L105)

### Coordinate Mapping

All rendering and interaction logic relies on the `CanvasMapper` [core/canvas\_mapper.py#8-10](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py#L8-L10) It transforms domain coordinates (cm) to canvas pixels (px) while maintaining aspect ratios and applying margins [core/canvas\_mapper.py#25-30](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py#L25-L30)

For details on coordinate transformations and sheet geometry construction, see [Canvas Helpers: Snap Engine & Sheet Geometry (ui/canvas/)](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#3.2.1).

Sources: [ui/drawing\_canvas.py#141-155](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L141-L155) [core/canvas\_mapper.py#8-62](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py#L8-L62) [ui/drawing\_canvas.py#61-64](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L61-L64)

## Snapping and Inference Engine

The canvas utilizes a sophisticated snapping system to assist in precise drawing. It integrates grid snapping, vertex snapping, and angular inference.

### Snap Resolution Logic

The engine evaluates potential snap points in a specific priority order:

1.  Vertex Snapping: Snaps to existing points within `SNAP_RADIUS` [ui/drawing\_canvas.py#65](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L65-L65)
2.  Inference Lines: Generates virtual lines (e.g., orthogonal or 45-degree extensions) from existing vertices [ui/drawing\_canvas.py#63](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L63-L63)
3.  Grid Snapping: Snaps to the nearest grid intersection if enabled in `AppSettings`.

Sources: [ui/drawing\_canvas.py#63-65](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L63-L65) [ui/drawing\_canvas.py#156-173](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L156-L173)

## Inline Segment Editor

The `_InlineSegmentEditor` is a floating QFrame that appears during drawing to allow manual entry of segment lengths and angles [ui/drawing\_canvas.py#102-105](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L102-L105)

-   Trigger: Appears when the user begins drawing a segment.
-   Interaction: Users can `Tab` between length and angle fields [ui/drawing\_canvas.py#180-185](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L180-L185)
-   Commit: Pressing `Enter` validates the input and adds the vertex at the calculated coordinate [ui/drawing\_canvas.py#177-179](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L177-L179)

Sources: [ui/drawing\_canvas.py#102-194](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L102-L194)

## Undo/Redo via \_UndoRecord

The `DrawingCanvas` maintains its own internal undo stack for in-progress edits using the `_UndoRecord` pattern. This allows users to revert individual vertex placements or movements before committing the final geometry to the `ProjectState`.

-   Hard Dirty: Occurs when the geometry is committed (e.g., closing a polygon), triggering a full layout recalculation.
-   Soft Dirty: Occurs during active dragging or drawing, updating the visual preview without modifying the underlying domain model.

Sources: [ui/drawing\_canvas.py#1-20](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L1-L20) [tests/test\_drawing\_canvas.py#92-112](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_drawing_canvas.py#L92-L112)

## Code Entity Mapping

### Drawing Interaction Flow

The following diagram illustrates how user input flows through the `DrawingCanvas` to update the domain models.

Sources: [ui/drawing\_canvas.py#113-124](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L113-L124) [ui/drawing\_canvas.py#61-64](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L61-L64) [tests/test\_drawing\_canvas.py#92-112](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_drawing_canvas.py#L92-L112)

### Rendering Pipeline Architecture

This diagram maps the visual layers to the internal methods and helper classes responsible for drawing them.

Sources: [ui/drawing\_canvas.py#102-105](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L102-L105) [ui/drawing\_canvas.py#141-155](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L141-L155) [core/canvas\_mapper.py#44-48](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py#L44-L48) [ui/canvas/sheet\_geometry.py#1-20](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/sheet_geometry.py#L1-L20)