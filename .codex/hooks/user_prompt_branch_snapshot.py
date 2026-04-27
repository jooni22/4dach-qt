#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from typing import Any

from branch_guard_common import (
    current_branch,
    current_head,
    detect_repo_root,
    dirty_paths,
    fingerprint_for_path,
    read_hook_input,
    save_snapshot,
)


def extract_prompt(payload: dict[str, Any]) -> str:
    prompt = payload.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt.strip()

    items = payload.get("input")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("type") in {"text", "input_text"}:
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
    return ""


def main() -> int:
    payload = read_hook_input()
    repo_root = detect_repo_root(payload.get("cwd"))
    turn_id = payload.get("turn_id")

    if repo_root is None or not isinstance(turn_id, str) or not turn_id:
        json.dump({}, sys.stdout)
        sys.stdout.write("\n")
        return 0

    prompt = extract_prompt(payload)
    dirty = dirty_paths(repo_root)
    save_snapshot(
        repo_root,
        turn_id,
        prompt,
        {
            "start_branch": current_branch(repo_root),
            "start_head": current_head(repo_root),
            "dirty_files": {
                path: fingerprint_for_path(repo_root, path)
                for path in dirty
            },
        },
    )

    json.dump({}, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
