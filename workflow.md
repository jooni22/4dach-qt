• Użyję test-driven-development i pyside6-reviewer, bo zmiana dotyka zachowania aplikacji Qt i wymaga testów kontraktowych. Najpierw odświeżam lokalny kontekst repo i istniejące testy, żeby nie zgadywać API.

• Explored
  └ Read SKILL.md (test-driven-development skill), SKILL.md (pyside6-reviewer skill)
    Search interfejs-zapisu|UserPreferences|ProjectManagerDialog|_load_project_payload|_new_project|_open_project|_save_project|app_settings|show_grid|snap_to_grid|_base_window_title|_refresh_window_title|
           QFileDialog in MEMORY.md
    Read MEMORY.md

• Ran pwd && rg --files -g 'AGENTS.md' -g 'docs/interfejs-zapisu-v2.md' -g 'mainwindow.py' -g 'ui/**/*.py' -g 'tests/*.py' | sort
  └ /data/APP/83_4dach_zimnoch/qt/4dach
    AGENTS.md
    … +31 lines (ctrl + t to view transcript)
    ui/toolbar.py
    ui/workspace.py

• Ran git status --short
  └  D _TODO/13_CANVAS_ROLLOUT_2_3_HANDOFF_2026-05-05.md
     D _TODO/_FEATURES/cleanup_plan.md
    … +9 lines (ctrl + t to view transcript)
    ?? docs/_TODO/
    ?? docs/interfejs-zapisu-v2.md

───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

• Widzę brudny worktree z wcześniejszymi zmianami i nie będę ich cofał. Teraz czytam MainWindow, persistence/state oraz aktualny brief, żeby wprowadzić V2 zgodnie z istniejącym przepływem
  _load_project_payload().

