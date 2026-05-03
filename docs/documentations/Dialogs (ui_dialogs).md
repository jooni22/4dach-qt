## Dialogs (ui/dialogs/)

Relevant source files

The `ui/dialogs/` package contains modal windows used for parametric shape entry, material management, application configuration, and company data entry. These dialogs bridge the gap between user input and the core domain models.

### Data Flow Pattern

All dialogs in the codebase follow a consistent lifecycle pattern to ensure data integrity and separation of concerns:

# Dialogs (ui/dialogs/)

2.  Initialization: The dialog is instantiated with existing data (either a domain object like `AppSettings` or a raw dictionary).
3.  `_load_values()`: Internal UI widgets (spin boxes, checkboxes, etc.) are populated from the provided data [ui/dialogs/settings\_dialog.py#48](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/settings_dialog.py#L48-L48) [ui/dialogs/shape\_dialogs.py#47](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/shape_dialogs.py#L47-L47)
4.  Interaction: The user modifies values. Dialogs often use `QFormLayout` for structured input [ui/dialogs/settings\_dialog.py#56](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/settings_dialog.py#L56-L56)
5.  `get_values()` / `build_settings()`: Upon acceptance (`QDialog.Accepted`), the parent caller invokes a getter method to retrieve the validated data as a dictionary or a new domain object [ui/dialogs/settings\_dialog.py#35-36](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/settings_dialog.py#L35-L36) [ui/dialogs/company\_dialog.py#59](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/company_dialog.py#L59-L59)

### Parametric Shape Dialogs

These dialogs allow users to create standard roof plane outlines by specifying dimensions rather than drawing freehand.

|  Dialog Class   |       Purpose        |                                         Key Inputs                                         |
|-----------------|----------------------|--------------------------------------------------------------------------------------------|
| `ProstokatDialog` | Rectangular outlines |                      Width, Height ui/dialogs/shape_dialogs.py#28-36                       |
|  `TrojkatDialog`  | Triangular outlines  |      Type (Isosceles, Right, Custom), Base, Height ui/dialogs/shape_dialogs.py#71-92       |
|  `TrapezDialog`   | Trapezoidal outlines | Type (Isosceles, Right), Bottom Base, Top Base, Height ui/dialogs/shape_dialogs.py#165-189 |

#### Shape Dialog Data Flow

The following diagram illustrates how `ProstokatDialog` interacts with the configuration system.

Parametric Entry Flow

Sources: [ui/dialogs/shape\_dialogs.py#16-57](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/shape_dialogs.py#L16-L57)

___

### Material Management (BlachyDialog)

The `BlachyDialog` serves as the material catalog editor. It manages a list of `Material` domain objects.

-   List Management: Users can add, edit, or remove materials [ui/dialogs/material\_dialog.py#64-66](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/material_dialog.py#L64-L66)
-   Detail View: Selecting a material in the `QListWidget` updates a read-only detail pane [ui/dialogs/material\_dialog.py#111-122](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/material_dialog.py#L111-L122)
-   Nested Dialog: Actual editing is performed in `DaneBlachyDialog`, which handles specific sheet properties like `effective_width_cm`, `module_length_cm`, and price [ui/dialogs/material\_dialog.py#144-153](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/material_dialog.py#L144-L153)
-   Validation: The dialog prevents duplicate IDs during the save process [ui/dialogs/material\_dialog.py#132-134](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/material_dialog.py#L132-L134)

Sources: [ui/dialogs/material\_dialog.py#23-162](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/material_dialog.py#L23-L162)

___

### Application Settings (SettingsDialog)

`SettingsDialog` provides a comprehensive UI for the `AppSettings` dataclass. It is organized into four logical groups:

1.  Wycinki (Cutouts): Configures `top_extra_cm` for partial sheet coverage [ui/dialogs/settings\_dialog.py#55-71](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/settings_dialog.py#L55-L71)
2.  Siatka i przyciąganie (Grid & Snapping): Controls grid sizes, snap behaviors (angles, points, axes), and CAD inference lines [ui/dialogs/settings\_dialog.py#75-147](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/settings_dialog.py#L75-L147)
3.  Rysowanie na żywo (Live Drawing): UI scale, angle modes (absolute vs relative), and decimal precision [ui/dialogs/settings\_dialog.py#149-171](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/settings_dialog.py#L149-L171)
4.  Interakcja (Interaction): Undo depth and drag modes (moving vertices vs inserting new ones) [ui/dialogs/settings\_dialog.py#173-200](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/settings_dialog.py#L173-L200)

Sources: [ui/dialogs/settings\_dialog.py#29-200](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/settings_dialog.py#L29-L200)

___

### Company Data (DaneFirmyDialog)

`DaneFirmyDialog` manages the `CompanyData` used in report headers. It handles simple string fields including company name, NIP (tax ID), address, website, and the path to the logo file [ui/dialogs/company\_dialog.py#22-40](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/company_dialog.py#L22-L40)

Sources: [ui/dialogs/company\_dialog.py#14-67](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/company_dialog.py#L14-L67)

___

### System Entity Mapping

This diagram maps the UI Dialog classes to the domain data structures they manipulate.

Dialog to Model Mapping

Sources: [ui/dialogs/settings\_dialog.py#29-37](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/settings_dialog.py#L29-L37) [ui/dialogs/material\_dialog.py#20](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/material_dialog.py#L20-L20) [ui/dialogs/company\_dialog.py#59-66](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/company_dialog.py#L59-L66) [ui/dialogs/shape\_dialogs.py#52-56](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/dialogs/shape_dialogs.py#L52-L56)