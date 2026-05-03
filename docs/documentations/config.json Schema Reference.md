## config.json Schema Reference

Relevant source files

The `config.json` file (and project files like `projekty/projekcik.json`) serves as the primary persistence mechanism for the 4Dach application. It encapsulates the entire state of a project, including company branding, material catalogs, geometric roof definitions, and user preferences. The schema utilizes a mix of verbose keys for human readability in settings and highly compact keys for geometric data to minimize file size.

### Top-Level Structure

The root object contains five primary keys that partition the data into logical domains.

|      Key      |                     Description                      |       Data Entity        |
|---------------|------------------------------------------------------|--------------------------|
| `company_data`  |   Information used for report headers (PDF/HTML).    |       `CompanyData`        |
|    `blachy`     |   Legacy/Redundant array of material definitions.    | `list[MaterialDefinition]` |
|   `materials`   |  Modern ordered dictionary of material definitions.  |     `MaterialRegistry`     |
| `project_state` | The core geometric and logical state of roof planes. |       `ProjectState`       |
| `app_settings`  |         Global UI and editor configuration.          |       `AppSettings`        |

Sources: `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json#L1-L1" min=1 file-path="config.json">Hii</FileRef>`, `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/projekty/projekcik.json#L1-L1" min=1 file-path="projekty/projekcik.json">Hii</FileRef>`

### Project State & Compact Roof Plane Format

The `project_state` object tracks the versioning and the collection of roof planes. To optimize storage, `RoofPlane` objects are serialized using single-letter keys.

#### Key Mapping for Roof Planes

Within `project_state["roof_planes"]["items"][plane_id]`:

# config.json Schema Reference

| Key |  Domain Property  |                       Description                       |
|-----|-------------------|---------------------------------------------------------|
|  `n`  |       `name`        |      Human-readable name of the plane (e.g., "1").      |
|  `m`  |    `material_id`    |     Foreign key referencing an entry in `materials`.      |
|  `o`  |      `outline`      | List of `[x, y]` coordinates defining the outer boundary. |
|  `h`  |       `holes`       |  List of lists of `[x, y]` coordinates defining cutouts.  |
|  `g`  |   `gen_settings`    |   Layout generation parameters (e.g., `{"o": "left"}`).   |
|  `r`  |     `rotation`      |         Rotation of the layout grid in degrees.         |
| `mp`  | `manual_placements` |            User-overridden sheet positions.             |
| `rm`  |  `removed_sheets`   |    List of sheet IDs explicitly deleted by the user.    |

#### Data Flow: Serialization

The transformation between the Python `RoofPlane` dataclass and this JSON structure is handled by `to_config_fragment` and `from_config` methods.

Serialization Logic Diagram

Sources: `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json#L1-L1" min=1 file-path="config.json">Hii</FileRef>`, `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L1-L1" min=1 file-path="core/models.py">Hii</FileRef>`

### Material Definitions

The schema maintains a dual representation of materials for backward compatibility. The `materials` key is the modern source of truth, using an `order` list and an `items` dictionary.

#### Material Property Fields

Each material entry in `materials["items"]` contains the following technical fields:

-   `n` (name): Unique identifier for the material.
-   `t` (type): Either `trapezowa` (trapezoidal) or `dachówkowa` (tile-effect).
-   `w` (effective\_width\_cm): The width of the sheet that covers the roof after overlap.
-   `min` / `max`: Constraints for `min_sheet_length_cm` and `max_sheet_length_cm`.
-   `top` / `bottom`: Allowance (overlap) values in cm.
-   `mod` (module\_length\_cm): Required for `dachówkowa` type; ensures sheet lengths are multiples of the tile module.
-   `p` (price\_per\_m2): Cost basis for financial reporting.

Sources: `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json#L1-L1" min=1 file-path="config.json">Hii</FileRef>`, `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/projekty/projekcik.json#L1-L1" min=1 file-path="projekty/projekcik.json">Hii</FileRef>`

### Application Settings

The `app_settings` block configures the `DrawingCanvas` and editor behavior. These values are loaded into the `AppSettings` dataclass.

Settings Mapping Diagram

Key Fields:

-   `partial_cutout_top_extra_cm`: The amount of material added to the top of a sheet when it is cut by a hole, ensuring it can be tucked under the previous row.
-   `undo_stack_depth`: Maximum number of states stored in `MainWindow._history`.
-   `ui_element_scale`: Multiplier for canvas labels and handles.

Sources: `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json#L1-L1" min=1 file-path="config.json">Hii</FileRef>`, `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L1-L1" min=1 file-path="core/app_settings.py">Hii</FileRef>`

### Implementation Details

#### Redundancy: `blachy` vs `materials`

The `blachy` array uses Polish keys (e.g., `szerokosc_efektywna`) and is primarily maintained for compatibility with older report generators or legacy versions of the tool. The application logic in `core/project_state.py` prioritizes the `materials` object for all layout calculations.

#### Versioning

The `project_state["version"]` field (currently `2`) allows the `Persistence` module to apply migrations if the schema changes. If a version mismatch is detected, the `ProjectState.from_config` method is responsible for normalizing the data.

Sources: `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json#L1-L1" min=1 file-path="config.json">Hii</FileRef>`, `<FileRef file-url="https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L1-L1" min=1 file-path="core/project_state.py">Hii</FileRef>`