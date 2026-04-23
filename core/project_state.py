from __future__ import annotations

from dataclasses import dataclass, field

from core.geometry import (
    delete_polygon_point,
    insert_polygon_point,
    replace_polygon_point,
    translate_polygon,
    validate_hole_polygon,
    validate_polygon,
)
from core.layout_engine import LayoutResult, generate_layout
from core.models import CompanyData, GenerationSettings, Material, Point2D, Polygon2D, RoofPlane, SheetPlacement


@dataclass(slots=True)
class ProjectState:
    company_data: CompanyData = field(default_factory=CompanyData)
    materials: list[Material] = field(default_factory=list)
    roof_planes: list[RoofPlane] = field(default_factory=list)
    active_plane_id: str | None = None
    version: int = 1

    @classmethod
    def from_config(cls, config_data: dict | None) -> "ProjectState":
        payload = config_data or {}
        project_payload = payload.get("project_state", {})
        materials = [Material.from_dict(item) for item in payload.get("blachy", [])]
        roof_planes: list[RoofPlane] = []

        for plane_payload in project_payload.get("roof_planes", []):
            outline_points = plane_payload.get("outline", [])
            if len(outline_points) < 3:
                continue
            outline = Polygon2D([Point2D(point["x"], point["y"]) for point in outline_points])
            holes = [
                Polygon2D([Point2D(point["x"], point["y"]) for point in hole_points])
                for hole_points in plane_payload.get("holes", [])
                if len(hole_points) >= 3
            ]
            roof_planes.append(
                RoofPlane(
                    id=plane_payload["id"],
                    name=plane_payload.get("name", plane_payload["id"]),
                    outline=outline,
                    holes=holes,
                    selected_material_id=plane_payload.get("selected_material_id"),
                    generation_settings=GenerationSettings.from_dict(plane_payload.get("generation_settings")),
                    auto_sheet_placements=[
                        SheetPlacement.from_dict(item) for item in plane_payload.get("auto_sheet_placements", [])
                    ],
                    manual_sheet_placements=[
                        SheetPlacement.from_dict(item) for item in plane_payload.get("manual_sheet_placements", [])
                    ],
                    layout_revision=int(plane_payload.get("layout_revision", 0)),
                )
            )

        active_plane_id = project_payload.get("active_plane_id")
        if active_plane_id is None and roof_planes:
            active_plane_id = roof_planes[0].id

        return cls(
            company_data=CompanyData.from_dict(payload.get("company_data")),
            materials=materials,
            roof_planes=roof_planes,
            active_plane_id=active_plane_id,
            version=project_payload.get("version", 1),
        )

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

    def set_active_material_for_plane(self, material_id: str, plane_id: str | None = None) -> bool:
        if not self.material_by_id(material_id):
            return False

        target_plane_id = plane_id or self.active_plane_id
        if target_plane_id is None:
            return False

        plane = next((item for item in self.roof_planes if item.id == target_plane_id), None)
        if plane is None:
            return False

        plane.selected_material_id = material_id
        return True

    def add_roof_plane(
        self,
        outline: Polygon2D,
        *,
        name: str | None = None,
        selected_material_id: str | None = None,
    ) -> RoofPlane:
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

    def move_roof_plane(self, dx: float, dy: float, plane_id: str | None = None) -> RoofPlane:
        plane = self.roof_plane_by_id(plane_id or self.active_plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")

        plane.outline = translate_polygon(plane.outline, dx, dy)
        plane.holes = [translate_polygon(hole, dx, dy) for hole in plane.holes]
        self._mark_plane_geometry_changed(plane)
        return plane

    def move_roof_plane_point(self, point_index: int, dx: float, dy: float, plane_id: str | None = None) -> RoofPlane:
        plane = self.roof_plane_by_id(plane_id or self.active_plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")
        if point_index < 0 or point_index >= len(plane.outline.points):
            raise IndexError("Nie znaleziono punktu o podanym indeksie")

        current_point = plane.outline.points[point_index]
        updated_outline = replace_polygon_point(
            plane.outline,
            point_index,
            Point2D(current_point.x + dx, current_point.y + dy),
        )
        self._set_plane_outline(plane, updated_outline)
        return plane

    def insert_roof_plane_point(self, edge_index: int, point: Point2D, plane_id: str | None = None) -> RoofPlane:
        plane = self.roof_plane_by_id(plane_id or self.active_plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")
        if edge_index < 0 or edge_index >= len(plane.outline.points):
            raise IndexError("Nie znaleziono krawędzi o podanym indeksie")

        updated_outline = insert_polygon_point(plane.outline, edge_index, point)
        self._set_plane_outline(plane, updated_outline)
        return plane

    def delete_roof_plane_point(self, point_index: int, plane_id: str | None = None) -> RoofPlane:
        plane = self.roof_plane_by_id(plane_id or self.active_plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")
        if point_index < 0 or point_index >= len(plane.outline.points):
            raise IndexError("Nie znaleziono punktu o podanym indeksie")

        updated_outline = delete_polygon_point(plane.outline, point_index)
        self._set_plane_outline(plane, updated_outline)
        return plane

    def add_hole_to_plane(self, hole: Polygon2D, plane_id: str | None = None) -> RoofPlane:
        plane = self.roof_plane_by_id(plane_id or self.active_plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")

        issues = validate_hole_polygon(plane.outline, hole, plane.holes)
        if issues:
            raise ValueError("; ".join(issues))

        plane.holes.append(hole)
        plane.layout_revision += 1
        plane.auto_sheet_placements.clear()
        plane.generation_settings.base_line_y_cm = self.resolve_base_line_y_cm(plane)
        return plane

    def delete_hole_from_plane(self, hole_index: int, plane_id: str | None = None) -> RoofPlane:
        plane = self.roof_plane_by_id(plane_id or self.active_plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")
        if hole_index < 0 or hole_index >= len(plane.holes):
            raise IndexError("Nie znaleziono wycinku o podanym indeksie")

        del plane.holes[hole_index]
        self._mark_plane_geometry_changed(plane)
        return plane

    def move_hole_in_plane(self, hole_index: int, dx: float, dy: float, plane_id: str | None = None) -> RoofPlane:
        plane = self.roof_plane_by_id(plane_id or self.active_plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")
        if hole_index < 0 or hole_index >= len(plane.holes):
            raise IndexError("Nie znaleziono wycinku o podanym indeksie")

        moved_hole = translate_polygon(plane.holes[hole_index], dx, dy)
        sibling_holes = [hole for index, hole in enumerate(plane.holes) if index != hole_index]
        issues = validate_hole_polygon(plane.outline, moved_hole, sibling_holes)
        if issues:
            raise ValueError("; ".join(issues))

        plane.holes[hole_index] = moved_hole
        plane.layout_revision += 1
        plane.auto_sheet_placements.clear()
        plane.generation_settings.base_line_y_cm = self.resolve_base_line_y_cm(plane)
        return plane

    def resolve_base_line_y_cm(self, plane: RoofPlane) -> float:
        return plane.outline.bounds().max_y

    def generate_layout_for_plane(self, plane_id: str | None = None) -> LayoutResult:
        plane = self.roof_plane_by_id(plane_id or self.active_plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")

        material = self.material_by_id(plane.selected_material_id) or self.material_by_id(self.active_material_id())
        if material is None:
            raise ValueError("Brak aktywnego materiału dla połaci")

        plane.generation_settings.base_line_y_cm = self.resolve_base_line_y_cm(plane)
        result = generate_layout(plane, material)
        plane.auto_sheet_placements = list(result.placements)
        plane.layout_revision += 1
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

    def _set_plane_outline(self, plane: RoofPlane, outline: Polygon2D) -> None:
        self._validate_plane_geometry(outline, plane.holes)
        plane.outline = outline
        self._mark_plane_geometry_changed(plane)

    def _validate_plane_geometry(self, outline: Polygon2D, holes: list[Polygon2D]) -> None:
        issues = validate_polygon(outline)
        if issues:
            raise ValueError("; ".join(issues))

        for hole_index, hole in enumerate(holes):
            sibling_holes = [candidate for index, candidate in enumerate(holes) if index != hole_index]
            hole_issues = validate_hole_polygon(outline, hole, sibling_holes)
            if hole_issues:
                raise ValueError("; ".join(hole_issues))

    def _mark_plane_geometry_changed(self, plane: RoofPlane) -> None:
        plane.layout_revision += 1
        plane.auto_sheet_placements.clear()
        plane.generation_settings.base_line_y_cm = self.resolve_base_line_y_cm(plane)

    def apply_to_config(self, config_data: dict) -> dict:
        config_data.update(self.to_config_fragment())
        return config_data

    def to_config_fragment(self) -> dict:
        return {
            "project_state": {
                "version": self.version,
                "active_plane_id": self.active_plane_id,
                "roof_planes": [
                    {
                        "id": plane.id,
                        "name": plane.name,
                        "selected_material_id": plane.selected_material_id,
                        "generation_settings": plane.generation_settings.to_dict(),
                        "auto_sheet_placements": [placement.to_dict() for placement in plane.auto_sheet_placements],
                        "manual_sheet_placements": [placement.to_dict() for placement in plane.manual_sheet_placements],
                        "layout_revision": plane.layout_revision,
                        "outline": [{"x": point.x, "y": point.y} for point in plane.outline.points],
                        "holes": [
                            [{"x": point.x, "y": point.y} for point in hole.points]
                            for hole in plane.holes
                        ],
                    }
                    for plane in self.roof_planes
                ],
            }
        }
