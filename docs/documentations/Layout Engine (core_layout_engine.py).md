## Layout Engine (core/layout\_engine.py)

Relevant source files

-   [core/layout\_engine.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py)
-   [tests/test\_layout\_engine.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_layout_engine.py)
-   [tests/test\_models\_and\_state.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_models_and_state.py)

The Layout Engine is the computational core of 4Dach, responsible for transforming 2D roof geometry and material specifications into a concrete sheet placement plan. It implements a sophisticated sweep-line-inspired algorithm that accounts for material constraints, cutout interactions, and overlapping requirements.

## Overview of the Layout Process

The entry point for layout generation is `generate_layout` [core/layout\_engine.py#164-168](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L164-L168) It takes a `RoofPlane` and a `Material` and returns a `LayoutResult` containing all necessary placement data for rendering and reporting.

The engine follows a multi-stage pipeline:

# Layout Engine (core/layout\_engine.py)

2.  Validation & Preparation: Ensures the plane has a valid outline and the material has a positive effective width [core/layout\_engine.py#172-191](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L172-L191)
3.  Band Generation: The roof is sliced into vertical "bands" based on the material's `effective_width_cm` [core/layout\_engine.py#193](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L193-L193)
4.  Slab Decomposition: Each band is analyzed vertically to identify continuous segments of roof material, interrupted by holes or the plane boundary [core/layout\_engine.py#194](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L194-L194)
5.  Cutout Interaction Analysis: Segments are flagged as "partial" if they contain cutouts that don't fully sever the sheet [core/layout\_engine.py#198-199](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L198-L199)
6.  Two-Phase Placement: Sheets are placed within segments, respecting `max_sheet_length_cm` and applying `top_extra_cm` extensions where partial cutouts are detected [core/layout\_engine.py#200-264](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L200-L264)

### Data Flow and Entity Mapping

The following diagram bridges the domain concepts to the specific classes and functions in the engine.

Layout Generation Pipeline

Sources: [core/layout\_engine.py#164-199](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L164-L199) [core/geometry.py#13-14](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L13-L14)

## Core Algorithm Components

### 1\. Band Generation and Origin Logic

The engine iterates through the roof's horizontal span using `_iter_band_ranges`. The starting point depends on the `layout_origin` setting ("left" or "right") [core/layout\_engine.py#174-186](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L174-L186) For "right" layouts, the bands are generated from the maximum X-coordinate backwards [core/layout\_engine.py#170-171](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L170-L171)

### 2\. Slab Decomposition & Union-Find Grouping

Within a band, the engine calls `vertical_segments_for_band` from the geometry module to get raw Y-intervals where the band intersects the roof polygon [core/layout\_engine.py#444](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L444-L444)

However, a single vertical strip might be composed of multiple disjoint "slabs" (e.g., if a hole splits a band). The engine uses a `_UnionFind` structure [core/layout\_engine.py#147-162](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L147-L162) to group these slabs into `LayoutBandSegment` objects. If two slabs are connected anywhere within the band's width, they are merged into a single segment [core/layout\_engine.py#470-485](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L470-L485)

### 3\. Cutout Interaction (Partial vs. Full)

The `_detect_cutout_interaction` function determines if a cutout merely "notches" a sheet or completely severs it [core/layout\_engine.py#198-199](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L198-L199)

-   Full Cutout: Splits the `LayoutBand` into multiple `LayoutBandSegment` entries.
-   Partial Cutout: Keeps the segment intact but sets `cutout_interaction = "partial"` and identifies the `partial_cut_line_y_cm` [core/layout\_engine.py#50-51](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L50-L51)

### 4\. Two-Phase Placement & Extensions

When a partial cutout is detected, the engine applies a "top extra" extension. This ensures that the sheet covers the area above a notch (like a chimney) without being treated as two separate pieces [core/layout\_engine.py#220-230](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L220-L230)

Sheet Placement Logic

Sources: [core/layout\_engine.py#200-264](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L200-L264) [core/layout\_engine.py#28-37](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L28-L37)

## Data Structures

### LayoutResult

The final output of the engine.

-   `placements`: List of `SheetPlacement` objects (final physical sheets) [core/layout\_engine.py#89](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L89-L89)
-   `bands`: Metadata about the vertical strips used for calculation [core/layout\_engine.py#90](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L90-L90)
-   `warnings`: Issues like `missing_outline` or `invalid_max_sheet_length` [core/layout\_engine.py#91](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L91-L91)
-   `rejected_segments`: Segments that were too small to be manufactured based on `min_sheet_length_cm` [core/layout\_engine.py#92](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L92-L92)

### LayoutBandSegment

Represents a continuous vertical piece of material within a band.

-   `coverage_polygons`: A list of `Polygon2D` representing the actual area of the roof covered by this segment [core/layout\_engine.py#47](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L47-L47)
-   `raw_length_cm`: The total vertical span [core/layout\_engine.py#46](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L46-L46)
-   `top_extra_cm`: Extension added to handle partial cutouts [core/layout\_engine.py#52](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L52-L52)

### Internal Helper and Diagnostic Types

The module also defines several support dataclasses used by the row/band algorithm and by `LayoutResult`. They are implementation details rather than a stability-guaranteed external API.

-   `_BandPiece`: Temporary slice of a slab within one band, carrying edge intervals and a polygon used for later segment merging.
-   `_RowGeometry`: Computed top/bottom bounds for a candidate row before it is accepted or rejected.
-   `_RowPhase`: Phase boundary metadata used when a segment is emitted in multiple row-generation passes.
-   `LayoutWarning`: Structured warning payload appended to `LayoutResult.warnings`.
-   `RejectedSegment`: Structured record stored in `LayoutResult.rejected_segments` when a segment cannot satisfy minimum-length rules.

## Implementation Details

### Min/Max Length Enforcement

The engine enforces material constraints during the row-iteration phase [core/layout\_engine.py#203-204](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L203-L204) If a segment exceeds `max_sheet_length_cm`, it is split into multiple `SheetPlacement` entries [core/layout\_engine.py#236-241](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L236-L241) If a final segment is shorter than `min_sheet_length_cm`, it is moved to `rejected_segments` and a warning is issued [core/layout\_engine.py#255-264](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L255-L264)

### Transverse Splits

If a material has a `module_length_cm` (common for tile-effect sheets), the engine calculates if a transverse split is required to align with the material's pattern [core/layout\_engine.py#93](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L93-L93)

Sources:

-   [core/layout\_engine.py#1-264](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L1-L264)
-   [core/models.py#15-25](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L15-L25)
-   [core/geometry.py#7-14](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L7-L14)
-   [tests/test\_layout\_engine.py#24-82](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_layout_engine.py#L24-L82)
