from __future__ import annotations

import copy
import logging
import re
from dataclasses import dataclass, field

from core.app_settings import AppSettings
from core.geometry import (
    delete_polygon_point,
    insert_polygon_point,
    replace_polygon_point,
    translate_polygon,
    validate_hole_polygon,
    validate_polygon,
)
from core.layout_engine import LayoutResult, generate_layout
from core.models import (
    CompanyData,
    GenerationSettings,
    Material,
    Point2D,
    Polygon2D,
    RoofPlane,
    SheetPlacement,
)


log = logging.getLogger(__name__)


@dataclass(slots=True)
class ProjectState:
    company_data: CompanyData = field(default_factory=CompanyData)
    materials: list[Material] = field(default_factory=list)
    roof_planes: list[RoofPlane] = field(default_factory=list)
    active_plane_id: str | None = None
    version: int = 1
    app_settings: AppSettings = field(default_factory=AppSettings)

    @classmethod
    def from_config(cls, config_data: dict | None) -> ProjectState:
        payload = config_data or {}
        project_payload = payload.get("project_state", {})
        material_payloads = payload.get("materials")
        if material_payloads is None:
            material_payloads = payload.get("blachy", [])
        materials = _deserialize_materials(material_payloads)
        roof_planes: list[RoofPlane] = []

        for plane_payload in _iter_plane_payloads(project_payload.get("roof_planes", [])):
            outline = _deserialize_polygon(plane_payload.get("outline", plane_payload.get("o", [])))
            holes = [
                hole
                for hole in (
                    _deserialize_polygon(hole_payload)
                    for hole_payload in plane_payload.get("holes", plane_payload.get("h", []))
                )
                if hole is not None and outline is not None
            ]
            roof_planes.append(
                RoofPlane(
                    id=plane_payload["id"],
                    name=plane_payload.get("name", plane_payload.get("n", plane_payload["id"])),
                    outline=outline,
                    holes=holes,
                    selected_material_id=plane_payload.get("selected_material_id", plane_payload.get("m")),
                    generation_settings=_deserialize_generation_settings(
                        plane_payload.get("generation_settings", plane_payload.get("g"))
                    ),
                    auto_sheet_placements=_deserialize_placements(plane_payload.get("auto_sheet_placements", []), source="auto"),
                    layout_bands=_deserialize_layout_bands(plane_payload.get("layout_bands", [])),
                    manual_sheet_placements=_deserialize_placements(
                        plane_payload.get("manual_sheet_placements", plane_payload.get("mp", [])),
                        source="manual",
                    ),
                    manually_removed_auto_sheet_ids=list(
                        plane_payload.get("manually_removed_auto_sheet_ids", plane_payload.get("rm", []))
                    ),
                    layout_revision=int(plane_payload.get("layout_revision", plane_payload.get("r", 0))),
                    layout_dirty_reason=plane_payload.get("layout_dirty_reason", plane_payload.get("d")),
                )
            )

        active_plane_id = project_payload.get("active_plane_id")
        if active_plane_id is None and roof_planes:
            active_plane_id = roof_planes[0].id

        app_settings = AppSettings.from_dict(payload.get("app_settings"))

        state = cls(
            company_data=CompanyData.from_dict(payload.get("company_data")),
            materials=materials,
            roof_planes=roof_planes,
            active_plane_id=active_plane_id,
            version=project_payload.get("version", 1),
            app_settings=app_settings,
        )
        state._rebuild_runtime_layout_cache()
        return state

    def active_roof_plane(self) -> RoofPlane | None:
        if self.active_plane_id is None:
            return None
        return next((plane for plane in self.roof_planes if plane.id == self.active_plane_id), None)

    def roof_plane_by_id(self, plane_id: str | None) -> RoofPlane | None:
        if plane_id is None:
            return None
        return next((plane for plane in self.roof_planes if plane.id == plane_id), None)

    def material_by_id(self, material_id: str | None) -> Material | None:
        if material_id is None:
            return None
        return next((material for material in self.materials if material.id == material_id), None)

    def available_material_ids(self) -> list[str]:
        return [material.id for material in self.materials]

    def upsert_material(self, material: Material) -> Material:
        normalized = Material.from_dict(material.to_dict())
        if not normalized.id.strip():
            raise ValueError("Identyfikator materiału nie może być pusty")
        if normalized.effective_width_cm <= 0:
            raise ValueError("Szerokość efektywna materiału musi być dodatnia")
        if normalized.min_sheet_length_cm < 0:
            raise ValueError("Minimalna długość arkusza nie może być ujemna")
        if normalized.max_sheet_length_cm < normalized.min_sheet_length_cm:
            raise ValueError("Maksymalna długość arkusza nie może być mniejsza niż minimalna")

        existing = self.material_by_id(normalized.id)
        if existing is None:
            self.materials.append(normalized)
            return normalized

        material_changed = existing.to_dict() != normalized.to_dict()
        existing.display_name = normalized.display_name
        existing.type = normalized.type
        existing.effective_width_cm = normalized.effective_width_cm
        existing.min_sheet_length_cm = normalized.min_sheet_length_cm
        existing.max_sheet_length_cm = normalized.max_sheet_length_cm
        existing.top_margin_cm = normalized.top_margin_cm
        existing.bottom_margin_cm = normalized.bottom_margin_cm
        existing.module_length_cm = normalized.module_length_cm
        existing.price_per_m2 = normalized.price_per_m2
        existing.batten_spacing_cm = normalized.batten_spacing_cm
        existing.counter_batten_spacing_cm = normalized.counter_batten_spacing_cm
        existing.modules = list(normalized.modules)
        existing.price_unit = normalized.price_unit
        if material_changed:
            self._mark_planes_using_material_dirty(normalized.id)
        return existing

    def remove_material(self, material_id: str) -> Material:
        material = self.material_by_id(material_id)
        if material is None:
            raise ValueError("Nie znaleziono materiału o podanym identyfikatorze")

        self.materials = [candidate for candidate in self.materials if candidate.id != material_id]
        for plane in self.roof_planes:
            if plane.selected_material_id == material_id:
                plane.selected_material_id = None
                self._mark_layout_inputs_changed(plane, "material_changed")
        return material

    def replace_materials(self, materials: list[Material]) -> list[Material]:
        desired_ids = [material.id for material in materials]
        for material_id in [material.id for material in self.materials if material.id not in desired_ids]:
            self.remove_material(material_id)
        for material in materials:
            self.upsert_material(material)
        self.materials = [self.material_by_id(material_id) for material_id in desired_ids if self.material_by_id(material_id) is not None]
        return self.materials

    def next_plane_id(self) -> str:
        used_ids = {plane.id for plane in self.roof_planes}
        index = len(self.roof_planes) + 1
        while True:
            candidate = f"plane-{index}"
            if candidate not in used_ids:
                return candidate
            index += 1

    def next_plane_name(self) -> str:
        return str(len(self.roof_planes) + 1)

    def set_active_plane(self, plane_id: str | None) -> bool:
        if plane_id is None:
            self.active_plane_id = None
            return True

        plane = self.roof_plane_by_id(plane_id)
        if plane is None:
            return False

        self.active_plane_id = plane.id
        return True

    def set_active_material_for_plane(self, material_id: str, plane_id: str | None = None) -> bool:
        if not self.material_by_id(material_id):
            return False

        target_plane_id = plane_id or self.active_plane_id
        if target_plane_id is None:
            return False

        plane = next((item for item in self.roof_planes if item.id == target_plane_id), None)
        if plane is None:
            return False

        if plane.selected_material_id == material_id:
            return True

        plane.selected_material_id = material_id
        self._mark_layout_inputs_changed(plane, "material_changed")
        return True

    def add_roof_plane(
        self,
        outline: Polygon2D | None = None,
        *,
        name: str | None = None,
        selected_material_id: str | None = None,
    ) -> RoofPlane:
        if outline is not None:
            issues = validate_polygon(outline)
            if issues:
                raise ValueError("; ".join(issues))

        material_id = selected_material_id or self.active_material_id()
        plane = RoofPlane(
            id=self.next_plane_id(),
            name=name or self.next_plane_name(),
            outline=outline,
            selected_material_id=material_id,
        )
        plane.generation_settings.base_line_y_cm = self.resolve_base_line_y_cm(plane)
        self.roof_planes.append(plane)
        self.active_plane_id = plane.id
        return plane

    def add_empty_roof_plane(
        self,
        *,
        name: str | None = None,
        selected_material_id: str | None = None,
    ) -> RoofPlane:
        return self.add_roof_plane(None, name=name, selected_material_id=selected_material_id)

    def rename_roof_plane(self, plane_id: str, name: str) -> RoofPlane:
        plane = self.roof_plane_by_id(plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono połaci o podanym identyfikatorze")

        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Nazwa połaci nie może być pusta")

        plane.name = normalized_name
        return plane

    def duplicate_roof_plane(self, plane_id: str | None = None, *, name: str | None = None) -> RoofPlane:
        source_plane = self._require_plane(plane_id)
        duplicate = RoofPlane(
            id=self.next_plane_id(),
            name=name or self.next_plane_name(),
            outline=_clone_polygon(source_plane.outline),
            holes=[_clone_polygon(hole) for hole in source_plane.holes],
            selected_material_id=source_plane.selected_material_id,
            generation_settings=GenerationSettings.from_dict(source_plane.generation_settings.to_dict()),
            auto_sheet_placements=[SheetPlacement.from_dict(placement.to_dict()) for placement in source_plane.auto_sheet_placements],
            layout_bands=copy.deepcopy(source_plane.layout_bands),
            manual_sheet_placements=[SheetPlacement.from_dict(placement.to_dict()) for placement in source_plane.manual_sheet_placements],
            manually_removed_auto_sheet_ids=list(source_plane.manually_removed_auto_sheet_ids),
            layout_revision=source_plane.layout_revision,
            layout_dirty_reason=source_plane.layout_dirty_reason,
        )
        duplicate.generation_settings.base_line_y_cm = self.resolve_base_line_y_cm(duplicate)
        self.roof_planes.append(duplicate)
        self.active_plane_id = duplicate.id
        return duplicate

    def delete_roof_plane(self, plane_id: str) -> RoofPlane:
        plane_index = next((index for index, plane in enumerate(self.roof_planes) if plane.id == plane_id), None)
        if plane_index is None:
            raise ValueError("Nie znaleziono połaci o podanym identyfikatorze")

        removed_plane = self.roof_planes.pop(plane_index)
        if not self.roof_planes:
            self.active_plane_id = None
        elif self.active_plane_id == plane_id:
            replacement_index = min(plane_index, len(self.roof_planes) - 1)
            self.active_plane_id = self.roof_planes[replacement_index].id
        return removed_plane

    def set_roof_plane_outline(self, outline: Polygon2D, plane_id: str | None = None) -> RoofPlane:
        plane = self._require_plane(plane_id)
        self._validate_plane_geometry(outline, plane.holes)
        plane.outline = outline
        self._mark_layout_inputs_changed(plane, "geometry_changed")
        return plane

    def set_roof_plane_geometry(
        self,
        outline: Polygon2D,
        holes: list[Polygon2D] | None = None,
        plane_id: str | None = None,
    ) -> RoofPlane:
        plane = self._require_plane(plane_id)
        next_holes = list(plane.holes if holes is None else holes)
        self._validate_plane_geometry(outline, next_holes)
        plane.outline = outline
        plane.holes = next_holes
        self._mark_layout_inputs_changed(plane, "geometry_changed")
        return plane

    def move_roof_plane(self, dx: float, dy: float, plane_id: str | None = None) -> RoofPlane:
        plane = self._require_plane(plane_id)
        outline = self._require_plane_outline(plane)
        plane.outline = translate_polygon(outline, dx, dy)
        plane.holes = [translate_polygon(hole, dx, dy) for hole in plane.holes]
        self._mark_plane_geometry_changed(plane)
        return plane

    def move_roof_plane_point(self, point_index: int, dx: float, dy: float, plane_id: str | None = None) -> RoofPlane:
        plane = self._require_plane(plane_id)
        outline = self._require_plane_outline(plane)
        if point_index < 0 or point_index >= len(outline.points):
            raise IndexError("Nie znaleziono punktu o podanym indeksie")

        current_point = outline.points[point_index]
        updated_outline = replace_polygon_point(
            outline,
            point_index,
            Point2D(current_point.x + dx, current_point.y + dy),
        )
        self._set_plane_outline(plane, updated_outline)
        return plane

    def insert_roof_plane_point(self, edge_index: int, point: Point2D, plane_id: str | None = None) -> RoofPlane:
        plane = self._require_plane(plane_id)
        outline = self._require_plane_outline(plane)
        if edge_index < 0 or edge_index >= len(outline.points):
            raise IndexError("Nie znaleziono krawędzi o podanym indeksie")

        updated_outline = insert_polygon_point(outline, edge_index, point)
        self._set_plane_outline(plane, updated_outline)
        return plane

    def delete_roof_plane_point(self, point_index: int, plane_id: str | None = None) -> RoofPlane:
        plane = self._require_plane(plane_id)
        outline = self._require_plane_outline(plane)
        if point_index < 0 or point_index >= len(outline.points):
            raise IndexError("Nie znaleziono punktu o podanym indeksie")

        updated_outline = delete_polygon_point(outline, point_index)
        self._set_plane_outline(plane, updated_outline)
        return plane

    def add_hole_to_plane(self, hole: Polygon2D, plane_id: str | None = None) -> RoofPlane:
        plane = self._require_plane(plane_id)
        outline = self._require_plane_outline(plane)

        self._validate_hole_geometry(outline, hole, plane.holes, hole_index=len(plane.holes))

        plane.holes.append(hole)
        self._mark_layout_inputs_changed(plane, "geometry_changed")
        return plane

    def set_hole_polygon(self, hole_index: int, hole: Polygon2D, plane_id: str | None = None) -> RoofPlane:
        plane = self._require_plane(plane_id)
        outline = self._require_plane_outline(plane)
        if hole_index < 0 or hole_index >= len(plane.holes):
            raise IndexError("Nie znaleziono wycinku o podanym indeksie")

        sibling_holes = [candidate for index, candidate in enumerate(plane.holes) if index != hole_index]
        self._validate_hole_geometry(outline, hole, sibling_holes, hole_index=hole_index)

        plane.holes[hole_index] = hole
        self._mark_layout_inputs_changed(plane, "geometry_changed")
        return plane

    def delete_hole_from_plane(self, hole_index: int, plane_id: str | None = None) -> RoofPlane:
        plane = self._require_plane(plane_id)
        self._require_plane_outline(plane)
        if hole_index < 0 or hole_index >= len(plane.holes):
            raise IndexError("Nie znaleziono wycinku o podanym indeksie")

        del plane.holes[hole_index]
        self._mark_plane_geometry_changed(plane)
        return plane

    def move_hole_in_plane(self, hole_index: int, dx: float, dy: float, plane_id: str | None = None) -> RoofPlane:
        plane = self._require_plane(plane_id)
        if hole_index < 0 or hole_index >= len(plane.holes):
            raise IndexError("Nie znaleziono wycinku o podanym indeksie")

        moved_hole = translate_polygon(plane.holes[hole_index], dx, dy)
        return self.set_hole_polygon(hole_index, moved_hole, plane.id)

    def move_hole_point(self, hole_index: int, point_index: int, dx: float, dy: float, plane_id: str | None = None) -> RoofPlane:
        plane = self._require_plane(plane_id)
        if hole_index < 0 or hole_index >= len(plane.holes):
            raise IndexError("Nie znaleziono wycinku o podanym indeksie")

        hole = plane.holes[hole_index]
        if point_index < 0 or point_index >= len(hole.points):
            raise IndexError("Nie znaleziono punktu wycinka o podanym indeksie")

        current_point = hole.points[point_index]
        updated_hole = replace_polygon_point(
            hole,
            point_index,
            Point2D(current_point.x + dx, current_point.y + dy),
        )
        return self.set_hole_polygon(hole_index, updated_hole, plane.id)

    def _is_placement_removed(self, placement_id: str, removed_ids: set[str]) -> bool:
        """Check if placement ID matches any removed ID (exact or legacy prefix match).

        Uses O(1) set lookup. For legacy backward-compatibility, checks if the
        placement_id has a -r{row} suffix and whether its base is in removed_ids.
        """
        if placement_id in removed_ids:
            return True
        # Legacy backward-compat: removed ID may lack -r\d+ suffix (old format)
        m = re.search(r"-r\d+$", placement_id)
        if m:
            base = placement_id[: m.start()]
            if base in removed_ids:
                return True
        return False
    
    def active_sheet_placements_for_plane(self, plane_id: str | None = None) -> list[SheetPlacement]:
        plane = self.roof_plane_by_id(plane_id or self.active_plane_id)
        if plane is None:
            return []

        removed_ids = set(plane.manually_removed_auto_sheet_ids)
        placements = [placement for placement in plane.auto_sheet_placements if not self._is_placement_removed(placement.id, removed_ids)]
        placements.extend(plane.manual_sheet_placements)
        return sorted(placements, key=lambda placement: (placement.band_index, placement.x_left_cm, placement.y_top_cm, placement.id))

    def add_manual_sheet_placement(self, placement: SheetPlacement, plane_id: str | None = None) -> SheetPlacement:
        plane = self.roof_plane_by_id(plane_id or self.active_plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")

        if placement.width_cm <= 0:
            raise ValueError("Szerokość arkusza musi być dodatnia")
        if placement.raw_length_cm <= 0 or placement.final_length_cm <= 0:
            raise ValueError("Długość arkusza musi być dodatnia")

        manual_placement = SheetPlacement(
            id=placement.id,
            band_index=placement.band_index,
            x_left_cm=placement.x_left_cm,
            x_right_cm=placement.x_right_cm,
            y_top_cm=placement.y_top_cm,
            y_bottom_cm=placement.y_bottom_cm,
            raw_length_cm=placement.raw_length_cm,
            final_length_cm=placement.final_length_cm,
            source="manual",
            split_reason=placement.split_reason,
        )
        duplicate_ids = {item.id for item in plane.auto_sheet_placements}
        duplicate_ids.update(item.id for item in plane.manual_sheet_placements)
        if manual_placement.id in duplicate_ids:
            raise ValueError("Arkusz o podanym identyfikatorze już istnieje")

        plane.manual_sheet_placements.append(manual_placement)
        plane.layout_revision += 1
        plane.layout_dirty_reason = "manual_override"
        return manual_placement

    def remove_sheet_placement(self, sheet_id: str, plane_id: str | None = None) -> None:
        plane = self.roof_plane_by_id(plane_id or self.active_plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")

        manual_index = next((index for index, placement in enumerate(plane.manual_sheet_placements) if placement.id == sheet_id), None)
        if manual_index is not None:
            del plane.manual_sheet_placements[manual_index]
            plane.layout_revision += 1
            plane.layout_dirty_reason = "manual_override"
            return

        if any(placement.id == sheet_id for placement in plane.auto_sheet_placements):
            if sheet_id not in plane.manually_removed_auto_sheet_ids:
                plane.manually_removed_auto_sheet_ids.append(sheet_id)
                plane.layout_revision += 1
                plane.layout_dirty_reason = "manual_override"
            return

        raise ValueError("Nie znaleziono arkusza o podanym identyfikatorze")

    def resolve_base_line_y_cm(self, plane: RoofPlane) -> float:
        if plane.outline is None:
            return 0.0
        return plane.outline.bounds().max_y

    def generate_layout_for_plane(self, plane_id: str | None = None) -> LayoutResult:
        plane = self.roof_plane_by_id(plane_id or self.active_plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")
        if plane.outline is None:
            raise ValueError("Aktywna połać nie ma jeszcze obrysu")

        material = self.material_by_id(plane.selected_material_id) or self.material_by_id(self.active_material_id())
        if material is None:
            raise ValueError("Brak aktywnego materiału dla połaci")

        plane.generation_settings.base_line_y_cm = self.resolve_base_line_y_cm(plane)
        result = generate_layout(plane, material, settings=self.app_settings)
        plane.auto_sheet_placements = list(result.placements)
        plane.layout_bands = [band.to_dict() for band in result.bands]
        plane.layout_revision += 1
        plane.layout_dirty_reason = None
        return result

    def generate_layout_for_active_plane(self) -> LayoutResult:
        return self.generate_layout_for_plane(self.active_plane_id)

    def active_material_id(self) -> str | None:
        active_plane = self.active_roof_plane()
        if active_plane and active_plane.selected_material_id:
            return active_plane.selected_material_id
        if self.materials:
            return self.materials[0].id
        return None

    def _require_plane(self, plane_id: str | None = None) -> RoofPlane:
        plane = self.roof_plane_by_id(plane_id or self.active_plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")
        return plane

    def _require_plane_outline(self, plane: RoofPlane) -> Polygon2D:
        if plane.outline is None:
            raise ValueError("Aktywna połać nie ma jeszcze obrysu")
        return plane.outline

    def _set_plane_outline(self, plane: RoofPlane, outline: Polygon2D) -> None:
        self._validate_plane_geometry(outline, plane.holes)
        plane.outline = outline
        self._mark_layout_inputs_changed(plane, "geometry_changed")

    def _validate_plane_geometry(self, outline: Polygon2D, holes: list[Polygon2D]) -> None:
        issues = validate_polygon(outline)
        if issues:
            raise ValueError("; ".join(issues))

        for hole_index, hole in enumerate(holes):
            sibling_holes = [candidate for index, candidate in enumerate(holes) if index != hole_index]
            self._validate_hole_geometry(outline, hole, sibling_holes, hole_index=hole_index)

    def _validate_hole_geometry(
        self,
        outline: Polygon2D,
        hole: Polygon2D,
        sibling_holes: list[Polygon2D],
        *,
        hole_index: int,
    ) -> None:
        hole_issues = validate_hole_polygon(outline, hole, sibling_holes)
        blocking_issues = [
            issue for issue in hole_issues if issue != "Wycinek musi leżeć w całości wewnątrz obrysu"
        ]
        if any(issue == "Wycinek musi leżeć w całości wewnątrz obrysu" for issue in hole_issues):
            log.warning("Hole %d partially or fully outside outline — allowed", hole_index)
        if blocking_issues:
            raise ValueError("; ".join(blocking_issues))

    def _mark_plane_geometry_changed(self, plane: RoofPlane) -> None:
        self._mark_layout_inputs_changed(plane, "geometry_changed")

    def _mark_layout_inputs_changed(self, plane: RoofPlane, reason: str) -> None:
        plane.layout_revision += 1
        plane.auto_sheet_placements.clear()
        plane.layout_bands.clear()
        plane.manually_removed_auto_sheet_ids.clear()
        plane.generation_settings.base_line_y_cm = self.resolve_base_line_y_cm(plane)
        plane.layout_dirty_reason = reason

    def _mark_planes_using_material_dirty(self, material_id: str) -> None:
        for plane in self.roof_planes:
            if plane.selected_material_id == material_id:
                self._mark_layout_inputs_changed(plane, "material_changed")

    def apply_to_config(self, config_data: dict) -> dict:
        config_data.pop("materials", None)
        config_data.update(self.to_config_fragment())
        return config_data

    def to_config_fragment(self) -> dict:
        return {
            "app_settings": self.app_settings.to_dict(),
            "materials": _serialize_materials(self.materials),
            "blachy": [material.to_dict() for material in self.materials],
            "project_state": {
                "version": max(self.version, 2),
                "active_plane_id": self.active_plane_id,
                "roof_planes": _serialize_roof_planes(self.roof_planes),
            }
        }

    def _rebuild_runtime_layout_cache(self) -> None:
        for plane in self.roof_planes:
            plane.generation_settings.base_line_y_cm = self.resolve_base_line_y_cm(plane)
            if plane.outline is None:
                plane.auto_sheet_placements = []
                plane.layout_bands = []
                continue
            if plane.layout_dirty_reason not in (None, "manual_override"):
                plane.auto_sheet_placements = []
                plane.layout_bands = []
                continue
            material = self.material_by_id(plane.selected_material_id) or self.material_by_id(self.active_material_id())
            if material is None:
                continue
            result = generate_layout(plane, material, settings=self.app_settings)
            plane.auto_sheet_placements = list(result.placements)
            plane.layout_bands = [band.to_dict() for band in result.bands]


def _deserialize_materials(payload: object) -> list[Material]:
    if isinstance(payload, dict):
        items = payload.get("items", {})
        order = payload.get("order", list(items.keys()))
        return [
            Material.from_dict(_expand_compact_material_payload(items[material_id], material_id))
            for material_id in order
            if material_id in items
        ]
    if isinstance(payload, list):
        return [Material.from_dict(item) for item in payload]
    return []


def _serialize_materials(materials: list[Material]) -> dict:
    return {
        "order": [material.id for material in materials],
        "items": {
            material.id: {
                "n": material.display_name,
                "t": material.type,
                "w": material.effective_width_cm,
                "min": material.min_sheet_length_cm,
                "max": material.max_sheet_length_cm,
                "top": material.top_margin_cm,
                "bottom": material.bottom_margin_cm,
                "mod": material.module_length_cm,
                "p": material.price_per_m2,
                "bat": material.batten_spacing_cm,
                "cbat": material.counter_batten_spacing_cm,
                "mods": list(material.modules),
                "u": material.price_unit,
            }
            for material in materials
        },
    }


def _expand_compact_material_payload(payload: dict, material_id: str) -> dict:
    return {
        "id": material_id,
        "display_name": payload.get("n"),
        "type": payload.get("t", "dachówkowa"),
        "effective_width_cm": payload.get("w", 0.0),
        "min_sheet_length_cm": payload.get("min", 0.0),
        "max_sheet_length_cm": payload.get("max", 900.0),
        "top_allowance_cm": payload.get("top", 0.0),
        "bottom_allowance_cm": payload.get("bottom", 0.0),
        "module_length_cm": payload.get("mod"),
        "price_per_m2": payload.get("p"),
        "odleglosc_miedzy_latami": payload.get("bat", 0.0),
        "odleglosc_miedzy_kontrlatami": payload.get("cbat", 0.0),
        "moduly": payload.get("mods", []),
        "cena_za": payload.get("u", "m2"),
    }


def _iter_plane_payloads(payload: object) -> list[dict]:
    if isinstance(payload, dict):
        items = payload.get("items", {})
        order = payload.get("order", list(items.keys()))
        return [dict(items[plane_id], id=plane_id) for plane_id in order if plane_id in items]
    if isinstance(payload, list):
        return payload
    return []


def _serialize_roof_planes(planes: list[RoofPlane]) -> dict:
    items: dict[str, dict] = {}
    order: list[str] = []
    for plane in planes:
        order.append(plane.id)
        payload = {
            "n": plane.name,
            "m": plane.selected_material_id,
            "g": _serialize_generation_settings(plane.generation_settings),
            "o": _serialize_polygon(plane.outline),
            "h": [_serialize_polygon(hole) for hole in plane.holes],
            "mp": _serialize_placements(plane.manual_sheet_placements),
            "rm": list(plane.manually_removed_auto_sheet_ids),
            "r": plane.layout_revision,
            "d": plane.layout_dirty_reason,
        }
        items[plane.id] = payload
    return {"order": order, "items": items}


def _serialize_generation_settings(settings: GenerationSettings) -> dict:
    payload = {"o": settings.layout_origin}
    if settings.origin_x_cm is not None:
        payload["x"] = settings.origin_x_cm
    if settings.origin_y_cm is not None:
        payload["y"] = settings.origin_y_cm
    return payload


def _deserialize_generation_settings(payload: object) -> GenerationSettings:
    if isinstance(payload, dict) and "o" in payload:
        return GenerationSettings.from_dict(
            {
                "layout_origin": payload.get("o", "left"),
                "origin_x_cm": payload.get("x"),
                "origin_y_cm": payload.get("y"),
            }
        )
    return GenerationSettings.from_dict(payload if isinstance(payload, dict) else None)


def _serialize_point(point: Point2D) -> list[float]:
    return [point.x, point.y]


def _deserialize_point(payload: object) -> Point2D | None:
    if isinstance(payload, dict):
        return Point2D(float(payload["x"]), float(payload["y"]))
    if isinstance(payload, (list, tuple)) and len(payload) == 2:
        return Point2D(float(payload[0]), float(payload[1]))
    return None


def _serialize_polygon(polygon: Polygon2D | None) -> list[list[float]]:
    if polygon is None:
        return []
    return [_serialize_point(point) for point in polygon.points]


def _deserialize_polygon(payload: object) -> Polygon2D | None:
    if not isinstance(payload, list):
        return None
    points = [point for point in (_deserialize_point(item) for item in payload) if point is not None]
    if len(points) < 3:
        return None
    return Polygon2D(points)


def _serialize_placements(placements: list[SheetPlacement]) -> dict:
    return {
        "order": [placement.id for placement in placements],
        "items": {
            placement.id: [
                placement.band_index,
                placement.x_left_cm,
                placement.x_right_cm,
                placement.y_top_cm,
                placement.y_bottom_cm,
                placement.raw_length_cm,
                placement.final_length_cm,
                placement.split_reason,
            ]
            for placement in placements
        },
    }


def _deserialize_placements(payload: object, *, source: str) -> list[SheetPlacement]:
    if isinstance(payload, dict):
        items = payload.get("items", {})
        order = payload.get("order", list(items.keys()))
        placements: list[SheetPlacement] = []
        for placement_id in order:
            entry = items.get(placement_id)
            if not isinstance(entry, (list, tuple)) or len(entry) < 7:
                continue
            placements.append(
                SheetPlacement(
                    id=placement_id,
                    band_index=int(entry[0]),
                    x_left_cm=float(entry[1]),
                    x_right_cm=float(entry[2]),
                    y_top_cm=float(entry[3]),
                    y_bottom_cm=float(entry[4]),
                    raw_length_cm=float(entry[5]),
                    final_length_cm=float(entry[6]),
                    source=source,
                    split_reason=entry[7] if len(entry) > 7 else None,
                )
            )
        return placements
    if isinstance(payload, list):
        return [SheetPlacement.from_dict({**item, "source": source}) for item in payload]
    return []


def _serialize_layout_bands(layout_bands: list[dict]) -> dict:
    items: dict[str, list] = {}
    order: list[str] = []
    for band in layout_bands:
        band_id = str(int(band.get("band_index", len(order))))
        order.append(band_id)
        items[band_id] = [
            band.get("x_left_cm", 0.0),
            band.get("x_right_cm", 0.0),
            [
                [
                    segment.get("segment_index", 0),
                    segment.get("y_top_cm", 0.0),
                    segment.get("y_bottom_cm", 0.0),
                    segment.get("raw_length_cm", 0.0),
                    [
                        _serialize_polygon(_deserialize_polygon(polygon))
                        for polygon in segment.get("coverage_polygons", [])
                    ],
                    segment.get("placement_id"),
                    segment.get("split_reason"),
                    segment.get("cutout_interaction"),
                    segment.get("partial_cut_line_y_cm"),
                    segment.get("top_extra_cm", 0.0),
                ]
                for segment in band.get("segments", [])
            ],
        ]
    return {"order": order, "items": items}


def _deserialize_layout_bands(payload: object) -> list[dict]:
    if isinstance(payload, dict):
        items = payload.get("items", {})
        order = payload.get("order", list(items.keys()))
        bands: list[dict] = []
        for band_id in order:
            entry = items.get(band_id)
            if not isinstance(entry, (list, tuple)) or len(entry) < 3:
                continue
            segments = []
            for segment_entry in entry[2]:
                if not isinstance(segment_entry, (list, tuple)) or len(segment_entry) < 5:
                    continue
                segments.append(
                    {
                        "segment_index": int(segment_entry[0]),
                        "x_left_cm": float(entry[0]),
                        "x_right_cm": float(entry[1]),
                        "y_top_cm": float(segment_entry[1]),
                        "y_bottom_cm": float(segment_entry[2]),
                        "raw_length_cm": float(segment_entry[3]),
                        "coverage_polygons": [
                            _serialize_polygon(_deserialize_polygon(polygon))
                            for polygon in segment_entry[4]
                        ],
                        "placement_id": segment_entry[5] if len(segment_entry) > 5 else None,
                        "split_reason": segment_entry[6] if len(segment_entry) > 6 else None,
                        "cutout_interaction": segment_entry[7] if len(segment_entry) > 7 else None,
                        "partial_cut_line_y_cm": segment_entry[8] if len(segment_entry) > 8 else None,
                        "top_extra_cm": float(segment_entry[9]) if len(segment_entry) > 9 and segment_entry[9] is not None else 0.0,
                    }
                )
            bands.append(
                {
                    "band_index": int(band_id),
                    "x_left_cm": float(entry[0]),
                    "x_right_cm": float(entry[1]),
                    "segments": segments,
                }
            )
        return bands
    if isinstance(payload, list):
        return list(payload)
    return []


def _clone_polygon(polygon: Polygon2D | None) -> Polygon2D | None:
    if polygon is None:
        return None
    return Polygon2D([Point2D(point.x, point.y) for point in polygon.points])
