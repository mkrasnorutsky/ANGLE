#!/bin/bash
# Fetch ANGLE's pinned DEPS. Run once after cloning, before building.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEPOT_TOOLS="${DEPOT_TOOLS:-$ROOT/.build-tools/depot_tools}"
if [[ ! -f "$DEPOT_TOOLS/gclient" ]]; then
  git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git "$DEPOT_TOOLS"
fi
git -C "$DEPOT_TOOLS" checkout b86fc981b72ab966f8260f73b4eca600b3b12677
export PATH="$DEPOT_TOOLS:$PATH"
export DEPOT_TOOLS_UPDATE=0
cd "$ROOT"
if [[ ! -f .gclient ]]; then
  python3 - <<'PY'
from pathlib import Path
Path('.gclient').write_text("solutions = [{'name': '.', 'url': 'https://github.com/mkrasnorutsky/ANGLE.git', 'deps_file': 'DEPS', 'managed': False, 'custom_deps': {}, 'custom_vars': {}}]\n")
PY
fi
gclient sync --no-history --shallow
