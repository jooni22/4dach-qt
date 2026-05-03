## Persistence Module (persistence.py)

Relevant source files

The `persistence.py` module serves as the centralized utility for managing the application's configuration and project data stored in `config.json`. It provides robust, atomic file operations to ensure data integrity during save cycles and graceful degradation during load cycles.

The module is designed to be Qt-free at the top level [persistence.py#1-5](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L1-L5) allowing core domain logic to perform I/O operations without requiring a `QApplication` instance or introducing dependencies on the UI layer.

## Configuration Path Resolution

The module defines a default location for the configuration file relative to its own filesystem position.

|  Variable   |     Type     |                                    Description                                     |
|-------------|--------------|------------------------------------------------------------------------------------|
| `_CONFIG_PATH` | `pathlib.Path` | Resolved as `config.json` in the same directory as `persistence.py`. persistence.py#12 |

Sources:

-   [persistence.py#12](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L12-L12)

## Data Loading (load\_config)

The `load_config` function handles the retrieval of the configuration dictionary. It is designed to be "fail-safe," ensuring the application can always start even if the configuration file is missing or corrupted.

### Implementation Details

-   Path Flexibility: Accepts an optional `Path` or `str` argument; otherwise, it defaults to `_CONFIG_PATH` [persistence.py#20](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L20-L20)
-   Error Handling:
    -   If the file is missing (`FileNotFoundError`), it returns an empty dictionary `{}` [persistence.py#24-25](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L24-L25)
    -   If the file is unreadable due to OS permissions (`OSError`) or contains invalid JSON (`json.JSONDecodeError`), it returns an empty dictionary `{}` [persistence.py#26-27](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L26-L27)

Sources:

-   [persistence.py#15-27](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L15-L27)

## Atomic Data Saving (save\_config)

The `save_config` function implements an atomic write pattern to prevent data loss in the event of a crash or power failure during the write process.

### Atomic Write Workflow

# Persistence Module (persistence.py)

2.  Temporary File Creation: It creates a temporary file using `tempfile.NamedTemporaryFile` in the same directory as the target config [persistence.py#39-44](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L39-L44)
3.  Serialization: The `config_data` dictionary is serialized to JSON with specific settings: `ensure_ascii=False` (to support Polish characters) and compact separators [persistence.py#46](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L46-L46)
4.  Replacement: Once the write to the temporary file is successful and the file handle is closed, `temp_path.replace(config_path)` is called [persistence.py#48](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L48-L48) This OS-level operation is atomic on most modern filesystems.

### UI Integration and Error Reporting

While the module is primarily Qt-free, `save_config` includes an optional `parent_widget` parameter. If an `OSError` occurs and a `parent_widget` is provided:

-   It performs a late import of `PySide6.QtWidgets.QMessageBox` [persistence.py#53](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L53-L53)
-   It displays a critical error dialog titled "Błąd zapisu" to the user [persistence.py#55-59](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L55-L59)

### Data Flow Diagram

The following diagram illustrates the flow from the application's internal state to the physical disk via the atomic replacement strategy.

Atomic Save Operation Flow

Sources:

-   [persistence.py#30-61](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L30-L61)

## Persistence Interaction Map

This diagram bridges the relationship between the `persistence.py` functions and the primary data structures defined in the `config.json` schema.

Configuration Entity Mapping

Sources:

-   [persistence.py#15-61](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L15-L61)
-   [config.json#1](https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json#L1-L1)

## Key Function Summary

|  Function   |                   Signature                    |                                                    Key Behavior                                                    |
|-------------|------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| `load_config` |       `(path: Path | str | None) -> dict`        |                       Graceful fallback to `{}` on any I/O or JSON error. persistence.py#15-27                       |
| `save_config` | `(config_data: dict, parent_widget, path) -> bool` | Uses `NamedTemporaryFile` for atomic replacement; late-imports `QMessageBox` for error reporting. persistence.py#30-61 |

Sources:

-   [persistence.py#1-61](https://github.com/jooni22/4dach-qt/blob/81f560ca/persistence.py#L1-L61)