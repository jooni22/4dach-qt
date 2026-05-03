## Persistence & Configuration

Relevant source files

This section provides an overview of how 4Dach manages data persistence and application configuration. The system relies on a single JSON file, `config.json`, which stores everything from global application preferences to detailed geometric data for roof projects.

Persistence is handled by a dedicated module that ensures atomic writes to prevent data corruption, while the core domain layer provides logic for serializing complex objects into compact formats suitable for storage.

### Persistence Mechanism

The `persistence.py` module serves as the interface between the application's memory and the disk. It is designed to be independent of the Qt framework (with the exception of optional error reporting) to allow for potential CLI or headless usage.

Key features include:

# Persistence & Configuration

-   Atomic Writes: `save_config` uses `tempfile.NamedTemporaryFile` and `os.replace` to ensure that a crash during saving does not leave the `config.json` file in a corrupted state [persistence.py#30-48](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L30-L48)
-   Graceful Loading: `load_config` handles missing files or syntax errors by returning an empty dictionary, allowing the application to initialize with default values [persistence.py#15-27](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L15-L27)
-   Default Path: The system defaults to a `config.json` located in the application root [persistence.py#12](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L12-L12)

For details, see [Persistence Module (persistence.py)](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#4.2).

### Serialization Architecture

The transition from live Python objects to JSON is managed primarily by the `ProjectState` class and associated models. Because roof geometry and sheet placements can be data-intensive, the system uses a compact serialization format for `RoofPlane` objects to reduce file size.

|           Code Entity           |                                         Serialization Responsibility                                         |
|---------------------------------|--------------------------------------------------------------------------------------------------------------|
| `ProjectState.to_config_fragment()` |              Aggregates all project data into a serializable dict core/project_state.py#203-217              |
|   `ProjectState.from_config()`    | Reconstructs the entire application state and triggers runtime cache rebuilding core/project_state.py#42-100 |
|      `AppSettings.to_dict()`      |                      Serializes UI and engine preferences core/app_settings.py#101-103                       |
|       `Material.to_dict()`        |                        Handles material properties and pricing core/models.py#186-206                        |

Data Flow Overview The following diagram illustrates how data moves from the UI through the domain models into the persistence layer.

Persistence Data Flow

Sources: [core/project\_state.py#42-100](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L42-L100) [persistence.py#30-48](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L30-L48) [ui/main\_window.py#280-310](https://github.com/jooni22/4dach-qt/blob/81f560ca/ui/main_window.py#L280-L310)

### config.json Schema

The configuration file is divided into several top-level keys. A notable aspect of the schema is the compact key mapping used for `RoofPlane` attributes (e.g., `o` for outline, `h` for holes, `m` for material ID) to minimize the footprint of geometric coordinate lists [core/project\_state.py#51-83](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L51-L83)

High-Level Schema Structure

Sources: [config.json#1](https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json#L1-L1) [core/project\_state.py#51-83](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L51-L83)

For details on specific fields and the compact key mapping, see [config.json Schema Reference](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#4.1).

### Sub-pages

-   [config.json Schema Reference](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#4.1): Full documentation of the JSON structure, including the `n/m/o/h/g/r` compact format and material property definitions.
-   [Persistence Module (persistence.py)](https://app.devin.ai/org/jooni22/wiki/jooni22/4dach-qt?branch=issue%2Fprevious-produced-plan-below-accomplish#4.2): Detailed API for `load_config` and `save_config`, including error handling and atomic write implementation.