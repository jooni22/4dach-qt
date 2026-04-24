from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose
from typing import Literal


MaterialType = Literal["dachówkowa", "trapezowa"]
SheetSource = Literal["auto", "manual"]
LayoutOrigin = Literal["left", "right"]


@dataclass(slots=True, frozen=True)
class Point2D:
    x: float
    y: float


@dataclass(slots=True, frozen=True)
class Bounds2D:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y


@dataclass(slots=True)
class Polygon2D:
    points: list[Point2D]

    def __post_init__(self) -> None:
        if len(self.points) < 3:
            raise ValueError("Polygon2D requires at least 3 points")

    def bounds(self) -> Bounds2D:
        xs = [point.x for point in self.points]
        ys = [point.y for point in self.points]
        return Bounds2D(min(xs), min(ys), max(xs), max(ys))

    def signed_area(self) -> float:
        area = 0.0
        points = self.points
        for index, point in enumerate(points):
            next_point = points[(index + 1) % len(points)]
            area += point.x * next_point.y - next_point.x * point.y
        return area / 2.0

    def area(self) -> float:
        return abs(self.signed_area())

    def translated(self, dx: float, dy: float) -> "Polygon2D":
        return Polygon2D([Point2D(point.x + dx, point.y + dy) for point in self.points])

    @classmethod
    def rectangle(cls, width_cm: float, height_cm: float, origin_x: float = 0.0, origin_y: float = 0.0) -> "Polygon2D":
        return cls(
            [
                Point2D(origin_x, origin_y),
                Point2D(origin_x + width_cm, origin_y),
                Point2D(origin_x + width_cm, origin_y + height_cm),
                Point2D(origin_x, origin_y + height_cm),
            ]
        )


@dataclass(slots=True)
class CompanyData:
    name: str = ""
    nip: str = ""
    address: str = ""
    website: str = ""
    logo: str = ""

    @classmethod
    def from_dict(cls, data: dict | None) -> "CompanyData":
        payload = data or {}
        return cls(
            name=payload.get("name", ""),
            nip=payload.get("nip", ""),
            address=payload.get("address", ""),
            website=payload.get("website", ""),
            logo=payload.get("logo", ""),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "nip": self.nip,
            "address": self.address,
            "website": self.website,
            "logo": self.logo,
        }


@dataclass(slots=True)
class MaterialDefinition:
    id: str
    display_name: str
    type: MaterialType
    effective_width_cm: float
    min_sheet_length_cm: float
    max_sheet_length_cm: float = 900.0
    top_margin_cm: float = 0.0
    bottom_margin_cm: float = 0.0
    module_length_cm: float | None = None
    price_per_m2: float | None = None
    batten_spacing_cm: float = 0.0
    counter_batten_spacing_cm: float = 0.0
    modules: list[int] = field(default_factory=list)
    price_unit: str = "m2"

    def __init__(
        self,
        id: str,
        display_name: str | None = None,
        type: MaterialType = "trapezowa",
        effective_width_cm: float = 0.0,
        min_sheet_length_cm: float = 0.0,
        max_sheet_length_cm: float = 900.0,
        top_margin_cm: float = 0.0,
        bottom_margin_cm: float = 0.0,
        module_length_cm: float | None = None,
        price_per_m2: float | None = None,
        batten_spacing_cm: float = 0.0,
        counter_batten_spacing_cm: float = 0.0,
        modules: list[int] | None = None,
        price_unit: str = "m2",
        nazwa: str | None = None,
        price_value: float | None = None,
    ) -> None:
        self.id = id
        self.display_name = (display_name or nazwa or id).strip() or id
        self.type = type
        self.effective_width_cm = float(effective_width_cm)
        self.min_sheet_length_cm = float(min_sheet_length_cm)
        self.max_sheet_length_cm = float(max_sheet_length_cm)
        self.top_margin_cm = float(top_margin_cm)
        self.bottom_margin_cm = float(bottom_margin_cm)
        self.module_length_cm = None if module_length_cm in (None, 0, 0.0) else float(module_length_cm)
        resolved_price = price_per_m2 if price_per_m2 is not None else price_value
        self.price_per_m2 = None if resolved_price is None else float(resolved_price)
        self.batten_spacing_cm = float(batten_spacing_cm)
        self.counter_batten_spacing_cm = float(counter_batten_spacing_cm)
        self.modules = list(modules or [])
        self.price_unit = price_unit

    @property
    def nazwa(self) -> str:
        return self.display_name

    @property
    def price_value(self) -> float:
        return 0.0 if self.price_per_m2 is None else self.price_per_m2

    @classmethod
    def from_dict(cls, data: dict) -> "MaterialDefinition":
        return cls(
            id=data.get("id") or data.get("nazwa") or data.get("display_name") or "material",
            display_name=data.get("display_name") or data.get("nazwa") or data.get("id") or "material",
            type=data.get("type", "dachówkowa"),
            effective_width_cm=float(data.get("effective_width_cm", data.get("szerokosc_efektywna", 0))),
            min_sheet_length_cm=float(data.get("min_dlugosc_arkusza", 0)),
            max_sheet_length_cm=float(data.get("max_sheet_length_cm", data.get("max_dlugosc_arkusza", 900))),
            top_margin_cm=float(data.get("top_allowance_cm", data.get("zapas_gorny", 0))),
            bottom_margin_cm=float(data.get("bottom_allowance_cm", data.get("zapas_dolny", 0))),
            module_length_cm=data.get("module_length_cm", data.get("dlugosc_modulu")),
            price_per_m2=(
                data.get("price_per_m2")
                if "price_per_m2" in data
                else float(data.get("cena_zl", 0)) + float(data.get("cena_gr", 0)) / 100.0
            ),
            batten_spacing_cm=float(data.get("odleglosc_miedzy_latami", 0)),
            counter_batten_spacing_cm=float(data.get("odleglosc_miedzy_kontrlatami", 0)),
            modules=[int(value) for value in data.get("moduly", [])],
            price_unit=data.get("cena_za", "m2"),
        )

    def to_dict(self) -> dict:
        normalized_price = 0.0 if self.price_per_m2 is None else self.price_per_m2
        zl = int(normalized_price)
        gr = int(round((normalized_price - zl) * 100))
        if gr == 100:
            zl += 1
            gr = 0
        return {
            "id": self.id,
            "type": self.type,
            "display_name": self.display_name,
            "nazwa": self.display_name,
            "effective_width_cm": self.effective_width_cm,
            "szerokosc_efektywna": self.effective_width_cm,
            "module_length_cm": self.module_length_cm,
            "dlugosc_modulu": 0 if self.module_length_cm is None else self.module_length_cm,
            "top_allowance_cm": self.top_margin_cm,
            "bottom_allowance_cm": self.bottom_margin_cm,
            "zapas_dolny": self.bottom_margin_cm,
            "zapas_gorny": self.top_margin_cm,
            "min_dlugosc_arkusza": self.min_sheet_length_cm,
            "max_sheet_length_cm": self.max_sheet_length_cm,
            "max_dlugosc_arkusza": self.max_sheet_length_cm,
            "odleglosc_miedzy_latami": self.batten_spacing_cm,
            "odleglosc_miedzy_kontrlatami": self.counter_batten_spacing_cm,
            "moduly": list(self.modules),
            "cena_za": self.price_unit,
            "price_per_m2": self.price_per_m2,
            "cena_zl": zl,
            "cena_gr": gr,
        }


