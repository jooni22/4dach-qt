## Theming & Icons (ui/theme\_manager.py, app\_icons.py)

Relevant source files

Theming in 4Dach is managed through a centralized system that coordinates Qt Palettes, CSS-like stylesheets (QSS), and dynamically colored SVG icons. The system supports two primary modes: Light and Dark, with user preferences persisted across application restarts.

## Theme Management

The `ThemeManager` class [ui/theme\_manager.py#119-120](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L119-L120) serves as the central controller for the application's visual state. It utilizes `QSettings` [ui/theme\_manager.py#125](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L125-L125) to store the user's theme choice under the key `"theme"` [ui/theme\_manager.py#122](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L122-L122)

### Theme Tokens and Palette Definitions

Colors are defined using the `_ThemeTokens` dataclass [ui/theme\_manager.py#17-35](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L17-L35) This structure holds both raw hex strings for stylesheets and `QColor` objects for icon rendering and the `QPalette`.

-   Dark Mode: Defined in `_build_dark_tokens()` [ui/theme\_manager.py#38-59](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L38-L59) using a dark grey window background (`#20242b`) and light text (`#f0f0f0`).
-   Light Mode: Defined in `_build_light_tokens()` [ui/theme\_manager.py#62-83](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L62-L83) using a beige/grey window background (`#d6d5cb`) and dark text (`#111111`).

### Stylesheet Application

The `_build_stylesheet` function [ui/theme\_manager.py#86-116](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L86-L116) transforms the `_ThemeTokens` into a global QSS string. This stylesheet handles complex widget styling that standard palettes cannot reach, such as:

-   QMenuBar and QMenu: Custom backgrounds and hover states [ui/theme\_manager.py#89-93](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L89-L93)
-   QToolBar: Specific borders and spacing for the application toolbar [ui/theme\_manager.py#94-99](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L94-L99)
-   DrawingCanvas: Explicit border styling via the `DrawingCanvas` selector [ui/theme\_manager.py#111](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L111-L111)
-   Custom Object Names: Specific styling for `material_button` and `theme_toggle` [ui/theme\_manager.py#112-115](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L112-L115)

### Theme Switching Flow

When a user toggles the theme, the `ThemeManager` updates its internal state and reapplies the styling to the `QApplication` instance.

Theme Application Logic

# Theming & Icons (ui/theme\_manager.py, app\_icons.py)

2.  Retrieve Tokens: `ThemeManager.tokens` returns the active `_ThemeTokens` [ui/theme\_manager.py#135-136](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L135-L136)
3.  Apply Palette: `app.setPalette(tokens.palette)` updates standard widget colors [ui/theme\_manager.py#145](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L145-L145)
4.  Apply Stylesheet: `app.setStyleSheet(_build_stylesheet(tokens))` updates advanced styling [ui/theme\_manager.py#146](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L146-L146)
5.  Persistence: `QSettings.setValue` stores the choice [ui/theme\_manager.py#154](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L154-L154)

Sources: [ui/theme\_manager.py#1-156](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L1-L156)

## Icon Registry and Rendering

Icons in 4Dach are stored as SVG strings in a central registry within `app_icons.py`. This approach allows for dynamic recoloring based on the active theme tokens without requiring multiple sets of image files.

### Icon Registry (`_ICON_SVGS`)

The `_ICON_SVGS` dictionary [app\_icons.py#5-30](https://github.com/jooni22/4dach-qt/blob/81f560ca/app_icons.py#L5-L30) maps logical icon names to their SVG source code. These icons are primarily sourced from Lucide or Material Design Icons (MDI).

|               Icon Key               |                     Usage                      |
|--------------------------------------|------------------------------------------------|
| `new_document`, `open_folder`, `save_floppy` |   Project lifecycle actions app_icons.py#6-8   |
|    `roof_outline`, `base_point_toggle`     |  Drawing and geometry tools app_icons.py#9-10  |
|         `from_left`, `from_right`          | Layout direction indicators app_icons.py#23-24 |
|              `sun`, `moon`               |     Theme toggle button app_icons.py#26-27     |

### The `build_icon` Utility

The `build_icon` function [app\_icons.py#31-64](https://github.com/jooni22/4dach-qt/blob/81f560ca/app_icons.py#L31-L64) is the engine for generating `QIcon` objects. It performs the following steps:

1.  SVG Retrieval: Fetches the SVG string from `_ICON_SVGS` [app\_icons.py#37](https://github.com/jooni22/4dach-qt/blob/81f560ca/app_icons.py#L37-L37)
2.  Recoloring: Replaces the `currentColor` placeholder in the SVG string with the hex value of the requested `QColor` [app\_icons.py#38-39](https://github.com/jooni22/4dach-qt/blob/81f560ca/app_icons.py#L38-L39)
3.  SVG Rendering: Uses `QSvgRenderer` to draw the SVG onto a `QPixmap` [app\_icons.py#41-59](https://github.com/jooni22/4dach-qt/blob/81f560ca/app_icons.py#L41-L59)
4.  Icon Creation: Returns a `QIcon` containing the rendered pixmap [app\_icons.py#61](https://github.com/jooni22/4dach-qt/blob/81f560ca/app_icons.py#L61-L61)

Sources: [app\_icons.py#1-64](https://github.com/jooni22/4dach-qt/blob/81f560ca/app_icons.py#L1-L64)

## Data Flow: Theme to UI Components

The following diagram illustrates how the `ThemeManager` and `app_icons` interact to provide a cohesive UI.

Theme and Icon Propagation

Sources: [ui/theme\_manager.py#17-35](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L17-L35) [ui/theme\_manager.py#119-156](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L119-L156) [app\_icons.py#5-30](https://github.com/jooni22/4dach-qt/blob/81f560ca/app_icons.py#L5-L30) [app\_icons.py#31-64](https://github.com/jooni22/4dach-qt/blob/81f560ca/app_icons.py#L31-L64)

## Integration in ToolbarController

The `ToolbarController` is the primary consumer of the icon system. It implements a `refresh_icons` method that is called whenever the theme changes.

Icon Update Sequence

1.  The `MainWindow` detects a theme change.
2.  It calls `ToolbarController.refresh_icons(tokens)`.
3.  `ToolbarController` iterates through its actions (e.g., `self.act_new`, `self.act_open`).
4.  It calls `build_icon("new_document", tokens.icon_fg)` to generate a theme-appropriate icon.
5.  The action is updated with `act.setIcon(new_icon)`.

Entity Mapping: Icons and Tokens

Sources: [ui/theme\_manager.py#32-34](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L32-L34) [app\_icons.py#31-33](https://github.com/jooni22/4dach-qt/blob/81f560ca/app_icons.py#L31-L33) [ui/theme\_manager.py#135-142](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/theme_manager.py#L135-L142)