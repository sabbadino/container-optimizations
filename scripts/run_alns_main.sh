#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root as the directory containing this script's parent
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Prefer the repo's local OR-Tools Python, fall back to system python if not found
PYBIN="${ROOT_DIR}/ortools/Scripts/python.exe"
if [ ! -x "${PYBIN}" ]; then
  PYBIN="python"
fi

INPUT_PATH="${ROOT_DIR}/inputs/alns_input_data_50_items_1.json"
OUTPUT_PATH="${ROOT_DIR}/outputs/alns_out.json"

# Allow optional overrides via CLI args: input output [--verbose]
if [ ${#} -ge 1 ]; then INPUT_PATH="$1"; fi
if [ ${#} -ge 2 ]; then OUTPUT_PATH="$2"; fi

# Run main.py with the same arguments as the VS Code launch config
"${PYBIN}" "${ROOT_DIR}/main.py" \
  --input "${INPUT_PATH}" \
  --output "${OUTPUT_PATH}" \
  --verbose
