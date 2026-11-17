#!/usr/bin/env bash
# Copy every skill from this repo's .claude/skills/ into ~/.claude/skills/
# so Claude Code sees them in any project (ghost-editor and shorts expect that path).
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.claude/skills"
DST="$HOME/.claude/skills"
mkdir -p "$DST"
for d in "$SRC"/*/; do
  name="$(basename "$d")"
  rm -rf "${DST:?}/$name"
  cp -R "$d" "$DST/$name"
  echo "installed $name"
done
echo "Done. Restart Claude Code to load the skills."
