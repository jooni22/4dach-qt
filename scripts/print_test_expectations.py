#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Expectation:
    test_id: str
    input_summary: str
    expected_summary: str


EXPECTATIONS: list[Expectation] = [
    Expectation(
        "tests/test_geometry.py::test_validate_polygon_detects_self_intersection",
        "polygon=[(0,0),(100,100),(0,100),(100,0)]",
        'lista issues zawiera tekst "Polygon zawiera samoprzeciecia"',
    ),
    Expectation(
        "tests/test_geometry.py::test_validate_hole_polygon_requires_hole_inside_outline",
        "outline=prostokat 300x200, hole=prostokat 60x60 od (260,30)",
        'lista issues zawiera tekst "Wycinek musi lezec..." lub dokladnie "Wycinek musi lezec w calosci wewnatrz obrysu"',
    ),
    Expectation(
        "tests/test_geometry.py::test_polygon_edit_operations_keep_expected_points_order",
        "start=prostokat 100x80; insert idx=0:(100,20); replace idx=1:(100,10); move dx=5 dy=-5; delete idx=1",
        "po insert: 5 punktow; po replace: punkt[1]=(100,10); po move: punkt[0]=(5,-5); po delete: 4 punkty",
    ),
    Expectation(
        "tests/test_geometry.py::test_delete_polygon_point_rejects_triangle_reduction",
        "triangle=[(0,0),(100,0),(0,100)] i delete idx=1",
        "rzucany jest ValueError",
    ),
    Expectation(
        "tests/test_canvas_mapper.py::test_mapper_scales_and_offsets_correctly",
        "bounds=(0,0)-(100,50), rect=400x300, margin=0",
        "map(0,0)->(0,50) i map(100,50)->(400,250) z tolerancja 0.01",
    ),
    Expectation(
        "tests/test_canvas_mapper.py::test_mapper_maps_rect",
        "bounds=(0,0)-(200,100), rect=400x200, map_rect x=0..100 y=0..50",
        "wynikowy rect ma width=200 i height=100 z tolerancja 0.01",
    ),
    Expectation(
        "tests/test_canvas_mapper.py::test_mapper_applies_margin",
        "bounds=(0,0)-(100,100), rect=200x200, margin=20",
        "zmapowany punkt (0,0) ma x>=20 i y>=20",
    ),
    Expectation(
        "tests/test_canvas_mapper.py::test_mapper_can_unmap_canvas_points_back_to_domain",
        "bounds=(10,20)-(110,70), rect=400x300, punkt=(55,35)",
        "map+unmap zwraca okolo (55,35) z tolerancja 0.01",
    ),
    Expectation(
        "tests/test_layout_engine.py::test_layout_engine_generates_deterministic_bands_for_simple_rectangle",
        "plane=prostokat 120x200, material.width=50, min=10, max=500",
        "placements=[(0,0..50,200),(1,50..100,200),(2,100..120,200)], 3 bands po 1 segmencie, warnings=[]",
    ),
    Expectation(
        "tests/test_layout_engine.py::test_layout_engine_splits_band_when_cutout_disconnects_vertical_strip",
        "plane=prostokat 90x100 z hole 30x40 od (30,30), material.width=30",
        "band 1 jest rozciety na 2 segmenty: y=0..30 i 70..100; lacznie placements dla bandow: 0/1/1/2",
    ),
    Expectation(
        "tests/test_layout_engine.py::test_layout_engine_keeps_connected_notched_band_as_one_segment_with_coverage_polygons",
        "plane=153x200 z hole 30x50 od (60,70), material.width=51",
        "sa 3 placements; band 1 ma 1 segment i 4 coverage_polygons; placement[1] obejmuje x=51..102",
    ),
    Expectation(
        "tests/test_layout_engine.py::test_layout_engine_handles_trapezoid_strip_lengths",
        "plane=trapez rownoramienny dol=200 gora=100 wys=120, material.width=50",
        "wszystkie 4 placementy maja final_length_cm=120 i skrajne y_top_cm sa rowne 0",
    ),
    Expectation(
        "tests/test_layout_engine.py::test_layout_engine_handles_irregular_polygon_without_qt_dependencies",
        "nieregularny 7-punktowy polygon z testu, material.width=50",
        "sa 3 placements; liczba coverage_polygons na bandach=[3,2,1]; dlugosc bandu 0 < bandu 1",
    ),
    Expectation(
        "tests/test_layout_engine.py::test_layout_engine_uses_single_cross_section_for_skewed_band_lengths",
        "skewed polygon [(0,20),(120,0),(120,100),(0,120)], material.width=50, max=100, min=0",
        "raw/final lengths=[100,8.3333,100,8.3333,100,3.3333], requires_transverse_split=False",
    ),
    Expectation(
        "tests/test_layout_engine.py::test_layout_engine_tracks_multiple_cutouts_inside_band_coverage",
        "plane=150x150 z 3 hole'ami po jednym w kazdym pasie, material.width=50",
        "sa 3 placements, a coverage_polygons dla kazdego bandu maja liczebnosc [4,4,4]",
    ),
    Expectation(
        "tests/test_layout_engine.py::test_layout_engine_supports_layout_direction_change",
        "plane=120x100, material.width=50; porownanie origin=left vs right",
        "left bands: 0..50/50..100/100..120; right bands: 70..120/20..70/0..20",
    ),
    Expectation(
        "tests/test_layout_engine.py::test_layout_engine_validates_min_and_max_sheet_length_edges",
        "plane=100x150 z hole 50x90 od (0,30), material.width=50 min=80 max=120",
        "pozostaje 1 placement: band 1 dlugosc=120 bez split_reason; rejected_segments ma dlugosc 3",
    ),
    Expectation(
        "tests/test_layout_engine.py::test_layout_engine_cutout_intersection_count",
        "outline=1000x1000, hole=300x300 od (350,350), material.width=51",
        "wiecej niz 1 placement maja tylko bandy [7,8,9,10,11]",
    ),
    Expectation(
        "tests/test_drawing_canvas.py::test_canvas_selects_vertex_handle_on_mouse_press",
        "klik LPM w wierzcholek 0 prostokata 300x200",
        "_active_vertex_index=0 i _dragging_vertex_index=0",
    ),
    Expectation(
        "tests/test_drawing_canvas.py::test_canvas_dragging_vertex_updates_preview_geometry_live",
        "drag wierzcholka 1 z prostokata 300x200 do punktu domeny (260,30)",
        "preview.points[1] jest blisko (260,30) z tolerancja 1.5 px domeny",
    ),
    Expectation(
        "tests/test_drawing_canvas.py::test_canvas_dragging_vertex_emits_updated_outline_on_release",
        "drag wierzcholka 2 do (240,180) i puszczenie myszy",
        "sygnal outline_edit_committed niesie outline z punktem[2] okolo (240,180); dragging resetuje sie do None",
    ),
    Expectation(
        "tests/test_drawing_canvas.py::test_canvas_recomputes_edge_lengths_for_preview_geometry",
        "drag wierzcholka 1 do (260,50)",
        "edge_lengths_cm() odpowiada dlugosciom segmentow preview z tolerancja 0.01",
    ),
    Expectation(
        "tests/test_drawing_canvas.py::test_canvas_rejects_invalid_geometry_and_restores_original_outline",
        "drag wierzcholka 2 do niepoprawnego punktu (0,0)",
        'outline_edit_rejected zawiera tekst z "Polygon"; wyswietlany outline wraca do oryginalu',
    ),
    Expectation(
        "tests/test_drawing_canvas.py::test_canvas_selects_cutout_polygon_before_main_plane",
        "klik w punkt (120,90) lezacy w hole 80x60 od (100,70)",
        "selected_cutout_index()=0 i selected_geometry_kind()='cutout_polygon'",
    ),
    Expectation(
        "tests/test_drawing_canvas.py::test_canvas_dragging_cutout_vertex_emits_updated_hole",
        "drag hole.points[1] do (210,70)",
        "hole_edit_committed emituje indeks 0 i hole z punktem[1] okolo (210,70); selected kind='cutout_vertex'",
    ),
    Expectation(
        "tests/test_drawing_canvas.py::test_canvas_rejects_cutout_vertex_drag_outside_plane",
        "drag hole.points[0] do (-10,70)",
        "outline_edit_rejected zawiera komunikat o wycinku poza obrysem; display_holes()[0] zostaje bez zmian",
    ),
    Expectation(
        "tests/test_drawing_canvas.py::test_canvas_builds_sheet_render_items_for_simple_rectangle",
        "outline=120x100 po layout dla material.width=50",
        "render items: [(0,100,1),(1,100,1),(2,100,1)] oraz label pierwszego='100'",
    ),
    Expectation(
        "tests/test_drawing_canvas.py::test_canvas_render_items_preserve_cutout_exclusions",
        "outline=90x100 z hole 30x40 od (30,30), material.width=30",
        "items=[(0,100),(1,30),(1,30),(2,100)] i kolor w otworze rozni sie od koloru obszaru pokrytego",
    ),
    Expectation(
        "tests/test_drawing_canvas.py::test_canvas_render_items_follow_layout_direction_change",
        "outline=120x100; porownanie origin=left i right",
        "dla left pierwszy polygon startuje od x=0, dla right od x=70",
    ),
    Expectation(
        "tests/test_drawing_canvas.py::test_canvas_updates_render_items_after_geometry_edit_and_relayout",
        "outline 120x100 zmieniony potem na 180x100 i przeliczony ponownie",
        "przed zmiana sa 3 items; po wyczyszczeniu layoutu brak items; po relayout 4 items i ostatni max_x=180",
    ),
    Expectation(
        "tests/test_reporting.py::test_build_report_aggregates_bom_by_sheet_length_and_cost",
        "plane=120x200 z hole 40x50 od (40,70), material.width=40, cena=12.5/m2",
        "net=2.2 m2, gross=2.2 m2, waste=0, koszt=27.5; BOM=[(70,1),(80,1),(200,2)]",
    ),
    Expectation(
        "tests/test_reporting.py::test_build_report_includes_layout_warnings_and_rejected_segments",
        "plane=100x150 z hole 50x90 od (0,30), material.width=50 min=80 max=120, cena=99/arkusz",
        "1 placement, total_cost=99, BOM=[(120,1)], 1 warning z tekstem zaczynajacym sie od 'Pominieto 3'",
    ),
    Expectation(
        "tests/test_reporting.py::test_build_report_html_contains_summary_bom_and_warnings",
        "firma='Firma Test', adres wielolinijkowy, material='Blacha testowa'",
        "HTML zawiera: 'Raport 4Dach - 1', 'Firma Test', 'Blacha testowa', 'Dlugosc arkusza [cm]' i nie zawiera 'podzialu poprzecznego'",
    ),
    Expectation(
        "tests/test_reporting.py::test_build_report_html_contains_svg_with_sheet_rects",
        "state z config_dict i prostokatem 300x200",
        "HTML zawiera <svg>, </svg>, co najmniej tyle <rect co placements oraz naglowek 'Ostrzezenia'",
    ),
    Expectation(
        "tests/test_reporting.py::test_build_report_html_uses_supplied_report_when_project_state_has_no_saved_placements",
        "state z materialem MAT1 i prostokatem 100x150 bez zapisanych placements",
        "HTML zawiera efektywna/gross 1.500 oraz wiersz BOM '<td>Material 1</td><td>MAT1</td><td>150.00</td><td>2</td><td>1.500</td>'",
    ),
    Expectation(
        "tests/test_reporting.py::test_build_project_report_aggregates_multiple_roof_planes_and_groups_lengths",
        "2 polacie: Front 100x100 i Back 50x100, ten sam material 10/m2",
        "sekcje=['Front','Back']; globalny BOM=[('MAT',100,3)]; total area=1.5 m2; total cost=15",
    ),
    Expectation(
        "tests/test_reporting.py::test_build_project_report_html_contains_all_plane_sections_and_global_summary",
        "firma='Firma Test', polacie 'Polac A' i 'Polac B'",
        "HTML zawiera raport projektu, obie polacie, zbiorcze zestawienie, 2 svg i laczna powierzchnie/koszt",
    ),
    Expectation(
        "tests/test_reporting.py::test_build_project_report_html_escapes_user_entered_text",
        "dane z HTML/JS w nazwie firmy, materialu i polaci",
        "surowe <script> i <img nie wystepuja; teksty sa escapowane jako encje HTML",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_company_data_round_trip",
        "company_data name='Super Dach', website='example.test'",
        "to_dict zachowuje name='Super Dach' i website='example.test'",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_loads_materials_from_config",
        "ProjectState.from_config(config.json)",
        "company='Super Dach Bis Jerzy Zimnoch', available_material_ids=['PD510'], material_by_id('PD510') istnieje",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_material_definition_supports_min_sheet_length_dual_keys",
        "Material.from_dict(... min_sheet_length_cm=42 ...)",
        "material.min_sheet_length_cm=42 oraz to_dict zwraca oba klucze: min_sheet_length_cm=42 i min_dlugosc_arkusza=42",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_layout_engine_splits_band_by_hole_and_flags_long_sheet",
        "plane=100x100 z hole 50x50 od (25,25), material.width=30, max=40",
        "layout ma 11 placements i kazdy placement.raw_length_cm <= 40",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_config_fragment_serializes_roof_planes",
        "state z jedna polacia id='plane-1', material='PD510'",
        "fragment.project_state.roof_planes[0] ma id='plane-1', selected_material_id='PD510', outline o 4 punktach",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_add_roof_plane_round_trip",
        "add_roof_plane(prostokat 300x200) przy materiale PD510 i zapis/odczyt configu",
        "powstaje plane-1; active_plane_id='plane-1'; po reload selected_material_id='PD510'; area=60000; baseline=200",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_can_switch_active_plane_explicitly",
        "2 polacie: 300x200 i 240x160; set_active_plane(first)",
        "zmiana zwraca True, aktywna jest pierwsza; ustawienie 'missing-plane' zwraca False i nic nie zmienia",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_can_add_multiple_empty_roof_planes_and_persist_them",
        "3x add_empty_roof_plane() przy materiale PD510",
        "ids=['plane-1','plane-2','plane-3'], nazwy=['1','2','3'], aktywna='plane-3', wszystkie outline=None po reload",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_delete_roof_plane_keeps_other_planes_intact",
        "3 polacie; usuniecie srodkowej",
        "zostaja tylko pierwsza i trzecia; druga nie istnieje; aktywna staje sie trzecia",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_round_trip_preserves_multiple_roof_planes",
        "pierwsza polac prostokat 300x200, druga pusta 'Taras', rename pierwszej na 'Front'",
        "po reload nazwy=['Front','Taras']; outline tylko na pierwszej; aktywna druga",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_hole_workflow_updates_layout_revision_and_serialization",
        "hole 50x60 od (100,40), potem move_hole dx=10 dy=15",
        "layout_revision=2; hole[0].point[0]=(110,55); te same dane sa w serializacji",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_supports_multiple_holes_and_round_trip",
        "2 hole: 50x60 od (40,50) i 70x40 od (220,120)",
        "plane i reload maja po 2 hole; punkty obu hole sa zachowane 1:1",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_rejects_hole_outside_outline",
        "outline 300x200, hole 80x80 od (260,20)",
        "rzucany jest ValueError z komunikatem o wycinku poza obrysem",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_rejects_overlapping_holes",
        "najpierw hole 80x80 od (40,30), potem hole 60x60 od (90,70)",
        "drugi add_hole_to_plane rzuca ValueError z komunikatem o nachodzeniu wycinkow",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_roof_plane_edit_operations_update_geometry_revision",
        "move plane (10,5), insert point(160,40), move point idx=1 o (0,10), delete point idx=1",
        "layout_revision=4; outline[0]=(10,5); outline[1]=(310,5); liczba punktow=4; baseline=205",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_rejects_outline_edit_when_it_breaks_hole_containment",
        "outline 300x200 z hole 60x60 od (30,40); move point 0 o (80,0)",
        "rzucany jest ValueError z komunikatem o wycinku poza obrysem",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_delete_hole_marks_geometry_changed",
        "outline 300x200 z hole 50x50 od (80,60); delete_hole idx=0",
        "layout_revision=2; holes=[]; baseline=200",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_can_edit_cutout_vertex_and_persist_result",
        "hole 50x50 od (80,60); move_hole_point hole=0 point=1 dx=20 dy=10",
        "hole.points[1]=(150,70) i po reload jest identycznie",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_generates_layout_for_active_plane_and_persists_auto_placements",
        "plane=153x200 z hole 30x50 od (60,70), material PD510",
        "3 placements, 3 bands, band1 ma 1 segment i 4 coverage_polygons; layout_revision=2; serializacja zawiera auto placements",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_manual_sheet_overrides_are_merged_and_serialized",
        "po auto-layout usuniety 1 auto arkusz i dodany manual id='plane-1-manual-1'",
        "aktywny zestaw nie zawiera usunietego auto id, zawiera manual; layout_dirty_reason='manual_override'; serializacja zachowuje oba wpisy",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_geometry_change_keeps_manual_sheets_but_marks_layout_dirty",
        "manual placement 120 cm na plane-1, potem move_roof_plane(10,5)",
        "manual_sheet_placements zostaja, a layout_dirty_reason='geometry_changed'",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_material_change_marks_layout_dirty_without_dropping_manual_sheets",
        "plane z materialem PD510 i jednym manual sheet; zmiana materialu na T20",
        "selected_material_id='T20'; manual sheets zostaja; layout_dirty_reason='material_changed'",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_can_create_and_edit_material_definitions",
        "upsert MAT1 a potem upsert z nowymi parametrami",
        "w rejestrze jest tylko MAT1; nazwa='Material 1 Plus'; effective_width=53; price=55",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_material_edit_marks_only_dependent_planes_dirty",
        "3 polacie: dwie na MAT1 i jedna na MAT2; edycja MAT1 po wygenerowaniu layoutow",
        "tylko polacie MAT1 dostaja layout_dirty_reason='material_changed' i czyszczone auto placements; MAT2 zostaje nietkniety",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_round_trip_preserves_material_registry_and_assignments",
        "plane na MAT1, generate_layout, potem update MAT1 i save/load",
        "po reload material ma nazwe 'Material 1 Updated', width=54, price=49.5; plane nadal ma selected_material_id='MAT1' i dirty_reason='material_changed'",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_layout_engine_uses_shared_baseline_for_module_lengths",
        "plane=120x200 z hole 40x50 od (40,70), material.width=40 modul=25, baseline=200",
        "dla srodkowego bandu final_length_cm=[70,80]",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_shape_builders_create_valid_polygons",
        "build_rectangle 300x200, build_triangle rownoramienny 300x180, build_trapezoid prostokatny 500/300/200",
        "rectangle ma 4 punkty, triangle 3, trapezoid 4; wszystkie maja area()>0",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_shape_factories_create_expected_polygons",
        "make_rectangle(320,180), make_triangle('dowolny',300,180,250), make_trapezoid('rownoramienny',500,300,200)",
        "rectangle ma punkty [(0,0),(320,0),(320,180),(0,180)]; triangle ma baze od (0,180) do (300,180) i apex x w (0,300); trapezoid ma punkty [(0,200),(100,0),(400,0),(500,200)]",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_shape_factories_validate_invalid_dimensions[rectangle-zero-width]",
        "make_rectangle(0,200)",
        'rzucany jest ValueError z tekstem "Szerokosc musi byc dodatnia"',
    ),
    Expectation(
        "tests/test_models_and_state.py::test_shape_factories_validate_invalid_dimensions[triangle-arm-too-short]",
        "make_triangle('dowolny',300,180,170)",
        'rzucany jest ValueError z tekstem "Ramie musi byc wieksze od wysokosci"',
    ),
    Expectation(
        "tests/test_models_and_state.py::test_shape_factories_validate_invalid_dimensions[trapezoid-zero-top-base]",
        "make_trapezoid('prostokatny',500,0,200)",
        'rzucany jest ValueError z tekstem "Podstawa gorna musi byc dodatnia"',
    ),
    Expectation(
        "tests/test_models_and_state.py::test_polygon_area_is_counted_in_cm2",
        "Polygon2D.rectangle(300,200)",
        "area() = 60000 cm2",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_load_config_and_save_config_round_trip",
        "tymczasowy JSON config z szerokoscia prostokata=400, potem zmiana na 500",
        "pierwszy odczyt zwraca dane 1:1; po zapisie reloaded['ksztalty']['prostokat']['szerokosc']=500",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_project_state_config_round_trip",
        "config z CompanyData+Material MAT1, potem add_roof_plane 300x200 i generate_layout",
        "po save/load jest 1 material, 1 plane z tym samym id, selected_material_id='MAT1' i layout_dirty_reason=None",
    ),
    Expectation(
        "tests/test_models_and_state.py::test_basic_user_workflow_smoke",
        "from_config z MAT1, add_roof_plane 300x200, generate_layout, dodanie manual placement",
        "po generate_layout auto placements istnieja i dirty_reason=None; po manual override dirty_reason='manual_override'; config zawiera project_state z ta flaga",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_exposes_expected_ui_contract",
        "start MainWindow()",
        "menu=['Plik','Ksztalt','Wycinki','Katalog','Arkusze']; tabs>=2; variant='PD510'; material ids=['PD510']; w menu Arkusze jest 'Przelicz aktywna polac'",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_refreshes_active_plane_on_primary_canvas",
        "dodanie polaci 320x180 i _refresh_canvas_from_state()",
        "primary_canvas.roof_plane.id == dodane plane.id; tytul aktywnej zakladki = plane.name",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_creates_plane_tabs_and_switches_active_plane",
        "2 polacie 320x180 i 210x140, potem zmiana aktywnej zakladki na 0",
        "sa 3 tabs: first, second, Raport; poczatkowo aktywna druga; po switch aktywna pierwsza i canvas pokazuje pierwsza",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_adds_renames_and_deletes_roof_plane_tabs",
        "_add_new_roof_plane(), rename przez dialog na 'Garaz', delete z potwierdzeniem Yes",
        "liczba polaci rosnie o 1, nowa polac ma outline=None i tab '*'; po rename tab='Garaz *'; po delete liczba wraca do bazowej",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_creates_rectangle_geometry_in_active_tab",
        "fake dialog prostokata: szerokosc=420, wysokosc=260",
        "powstaje 1 polac z outline build_rectangle_outline(420,260); canvas pokazuje te polac; tab ma suffix '*'",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_keeps_generated_shapes_separate_per_tab_and_persists_geometry",
        "pierwszy dialog: prostokat 300x200, drugi dialog: trapez prostokatny 500/300/240",
        "kazda zakladka zachowuje osobna geometrie; po save/load sa 2 polacie z tymi samymi outline",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_generates_project_report_for_all_roof_planes",
        "2 polacie 'Front' i 'Back', potem _gen_report('standard')",
        "_latest_report_html zawiera raport projektu i obie nazwy; _latest_report_plane_id=None; aktywna zakladka=Raport",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_commits_canvas_outline_edits_to_project_state",
        "canvas.outline_edit_committed emituje nowy 4-punktowy outline",
        "plane.outline zostaje zaktualizowany; layout_dirty_reason=None; layout_bands nie sa puste",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_rolls_back_invalid_canvas_outline_edit",
        "outline z hole; commit niepoprawnego outline wpychajacego hole poza obrys",
        "plane.outline wraca do oryginalu; pokazuje sie warning z tekstem o wycinku poza obrysem",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_commits_canvas_cutout_edits_to_project_state",
        "canvas.hole_edit_committed emituje hole=prostokat 80x50 od (40,30)",
        "plane.holes[0] zostaje podmieniony; layout_dirty_reason=None; layout_bands nie sa puste",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_material_catalog_edit_updates_project_state_and_dependent_workspace",
        "edycja katalogu: PD510 -> 'PD510 Plus', width=53, modul=30",
        "project_state.material_by_id('PD510').nazwa='PD510 Plus'; zalezne polacie sa przeliczone; aktywny canvas ma material PD510 z module_length_cm=30",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_connects_initial_canvas_edit_signals_on_startup",
        "start okna z configiem zawierajacym plane-1, potem emit outline_edit_committed",
        "outline plane-1 w project_state aktualizuje sie od razu na starcie",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_freehand_outline_uses_canvas_mapper_instead_of_raw_pixels",
        "zamkniecie podobnego prostokata freehand na canvas 640x420 i 960x630",
        "wynikowe outline.points sa identyczne dla obu rozmiarow widgetu",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_open_project_resets_cached_report_and_company_title",
        "okno ma stary cached report, a load_config zwraca potem 'Firma B'",
        "po _open_project(): _latest_report_html='', _latest_report_plane_id=None, windowTitle()='4Dach - Firma B' lub rownowazny tytul z Firma B",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_marks_project_dirty_until_explicit_save",
        "commit outline do plane i potem _save_project()",
        "przed zapisem _has_unsaved_changes=True i brak write; po save _has_unsaved_changes=False i zapis zostal wykonany",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_unsaved_close_confirmation_can_cancel_or_discard",
        "sa niezapisane zmiany; QMessageBox zwraca kolejno Cancel potem Discard",
        "pierwsze potwierdzenie zwraca False, drugie True",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_undo_redo_restores_outline_and_material",
        "zmiana outline, potem zmiana materialu na T20, potem undo/redo x2",
        "undo1 cofa material do PD510; undo2 cofa outline; redo1 przywraca outline; redo2 przywraca material T20",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_report_generation_recalculates_only_dirty_planes",
        "2 polacie, tylko pierwsza ma layout_dirty_reason='geometry_changed'",
        "_gen_report('standard') przelicza tylko first_plane.id",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_blachy_dialog_exposes_save_button",
        "start BlachyDialog([])",
        "QDialogButtonBox istnieje i ma standardowy przycisk Save",
    ),
    Expectation(
        "tests/test_mainwindow_ui_contract.py::test_mainwindow_triangle_dialog_shows_validation_error_without_mutating_state",
        "fake dialog trojkata: typ='dowolny', podstawa=300, wysokosc=180, ramie=100",
        "nie powstaje zadna polac; pokazuje sie komunikat walidacyjny",
    ),
]


def main() -> int:
    for index, entry in enumerate(EXPECTATIONS, start=1):
        print(
            f"{index}. {entry.test_id}; dane wejsciowe: {entry.input_summary}; "
            f"prawidlowa odpowiedz lub zakres: {entry.expected_summary}"
        )
    print(f"\nLacznie opisanych oczekiwan: {len(EXPECTATIONS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