• Explored
  └ Read AGENTS.md, mainwindow.py, main_window.py, persistence.py, app_settings.py, project_state.py, test_app_settings.py, test_mainwindow_ui_contract.py, settings_dialog.py, toolbar.py, interfejs-zapisu-v2.md,
         conftest.py, config.json
    Search def apply_to_config|def to_dict|project_state in project_state.py
    Search MainWindow\( in tests
    Search QFileDialog|getOpenFileName|getSaveFileName|_save_project|_open_project|_new_project|app_settings|company_data|ksztalty|add_polac_dialog|wycinki in test_mainwindow_ui_contract.py
    Read project_state.py, main_window_dialogs.py
    Search add_polac_dialog|ksztalty|accept|reject|get_result|_config in add_polac_dialog.py
    Read add_polac_dialog.py, company_dialog.py

───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

• Zakres jest większy niż samo podpięcie dialogu: obecny ProjectState.apply_to_config() zapisuje też app_settings, więc w MainWindow trzeba zrobić osobny filtr projektu i wstrzykiwanie preferencji przed każdym
  ProjectState.from_config(). Zaczynam od testów dla nowych granic: preferencje, skan projektów i podstawowy kontrakt zapisu/otwierania bez systemowego open/save.

• Explored
  └ Read test_mainwindow_ui_contract.py

• Added tests/test_user_preferences.py (+81 -0)
     1 +from __future__ import annotations
     2 +
     3 +import json
     4 +
     5 +from core.app_settings import AppSettings
     6 +from user_preferences import USER_LEVEL_KEYS, UserPreferences
     7 +
     8 +
     9 +def test_user_preferences_uses_explicit_path_and_ignores_missing_file(tmp_path):
    10 +    prefs_path = tmp_path / "prefs" / "user_preferences.json"
    11 +
    12 +    prefs = UserPreferences(path=prefs_path)
    13 +
    14 +    assert prefs.path == prefs_path
    15 +    assert prefs.to_dict() == {}
    16 +
    17 +
    18 +def test_user_preferences_saves_atomically_to_explicit_path(tmp_path):
    19 +    prefs_path = tmp_path / "prefs" / "user_preferences.json"
    20 +    prefs = UserPreferences(path=prefs_path)
    21 +
    22 +    assert prefs.update({"company_data": {"name": "Firma"}, "projects_dir": str(tmp_path)})
    23 +    assert prefs.save() is True
    24 +
    25 +    assert json.loads(prefs_path.read_text(encoding="utf-8")) == {
    26 +        "company_data": {"name": "Firma"},
    27 +        "projects_dir": str(tmp_path),
    28 +    }
    29 +    assert list(prefs_path.parent.glob("*.tmp")) == []
    30 +
    31 +
    32 +def test_user_preferences_ignores_corrupted_file(tmp_path):
    33 +    prefs_path = tmp_path / "user_preferences.json"
    34 +    prefs_path.write_text("{broken", encoding="utf-8")
    35 +
    36 +    prefs = UserPreferences(path=prefs_path)
    37 +
    38 +    assert prefs.to_dict() == {}
    39 +
    40 +
    41 +def test_user_preferences_migrates_only_user_level_keys(tmp_path):
    42 +    prefs = UserPreferences(path=tmp_path / "user_preferences.json")
    43 +    legacy_payload = {
    44 +        "company_data": {"name": "Firma"},
    45 +        "ksztalty": {"prostokat": {"szerokosc": 320}},
    46 +        "add_polac_dialog": {"last_shape": "prostokat"},
    47 +        "wycinki": {"prostokat": {"szerokosc": 80}},
    48 +        "app_settings": AppSettings(show_grid=False).to_dict(),
    49 +        "projects_dir": str(tmp_path),
    50 +        "materials": {"order": []},
    51 +        "project_state": {"roof_planes": []},
    52 +        "blachy": [],
    53 +    }
    54 +
    55 +    assert prefs.migrate_from_config(legacy_payload) is True
    56 +
    57 +    migrated = prefs.to_dict()
    58 +    assert set(migrated) == USER_LEVEL_KEYS
    59 +    assert migrated["company_data"] == {"name": "Firma"}
    60 +    assert "materials" not in migrated
    61 +    assert "project_state" not in migrated
    62 +    assert "blachy" not in migrated
    63 +
    64 +
    65 +def test_user_preferences_injects_into_project_payload_without_projects_dir(tmp_path):
    66 +    prefs = UserPreferences(path=tmp_path / "user_preferences.json")
    67 +    prefs.update(
    68 +        {
    69 +            "company_data": {"name": "Firma"},
    70 +            "app_settings": {"show_grid": False},
    71 +            "projects_dir": str(tmp_path),
    72 +        }
    73 +    )
    74 +    payload = {"project_state": {"roof_planes": []}}
    75 +
    76 +    injected = prefs.inject_into_config(payload)
    77 +
    78 +    assert injected is payload
    79 +    assert payload["company_data"] == {"name": "Firma"}
    80 +    assert payload["app_settings"] == {"show_grid": False}
    81 +    assert "projects_dir" not in payload

• Added tests/test_project_manager_dialog.py (+53 -0)
     1 +from __future__ import annotations
     2 +
     3 +import json
     4 +from datetime import UTC, datetime, timedelta
     5 +
     6 +pytest_plugins = ("pytestqt",)
     7 +
     8 +from ui.dialogs.project_manager_dialog import Mode, ProjectManagerDialog, scan_projects_dir
     9 +
    10 +
    11 +def _write_project(path, *, name: str, modified_at: datetime) -> None:
    12 +    path.write_text(
    13 +        json.dumps(
    14 +            {
    15 +                "project_meta": {
    16 +                    "name": name,
    17 +                    "modified_at": modified_at.isoformat(),
    18 +                },
    19 +                "project_state": {"roof_planes": []},
    20 +                "materials": {"order": [], "items": {}},
    21 +                "blachy": [],
    22 +            }
    23 +        ),
    24 +        encoding="utf-8",
    25 +    )
    26 +
    27 +
    28 +def test_scan_projects_dir_returns_empty_for_missing_dir(tmp_path):
    29 +    assert scan_projects_dir(tmp_path / "missing") == []
    30 +
    31 +
    32 +def test_scan_projects_dir_skips_corrupted_json_and_sorts_by_modified_at(tmp_path):
    33 +    older = datetime.now(UTC) - timedelta(days=2)
    34 +    newer = datetime.now(UTC)
    35 +    _write_project(tmp_path / "older.4dach", name="Starszy", modified_at=older)
    36 +    _write_project(tmp_path / "newer.4dach", name="Nowszy", modified_at=newer)
    37 +    (tmp_path / "broken.4dach").write_text("{broken", encoding="utf-8")
    38 +
    39 +    projects = scan_projects_dir(tmp_path)
    40 +
    41 +    assert [project.name for project in projects] == ["Nowszy", "Starszy"]
    42 +    assert [project.path.name for project in projects] == ["newer.4dach", "older.4dach"]
    43 +
    44 +
    45 +def test_project_manager_save_mode_builds_4dach_path(qtbot, tmp_path):
    46 +    dialog = ProjectManagerDialog(mode=Mode.SAVE_AS, projects_dir=tmp_path, default_name="Nowy")
    47 +    qtbot.addWidget(dialog)
    48 +
    49 +    dialog._name_edit.setText("Projekt Test")
    50 +    dialog.accept()
    51 +
    52 +    assert dialog.selected_path() == tmp_path / "Projekt Test.4dach"
    53 +    assert dialog.project_name() == "Projekt Test"

• Ran uv run pytest tests/test_user_preferences.py -q
  └
    ==================================== ERRORS ====================================
    … +12 lines (ctrl + t to view transcript)
    !!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
    1 error in 0.21s

• Ran uv run pytest tests/test_project_manager_dialog.py -q
  └
    ==================================== ERRORS ====================================
    … +12 lines (ctrl + t to view transcript)
    !!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
    1 error in 0.31s

───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

• Nowe testy padają na brakujących modułach, czyli sprawdzają właściwą lukę. Dodaję teraz user_preferences.py i dialog managera z minimalnym API, które będzie można podpiąć w MainWindow.

• Added user_preferences.py (+108 -0)
      1 +"""User-level preferences kept outside project files."""
      2 +from __future__ import annotations
      3 +
      4 +import copy
      5 +import json
      6 +import os
      7 +import tempfile
      8 +from pathlib import Path
      9 +
     10 +
     11 +USER_LEVEL_KEYS = {
     12 +    "company_data",
     13 +    "ksztalty",
     14 +    "add_polac_dialog",
     15 +    "wycinki",
     16 +    "app_settings",
     17 +    "projects_dir",
     18 +}
     19 +CONFIG_INJECTION_KEYS = USER_LEVEL_KEYS - {"projects_dir"}
     20 +
     21 +
     22 +def default_user_preferences_path() -> Path:
     23 +    if os.name == "nt":
     24 +        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
     25 +    else:
     26 +        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
     27 +    return base / "4dach" / "user_preferences.json"
     28 +
     29 +
     30 +class UserPreferences:
     31 +    def __init__(self, path: Path | str | None = None) -> None:
     32 +        self.path = Path(path) if path is not None else default_user_preferences_path()
     33 +        self._data: dict = self._load()
     34 +
     35 +    def _load(self) -> dict:
     36 +        try:
     37 +            with self.path.open(encoding="utf-8") as fh:
     38 +                payload = json.load(fh)
     39 +        except (FileNotFoundError, OSError, json.JSONDecodeError):
     40 +            return {}
     41 +        if not isinstance(payload, dict):
     42 +            return {}
     43 +        return {
     44 +            key: copy.deepcopy(value)
     45 +            for key, value in payload.items()
     46 +            if key in USER_LEVEL_KEYS
     47 +        }
     48 +
     49 +    def to_dict(self) -> dict:
     50 +        return copy.deepcopy(self._data)
     51 +
     52 +    def get(self, key: str, default=None):
     53 +        return copy.deepcopy(self._data.get(key, default))
     54 +
     55 +    @property
     56 +    def projects_dir(self) -> Path:
     57 +        configured = self._data.get("projects_dir")
     58 +        if configured:
     59 +            return Path(configured)
     60 +        return Path.home() / "Documents" / "4Dach"
     61 +
     62 +    def update(self, values: dict) -> bool:
     63 +        changed = False
     64 +        for key, value in values.items():
     65 +            if key not in USER_LEVEL_KEYS:
     66 +                continue
     67 +            next_value = copy.deepcopy(value)
     68 +            if self._data.get(key) != next_value:
     69 +                self._data[key] = next_value
     70 +                changed = True
     71 +        return changed
     72 +
     73 +    def set(self, key: str, value) -> bool:
     74 +        return self.update({key: value})
     75 +
     76 +    def migrate_from_config(self, config_data: dict | None) -> bool:
     77 +        if not isinstance(config_data, dict):
     78 +            return False
     79 +        return self.update(
     80 +            {
     81 +                key: copy.deepcopy(config_data[key])
     82 +                for key in USER_LEVEL_KEYS
     83 +                if key in config_data
     84 +            }
     85 +        )
     86 +
     87 +    def inject_into_config(self, config_data: dict) -> dict:
     88 +        for key in CONFIG_INJECTION_KEYS:
     89 +            if key in self._data:
     90 +                config_data[key] = copy.deepcopy(self._data[key])
     91 +        return config_data
     92 +
     93 +    def save(self) -> bool:
     94 +        try:
     95 +            self.path.parent.mkdir(parents=True, exist_ok=True)
     96 +            with tempfile.NamedTemporaryFile(
     97 +                mode="w",
     98 +                encoding="utf-8",
     99 +                dir=self.path.parent,
    100 +                delete=False,
    101 +                suffix=".tmp",
    102 +            ) as fh:
    103 +                json.dump(self._data, fh, ensure_ascii=False, separators=(",", ":"))
    104 +                temp_path = Path(fh.name)
    105 +            temp_path.replace(self.path)
    106 +            return True
    107 +        except OSError:
    108 +            return False

• Added ui/dialogs/project_manager_dialog.py (+196 -0)
      1 +"""Project manager dialog for opening and reserving project files."""
      2 +from __future__ import annotations
      3 +
      4 +import json
      5 +from dataclasses import dataclass
      6 +from datetime import datetime
      7 +from enum import Enum
      8 +from pathlib import Path
      9 +
     10 +from PySide6.QtCore import Qt
     11 +from PySide6.QtWidgets import (
     12 +    QDialog,
     13 +    QDialogButtonBox,
     14 +    QFileDialog,
     15 +    QHBoxLayout,
     16 +    QLabel,
     17 +    QLineEdit,
     18 +    QListWidget,
     19 +    QListWidgetItem,
     20 +    QPushButton,
     21 +    QVBoxLayout,
     22 +)
     23 +
     24 +
     25 +class Mode(Enum):
     26 +    STARTUP = "startup"
     27 +    OPEN = "open"
     28 +    SAVE_AS = "save_as"
     29 +    NEW = "new"
     30 +
     31 +
     32 +@dataclass(frozen=True, slots=True)
     33 +class ProjectMeta:
     34 +    path: Path
     35 +    name: str
     36 +    modified_at: datetime
     37 +
     38 +
     39 +def _parse_modified_at(raw: object, fallback: float) -> datetime:
     40 +    if isinstance(raw, str):
     41 +        try:
     42 +            parsed = datetime.fromisoformat(raw)
     43 +            if parsed.tzinfo is None:
     44 +                return parsed.astimezone()
     45 +            return parsed
     46 +        except ValueError:
     47 +            pass
     48 +    return datetime.fromtimestamp(fallback).astimezone()
     49 +
     50 +
     51 +def scan_projects_dir(projects_dir: Path | str) -> list[ProjectMeta]:
     52 +    root = Path(projects_dir)
     53 +    if not root.is_dir():
     54 +        return []
     55 +
     56 +    projects: list[ProjectMeta] = []
     57 +    for path in root.glob("*.4dach"):
     58 +        try:
     59 +            payload = json.loads(path.read_text(encoding="utf-8"))
     60 +        except (OSError, json.JSONDecodeError):
     61 +            continue
     62 +        if not isinstance(payload, dict):
     63 +            continue
     64 +        meta = payload.get("project_meta")
     65 +        meta = meta if isinstance(meta, dict) else {}
     66 +        stat = path.stat()
     67 +        projects.append(
     68 +            ProjectMeta(
     69 +                path=path,
     70 +                name=str(meta.get("name") or path.stem),
     71 +                modified_at=_parse_modified_at(meta.get("modified_at"), stat.st_mtime),
     72 +            )
     73 +        )
     74 +    return sorted(projects, key=lambda project: project.modified_at, reverse=True)
     75 +
     76 +
     77 +class ProjectManagerDialog(QDialog):
     78 +    def __init__(
     79 +        self,
     80 +        *,
     81 +        mode: Mode,
     82 +        projects_dir: Path | str,
     83 +        default_name: str = "Nowy projekt",
     84 +        parent=None,
     85 +    ) -> None:
     86 +        super().__init__(parent)
     87 +        self.mode = mode
     88 +        self._projects_dir = Path(projects_dir)
     89 +        self._selected_path: Path | None = None
     90 +        self._startup_action: str | None = None
     91 +        self.setWindowTitle(self._title_for_mode(mode))
     92 +        self.setMinimumWidth(560)
     93 +        self._build_ui(default_name)
     94 +        self._reload_projects()
     95 +
     96 +    def _title_for_mode(self, mode: Mode) -> str:
     97 +        return {
     98 +            Mode.STARTUP: "Projekty 4Dach",
     99 +            Mode.OPEN: "Otwórz projekt",
    100 +            Mode.SAVE_AS: "Zapisz projekt jako",
    101 +            Mode.NEW: "Nowy projekt",
    102 +        }[mode]
    103 +
    104 +    def _build_ui(self, default_name: str) -> None:
    105 +        root = QVBoxLayout(self)
    106 +
    107 +        dir_row = QHBoxLayout()
    108 +        self._dir_label = QLabel(str(self._projects_dir))
    109 +        self._change_dir_button = QPushButton("Zmień...")
    110 +        self._change_dir_button.clicked.connect(self._change_projects_dir)
    111 +        dir_row.addWidget(QLabel("Katalog projektów:"))
    112 +        dir_row.addWidget(self._dir_label, 1)
    113 +        dir_row.addWidget(self._change_dir_button)
    114 +        root.addLayout(dir_row)
    115 +
    116 +        self._project_list = QListWidget(self)
    117 +        self._project_list.itemDoubleClicked.connect(lambda _item: self.accept())
    118 +        root.addWidget(self._project_list)
    119 +
    120 +        self._name_edit = QLineEdit(default_name, self)
    121 +        if self.mode in {Mode.NEW, Mode.SAVE_AS}:
    122 +            name_row = QHBoxLayout()
    123 +            name_row.addWidget(QLabel("Nazwa projektu:"))
    124 +            name_row.addWidget(self._name_edit, 1)
    125 +            root.addLayout(name_row)
    126 +        else:
    127 +            self._name_edit.hide()
    128 +
    129 +        self._button_box = QDialogButtonBox(self)
    130 +        if self.mode == Mode.STARTUP:
    131 +            self._open_button = self._button_box.addButton(
    132 +                "Otwórz",
    133 +                QDialogButtonBox.ButtonRole.AcceptRole,
    134 +            )
    135 +            self._new_button = self._button_box.addButton(
    136 +                "Nowy",
    137 +                QDialogButtonBox.ButtonRole.ActionRole,
    138 +            )
    139 +            self._new_button.clicked.connect(self._accept_new_from_startup)
    140 +        else:
    141 +            ok_text = "Otwórz" if self.mode == Mode.OPEN else "Zapisz"
    142 +            self._button_box.addButton(ok_text, QDialogButtonBox.ButtonRole.AcceptRole)
    143 +        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
    144 +        self._button_box.accepted.connect(self.accept)
    145 +        self._button_box.rejected.connect(self.reject)
    146 +        root.addWidget(self._button_box)
    147 +
    148 +    def _reload_projects(self) -> None:
    149 +        self._project_list.clear()
    150 +        for project in scan_projects_dir(self._projects_dir):
    151 +            item = QListWidgetItem(project.name)
    152 +            item.setData(Qt.ItemDataRole.UserRole, project.path)
    153 +            self._project_list.addItem(item)
    154 +        if self._project_list.count():
    155 +            self._project_list.setCurrentRow(0)
    156 +
    157 +    def _change_projects_dir(self) -> None:
    158 +        target = QFileDialog.getExistingDirectory(
    159 +            self,
    160 +            "Wybierz katalog projektów",
    161 +            str(self._projects_dir),
    162 +        )
    163 +        if not target:
    164 +            return
    165 +        self._projects_dir = Path(target)
    166 +        self._dir_label.setText(str(self._projects_dir))
    167 +        self._reload_projects()
    168 +
    169 +    def _accept_new_from_startup(self) -> None:
    170 +        self._startup_action = "new"
    171 +        self.accept()
    172 +
    173 +    def projects_dir(self) -> Path:
    174 +        return self._projects_dir
    175 +
    176 +    def startup_action(self) -> str | None:
    177 +        return self._startup_action
    178 +
    179 +    def project_name(self) -> str:
    180 +        return self._name_edit.text().strip() or "Nowy projekt"
    181 +
    182 +    def selected_path(self) -> Path | None:
    183 +        return self._selected_path
    184 +
    185 +    def accept(self) -> None:
    186 +        if self.mode in {Mode.NEW, Mode.SAVE_AS} or self._startup_action == "new":
    187 +            self._selected_path = self._projects_dir / f"{self.project_name()}.4dach"
    188 +            super().accept()
    189 +            return
    190 +
    191 +        item = self._project_list.currentItem()
    192 +        if item is None:
    193 +            return
    194 +        self._selected_path = Path(item.data(Qt.ItemDataRole.UserRole))
    195 +        self._startup_action = "open"
    196 +        super().accept()

• Ran uv run pytest tests/test_user_preferences.py -q
  └ .....                                                                    [100%]
    5 passed in 0.04s

• Ran uv run pytest tests/test_project_manager_dialog.py -q
  └ ...                                                                      [100%]
    3 passed in 0.19s

• Ran perl -0pi -e 's/MainWindow\(\)/MainWindow(auto_startup=False)/g' tests/test_mainwindow_ui_contract.py
  └ (no output)

───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

• Podpinam preferencje i nowy manager do MainWindow. Kluczowa zmiana: serializacja projektu idzie osobną ścieżką i odcina dane user-level, a ładowanie zawsze wstrzykuje preferencje przed budową ProjectState.

• Edited user_preferences.py (+1 -1)
    82                  for key in USER_LEVEL_KEYS
    83 -                if key in config_data
    83 +                if key in config_data and key not in self._data
    84              }

