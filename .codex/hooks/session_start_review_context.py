#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


OPEN_ITEMS_HEADER = "## Open Items"


def read_hook_input() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def detect_repo_root(start_cwd: str | None) -> Path | None:
    cwd = Path(start_cwd or ".").resolve()
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    stdout = result.stdout.strip()
    return Path(stdout).resolve() if stdout else None


def detect_branch(repo_root: Path | None) -> str | None:
    if repo_root is None:
        return None
    result = subprocess.run(
        ["git", "-C", str(repo_root), "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=False,
    )
    branch = result.stdout.strip()
    return branch or None


def count_open_backlog_items(backlog_path: Path) -> int | None:
    if not backlog_path.is_file():
        return None

    try:
        lines = backlog_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    in_open_items = False
    count = 0
    for raw_line in lines:
        line = raw_line.strip()
        if line == OPEN_ITEMS_HEADER:
            in_open_items = True
            continue
        if in_open_items and line.startswith("## "):
            break
        if not in_open_items:
            continue

        # Intentionally minimal heuristic: only count backlog table rows in the
        # "Open Items" section whose status cell is exactly `open`/open.
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        status = cells[1].strip("`").strip().lower()
        if status == "open":
            count += 1

    return count


def build_context() -> str:
    payload = read_hook_input()
    repo_root = detect_repo_root(payload.get("cwd"))
    branch = detect_branch(repo_root)

    if repo_root is None:
        return (
            "Workflow reminder: no git repository was detected from the current session cwd. "
            "Open Codex inside the 4dach-qt repository before implementation work."
        )

    agents_path = repo_root / "AGENTS.md"
    backlog_path = repo_root / "docs" / "review-backlog.md"
    agents_exists = agents_path.is_file()
    backlog_exists = backlog_path.is_file()
    open_count = count_open_backlog_items(backlog_path) if backlog_exists else None

    if not backlog_exists:
        backlog_summary = "missing"
    elif open_count is None:
        backlog_summary = "present; open count unavailable"
    else:
        backlog_summary = f"present; open items: {open_count}"

    return "\n".join(
        [
            "4dach-qt workflow reminder:",
            f"- Repo root: {repo_root}",
            f"- Current branch: {branch or 'detached-or-unknown'}",
            f"- AGENTS.md: {'present' if agents_exists else 'missing'}",
            f"- docs/review-backlog.md: {backlog_summary}",
            "- Before implementation, read AGENTS.md and review the backlog if it exists.",
            "- Check unresolved backlog items relevant to the current stage before editing.",
            "- Preserve the existing stage-based branch and stacked-PR workflow.",
            "- This hook is advisory only: it does not modify files, branches, or prompts.",
        ]
    )


def main() -> int:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": build_context(),
        }
    }
    json.dump(output, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
