## Project State Management (core/project\_state.py)

Relevant source files

The `ProjectState` class serves as the central "Single Source of Truth" for the application's data. It encapsulates the lifecycle of roof planes, the material registry, application settings, and company metadata. It is responsible for maintaining consistency between geometric inputs and the resulting sheet layouts through a robust dirty-tracking mechanism.

### Core Responsibilities and Data Flow

`ProjectState` acts as a facade for domain operations, ensuring that any mutation to a `RoofPlane` or `Material` correctly triggers layout invalidation or cache rebuilding.

#### System Architecture and Entity Mapping

The following diagram maps the high-level project concepts to their specific implementation entities within the `core/` package.

Diagram: Project State Entity Mapping

Sources: [core/project\_state.py#33-39](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L33-L39) [core/models.py#17-26](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L17-L26) [core/models.py#104-148](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L104-L148) [core/models.py#151-175](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/models.py#L151-L175) [core/app\_settings.py#11-47](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/app_settings.py#L11-L47)

___

### Plane Lifecycle and Geometry Mutation

`ProjectState` manages the addition, deletion, and duplication of planes, as well as safe geometric mutations that maintain topological validity.

-   Plane Management: Planes are identified by unique IDs. The `active_plane_id` tracks which plane is currently focused in the UI [core/project\_state.py#37](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L37-L37)
-   Safe Mutation: Instead of direct property access, `ProjectState` provides methods like `update_plane_outline` and `update_plane_hole` [core/project\_state.py#249-281](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L249-L281) These methods validate the new geometry using `validate_polygon` and `validate_hole_polygon` before committing the change [core/project\_state.py#14-15](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L14-L15)
-   Coordinate Transformation: The `translate_plane` method shifts the entire geometry (outline and holes) while maintaining relative positioning [core/project\_state.py#311-321](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L311-L321)

Sources: [core/project\_state.py#102-106](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L102-L106) [core/project\_state.py#183-228](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L183-L228) [core/project\_state.py#249-321](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L249-L321)

___

### Material Registry and Dependency Tracking

The material registry handles the `Material` catalog. Because roof planes depend on material properties (e.g., `effective_width_cm`) for layout generation, mutations to materials propagate "dirty" states to dependent planes.

|      Method       |                  Role                  |                                          Impact                                           |
|-------------------|----------------------------------------|-------------------------------------------------------------------------------------------|
|  `upsert_material`  | Adds or updates a material definition. | Triggers `_mark_planes_using_material_dirty` if properties changed core/project_state.py#114-146 |
|  `remove_material`  |  Deletes a material from the catalog.  |  Unsets `selected_material_id` on planes and marks them dirty core/project_state.py#148-158   |
| `replace_materials` |      Bulk update of the catalog.       |    Syncs the registry with a new list, removing orphans core/project_state.py#160-167     |

Sources: [core/project\_state.py#114-167](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L114-L167) [core/project\_state.py#417-422](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L417-L422)

___

### Dirty-Tracking and Manual Overrides

A critical feature of `ProjectState` is distinguishing between automatic layout generation and manual user adjustments.

#### Layout Invalidation Logic

The system uses `layout_dirty_reason` and `layout_revision` to track state.

# Project State Management (core/project\_state.py)

2.  Hard Dirty: Geometric changes (outline/holes) or material property changes (width) set a dirty reason (e.g., `"outline_changed"`). This requires a full re-run of `generate_layout` [core/project\_state.py#424-432](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L424-L432)
3.  Soft Dirty: Changes to non-geometric settings (e.g., `top_extra_cm`) might trigger a refresh without invalidating the entire structure if handled by the layout engine.
4.  Manual Overrides:
    -   Additions: Stored in `manual_sheet_placements` [core/project\_state.py#73-76](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L73-L76)
    -   Removals: IDs of deleted automatic sheets are stored in `manually_removed_auto_sheet_ids` [core/project\_state.py#77-79](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L77-L79)
    -   Persistence: These overrides are merged back into the generated layout during the `_rebuild_runtime_layout_cache` process [core/project\_state.py#434-448](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L434-L448)

Sources: [core/project\_state.py#71-81](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L71-L81) [core/project\_state.py#417-432](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L417-L432) [core/project\_state.py#434-448](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L434-L448)

___

### Serialization and Cache Rebuilding

`ProjectState` supports two serialization formats: a verbose standard format and a compact format optimized for JSON storage (using single-letter keys).

#### Initialization and Serialization Flow

When a project is loaded via `from_config`, the state is not immediately ready for rendering. It must go through a cache rebuilding phase.

Diagram: Load and Rebuild Sequence

#### Compact Key Mapping

The `to_config_fragment` method uses a compact dictionary structure to minimize file size.

| Compact Key |        Domain Field         |           Source            |
|-------------|-----------------------------|-----------------------------|
|      `n`      |            `name`             |  core/project_state.py#64   |
|      `m`      |     `selected_material_id`      |  core/project_state.py#67   |
|      `o`      |      `outline` (points)       |  core/project_state.py#52   |
|      `h`      |  `holes` (list of polygons)   |  core/project_state.py#57   |
|      `g`      |     `generation_settings`     | core/project_state.py#68-70 |
|     `mp`      |    `manual_sheet_placements`    | core/project_state.py#73-76 |
|     `rm`      | `manually_removed_auto_sheet_ids` | core/project_state.py#77-79 |

Sources: [core/project\_state.py#42-100](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L42-L100) [core/project\_state.py#434-448](https://github.com/jooni22/4dach-qt/blob/81f560ca/core/project_state.py#L434-L448) [config.json#17-31](https://github.com/jooni22/4dach-qt/blob/81f560ca/config.json#L17-L31)