## Glossary

Relevant source files

This glossary defines technical terms, Polish domain vocabulary, and architectural concepts used within the 4Dach codebase. It serves as a reference for onboarding engineers to bridge the gap between industry-specific terminology and code implementation.

## 1\. Domain Vocabulary (Polish/English)

The codebase frequently uses Polish terms in both the data schema (for legacy compatibility) and the UI.

|     Polish Term     |   English Translation   |                              Code Entity / Context                               |
|---------------------|-------------------------|----------------------------------------------------------------------------------|
|       Blacha        |    Sheet / Material     |       Used in `config.json` as a key for the material catalog config.json#5        |
|        Połać        |       Roof Plane        |              Represented by the `RoofPlane` class core/models.py#223               |
|        Otwór        |      Hole / Cutout      |     Represented as a list of `Polygon2D` in `RoofPlane.holes` core/models.py#230     |
| Zapas (Górny/Dolny) | Allowance (Top/Bottom)  | Extra length added to sheets for overlapping. See `top_margin_cm` core/models.py#113 |
|  Łata / Kontrłata   | Batten / Counter-batten |        Spacing parameters for tile-like materials core/models.py#117-118         |
|       Krawędź       |          Edge           |              A segment between two `Point2D` vertices in a `Polygon2D`.              |

## 2\. Core Architectural Concepts

### 2.1. Project State & Persistence

The `ProjectState` is the single source of truth for the application. It manages the lifecycle of roof planes, materials, and application settings.

-   Compact Serialization: To save space in `config.json`, `RoofPlane` uses a compact key format:
    -   `o`: Outline (points)
    -   `h`: Holes (list of point lists)
    -   `m`: Material ID
    -   `g`: Generation Settings
    -   `r`: Layout Revision
-   Dirty Tracking: The system uses `layout_dirty_reason` to determine if a layout needs recalculation. Reasons include `geometry_changed`, `material_changed`, or `settings_changed` [core/project\_state.py#81](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L81-L81)

### 2.2. Layout Engine Terminology

The `LayoutEngine` decomposes a complex `Polygon2D` into manufacturable sheets.

-   Band: A vertical strip of the roof plane with a width equal to the material's `effective_width_cm`.
-   Slab: A horizontal decomposition of a band used during geometric calculations to handle complex intersections [core/layout\_engine.py#126](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L126-L126)
-   Partial Cutout: A scenario where a hole (cutout) does not cross the entire width of a band. The engine handles this by adding `top_extra_cm` to the sheet to ensure structural integrity [core/layout\_engine.py#52](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L52-L52)

### 2.3. UI Interaction Modes

The `DrawingCanvas` operates in distinct modes defined in `ui/drawing_canvas.py`:

-   `MODE_DRAW_OUTLINE`: Entry mode for creating the primary boundary of a new `RoofPlane` [ui/drawing\_canvas.py#6](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L6-L6)
-   `MODE_DRAW_CUTOUT`: Mode for drawing internal holes within an existing plane [ui/drawing\_canvas.py#7](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L7-L7)
-   `InferenceLine`: Temporary visual guides shown during drawing to help align vertices to axes or existing points [ui/drawing\_canvas.py#63](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/drawing_canvas.py#L63-L63)

## 3\. Data Flow Diagrams

### From Domain Model to Code Entities

The following diagram maps the conceptual "Roof" entities to their specific Python class implementations and serialization keys.

Diagram: Model to Entity Mapping

Sources: [core/models.py#34-240](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L34-L240) [core/project\_state.py#33-100](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L33-L100) [config.json#1-40](https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json#L1-L40)

### Layout Generation Pipeline

This diagram illustrates the transformation of a `RoofPlane` into a `LayoutResult` through the `LayoutEngine`.

Diagram: Layout Calculation Flow

Sources: [core/layout\_engine.py#164-220](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L164-L220) [core/layout\_engine.py#147-162](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L147-L162)

## 4\. Abbreviations Reference

# Glossary

| Abbreviation |          Full Term          |                                                                           Description                                                                           |
|--------------|-----------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
|     BOM      |      Bill of Materials      |                           The aggregated list of sheets required for the project, found in `LayoutReport.bom_rows` core/reporting.py#28                           |
|   CM2 / M2   | Square Centimeters / Meters |                       The standard units for internal geometry (`cm`) vs reporting (`m2`). Conversion is handled by `cm2_to_m2` core/models.py#8                        |
|     RMB      |     Right Mouse Button      |                                   Often used in `AppSettings` (e.g., `close_on_rmb`) to define UI behavior core/app_settings.py#64                                    |
|   EPSILON    |   Floating Point Epsilon    | Used for geometric comparisons to avoid precision errors. Defined as `1e-9` in `geometry.py` core/geometry.py#7 and `1e-6` in `layout_engine.py` core/layout_engine.py#17 |

Sources: [core/reporting.py#13-30](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L13-L30) [core/app\_settings.py#50-78](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L50-L78) [core/geometry.py#1-20](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L1-L20) [core/layout\_engine.py#1-20](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/layout_engine.py#L1-L20)