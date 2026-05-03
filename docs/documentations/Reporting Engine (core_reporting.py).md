## Reporting Engine (core/reporting.py)

Relevant source files

The Reporting Engine is responsible for aggregating geometric data and layout results into human-readable business documents. It transforms raw sheet placements and material definitions into Bill of Materials (BOM), cost estimates, and visual SVG previews.

## Core Data Structures

The engine uses several specialized dataclasses to represent different levels of report granularity, from individual sheet rows to project-wide totals.

|      Class       |                                                     Purpose                                                     |
|------------------|-----------------------------------------------------------------------------------------------------------------|
|      `BomRow`      |              Represents a group of sheets of the same length and material. core/reporting.py#12-19              |
|   `LayoutReport`   |              Encapsulates the summary data for a single layout operation. core/reporting.py#21-29               |
| `RoofPlaneSection` | Detailed data for one specific roof plane, including its preview and specific warnings. core/reporting.py#49-62 |
|  `ProjectTotals`   |                Aggregated metrics across all roof planes in the project. core/reporting.py#65-72                |
|  `ProjectReport`   |               The top-level container for a complete project-wide report. core/reporting.py#75-93               |

### Natural Language to Code Entity Mapping: Reporting Logic

The following diagram maps business concepts (like "Waste Calculation") to the specific functions and data structures that implement them.

Diagram: Reporting Domain Mapping

Sources: [core/reporting.py#12-19](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L12-L19) [core/reporting.py#65-72](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L65-L72) [core/reporting.py#151-186](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L151-L186) [core/reporting.py#307-353](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L307-L353) [core/models.py#205-207](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L205-L207)

## The Reporting Pipeline

The pipeline follows a hierarchical aggregation pattern. It starts by analyzing individual `SheetPlacement` objects for a plane, then groups them by length, and finally sums these groups across the entire project.

### Data Flow and Aggregation

Diagram: Report Generation Flow

Sources: [core/reporting.py#119-148](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L119-L148) [core/reporting.py#151-218](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L151-L218) [core/reporting.py#421-470](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L421-L470)

### Key Functions

# Reporting Engine (core/reporting.py)

-   `build_report`: Entry point for single-plane reporting. It retrieves placements from `ProjectState` and calculates areas and costs for the active view. [core/reporting.py#119-148](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L119-L148)
-   `build_project_report`: Orchestrates the full project scan. It iterates through all `RoofPlane` objects, triggers layout generation if the plane is "dirty" (i.e., modified but not re-calculated), and aggregates a global BOM. [core/reporting.py#151-218](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L151-L218)
-   `_build_roof_plane_section`: The primary calculation logic. It determines `effective_area_m2` (net roof area) and `material_usage_area_m2` (gross area of sheets used), then derives waste percentages. [core/reporting.py#221-275](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L221-L275)
-   `_build_preview_svg`: Generates a compact SVG string representing the roof outline and sheet layout. It uses a coordinate transformation to fit the roof into a fixed 400x400 view box while maintaining aspect ratio. [core/reporting.py#307-353](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L307-L353)

## Calculations and Unit Conversion

The engine performs all internal geometric calculations in $cm^2$ and converts them to $m^2$ for the final report using `cm2_to_m2`.

### Waste and Cost Logic

-   Waste Area: Calculated as `gross_sheet_area - net_roof_area`. [core/reporting.py#244-245](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L244-L245)
-   Waste Percent: `(waste_area / gross_sheet_area) * 100`. [core/reporting.py#247-249](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L247-L249)
-   Costing: Supports both `m2` (area-based) and `arkusz` (per-sheet) pricing models. For `arkusz`, the cost is simply `quantity * price_value`. [core/reporting.py#261-267](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L261-L267)

Sources: [core/reporting.py#244-267](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L244-L267) [core/models.py#205-207](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L205-L207)

## HTML Generation

The `build_project_report_html` function generates a self-contained HTML document. It uses a CSS grid layout for the header (Company Data) and includes embedded SVG previews for every roof plane.

### Warning and Error Propagation

The engine collects warnings from multiple sources:

1.  Layout Engine: Reports rejected segments (e.g., sheets too short to be manufactured). [core/reporting.py#284-290](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L284-L290)
2.  Validation: Checks for missing materials or incomplete geometry. [core/reporting.py#293-304](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L293-L304)
3.  Project State: Identifies if a layout is "dirty" and needs recalculation. [core/reporting.py#167-174](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L167-L174)

These warnings are aggregated into the `warnings` list in `LayoutReport` and rendered as a highlighted list in the final HTML. [core/reporting.py#537-545](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L537-L545)

Sources: [core/reporting.py#421-470](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L421-L470) [core/reporting.py#537-545](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L537-L545) [core/reporting.py#284-304](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/reporting.py#L284-L304)