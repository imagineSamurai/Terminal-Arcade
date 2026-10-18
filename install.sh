#!/usr/bin/env sh
set -e
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/arcade" ]; then
    chmod +x "$SCRIPT_DIR/arcade" 2>/dev/null || true
    "$SCRIPT_DIR/arcade" --install
else
    python3 "$SCRIPT_DIR/arcade.py" --install
fi
