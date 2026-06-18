#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$ROOT_DIR/skills"

usage() {
  cat <<'EOF'
Usage:
  ./install.sh --dest <skills-dir> [--dry-run]
  ./install.sh --codex [--dry-run]
  ./install.sh --claude [--dry-run]
  ./install.sh --all [--dry-run]

Examples:
  ./install.sh --codex
  ./install.sh --dest "$HOME/.codex/skills"
  ./install.sh --all --dry-run

This copies ctf-* skill directories into the selected skills directory.
Existing ctf-* skills at the destination are replaced. Other skills are not touched.
EOF
}

dry_run=0
destinations=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest)
      [[ $# -ge 2 ]] || { echo "--dest requires a path" >&2; exit 2; }
      destinations+=("$2")
      shift 2
      ;;
    --codex)
      destinations+=("$HOME/.codex/skills")
      shift
      ;;
    --claude)
      destinations+=("$HOME/.claude/skills")
      shift
      ;;
    --all)
      destinations+=("$HOME/.codex/skills" "$HOME/.claude/skills")
      shift
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ${#destinations[@]} -eq 0 ]]; then
  usage >&2
  exit 2
fi

if [[ ! -d "$SKILLS_DIR" ]]; then
  echo "skills directory not found: $SKILLS_DIR" >&2
  exit 1
fi

for dest in "${destinations[@]}"; do
  echo "Installing CTF skills to $dest"
  if [[ "$dry_run" -eq 1 ]]; then
    for src in "$SKILLS_DIR"/ctf-*; do
      [[ -d "$src" ]] || continue
      echo "DRY-RUN copy $(basename "$src") -> $dest/$(basename "$src")"
    done
    continue
  fi
  mkdir -p "$dest"
  for src in "$SKILLS_DIR"/ctf-*; do
    [[ -d "$src" ]] || continue
    name="$(basename "$src")"
    rm -rf "$dest/$name"
    cp -R "$src" "$dest/$name"
    echo "installed $name"
  done
done
