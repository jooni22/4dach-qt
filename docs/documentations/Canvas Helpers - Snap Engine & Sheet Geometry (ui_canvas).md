## Canvas Helpers: Snap Engine & Sheet Geometry (ui/canvas/)

Relevant source files

This page details the specialized helper modules located in `ui/canvas/` and `core/canvas_mapper.py`. These modules provide the geometric logic required for interactive drawing (snapping and inference) and the rendering of complex sheet layouts, decoupled from the main `DrawingCanvas` widget.

## CanvasMapper: Coordinate Transformation

The `CanvasMapper` class is the bridge between the Domain Space (real-world centimeters) and the Canvas Space (screen pixels). It handles aspect-ratio preservation, centering, and margins.

### Key Responsibilities

-   Scaling: Calculates a uniform `scale` factor to fit the domain `Bounds2D` into the available `canvas_rect` while respecting margins `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py#L25-L28" min=25 max=28 file-path="core/canvas_mapper.py">Hii</FileRef>`.
-   Centering: Computes `offset_x` and `offset_y` to center the drawing if the aspect ratios do not match `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py#L29-L30" min=29 max=30 file-path="core/canvas_mapper.py">Hii</FileRef>`.
-   Mapping: Provides `map_point`, `map_x`, `map_y`, and `map_rect` to convert cm to pixels `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py#L32-L55" min=32 max=55 file-path="core/canvas_mapper.py">Hii</FileRef>`.
-   Unmapping: Provides `unmap_point` to convert mouse coordinates (pixels) back into domain coordinates (cm) for geometry manipulation `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py#L38-L42" min=38 max=42 file-path="core/canvas_mapper.py">Hii</FileRef>`.

### Coordinate System Mapping

|     From     |      To      |       Method        |                                                                              File                                                                               |
|--------------|--------------|---------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Point2D` (cm) | `QPointF` (px) |  `map_point(point)`   | `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py#L32-L36" min=32 max=36 file-path="core/canvas_mapper.py">Hii</FileRef>` |
| `QPointF` (px) | `Point2D` (cm) | `unmap_point(point)`  | `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py#L38-L42" min=38 max=42 file-path="core/canvas_mapper.py">Hii</FileRef>` |
|  `float` (cm)  |  `float` (px)  | `map_length(length_cm)` | `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py#L57-L58" min=57 max=58 file-path="core/canvas_mapper.py">Hii</FileRef>` |

Sources: `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/core/canvas_mapper.py#L8-L58" min=8 max=58 file-path="core/canvas_mapper.py">Hii</FileRef>`, `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_canvas_mapper.py#L13-L62" min=13 max=62 file-path="tests/test_canvas_mapper.py">Hii</FileRef>`

___

## Snap Engine (snap\_helpers.py)

The snapping engine provides logic for aligning the cursor to existing geometry, grid points, or specific angles. It uses a hierarchy of "Snap States" to determine the final coordinate.

### Data Structures

-   `DrawSnapState`: Represents a successful snap, containing the `kind` (e.g., "vertex", "grid", "axis"), the snapped `Point2D`, and an optional `label` (e.g., "90°") `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/snap_helpers.py#L14-L18" min=14 max=18 file-path="ui/canvas/snap_helpers.py">Hii</FileRef>`.
-   `InferenceLine`: Defines temporary alignment lines (horizontal or vertical) generated from existing vertices to aid drawing `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/snap_helpers.py#L21-L25" min=21 max=25 file-path="ui/canvas/snap_helpers.py">Hii</FileRef>`.

### Snap Resolution Logic

The engine evaluates candidates in a specific order of priority:

