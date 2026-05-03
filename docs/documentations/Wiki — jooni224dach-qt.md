## Geometry Engine (core/geometry.py)

Relevant source files

The Geometry Engine is the computational core of 4Dach, responsible for 2D spatial operations, polygon construction, and topological validation. It provides the mathematical foundation used by the Layout Engine to calculate sheet placements and by the UI to validate user-drawn shapes.

## Core Geometry Operations

The engine operates primarily on `Point2D` and `Polygon2D` structures defined in `core/models.py`. It utilizes a global `EPSILON` constant of `1e-9` for all floating-point comparisons to ensure stability across geometric calculations [core/geometry.py#7](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L7-L7)

### Polygon Construction Factories

The engine provides high-level factories for creating parametric shapes. These functions enforce positive dimensions via `_require_positive` [core/geometry.py#10-13](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L10-L13)

|    Function    |                        Purpose                         |              Parameters              |
|----------------|--------------------------------------------------------|--------------------------------------|
| `make_rectangle` |           Creates an axis-aligned rectangle.           |          `width_cm`, `height_cm`           |
| `make_triangle`  | Creates right-angled, isosceles, or scalene triangles. | `type`, `base_cm`, `height_cm`, `side_length_cm` |
| `make_trapezoid` |     Creates right-angled or isosceles trapezoids.      |  `type`, `bottom_base`, `top_base`, `height`   |

The `make_triangle` function includes logic for scalene ("dowolny") triangles, where it calculates the apex X-coordinate using the Pythagorean theorem based on a provided side length, ensuring the side is longer than the height [core/geometry.py#34-43](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L34-L43)

Sources: [core/geometry.py#15-84](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L15-L84) [core/models.py#65-73](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L65-L73)

### Validation and Integrity

The engine performs rigorous checks to ensure that roof outlines and cutouts (holes) are mathematically sound before they are used in layout generation.

#### Polygon Validation (`validate_polygon`)

This function checks a single polygon for:

1.  Non-zero Area: Uses `polygon.area()` to ensure the shape isn't degenerate [core/geometry.py#179-180](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L179-L180)
2.  Duplicate Points: Ensures every vertex is unique [core/geometry.py#182-183](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L182-L183)
3.  Zero-length Edges: Checks that no two consecutive points are the same [core/geometry.py#186-187](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L186-L187)
4.  Self-intersections: Uses `polygon_has_self_intersections` to detect crossing edges [core/geometry.py#189-190](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L189-L190)

#### Hole Validation (`validate_hole_polygon`)

A critical "Regression Guard" exists here to ensure cutouts are valid relative to the roof plane [tests/test\_geometry.py#3-17](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_geometry.py#L3-L17) It verifies:

-   The hole is entirely contained within the parent outline using `polygon_is_inside_polygon` [core/geometry.py#202-203](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L202-L203)
-   The hole does not overlap with existing "sibling" holes [core/geometry.py#206-207](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L206-L207)

Sources: [core/geometry.py#177-210](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L177-L210) [tests/test\_geometry.py#73-101](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_geometry.py#L73-L101)

## Containment and Intersection Logic

The system uses several algorithms to determine spatial relationships between shapes.

### Point and Polygon Containment

-   `polygon_is_inside_polygon`: Determines if polygon A is inside polygon B. It checks if all vertices of A are inside B and, crucially, checks the midpoints of all edges of A to catch cases where a diamond-shaped hole might have vertices on the boundary but edges exiting the shape [core/geometry.py#230-245](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L230-L245) [tests/test\_geometry.py#118-135](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_geometry.py#L118-L135)
-   `point_in_polygon`: Implements the Ray Casting algorithm (even-odd rule) to determine if a point is inside a shape [core/geometry.py#212-228](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L212-L228)

### Vertical Band Intersection

The `vertical_segments_for_band` function is a bridge between the Geometry Engine and the Layout Engine. It calculates the vertical spans (segments) of a polygon that fall within a specific horizontal range (a "band").

1.  It clips the polygon against two vertical lines (`x_min` and `x_max`).
2.  It identifies all intersection points with the band boundaries.
3.  It returns a list of vertical intervals `(y_start, y_end)` representing the solid parts of the roof within that band.

Sources: [core/geometry.py#247-280](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L247-L280) [core/layout\_engine.py#16](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L16-L16)

## Natural Language to Code Mapping

The following diagrams map the conceptual geometric requirements to the specific implementation entities in `core/geometry.py`.

### Shape Construction Flow

This diagram shows how user-provided parameters are transformed into `Polygon2D` objects.

Sources: [core/geometry.py#15-84](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L15-L84) [core/geometry.py#126-175](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L126-L175)

### Hole Validation Workflow

This diagram illustrates the "Regression Guard" logic that prevents invalid cutouts from breaking the layout engine.

Sources: [core/geometry.py#7](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L7-L7) [core/geometry.py#196-210](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L196-L210) [core/geometry.py#230-245](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L230-L245)

## Mathematical Utility Functions

# Geometry Engine (core/geometry.py)

|           Function           |                                                               Implementation Detail                                                                |
|------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
|         `_orientation`          |               Calculates the cross product of vectors `(b-a)` and `(c-a)` to determine winding or collinearity core/geometry.py#126-127                |
|      `segments_intersect`      |            Uses orientation tests to determine if two line segments cross, including endpoint-on-segment cases core/geometry.py#138-152            |
| `project_point_to_segment_clamped` |                 Finds the nearest point on a segment to a given point, clamping to the segment endpoints core/geometry.py#115-123                  |
|     `canonicalize_polygon`     | Reorders vertices to start from the point with the minimum X (then minimum Y) to ensure consistent polygon representation core/geometry.py#282-287 |

Sources: [core/geometry.py#115-152](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L115-L152) [core/geometry.py#282-287](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L282-L287)