Material = MaterialDefinition


@dataclass(slots=True)
class GenerationSettings:
    layout_origin: LayoutOrigin = "left"
    base_line_y_cm: float | None = None

    @classmethod
    def from_dict(cls, data: dict | None) -> "GenerationSettings":
        payload = data or {}
        base_line_y_cm = payload.get("base_line_y_cm")
        return cls(
            layout_origin=payload.get("layout_origin", "left"),
            base_line_y_cm=None if base_line_y_cm in (None, "") else float(base_line_y_cm),
        )

    def to_dict(self) -> dict:
        return {
            "layout_origin": self.layout_origin,
            "base_line_y_cm": self.base_line_y_cm,
        }


@dataclass(slots=True)
class SheetPlacement:
    id: str
    band_index: int
    x_left_cm: float
    x_right_cm: float
    y_top_cm: float
    y_bottom_cm: float
    raw_length_cm: float
    final_length_cm: float
    source: SheetSource = "auto"
    split_reason: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "SheetPlacement":
        return cls(
            id=data["id"],
            band_index=int(data.get("band_index", 0)),
            x_left_cm=float(data.get("x_left_cm", 0.0)),
            x_right_cm=float(data.get("x_right_cm", 0.0)),
            y_top_cm=float(data.get("y_top_cm", 0.0)),
            y_bottom_cm=float(data.get("y_bottom_cm", 0.0)),
            raw_length_cm=float(data.get("raw_length_cm", 0.0)),
            final_length_cm=float(data.get("final_length_cm", 0.0)),
            source=data.get("source", "auto"),
            split_reason=data.get("split_reason"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "band_index": self.band_index,
            "x_left_cm": self.x_left_cm,
            "x_right_cm": self.x_right_cm,
            "y_top_cm": self.y_top_cm,
            "y_bottom_cm": self.y_bottom_cm,
            "raw_length_cm": self.raw_length_cm,
            "final_length_cm": self.final_length_cm,
            "source": self.source,
            "split_reason": self.split_reason,
        }

    @property
    def width_cm(self) -> float:
        return self.x_right_cm - self.x_left_cm

    @property
    def area_cm2(self) -> float:
        return self.width_cm * self.final_length_cm


@dataclass(slots=True)
class RoofPlane:
    id: str
    name: str
    outline: Polygon2D | None = None
    holes: list[Polygon2D] = field(default_factory=list)
    selected_material_id: str | None = None
    generation_settings: GenerationSettings = field(default_factory=GenerationSettings)
    auto_sheet_placements: list[SheetPlacement] = field(default_factory=list)
    manual_sheet_placements: list[SheetPlacement] = field(default_factory=list)
    manually_removed_auto_sheet_ids: list[str] = field(default_factory=list)
    layout_revision: int = 0
    layout_dirty_reason: str | None = None

    @property
    def net_area_cm2(self) -> float:
        if self.outline is None:
            return 0.0
        holes_area = sum(hole.area() for hole in self.holes)
        return self.outline.area() - holes_area

    def with_outline(self, outline: Polygon2D) -> "RoofPlane":
        return RoofPlane(
            id=self.id,
            name=self.name,
            outline=outline,
            holes=list(self.holes),
            selected_material_id=self.selected_material_id,
            generation_settings=self.generation_settings,
            auto_sheet_placements=list(self.auto_sheet_placements),
            manual_sheet_placements=list(self.manual_sheet_placements),
            manually_removed_auto_sheet_ids=list(self.manually_removed_auto_sheet_ids),
            layout_revision=self.layout_revision + 1,
            layout_dirty_reason=self.layout_dirty_reason,
        )


def cm2_to_m2(value_cm2: float) -> float:
    return value_cm2 / 10000.0


def almost_equal(left: float, right: float, tolerance: float = 1e-6) -> bool:
    return isclose(left, right, abs_tol=tolerance)
