#!/usr/bin/env bash
# 为当前 worktree 创建可复现的 Python 解析环境。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV="$ROOT/.venv"

if [[ ! -x "$VENV/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install -r "$ROOT/requirements.txt"
printf 'Python environment ready: %s\n' "$VENV"
