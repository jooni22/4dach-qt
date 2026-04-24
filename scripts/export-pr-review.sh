#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/export-pr-review.sh PR_NUMBER [OUTPUT_DIR]

Exports raw GitHub review data for one pull request using `gh api`.

Files written:
  pull-request.json
  review-comments.json
  issue-comments.json
  reviews.json

If OUTPUT_DIR is omitted, a temporary directory is created and its path is printed.
EOF
}

fail() {
  printf 'error: %s\n' "$1" >&2
  exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  fail "GitHub CLI (`gh`) is not installed. Install it first: https://cli.github.com/"
fi

if ! gh auth status >/dev/null 2>&1; then
  fail "GitHub CLI is not authenticated. Run `gh auth login` and retry."
fi

pr_number="$1"
if [[ ! "$pr_number" =~ ^[0-9]+$ ]]; then
  fail "PR number must be a positive integer."
fi

if [[ $# -eq 2 ]]; then
  output_dir="$2"
  mkdir -p "$output_dir"
else
  output_dir="$(mktemp -d "${TMPDIR:-/tmp}/pr-review-${pr_number}-XXXXXX")"
fi

if ! gh api "repos/:owner/:repo/pulls/${pr_number}" >/dev/null 2>&1; then
  fail "Pull request #${pr_number} was not found for the current repository or is not accessible."
fi

accept_header="Accept: application/vnd.github+json"

printf 'Exporting PR #%s review data to %s\n' "$pr_number" "$output_dir" >&2

gh api -H "$accept_header" "repos/:owner/:repo/pulls/${pr_number}" >"${output_dir}/pull-request.json"
gh api --paginate --slurp -H "$accept_header" "repos/:owner/:repo/pulls/${pr_number}/comments?per_page=100" >"${output_dir}/review-comments.json"
gh api --paginate --slurp -H "$accept_header" "repos/:owner/:repo/issues/${pr_number}/comments?per_page=100" >"${output_dir}/issue-comments.json"
gh api --paginate --slurp -H "$accept_header" "repos/:owner/:repo/pulls/${pr_number}/reviews?per_page=100" >"${output_dir}/reviews.json"

printf '%s\n' "$output_dir"
