## Domain Models (core/models.py)

Relevant source files

This page provides a detailed reference for the domain data structures used throughout the 4Dach application. These models define the geometric and physical properties of roof planes, materials, and layouts, as well as the serialization strategies used to persist project data.

## Overview of Domain Entities

The domain layer is built on `dataclasses` for memory efficiency and clarity. It handles the transition from raw geometric shapes to manufacturer-specific material definitions and final sheet placements.

### Core Geometry Models

-   `Point2D`: A simple immutable `(x, y)` coordinate pair [core/models.py#12-15](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L12-L15)
-   `Bounds2D`: Represents an axis-aligned bounding box with `width` and `height` properties [core/models.py#18-32](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L18-L32)
-   `Polygon2D`: A collection of `Point2D` objects representing a closed shape. It includes utility methods for calculating `area`, `signed_area`, and generating bounding boxes [core/models.py#34-73](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L34-L73)

### Business Logic Models

# Domain Models (core/models.py)

-   `MaterialDefinition`: Defines the physical constraints of a roofing material (e.g., effective width, min/max length, overlap allowances). It supports both modern and legacy naming conventions for fields [core/models.py#105-190](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L105-L190)
-   `RoofPlane`: The central entity for a single roof surface. It contains the `outline` (Polygon2D), a list of `holes` (cutouts), and the associated `MaterialDefinition` [core/models.py#246-302](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L246-L302)
-   `SheetPlacement`: Represents a single physical sheet of material placed on a roof, including its geometric coordinates, length, and source (auto-generated vs. manual) [core/models.py#207-243](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L207-L243)

___

## Code Entity Mapping

The following diagram bridges the gap between natural language concepts used in the UI and the specific class names and file locations within the codebase.

### System Concept to Code Entity

Sources: [core/models.py#34-36](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L34-L36) [core/models.py#106](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L106-L106) [core/models.py#207](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L207-L207) [core/models.py#246](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L246-L246)

___

## Serialization Strategies

The system employs two distinct serialization formats: a Verbose Format used for runtime data exchange and UI components, and a Compact Format used for saving to `config.json` to reduce file size.

### 1\. Verbose Format (`to_dict`)

Used primarily by UI dialogs and the reporting engine. It uses descriptive keys and human-readable structures.

-   Example: `min_sheet_length_cm`, `effective_width_cm`.
-   Implementation: Found in `to_dict()` methods across all model classes [core/models.py#95-102](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L95-L102) [core/models.py#192-205](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L192-L205)

### 2\. Compact Format (The "o/h/m/r" Keys)

The `ProjectState` serializes `RoofPlane` objects into a highly compressed dictionary for storage in `config.json`.

| Key |   Domain Property   |                       Description                       |
|-----|---------------------|---------------------------------------------------------|
|  `n`  |        `name`         |             The display name of the plane.              |
|  `m`  | `selected_material_id`  |        ID of the material assigned to the plane.        |
|  `o`  |       `outline`       |      List of `[x, y]` pairs for the outer boundary.       |
|  `h`  |        `holes`        |       List of lists of `[x, y]` pairs for cutouts.        |
|  `g`  | `generation_settings` |          Layout direction and origin settings.          |
|  `r`  |   `layout_revision`   | Integer used for dirty-tracking and cache invalidation. |

Sources: [core/models.py#334-345](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L334-L345) [config.json#1](https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json#L1-L1)

### Data Flow: Serialization Round-trip

Sources: [core/project\_state.py#75-115](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L75-L115) [core/models.py#304-332](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L304-L332) [tests/test\_models\_and\_state.py#181-201](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_models_and_state.py#L181-L201)

___

## Detailed Model Reference

### MaterialDefinition

The `MaterialDefinition` class (aliased as `Material` in some contexts) handles the conversion between Polish legacy fields and standardized internal fields.

-   Rounding Logic: Centimeter fields are automatically rounded to the nearest integer during initialization to ensure grid alignment [core/models.py#144-153](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L144-L153)
-   Dual Key Support: The `from_dict` method supports both `effective_width_cm` and `szerokosc_efektywna` to maintain compatibility with older configuration files [core/models.py#171-175](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L171-L175)

### Polygon2D and Validation

Polygons are validated before being used in the layout engine. The `core/geometry.py` module provides the validation logic used by the models.

-   Self-Intersection: Checked via `polygon_has_self_intersections` [core/geometry.py#162-174](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L162-L174)
-   Containment: Holes must be entirely within the outline. This is a critical regression guard in the codebase [core/geometry.py#195-200](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L195-L200) [tests/test\_geometry.py#87-101](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_geometry.py#L87-L101)

### RoofPlane Lifecycle

A `RoofPlane` tracks its own "dirty" state via `layout_revision`. When the geometry (outline or holes) or the material changes, the revision is incremented, signaling the `LayoutEngine` that a re-calculation is required [core/models.py#246-302](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L246-L302)

Sources: [core/models.py#106-205](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L106-L205) [core/geometry.py#177-193](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/geometry.py#L177-L193) [tests/test\_models\_and\_state.py#122-154](https://github.com/jooni22/4dach-qt/blob/81f560ca/tests/test_models_and_state.py#L122-L154)