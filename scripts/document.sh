#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for task_python in python3 python py; do
  if command -v "$task_python" >/dev/null 2>&1 && "$task_python" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    exec "$task_python" "$SCRIPT_DIR/pipeline.py" document "$@"
  fi
done
echo "ERROR: se requiere un intérprete funcional de Python 3.10 o posterior." >&2
exit 1
