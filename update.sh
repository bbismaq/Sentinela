#!/usr/bin/env bash
# Sentinela updater — copies only the skill files (no dependency reinstall).
# Use after `git pull` when the maintainer publishes skill improvements.
# If you have NEVER installed Sentinela before, run install.sh instead.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="${HOME}/.claude/skills/sentinela"

if [ ! -d "$SKILL_ROOT" ]; then
    echo "Sentinela is not installed yet. Run ./install.sh first." >&2
    exit 1
fi

mkdir -p "$SKILL_ROOT/scripts"
cp -f "$REPO_ROOT/skills/sentinela/SKILL.md" "$SKILL_ROOT/SKILL.md"
cp -f "$REPO_ROOT"/scripts/*.py "$SKILL_ROOT/scripts/"

echo "Sentinela skill updated."
