## Core & Geometry Tests

Relevant source files

This page documents the test suite for the core domain logic and geometric operations of 4Dach. These tests ensure the reliability of the layout engine, the integrity of project state transitions, and the mathematical correctness of polygon operations.

## Geometry Engine Tests (`test_geometry.py`)

The geometry tests serve as a critical regression guard for the `core/geometry.py` module. They focus on polygon validation, containment logic, and point-to-segment projections.

### Polygon Validation & Regression Guards

A primary focus is `validate_hole_polygon`, which ensures that cutouts (holes) are strictly contained within the roof-plane outline [tests/test\_geometry.py#65-71](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_geometry.py#L65-L71) These tests prevent regressions where invalid geometry might lead to silent failures in the layout engine [tests/test\_geometry.py#9-13](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_geometry.py#L9-L13)

# Core & Geometry Tests

|                  Test Case                  |       Code Entity       |                                                         Purpose                                                         |
|---------------------------------------------|-------------------------|-------------------------------------------------------------------------------------------------------------------------|
|   `test_validate_hole_polygon_outside_outline`    |   `validate_hole_polygon`   |                        Rejects holes completely outside the outline tests/test_geometry.py#87-95                        |
| `test_validate_hole_polygon_vertex_outside_outline` |   `validate_hole_polygon`   |                      Rejects holes if any vertex exits the boundary tests/test_geometry.py#102-112                      |
|  `test_validate_hole_polygon_edge_crosses_outline`  | `polygon_is_inside_polygon` | Verifies that holes with vertices on the boundary but interior edges inside are accepted tests/test_geometry.py#118-138 |
|         `test_zero_area_polygon_reported`         |    `validate_polygon`     |                   Detects degenerate polygons with zero or negative area tests/test_geometry.py#57-61                   |

### Geometric Utility Mapping

The following diagram bridges natural language geometric concepts to the specific functions tested in `core/geometry.py`.

Geometry Logic Mapping

Sources: [tests/test\_geometry.py#22-31](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_geometry.py#L22-L31) [core/geometry.py#177-192](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L177-L192)

___

## Models & Project State Tests (`test_models_and_state.py`)

These tests verify the lifecycle of the `ProjectState` and the serialization of domain models.

### Serialization & Round-Trips

The test suite ensures that `ProjectState` can be serialized to a compact JSON format and restored without data loss.

-   Compact Format: Verifies the use of single-letter keys (e.g., `o` for outline, `m` for material) in `to_config_fragment` [tests/test\_models\_and\_state.py#194-200](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_models_and_state.py#L194-L200)
-   Material Mapping: Ensures `Material` definitions support legacy Polish keys (e.g., `min_dlugosc_arkusza`) for backward compatibility [tests/test\_models\_and\_state.py#103-120](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_models_and_state.py#L103-L120)
-   Field Normalization: Confirms that floating-point inputs for material margins are correctly rounded to integers during model instantiation [tests/test\_models\_and\_state.py#122-153](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_models_and_state.py#L122-L153)

### State Management

-   Dirty Tracking: Tests that the `layout_dirty_reason` is correctly set when geometry or materials change [tests/test\_models\_and\_state.py#53](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_models_and_state.py#L53-L53)
-   Manual Overrides: Validates the merging of manual sheet placements with auto-generated layouts [tests/test\_models\_and\_state.py#50-51](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_models_and_state.py#L50-L51)

Sources: [tests/test\_models\_and\_state.py#66-79](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_models_and_state.py#L66-L79) [tests/test\_models\_and\_state.py#181-201](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_models_and_state.py#L181-L201) [core/models.py#166-190](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L166-L190)

___

## Layout Engine Tests (`test_layout_engine.py`)

The `test_layout_engine.py` file validates the core algorithm responsible for placing sheets on roof planes.

### Band Generation & Placement Logic

-   Deterministic Bands: Ensures that for a simple rectangle, the engine generates predictable `LayoutBand` and `SheetPlacement` objects [tests/test\_layout\_engine.py#24-41](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_layout_engine.py#L24-L41)
-   Cutout Interaction: Tests the "two-phase" placement where a hole might split a vertical band into multiple segments [tests/test\_layout\_engine.py#44-62](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_layout_engine.py#L44-L62)
-   Partial Cutouts: Verifies the `cutout_interaction == "partial"` flag when a hole notches a sheet but does not disconnect it [tests/test\_layout\_engine.py#64-81](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_layout_engine.py#L64-L81)

### Constraint Enforcement

-   Min/Max Length: Validates that the engine rejects segments shorter than `min_sheet_length_cm` and correctly stacks sheets to avoid exceeding `max_sheet_length_cm` [tests/test\_layout\_engine.py#189-196](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_layout_engine.py#L189-L196)
-   Layout Direction: Confirms that changing `layout_origin` from "left" to "right" correctly mirrors the placement coordinates [tests/test\_layout\_engine.py#169-187](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_layout_engine.py#L169-L187)

Layout Engine Data Flow

Sources: [core/layout\_engine.py#164-215](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L164-L215) [tests/test\_layout\_engine.py#24-62](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_layout_engine.py#L24-L62)

___

## App Settings & Reporting Tests

### App Settings (`test_app_settings.py`)

These tests focus on the `AppSettings` dataclass, specifically validation and clamping of user-provided values.

-   Clamping: Ensures negative values for `partial_cutout_top_extra_cm` are clamped to zero [tests/test\_app\_settings.py#98-101](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_app_settings.py#L98-L101)
-   Type Safety: Verifies that invalid types (e.g., strings instead of floats) in `from_dict` fall back to safe defaults [tests/test\_app\_settings.py#103-122](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_app_settings.py#L103-L122)

### Reporting Engine (`test_reporting.py`)

Tests for `core/reporting.py` ensure that the Bill of Materials (BOM) and HTML/SVG outputs are accurate.

-   BOM Aggregation: Verifies that sheets of the same length are grouped and their total area/cost is summed correctly [tests/test\_reporting.py#14-44](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_reporting.py#L14-L44)
-   HTML Escaping: Ensures that company names and addresses are safely escaped for HTML generation [tests/test\_reporting.py#88-92](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_reporting.py#L88-L92)
-   SVG Preview: Validates that the report includes an SVG element containing `<rect>` tags corresponding to the sheet placements [tests/test\_reporting.py#105-123](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_reporting.py#L105-L123)

Sources: [tests/test\_app\_settings.py#98-122](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_app_settings.py#L98-L122) [tests/test\_reporting.py#14-44](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_reporting.py#L14-L44) [core/reporting.py#151-207](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L151-L207)