1.  Vertex Snap: Snaps to existing points in `target_vertices` if within `radius` `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/snap_helpers.py#L111-L117" min=111 max=117 file-path="ui/canvas/snap_helpers.py">Hii</FileRef>`.
2.  Inference Snap: Snaps to the intersection of two inference lines or to a single horizontal/vertical alignment line `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/snap_helpers.py#L134-L152" min=134 max=152 file-path="ui/canvas/snap_helpers.py">Hii</FileRef>`.
3.  Edge Snap: Projects the point onto the nearest segment in `target_edges` `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/snap_helpers.py#L192-L205" min=192 max=205 file-path="ui/canvas/snap_helpers.py">Hii</FileRef>`.
4.  Angular/Axis Snap: Locks the point to 0/90/180/270 degrees (Axis) or 45/30/60 degrees relative to a start point `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/snap_helpers.py#L155-L189" min=155 max=189 file-path="ui/canvas/snap_helpers.py">Hii</FileRef>`.
5.  Grid Snap: Rounds the coordinate to the nearest `step_cm` increment `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/snap_helpers.py#L27-L32" min=27 max=32 file-path="ui/canvas/snap_helpers.py">Hii</FileRef>`.

### Diagram: Snap Resolution Flow

This diagram shows how `DrawingCanvas` uses `snap_helpers.py` to resolve a raw mouse position.

Sources: `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/snap_helpers.py#L27-L189" min=27 max=189 file-path="ui/canvas/snap_helpers.py">Hii</FileRef>`, `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_canvas_pure_helpers.py#L55-L81" min=55 max=81 file-path="tests/test_canvas_pure_helpers.py">Hii</FileRef>`

___

## Sheet Geometry & Rendering (sheet\_geometry.py)

This module handles the complex task of preparing `SheetPlacement` domain objects for rendering. It accounts for "Partial Cutouts" and "Top Extensions" by clipping coverage polygons to the physical bounds of the sheet.

### Rendering Data Flow

# Canvas Helpers: Snap Engine & Sheet Geometry (ui/canvas/)

2.  Map Layout: `build_layout_segment_map` creates a lookup table for `LayoutBandSegment` data using `(band_index, segment_index)` keys `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/sheet_geometry.py#L50-L61" min=50 max=61 file-path="ui/canvas/sheet_geometry.py">Hii</FileRef>`.
3.  Polygon Clipping: Sheets are often shorter than the band they occupy (due to cutouts). `clip_polygon_to_vertical_span` uses a Sutherland-Hodgman-style clipping algorithm to trim the coverage area to the sheet's `y_top_cm` and `y_bottom_cm` `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/sheet_geometry.py#L116-L132" min=116 max=132 file-path="ui/canvas/sheet_geometry.py">Hii</FileRef>`.
4.  Extension: If a sheet has a `top_extra_cm` (for overlapping the ridge), `extend_polygon_top` adjusts the top vertices upward `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/sheet_geometry.py#L185-L192" min=185 max=192 file-path="ui/canvas/sheet_geometry.py">Hii</FileRef>`.
5.  Path Generation: `sheet_item_path` converts the clipped `Polygon2D` list into a single `QPainterPath` for efficient drawing by `QPainter` `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/sheet_geometry.py#L194-L200" min=194 max=200 file-path="ui/canvas/sheet_geometry.py">Hii</FileRef>`.

### Sheet Clipping Logic

The `clip_polygon_to_half_plane` function performs the core geometric intersection, interpolating new vertices where a polygon edge crosses the clipping boundary `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/sheet_geometry.py#L135-L162" min=135 max=162 file-path="ui/canvas/sheet_geometry.py">Hii</FileRef>`.

### Diagram: Sheet Rendering Pipeline

This diagram bridges the domain model `SheetPlacement` to the rendered `SheetRenderItem`.

### SheetRenderItem Class

|   Attribute   |      Type       |              Description              |
|---------------|-----------------|---------------------------------------|
| `placement_id`  |       `str`       |   Unique ID from the layout engine    |
|    `source`     |       `str`       |          "auto" or "manual"           |
|   `polygons`    | `list[Polygon2D]` | The clipped/extended geometry to draw |
| `final_length_cm` |      `float`      |    The actual length of the sheet     |

Sources: `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/sheet_geometry.py#L16-L47" min=16 max=47 file-path="ui/canvas/sheet_geometry.py">Hii</FileRef>`, `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/canvas/sheet_geometry.py#L116-L162" min=116 max=162 file-path="ui/canvas/sheet_geometry.py">Hii</FileRef>`, `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_canvas_pure_helpers.py#L8-L53" min=8 max=53 file-path="tests/test_canvas_pure_helpers.py">Hii</FileRef>`