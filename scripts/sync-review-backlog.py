#!/usr/bin/env python3
"""Generate a readable PR review snapshot from raw GitHub export JSON.

This script intentionally does not edit docs/review-backlog.md statuses.
It writes a machine-generated source document under docs/reviews/ so humans
and later agents can triage review feedback in a controlled way.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize raw GitHub PR review exports into a markdown snapshot "
            "under docs/reviews/pr-XXX.md."
        )
    )
    parser.add_argument(
        "export_dir",
        type=Path,
        help="Directory created by scripts/export-pr-review.sh",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output path. Defaults to docs/reviews/pr-XXX.md.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing export file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def flatten_records(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, dict):
        return [payload]
    if not isinstance(payload, list):
        raise SystemExit(f"Unsupported JSON payload type: {type(payload).__name__}")

    flattened: list[dict[str, Any]] = []
    stack = list(payload)
    while stack:
        item = stack.pop(0)
        if isinstance(item, list):
            stack[0:0] = item
            continue
        if isinstance(item, dict):
            flattened.append(item)
            continue
        raise SystemExit(f"Unsupported list element type: {type(item).__name__}")
    return flattened


def collapse_text(value: str | None, limit: int = 140) -> str:
    raw = (value or "").strip()
    if not raw:
        return "-"
    single_line = " ".join(raw.split())
    if len(single_line) <= limit:
        return single_line
    return f"{single_line[: limit - 1].rstrip()}…"


def markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def as_login(user: dict[str, Any] | None) -> str:
    if not user:
        return "unknown"
    return str(user.get("login") or "unknown")


def is_agent(user: dict[str, Any] | None) -> str:
    if not user:
        return "unknown"
    user_type = str(user.get("type") or "").lower()
    login = str(user.get("login") or "").lower()
    return "yes" if user_type == "bot" or login.endswith("[bot]") else "no"


def normalize_review_comment(pr_number: int, record: dict[str, Any]) -> dict[str, Any]:
    line = record.get("line") or record.get("original_line") or record.get("position")
    return {
        "id": f"review_comment:{record.get('id', 'unknown')}",
        "pr_number": pr_number,
        "author": as_login(record.get("user")),
        "agent": is_agent(record.get("user")),
        "file_path": record.get("path") or "-",
        "line": str(line) if line is not None else "-",
        "body_summary": collapse_text(record.get("body")),
        "body": (record.get("body") or "").strip(),
        "source_type": "review_comment",
        "state": "-",
        "created_at": record.get("created_at") or "-",
        "url": record.get("html_url") or "-",
    }


def normalize_issue_comment(pr_number: int, record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"issue_comment:{record.get('id', 'unknown')}",
        "pr_number": pr_number,
        "author": as_login(record.get("user")),
        "agent": is_agent(record.get("user")),
        "file_path": "-",
        "line": "-",
        "body_summary": collapse_text(record.get("body")),
        "body": (record.get("body") or "").strip(),
        "source_type": "issue_comment",
        "state": "-",
        "created_at": record.get("created_at") or "-",
        "url": record.get("html_url") or "-",
    }


def normalize_review_event(pr_number: int, record: dict[str, Any]) -> dict[str, Any]:
    state = str(record.get("state") or "-")
    summary = collapse_text(record.get("body") or state)
    return {
        "id": f"review:{record.get('id', 'unknown')}",
        "pr_number": pr_number,
        "author": as_login(record.get("user")),
        "agent": is_agent(record.get("user")),
        "file_path": "-",
        "line": "-",
        "body_summary": summary,
        "body": (record.get("body") or "").strip(),
        "source_type": "review",
        "state": state,
        "created_at": record.get("submitted_at") or record.get("created_at") or "-",
        "url": record.get("html_url") or "-",
    }


def markdown_quote(value: str) -> str:
    text = value.strip()
    if not text:
        return "> _No body text provided._"
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())


def sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (str(item["created_at"]), str(item["source_type"]), str(item["id"]))


def render_markdown(
    *,
    repo: str,
    pr_number: int,
    pr_title: str,
    pr_url: str,
    head_ref: str,
    base_ref: str,
    export_dir: Path,
    items: list[dict[str, Any]],
) -> str:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    lines = [
        f"# PR #{pr_number:03d} Review Snapshot",
        "",
        "This file is generated by `scripts/sync-review-backlog.py` from raw GitHub exports.",
        "Use it as source material for updating `docs/review-backlog.md`.",
        "",
        "## PR Metadata",
        "",
        f"- Repository: `{repo}`",
        f"- PR: [#{pr_number}]({pr_url})",
        f"- Title: {pr_title}",
        f"- Head branch: `{head_ref}`",
        f"- Base branch: `{base_ref}`",
        f"- Export directory: `{export_dir}`",
        f"- Generated at: `{generated_at}`",
        "",
        "## Normalized Items",
        "",
        "| ID | Source | Author | Agent | File | Line | Summary |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    if items:
        for item in items:
            lines.append(
                "| {id} | `{source_type}` | `{author}` | `{agent}` | `{file_path}` | `{line}` | {body_summary} |".format(
                    id=markdown_cell(str(item["id"])),
                    source_type=markdown_cell(str(item["source_type"])),
                    author=markdown_cell(str(item["author"])),
                    agent=markdown_cell(str(item["agent"])),
                    file_path=markdown_cell(str(item["file_path"])),
                    line=markdown_cell(str(item["line"])),
                    body_summary=markdown_cell(str(item["body_summary"])),
                )
            )
    else:
        lines.append("| _none_ | - | - | - | - | - | No comments or review events were exported. |")

    lines.extend(
        [
            "",
            "## Detailed Items",
            "",
        ]
    )

    if not items:
        lines.append("No review comments, issue comments, or review events were found in the export.")
        return "\n".join(lines) + "\n"

    for item in items:
        lines.extend(
            [
                f"### {item['id']}",
                "",
                f"- Source: `{item['source_type']}`",
                f"- Author: `{item['author']}`",
                f"- Agent: `{item['agent']}`",
                f"- File: `{item['file_path']}`",
                f"- Line: `{item['line']}`",
                f"- Review state: `{item['state']}`",
                f"- Created at: `{item['created_at']}`",
                f"- URL: {item['url']}",
                f"- Summary: {item['body_summary']}",
                "- Body:",
                markdown_quote(item["body"]),
                "",
            ]
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    export_dir = args.export_dir.resolve()
    if not export_dir.is_dir():
        raise SystemExit(f"Export directory does not exist: {export_dir}")

    pr_payload = load_json(export_dir / "pull-request.json")
    pr_number = pr_payload.get("number")
    if not isinstance(pr_number, int):
        raise SystemExit("pull-request.json is missing a numeric `number` field.")

    repo = ""
    head_repo = pr_payload.get("head", {}).get("repo", {})
    base_repo = pr_payload.get("base", {}).get("repo", {})
    repo = (
        str(head_repo.get("full_name") or "")
        or str(base_repo.get("full_name") or "")
        or "unknown"
    )

    items: list[dict[str, Any]] = []
    for record in flatten_records(load_json(export_dir / "review-comments.json")):
        items.append(normalize_review_comment(pr_number, record))
    for record in flatten_records(load_json(export_dir / "issue-comments.json")):
        items.append(normalize_issue_comment(pr_number, record))
    for record in flatten_records(load_json(export_dir / "reviews.json")):
        items.append(normalize_review_event(pr_number, record))

    items.sort(key=sort_key)

    output_path = args.output or Path("docs") / "reviews" / f"pr-{pr_number:03d}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_markdown(
            repo=repo,
            pr_number=pr_number,
            pr_title=str(pr_payload.get("title") or "(untitled)"),
            pr_url=str(pr_payload.get("html_url") or "-"),
            head_ref=str(pr_payload.get("head", {}).get("ref") or "-"),
            base_ref=str(pr_payload.get("base", {}).get("ref") or "-"),
            export_dir=export_dir,
            items=items,
        ),
        encoding="utf-8",
    )

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
