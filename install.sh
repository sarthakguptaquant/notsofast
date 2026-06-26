#!/usr/bin/env bash
# Install the notsofast skill into a Claude skills directory.
#
# Usage:
#   ./install.sh                 # install for the current user (~/.claude/skills)
#   ./install.sh --project       # install into ./.claude/skills (this repo/project)
#   ./install.sh --dir PATH      # install into a custom skills directory
#
# One-liner (public repo):
#   curl -fsSL https://raw.githubusercontent.com/sarthakguptaquant/notsofast/main/install.sh | bash
#
# This copies skills/notsofast/ into the target skills directory. It does not
# require Claude Code itself; any agent runtime that reads SKILL.md folders can use it.
set -euo pipefail

REPO="https://github.com/sarthakguptaquant/notsofast.git"
SKILL="notsofast"
TARGET="${HOME}/.claude/skills"

while [ $# -gt 0 ]; do
  case "$1" in
    --project) TARGET="$(pwd)/.claude/skills" ;;
    --dir) shift; TARGET="$1" ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

# Resolve the skill source: prefer the local checkout if this script sits in the repo,
# otherwise clone (uses the caller's git credentials, so it works for the private repo too).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "${SCRIPT_DIR}/skills/${SKILL}" ]; then
  SRC="${SCRIPT_DIR}/skills/${SKILL}"
  CLEANUP=""
else
  TMP="$(mktemp -d)"
  echo "Cloning ${REPO} ..."
  git clone --depth 1 "${REPO}" "${TMP}/repo"
  SRC="${TMP}/repo/skills/${SKILL}"
  CLEANUP="${TMP}"
fi

mkdir -p "${TARGET}"
rm -rf "${TARGET:?}/${SKILL}"
cp -R "${SRC}" "${TARGET}/${SKILL}"
[ -n "${CLEANUP}" ] && rm -rf "${CLEANUP}"

echo "Installed ${SKILL} -> ${TARGET}/${SKILL}"
echo "Verify: python3 ${TARGET}/${SKILL}/scripts/test_notsofast.py"