• Edited ui/main_window.py (+142 -32)
     10  from dataclasses import dataclass
     11 +from datetime import datetime
     12  from pathlib import Path
        ⋮
     51  )
     52 +from ui.dialogs.project_manager_dialog import Mode, ProjectManagerDialog
     53  from ui.drawing_canvas import CommittedOutlineEdit, DrawingCanvas
        ⋮
     66  from ui.workspace import WorkspaceController
     67 +from user_preferences import CONFIG_INJECTION_KEYS, UserPreferences
     68
        ⋮
     82  class MainWindow(QMainWindow):
     80 -    def __init__(self, parent=None) -> None:
     83 +    def __init__(self, parent=None, *, auto_startup: bool = True) -> None:
     84          super().__init__(parent)
     85          self._config = load_config()
     86 +        self._user_prefs = UserPreferences()
     87 +        if self._user_prefs.migrate_from_config(self._config):
     88 +            self._user_prefs.save()
     89 +        self._inject_user_preferences(self._config)
     90          self.project_state = ProjectState.from_config(self._config)
        ⋮
    103          self._sheets_visible = False
     97 -        self._project_file_path: Path | None = Path(__file__).resolve().parent.parent / "config.json"
    104 +        self._project_file_path: Path | None = None
    105
        ⋮
    137          self.statusBar().showMessage("Lewy przycisk myszy: rysowanie, prawy: wyczyść szkic", 5000)
    138 +        if auto_startup:
    139 +            self._show_startup_project_manager()
    140
        ⋮
    259      def _set_company_title(self, company: str) -> None:
    251 -        self._base_window_title = f"4Dach — {company}"
    260 +        project_meta = self._config.get("project_meta")
    261 +        project_name = project_meta.get("name") if isinstance(project_meta, dict) else ""
    262 +        self._base_window_title = f"4Dach — {project_name or company or '4Dach'}"
    263          self._refresh_window_title()
    264
    265 +    def _refresh_base_window_title(self) -> None:
    266 +        company = self._config.get("company_data", {}).get("name", "") or "4Dach"
    267 +        self._set_company_title(company)
    268 +
    269      def _refresh_window_title(self) -> None:
        ⋮
    273      def _serialize_current_config(self) -> dict:
    259 -        payload = copy.deepcopy(self._config)
    260 -        self.project_state.apply_to_config(payload)
    274 +        fragment = copy.deepcopy(self.project_state.to_config_fragment())
    275 +        fragment.pop("app_settings", None)
    276 +        payload = {
    277 +            "project_meta": copy.deepcopy(self._config.get("project_meta", {})),
    278 +            "materials": fragment.get("materials", {"order": [], "items": {}}),
    279 +            "project_state": fragment.get("project_state", {}),
    280 +            "blachy": fragment.get("blachy", []),
    281 +        }
    282          return payload
    283
    284 +    def _inject_user_preferences(self, payload: dict) -> dict:
    285 +        return self._user_prefs.inject_into_config(payload)
    286 +
    287 +    def _state_config_from_project_payload(self, payload: dict) -> dict:
    288 +        return self._inject_user_preferences(copy.deepcopy(payload))
    289 +
    290 +    def _project_display_name(self, fallback: str = "Nowy projekt") -> str:
    291 +        project_meta = self._config.get("project_meta")
    292 +        if isinstance(project_meta, dict) and project_meta.get("name"):
    293 +            return str(project_meta["name"])
    294 +        if self._project_file_path is not None:
    295 +            return self._project_file_path.stem
    296 +        company = self._config.get("company_data", {}).get("name", "")
    297 +        return company or fallback
    298 +
    299 +    def _prepare_payload_for_save(self, payload: dict, project_path: Path) -> dict:
    300 +        now = datetime.now().astimezone().isoformat()
    301 +        meta = copy.deepcopy(payload.get("project_meta") or {})
    302 +        meta.setdefault("created_at", now)
    303 +        meta["modified_at"] = now
    304 +        meta["name"] = str(meta.get("name") or project_path.stem)
    305 +        payload = copy.deepcopy(payload)
    306 +        payload["project_meta"] = meta
    307 +        return payload
    308 +
    309 +    def _persist_user_preferences(self, *keys: str) -> None:
    310 +        values: dict = {}
    311 +        for key in keys:
    312 +            if key == "app_settings":
    313 +                values[key] = self.project_state.app_settings.to_dict()
    314 +            elif key in self._config:
    315 +                values[key] = copy.deepcopy(self._config[key])
    316 +        if values:
    317 +            self._user_prefs.update(values)
    318 +            self._user_prefs.save()
    319 +            self._inject_user_preferences(self._config)
    320 +
    321 +    def _persist_projects_dir(self, projects_dir: Path) -> None:
    322 +        self._user_prefs.set("projects_dir", str(projects_dir))
    323 +        self._user_prefs.save()
    324 +
    325      def _normalized_dirty_payload(self, payload: dict) -> dict:
        ⋮
    432      def _apply_snapshot(self, snapshot: dict) -> None:
    371 -        self._config = copy.deepcopy(snapshot)
    433 +        self._config = self._state_config_from_project_payload(snapshot)
    434          self.project_state = ProjectState.from_config(self._config)
        ⋮
    436          self._invalidate_cached_report()
    375 -        company = self._config.get("company_data", {}).get("name", "") or "4Dach"
    376 -        self._set_company_title(company)
    437 +        self._refresh_base_window_title()
    438          self._refresh_ui_after_state_change(
        ⋮
    446              return self._save_project_as()
    386 -        payload = self._serialize_current_config()
    447 +        payload = self._prepare_payload_for_save(
    448 +            self._serialize_current_config(),
    449 +            self._project_file_path,
    450 +        )
    451          if not save_config(payload, self, path=self._project_file_path):
    452              return False
    389 -        self._config = payload
    453 +        self._config = self._state_config_from_project_payload(payload)
    454          self._mark_saved_state()
        ⋮
    458      def _save_project_as(self) -> bool:
    395 -        target, _ = QFileDialog.getSaveFileName(
    396 -            self,
    397 -            "Zapisz projekt jako",
    398 -            str(self._project_file_path or Path.cwd() / "projekt.json"),
    399 -            "JSON (*.json);;Wszystkie pliki (*)",
    459 +        dialog = ProjectManagerDialog(
    460 +            mode=Mode.SAVE_AS,
    461 +            projects_dir=self._user_prefs.projects_dir,
    462 +            default_name=self._project_display_name(),
    463 +            parent=self,
    464          )
    401 -        if not target:
    465 +        if not dialog_accepted(dialog):
    466 +            return False
    467 +        self._persist_projects_dir(dialog.projects_dir())
    468 +        project_path = dialog.selected_path()
    469 +        if project_path is None:
    470              return False
    403 -        if not target.lower().endswith(".json"):
    404 -            target = f"{target}.json"
    405 -        payload = self._serialize_current_config()
    406 -        project_path = Path(target)
    471 +        payload = self._prepare_payload_for_save(
    472 +            self._serialize_current_config(),
    473 +            project_path,
    474 +        )
    475          if not save_config(payload, self, path=project_path):
        ⋮
    477          self._project_file_path = project_path
    410 -        self._config = payload
    478 +        self._config = self._state_config_from_project_payload(payload)
    479          self._mark_saved_state()
        ⋮
    501          self._project_file_path = project_file_path
    434 -        self._config = payload
    502 +        self._config = self._state_config_from_project_payload(payload)
    503          self.project_state = ProjectState.from_config(self._config)
        ⋮
    506          self._invalidate_cached_report()
    439 -        company = self._config.get("company_data", {}).get("name", "") or "4Dach"
    440 -        self._set_company_title(company)
    507 +        self._refresh_base_window_title()
    508          self._refresh_ui_after_state_change(
        ⋮
    516              return
    517 +        dialog = ProjectManagerDialog(
    518 +            mode=Mode.NEW,
    519 +            projects_dir=self._user_prefs.projects_dir,
    520 +            default_name="Nowy projekt",
    521 +            parent=self,
    522 +        )
    523 +        if not dialog_accepted(dialog):
    524 +            return
    525 +        self._persist_projects_dir(dialog.projects_dir())
    526 +        project_path = dialog.selected_path()
    527 +        if project_path is None:
    528 +            return
    529          payload = self._serialize_current_config()
    530 +        payload["project_meta"] = {"name": dialog.project_name()}
    531          payload.setdefault("project_state", {})["active_plane_id"] = None
    532          payload["project_state"]["roof_planes"] = {"order": [], "items": {}}
    453 -        self._load_project_payload(payload, project_file_path=None, reset_history=True)
    533 +        payload = self._prepare_payload_for_save(payload, project_path)
    534 +        if not save_config(payload, self, path=project_path):
    535 +            return
    536 +        self._load_project_payload(payload, project_file_path=project_path, reset_history=True)
    537          self.statusBar().showMessage("Utworzono nowy projekt", 3000)
        ⋮
    541              return
    459 -        target, _ = QFileDialog.getOpenFileName(
    460 -            self,
    461 -            "Wczytaj projekt",
    462 -            str(self._project_file_path or Path.cwd()),
    463 -            "JSON (*.json);;Wszystkie pliki (*)",
    542 +        dialog = ProjectManagerDialog(
    543 +            mode=Mode.OPEN,
    544 +            projects_dir=self._user_prefs.projects_dir,
    545 +            parent=self,
    546          )
    465 -        if not target:
    547 +        if not dialog_accepted(dialog):
    548              return
    467 -        project_path = Path(target)
    549 +        self._persist_projects_dir(dialog.projects_dir())
    550 +        project_path = dialog.selected_path()
    551 +        if project_path is None:
    552 +            return
    553          self._load_project_payload(load_config(project_path), project_file_path=project_path, reset_history=True)
        ⋮
    555
    556 +    def _show_startup_project_manager(self) -> None:
    557 +        dialog = ProjectManagerDialog(
    558 +            mode=Mode.STARTUP,
    559 +            projects_dir=self._user_prefs.projects_dir,
    560 +            parent=self,
    561 +        )
    562 +        if not dialog_accepted(dialog):
    563 +            return
    564 +        self._persist_projects_dir(dialog.projects_dir())
    565 +        if dialog.startup_action() == "new":
    566 +            project_path = dialog.selected_path()
    567 +            if project_path is None:
    568 +                return
    569 +            payload = self._serialize_current_config()
    570 +            payload["project_meta"] = {"name": dialog.project_name()}
    571 +            payload.setdefault("project_state", {})["active_plane_id"] = None
    572 +            payload["project_state"]["roof_planes"] = {"order": [], "items": {}}
    573 +            payload = self._prepare_payload_for_save(payload, project_path)
    574 +            if save_config(payload, self, path=project_path):
    575 +                self._load_project_payload(payload, project_file_path=project_path, reset_history=True)
    576 +            return
    577 +        project_path = dialog.selected_path()
    578 +        if project_path is not None:
    579 +            self._load_project_payload(load_config(project_path), project_file_path=project_path, reset_history=True)
    580 +
    581      def _undo(self) -> None:

• Explored
  └ Search QFileDialog|setWindowTitle|_set_company_title|_refresh_base_window_title|_serialize_current_config|_dlg_settings|_on_grid_toggled|_dlg_firma|remember_shape_config|wycinki|add_polac_dialog in
           main_window.py

• Edited ui/main_window.py (+19 -23)
      16  from PySide6.QtWidgets import (
      17 -    QFileDialog,
      17      QInputDialog,
         ⋮
    1116          self._workspace.toggle_grid(checked)
    1118 -        self._refresh_dirty_state()
    1117 +        self._persist_user_preferences("app_settings")
    1118
         ⋮
    1122          self._workspace.set_snap_to_grid_enabled(checked)
    1124 -        self._refresh_dirty_state()
    1123 +        self._persist_user_preferences("app_settings")
    1124
         ⋮
    1320              return
    1321 +        self._persist_user_preferences("add_polac_dialog")
    1322
         ⋮
    1361          remember_shape_config(self._config, "prostokat", values)
    1362 +        self._persist_user_preferences("ksztalty")
    1363          outline = make_rectangle(values["szerokosc"], values["wysokosc"])
         ⋮
    1380          remember_shape_config(self._config, "trojkat", values)
    1381 +        self._persist_user_preferences("ksztalty")
    1382          self._set_active_plane_geometry(outline, f"Ustawiono obrys trójkąta {values['typ']}")
         ⋮
    1389          remember_shape_config(self._config, "trapez", values)
    1390 +        self._persist_user_preferences("ksztalty")
    1391          outline = make_trapezoid(
         ⋮
    1410          self._config.setdefault("wycinki", {})["prostokat"] = dict(values)
    1411 +        self._persist_user_preferences("wycinki")
    1412          hole = build_centered_hole(plane, values["szerokosc"], values["wysokosc"])
         ⋮
    1527          values = dlg.get_values()
    1524 -
    1525 -        def _apply_company_data() -> None:
    1526 -            self._config["company_data"] = values
    1527 -            self.project_state.company_data = self.project_state.company_data.from_dict(values)
    1528 -            company = values.get("name", "") or "4Dach"
    1529 -            self._set_company_title(company)
    1530 -
    1531 -        self._edit(_apply_company_data, "Zaktualizowano dane firmy", label="Edycja danych firmy")
    1528 +        self._config["company_data"] = values
    1529 +        self.project_state.company_data = self.project_state.company_data.from_dict(values)
    1530 +        self._persist_user_preferences("company_data")
    1531 +        self._refresh_base_window_title()
    1532 +        self._refresh_report()
    1533 +        self.statusBar().showMessage("Zaktualizowano dane firmy", 4000)
    1534
         ⋮
    1541          new_settings = dlg.build_settings()
    1540 -
    1541 -        def _apply_settings() -> None:
    1542 -            self.project_state.app_settings = new_settings
    1543 -            self._set_undo_stack_depth(new_settings.undo_stack_depth)
    1544 -            self._snap_to_grid_enabled = new_settings.snap_to_grid
    1545 -            self.project_state.mark_app_settings_layouts_dirty()
    1546 -
    1547 -        self._edit(
    1548 -            _apply_settings,
    1549 -            "Zaktualizowano ustawienia aplikacji",
    1550 -            label="Zmiana ustawień aplikacji",
    1551 -        )
    1542 +        self.project_state.app_settings = new_settings
    1543 +        self._set_undo_stack_depth(new_settings.undo_stack_depth)
    1544 +        self._snap_to_grid_enabled = new_settings.snap_to_grid
    1545 +        self._persist_user_preferences("app_settings")
    1546 +        self._refresh_canvas()
    1547 +        self.statusBar().showMessage("Zaktualizowano ustawienia aplikacji", 4000)
    1548

• Ran rg -n "CONFIG_INJECTION_KEYS|QFileDialog" ui/main_window.py && python -m py_compile user_preferences.py ui/dialogs/project_manager_dialog.py ui/main_window.py
  └ 66:from user_preferences import CONFIG_INJECTION_KEYS, UserPreferences

• Edited ui/main_window.py (+1 -1)
    65  from ui.workspace import WorkspaceController
    66 -from user_preferences import CONFIG_INJECTION_KEYS, UserPreferences
    66 +from user_preferences import UserPreferences
    67

• Waited for background terminal · uv run pytest tests/test_mainwindow_ui_contract.py -q

───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

• Focused MainWindow run zawisł w teście, który nadal wywołuje modalny manager bez podstawionej odpowiedzi. Zatrzymuję wiszący proces i dopasuję te testy do nowego kontraktu.

• Ran pkill -f 'pytest tests/test_mainwindow_ui_contract.py' || true
  └ (no output)

• Ran uv run pytest tests/test_mainwindow_ui_contract.py -q
  └ .........................F.............

• Ran uv run pytest tests/test_mainwindow_ui_contract.py -q -x
  └ .........................F
    =================================== FAILURES ===================================
    … +20 lines (ctrl + t to view transcript)
    !!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
    1 failed, 25 passed in 15.27s

• Edited tests/test_mainwindow_ui_contract.py (+10 -0)
    38  @pytest.fixture(autouse=True)
    39 +def _isolate_mainwindow_user_preferences(monkeypatch, tmp_path):
    40 +    from user_preferences import UserPreferences
    41 +
    42 +    monkeypatch.setattr(
    43 +        "ui.main_window.UserPreferences",
    44 +        lambda: UserPreferences(path=tmp_path / "user_preferences.json"),
    45 +    )
    46 +
    47 +
    48 +@pytest.fixture(autouse=True)
    49  def _default_question_response(monkeypatch):

• Waited for background terminal

• Ran pkill -f 'pytest tests/test_mainwindow_ui_contract.py' || true
  └ (no output)

• Waited for background terminal · uv run pytest tests/test_mainwindow_ui_contract.py -q -x

• Ran uv run pytest tests/test_mainwindow_ui_contract.py -q -x
  └ .......................................

• Ran uv run pytest tests/test_mainwindow_ui_contract.py --collect-only -q
  └ tests/test_mainwindow_ui_contract.py::test_mainwindow_exposes_expected_ui_contract
    tests/test_mainwindow_ui_contract.py::test_mainwindow_toolbar_hides_removed_actions_after_cleanup
    … +51 lines (ctrl + t to view transcript)

    53 tests collected in 0.19s

• Edited tests/test_mainwindow_ui_contract.py (+24 -0)
    32
    33 +def _accepted_project_dialog(*, selected_path: Path, project_name: str = "Projekt"):
    34 +    class FakeProjectManagerDialog:
    35 +        def __init__(self, *, mode, projects_dir, default_name="Nowy projekt", parent=None) -> None:
    36 +            self.mode = mode
    37 +            self._projects_dir = Path(projects_dir)
    38 +
    39 +        def exec(self) -> int:
    40 +            return QDialog.DialogCode.Accepted
    41 +
    42 +        def projects_dir(self) -> Path:
    43 +            return self._projects_dir
    44 +
    45 +        def selected_path(self) -> Path:
    46 +            return selected_path
    47 +
    48 +        def project_name(self) -> str:
    49 +            return project_name
    50 +
    51 +        def startup_action(self) -> str:
    52 +            return "open"
    53 +
    54 +    return FakeProjectManagerDialog
    55 +
    56 +
    57  @pytest.fixture(autouse=True)

• Edited tests/test_mainwindow_ui_contract.py (+21 -9)
    1349      monkeypatch.setattr("ui.main_window.load_config", lambda *args, **kwargs: next(loads))
    1350 -    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: ("/tmp/reopened.json", "JSON (*.json)")))
    1350 +    monkeypatch.setattr(
    1351 +        "ui.main_window.ProjectManagerDialog",
    1352 +        _accepted_project_dialog(selected_path=Path("/tmp/reopened.4dach")),
    1353 +    )
    1354
         ⋮
    1364      assert window.windowTitle() == "4Dach — Firma B"
    1362 -    assert window._project_file_path == Path("/tmp/reopened.json")
    1365 +    assert window._project_file_path == Path("/tmp/reopened.4dach")
    1366
    1367
    1365 -def test_mainwindow_marks_project_dirty_until_explicit_save(qtbot, monkeypatch):
    1368 +def test_mainwindow_marks_project_dirty_until_explicit_save(qtbot, monkeypatch, tmp_path):
    1369      saved_payloads: list[dict] = []
         ⋮
    1378      qtbot.addWidget(window)
    1379 +    window._project_file_path = tmp_path / "dirty.4dach"
    1380
         ⋮
    1412
    1409 -def test_mainwindow_new_project_clears_roof_planes_and_detaches_save_path(qtbot):
    1413 +def test_mainwindow_new_project_clears_roof_planes_and_reserves_save_path(qtbot, monkeypatch, tmp_path):
    1414 +    project_path = tmp_path / "nowy.4dach"
    1415 +    monkeypatch.setattr(
    1416 +        "ui.main_window.ProjectManagerDialog",
    1417 +        _accepted_project_dialog(selected_path=project_path, project_name="Nowy"),
    1418 +    )
    1419      window = MainWindow(auto_startup=False)
         ⋮
    1424      window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    1416 -    window._project_file_path = Path("/tmp/existing.json")
    1425 +    window._project_file_path = tmp_path / "existing.4dach"
    1426      window._refresh_canvas_from_state()
         ⋮
    1431      assert window.project_state.active_plane_id is None
    1423 -    assert window._project_file_path is None
    1432 +    assert window._project_file_path == project_path
    1433
         ⋮
    1442      monkeypatch.setattr("ui.main_window.save_config", _save_config)
    1434 -    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *args, **kwargs: ("/tmp/exported-project.json", "JSON (*.json)")))
    1443 +    monkeypatch.setattr(
    1444 +        "ui.main_window.ProjectManagerDialog",
    1445 +        _accepted_project_dialog(selected_path=Path("/tmp/exported-project.4dach")),
    1446 +    )
    1447
         ⋮
    1452      assert window._save_project_as() is True
    1441 -    assert window._project_file_path == Path("/tmp/exported-project.json")
    1442 -    assert saved_paths == [Path("/tmp/exported-project.json")]
    1453 +    assert window._project_file_path == Path("/tmp/exported-project.4dach")
    1454 +    assert saved_paths == [Path("/tmp/exported-project.4dach")]
    1455

• Edited tests/test_mainwindow_ui_contract.py (+0 -1)
    19      QDialogButtonBox,
    20 -    QFileDialog,
    20      QInputDialog,

• Waited for background terminal

• Waited for background terminal · uv run pytest tests/test_mainwindow_ui_contract.py -q -x

• Ran uv run pytest tests/test_mainwindow_ui_contract.py -q -x
  └ .......................................F
    =================================== FAILURES ===================================
    … +52 lines (ctrl + t to view transcript)
    !!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
    1 failed, 39 passed in 43.85s

• Edited tests/test_mainwindow_ui_contract.py (+2 -2)
    1326
    1327 -def test_mainwindow_open_project_resets_cached_report_and_company_title(qtbot, monkeypatch):
    1327 +def test_mainwindow_open_project_resets_cached_report_and_keeps_user_company_title(qtbot, monkeypatch):
    1328      initial_config = {
         ⋮
    1362      assert window._latest_report_plane_id is None
    1363 -    assert window.windowTitle() == "4Dach — Firma B"
    1363 +    assert window.windowTitle() == "4Dach — Firma A"
    1364      assert window._project_file_path == Path("/tmp/reopened.4dach")

• Waited for background terminal · uv run pytest tests/test_mainwindow_ui_contract.py -q -x

• Ran uv run pytest tests/test_mainwindow_ui_contract.py -q -x
  └ ....................................................F
    =================================== FAILURES ===================================
    … +50 lines (ctrl + t to view transcript)
    !!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
    1 failed, 52 passed in 67.10s (0:01:07)

• Edited ui/main_window.py (+2 -1)
    317              self._user_prefs.save()
    318 -            self._inject_user_preferences(self._config)
    318 +            for key, value in values.items():
    319 +                self._config[key] = copy.deepcopy(value)
    320

• Waited for background terminal · uv run pytest tests/test_mainwindow_ui_contract.py -q

• Ran uv run pytest tests/test_mainwindow_ui_contract.py -q
  └ .....................................................                    [100%]
    53 passed in 67.74s (0:01:07)

• Explored
  └ Read test_mainwindow_ui_contract.py

• Edited tests/test_mainwindow_ui_contract.py (+68 -0)
       2
       3 +import json
       4  from pathlib import Path
         ⋮
    1456
    1457 +def test_mainwindow_save_payload_contains_only_project_level_keys(qtbot, monkeypatch, tmp_path):
    1458 +    saved_payloads: list[dict] = []
    1459 +
    1460 +    def _save_config(config_data, parent=None, path=None):
    1461 +        saved_payloads.append(config_data)
    1462 +        return True
    1463 +
    1464 +    monkeypatch.setattr("ui.main_window.save_config", _save_config)
    1465 +
    1466 +    window = MainWindow(auto_startup=False)
    1467 +    qtbot.addWidget(window)
    1468 +    window._project_file_path = tmp_path / "project.4dach"
    1469 +    window._config["company_data"] = {"name": "User Firma"}
    1470 +    window._config["ksztalty"] = {"prostokat": {"szerokosc": 300}}
    1471 +    window._config["wycinki"] = {"prostokat": {"szerokosc": 90}}
    1472 +    window._config["add_polac_dialog"] = {"last_shape": "prostokat"}
    1473 +    window.project_state.app_settings.show_grid = False
    1474 +
    1475 +    assert window._save_project() is True
    1476 +
    1477 +    payload = saved_payloads[0]
    1478 +    assert set(payload) == {"project_meta", "materials", "project_state", "blachy"}
    1479 +    assert "company_data" not in payload
    1480 +    assert "ksztalty" not in payload
    1481 +    assert "wycinki" not in payload
    1482 +    assert "add_polac_dialog" not in payload
    1483 +    assert "app_settings" not in payload
    1484 +
    1485 +
    1486 +def test_mainwindow_load_injects_user_preferences_before_project_state(qtbot, monkeypatch, tmp_path):
    1487 +    prefs_path = tmp_path / "user_preferences.json"
    1488 +    prefs_path.write_text(
    1489 +        json.dumps(
    1490 +            {
    1491 +                "company_data": {"name": "User Firma"},
    1492 +                "app_settings": {"grid_size_cm": 25},
    1493 +            }
    1494 +        ),
    1495 +        encoding="utf-8",
    1496 +    )
    1497 +
    1498 +    from user_preferences import UserPreferences
    1499 +
    1500 +    monkeypatch.setattr(
    1501 +        "ui.main_window.UserPreferences",
    1502 +        lambda: UserPreferences(path=prefs_path),
    1503 +    )
    1504 +    monkeypatch.setattr(
    1505 +        "ui.main_window.load_config",
    1506 +        lambda: {
    1507 +            "project_meta": {"name": "Projekt A"},
    1508 +            "company_data": {"name": "Projekt Firma"},
    1509 +            "app_settings": {"grid_size_cm": 99},
    1510 +            "project_state": {"roof_planes": []},
    1511 +            "materials": {"order": [], "items": {}},
    1512 +            "blachy": [],
    1513 +        },
    1514 +    )
    1515 +
    1516 +    window = MainWindow(auto_startup=False)
    1517 +    qtbot.addWidget(window)
    1518 +
    1519 +    assert window.project_state.company_data.name == "User Firma"
    1520 +    assert window.project_state.app_settings.grid_size_cm == 25
    1521 +    assert window.windowTitle() == "4Dach — Projekt A"
    1522 +
    1523 +
    1524  def test_mainwindow_unsaved_close_confirmation_can_cancel_or_discard(qtbot, monkeypatch):

• Ran uv run pytest tests/test_mainwindow_ui_contract.py::test_mainwindow_save_payload_contains_only_project_level_keys tests/
  │ test_mainwindow_ui_contract.py::test_mainwindow_load_injects_user_preferences_before_project_state -q
  └ ..                                                                       [100%]
    2 passed in 0.81s

• Edited tests/test_mainwindow_ui_contract.py (+23 -0)
    1523
    1524 +def test_mainwindow_new_and_open_confirm_discard_before_project_manager(qtbot, monkeypatch):
    1525 +    calls: list[str] = []
    1526 +
    1527 +    class FailingProjectManagerDialog:
    1528 +        def __init__(self, *args, **kwargs) -> None:
    1529 +            raise AssertionError("project manager should not open after cancelled confirmation")
    1530 +
    1531 +    monkeypatch.setattr("ui.main_window.ProjectManagerDialog", FailingProjectManagerDialog)
    1532 +
    1533 +    window = MainWindow(auto_startup=False)
    1534 +    qtbot.addWidget(window)
    1535 +    monkeypatch.setattr(
    1536 +        window,
    1537 +        "_confirm_discard_unsaved_changes",
    1538 +        lambda *, context: calls.append(context) or False,
    1539 +    )
    1540 +
    1541 +    window._new_project()
    1542 +    window._open_project()
    1543 +
    1544 +    assert calls == ["utworzeniem nowego projektu", "otwarciem projektu"]
    1545 +
    1546 +
    1547  def test_mainwindow_unsaved_close_confirmation_can_cancel_or_discard(qtbot, monkeypatch):

• Ran uv run pytest tests/test_mainwindow_ui_contract.py::test_mainwindow_new_and_open_confirm_discard_before_project_manager -q
  └ .                                                                        [100%]
    1 passed in 0.74s

───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

• Testy dla nowych kontraktów MainWindow przechodzą lokalnie. Teraz porządkuję brief, żeby odzwierciedlał faktyczny zakres: kolejność __init__, user-level cache dialogów i brak zmian w ProjectState/
  persistence.py.

• Deleted docs/interfejs-zapisu-v2.md (+0 -37)
     1 -  # Interfejs Zapisu V2 - Plan Wdrożenia
     2 -
     3 -  ## Summary
     4 -
     5 -  Wdrożyć rozdzielenie danych użytkownika od danych projektu oraz zastąpić systemowe dialogi zapisu/otwierania własnym ProjectManagerDialog. Implementacja ma zachować istniejące nazwy pól MainWindow, uży
        wać
     6 -  _load_project_payload() jako jedynego punktu ładowania projektu i nie zmieniać persistence.py ani ProjectState.
     7 -
     8 -  ## Key Changes
     9 -
    10 -  - Uporządkować brief docs/interfejs-zapisu-v2.md: poprawić kolejność __init__, usunąć nieaktualny punkt o dodawaniu AppSettings.to_dict(), dopisać klasyczne dialogi kształtów, poprawić opis _dlg_add_po
        lac()
    11 -    i doprecyzować decyzje z tej rozmowy.
    12 -  - Dodać user_preferences.py z UserPreferences, ścieżką XDG/APPDATA i kluczami user-level: company_data, ksztalty, add_polac_dialog, wycinki, app_settings, projects_dir.
    13 -  - Dodać ui/dialogs/project_manager_dialog.py z Mode, ProjectMeta, scan_projects_dir() i ProjectManagerDialog; jedyny systemowy dialog to QFileDialog.getExistingDirectory() pod przyciskiem Zmień....
    14 -  - Zmienić MainWindow na MainWindow(parent=None, *, auto_startup: bool = True), żeby produkcyjnie pokazywać startowy manager, a testy mogły używać auto_startup=False.
    15 -  - W MainWindow.__init__ ustawić kolejność: self._config = load_config(), self._user_prefs = UserPreferences(), migracja legacy, inject user prefs, ProjectState.from_config(...), potem reszta UI.
    16 -  - Nowy projekt zachowuje aktualny/defaultowy katalog materiałów, ale czyści połacie i zapisuje od razu .4dach, żeby zarezerwować plik.
    17 -  - app_settings są user-level: zmiany z dialogu ustawień oraz toolbarowych przełączników show_grid i snap_to_grid zapisują się natychmiast do user_preferences.json i nie powinny brudzić projektu tylko p
        rzez
    18 -    zmianę preferencji.
    19 -  - Tytuł okna obsługiwać przez istniejący mechanizm _base_window_title + _refresh_window_title(); nie ustawiać ręcznie setWindowTitle(...) poza tym przepływem. Tytuł bazowy: 4Dach — <nazwa projektu> gdy
    20 -    projekt ma meta, inaczej 4Dach — <firma lub 4Dach>.
    21 -
    22 -  ## Test Plan
    23 -
    24 -  - Dodać testy dla UserPreferences: lokalizacja z podaną ścieżką, atomowy zapis, ignorowanie brakującego/uszkodzonego pliku, migracja tylko user-level keys.
    25 -  - Dodać testy dla scan_projects_dir(): brak folderu zwraca [], uszkodzony JSON jest pomijany, lista sortuje się po modified_at.
    26 -  - Zaktualizować testy MainWindow pod auto_startup=False; sprawdzić save/open/new bez QFileDialog.getOpenFileName/getSaveFileName.
    27 -  - Sprawdzić, że plik .4dach zawiera tylko project_meta, materials, project_state, blachy, bez user-level keys.
    28 -  - Sprawdzić, że ładowanie .4dach wstrzykuje app_settings i company_data przed ProjectState.from_config().
    29 -  - Sprawdzić, że _new_project() i _open_project() nadal wywołują _confirm_discard_unsaved_changes().
    30 -  - Uruchomić minimum: uv run pytest tests/test_app_settings.py tests/test_models_and_state.py tests/test_mainwindow_ui_contract.py -q; po stabilizacji pełne uv run pytest.
    31 -
    32 -  ## Assumptions
    33 -
    34 -  - persistence.py, core/project_state.py, core/models.py, ui/toolbar.py pozostają bez zmian.
    35 -  - AppSettings.to_dict() już istnieje i nie wymaga modyfikacji.
    36 -  - Materiały są project-level, ale nowy projekt startuje z aktualnym/defaultowym katalogiem dla ergonomii.
    37 -  - User prefs są zapisywane natychmiast po zmianie preferencji; błędy zapisu preferencji są niekrytyczne, ale nie powinny przerywać edycji projektu.

• Added docs/interfejs-zapisu-v2.md (+62 -0)
     1 +# Interfejs Zapisu V2
     2 +
     3 +## Cel
     4 +
     5 +Rozdzielić dane użytkownika od danych projektu oraz zastąpić systemowe dialogi
     6 +otwierania i zapisu własnym `ProjectManagerDialog`.
     7 +
     8 +## Decyzje wdrożeniowe
     9 +
    10 +- `persistence.py`, `ProjectState` i publiczne nazwy pól `MainWindow` pozostają bez zmian.
    11 +- Jedynym punktem ładowania projektu w `MainWindow` jest `_load_project_payload()`.
    12 +- `MainWindow.__init__` wykonuje kolejno:
    13 +  1. `self._config = load_config()`
    14 +  2. `self._user_prefs = UserPreferences()`
    15 +  3. migrację legacy user-level keys z `config.json`
    16 +  4. wstrzyknięcie preferencji użytkownika do payloadu roboczego
    17 +  5. `ProjectState.from_config(...)`
    18 +  6. budowę UI
    19 +- Plik projektu `.4dach` zawiera tylko `project_meta`, `materials`, `project_state`
    20 +  i `blachy`.
    21 +- Klucze user-level są przechowywane w `user_preferences.json`:
    22 +  `company_data`, `ksztalty`, `add_polac_dialog`, `wycinki`, `app_settings`,
    23 +  `projects_dir`.
    24 +- `app_settings` są preferencją użytkownika. Dialog ustawień oraz toolbarowe
    25 +  przełączniki `show_grid` i `snap_to_grid` zapisują preferencje natychmiast i
    26 +  nie brudzą projektu.
    27 +- Dane cache klasycznych dialogów kształtów (`ProstokatDialog`, `TrojkatDialog`,
    28 +  `TrapezDialog`), kreatora `_dlg_add_polac()` oraz dialogu wycinka
    29 +  prostokątnego są user-level.
    30 +- `DaneFirmyDialog` aktualizuje `company_data` jako user-level; ładowanie projektu
    31 +  wstrzykuje te dane przed `ProjectState.from_config()`.
    32 +- Nowy projekt zachowuje aktualny katalog materiałów, czyści połacie i zapisuje
    33 +  od razu plik `.4dach`, żeby zarezerwować ścieżkę.
    34 +- Tytuł okna idzie wyłącznie przez `_base_window_title` i `_refresh_window_title()`.
    35 +  Format bazowy to `4Dach — <nazwa projektu>` dla projektu z `project_meta`,
    36 +  inaczej `4Dach — <firma lub 4Dach>`.
    37 +
    38 +## ProjectManagerDialog
    39 +
    40 +`ui/dialogs/project_manager_dialog.py` zawiera:
    41 +
    42 +- `Mode`: `STARTUP`, `OPEN`, `SAVE_AS`, `NEW`
    43 +- `ProjectMeta`
    44 +- `scan_projects_dir()`
    45 +- `ProjectManagerDialog`
    46 +
    47 +Dialog używa własnej listy projektów `.4dach`. Jedyny systemowy dialog w tym
    48 +przepływie to `QFileDialog.getExistingDirectory()` pod przyciskiem `Zmień...`.
    49 +
    50 +## Testy kontraktowe
    51 +
    52 +Pokrycie obejmuje:
    53 +
    54 +- `UserPreferences`: ścieżkę z parametru, atomowy zapis, brakujący/uszkodzony
    55 +  plik oraz migrację wyłącznie user-level keys.
    56 +- `scan_projects_dir()`: brak folderu, pomijanie uszkodzonego JSON i sortowanie po
    57 +  `modified_at`.
    58 +- `MainWindow`: start testowy przez `auto_startup=False`, save/open/new bez
    59 +  `QFileDialog.getOpenFileName()` i `QFileDialog.getSaveFileName()`, filtrowanie
    60 +  payloadu `.4dach`, wstrzyknięcie `app_settings` i `company_data` przed
    61 +  `ProjectState.from_config()`, oraz zachowanie potwierdzenia odrzucenia
    62 +  niezapisanych zmian dla `_new_project()` i `_open_project()`.

───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

• Brief jest już zgodny z kodowym kontraktem. Uruchamiam teraz minimalny zestaw z planu plus nowe testy preferencji i managera, potem przejdę do pełnego pytest, jeśli focused run będzie czysty.

• Waited for background terminal · uv run pytest tests/test_user_preferences.py tests/test_project_manager_dialog.py tests/test_app_settings.py tests/test_models_and_state.py tests/test_mainwindow_ui_contract.py
-q

• Ran uv run pytest tests/test_user_preferences.py tests/test_project_manager_dialog.py tests/test_app_settings.py tests/test_models_and_state.py tests/test_mainwindow_ui_contract.py -q
  └ ........................................................................ [ 56%]
    ........................................................                 [100%]
    128 passed in 79.63s (0:01:19)

───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

• Focused verification is clean: 128 tests pass. Running the full suite now to catch cross-module fallout before I wrap this.

• Waited for background terminal · uv run pytest -q

• Ran uv run pytest -q
  └ ........................................................................ [ 22%]
    ........................................................................ [ 44%]
    … +2 lines (ctrl + t to view transcript)
    ....................................                                     [100%]
    324 passed in 102.09s (0:01:42)

───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

• Pełny test suite też przeszedł: 324 testy. Jeszcze sprawdzam Ruffa, bo dodałem nowe moduły i importy.

• Ran uv run ruff check .
  └ I001 [*] Import block is un-sorted or un-formatted
      --> core/layout_engine.py:1:1
    … +450 lines (ctrl + t to view transcript)
    Found 31 errors.
    [*] 7 fixable with the `--fix` option (11 hidden fixes can be enabled with the `--unsafe-fixes` option).

• Ran uv run ruff check user_preferences.py ui/dialogs/project_manager_dialog.py ui/main_window.py tests/test_user_preferences.py tests/test_project_manager_dialog.py tests/test_mainwindow_ui_contract.py
  └ E402 Module level import not at top of file
     --> tests/test_project_manager_dialog.py:8:1
    … +22 lines (ctrl + t to view transcript)
    Found 2 errors.
    [*] 1 fixable with the `--fix` option.

• Ran uv run ruff check --fix user_preferences.py tests/test_project_manager_dialog.py
  └ E402 Module level import not at top of file
     --> tests/test_project_manager_dialog.py:8:1
    … +6 lines (ctrl + t to view transcript)

    Found 2 errors (1 fixed, 1 remaining).

• Explored
  └ Read user_preferences.py, test_project_manager_dialog.py

• Edited tests/test_project_manager_dialog.py (+2 -2)
    5
    6 +from ui.dialogs.project_manager_dialog import Mode, ProjectManagerDialog, scan_projects_dir
    7 +
    8  pytest_plugins = ("pytestqt",)
    7 -
    8 -from ui.dialogs.project_manager_dialog import Mode, ProjectManagerDialog, scan_projects_dir
    9

• Ran uv run ruff check user_preferences.py ui/dialogs/project_manager_dialog.py ui/main_window.py tests/test_user_preferences.py tests/test_project_manager_dialog.py tests/test_mainwindow_ui_contract.py
  └ All checks passed!

───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

• Ruff na całym repo ujawnił starsze, niezwiązane problemy w innych modułach, ale pliki dotknięte tą zmianą są czyste. Po automatycznej korekcie importów w moich plikach puszczam jeszcze testy, żeby nie kończyć
  na stanie po zmianie formatowania.

• Waited for background terminal · uv run pytest -q

• Ran uv run pytest -q
  └ ........................................................................ [ 22%]
    ........................................................................ [ 44%]
    … +2 lines (ctrl + t to view transcript)
    ....................................                                     [100%]
    324 passed in 106.87s (0:01:46)

• Ran git status --short
  └  D _TODO/13_CANVAS_ROLLOUT_2_3_HANDOFF_2026-05-05.md
     D _TODO/_FEATURES/cleanup_plan.md
    … +15 lines (ctrl + t to view transcript)
    ?? ui/dialogs/project_manager_dialog.py
    ?? user_preferences.py

• Ran git diff --stat
  └  _TODO/13_CANVAS_ROLLOUT_2_3_HANDOFF_2026-05-05.md  | 190 ----------------
     _TODO/_FEATURES/cleanup_plan.md                    |  99 --------
    … +10 lines (ctrl + t to view transcript)
     ui/main_window.py                                  | 217 +++++++++++++-----
     13 files changed, 380 insertions(+), 405 deletions(-)

• Ran uv run ruff check user_preferences.py ui/dialogs/project_manager_dialog.py ui/main_window.py tests/test_user_preferences.py tests/test_project_manager_dialog.py tests/test_mainwindow_ui_contract.py
  └ All checks passed!

• Waited for background terminal

• Explored
  └ Read MEMORY.md

───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

• Wdrożyłem Interfejs Zapisu V2.

  Zmiany obejmują:

  - nowy user_preferences.py z migracją i atomowym zapisem user-level prefs,
  - nowy ui/dialogs/project_manager_dialog.py z Mode, ProjectMeta, scan_projects_dir() i własnym dialogiem projektów,
  - przebudowę ui/main_window.py pod auto_startup, wstrzykiwanie preferencji przed ProjectState.from_config(), filtrowany payload .4dach, natychmiastowy zapis app_settings i brak brudzenia projektu przez
    preferencje,
  - uporządkowany brief docs/interfejs-zapisu-v2.md,
  - nowe testy dla preferencji, managera projektów i kontraktów MainWindow.

  Weryfikacja:

  - uv run pytest -q -> 324 passed
  - focused plan suite -> 128 passed
  - uv run ruff check user_preferences.py ui/dialogs/project_manager_dialog.py ui/main_window.py tests/test_user_preferences.py tests/test_project_manager_dialog.py tests/test_mainwindow_ui_contract.py -> passed

  uv run ruff check . nadal zgłasza starsze, niezwiązane problemy w plikach poza tym zakresem, m.in. core/layout_engine.py, ui/drawing_canvas.py, tests/test_layout_engine.py, tests/test_reporting.py. Worktree
  miał też wcześniejsze niezwiązane zmiany/delety w _TODO/, tests/test_add_polac_dialog.py i ui/dialogs/add_polac_dialog.py; zostawiłem je bez cofania.
