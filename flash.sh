#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$TASK_ROOT"
if [[ "${1:-}" == "--help" || "${1:-}" == "--verify-only" ]]; then
    exec python3 -m tools.flash "$@"
fi
if ! command -v python3 >/dev/null; then
    echo 'Install Python first: sudo apt install python3 python3-venv' >&2
    exit 1
fi
if ! python3 -m venv "$TASK_ROOT/.flash-venv"; then
    echo 'Run: sudo apt install python3-venv' >&2
    echo 'Then run: bash flash.sh' >&2
    exit 1
fi
TASK_PYTHON="$TASK_ROOT/.flash-venv/bin/python"
if ! "$TASK_PYTHON" -c 'import importlib.metadata as m; import serial; assert m.version("esptool") == "4.11.0"' 2>/dev/null; then
    echo 'Installing the small flashing tools (first run only)...'
    "$TASK_PYTHON" -m pip --disable-pip-version-check install -q -r tools/requirements-flash.txt
fi
exec "$TASK_PYTHON" -m tools.flash "$@"
