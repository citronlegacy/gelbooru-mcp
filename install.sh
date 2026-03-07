#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="$(dirname "$0")/.venv"

echo "Creating virtual environment at $VENV_DIR..."
python3 -m venv "$VENV_DIR"

echo "Installing requirements..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$(dirname "$0")/requirements.txt"

echo ""
echo "Done! To run the MCP server:"
echo "  $VENV_DIR/bin/python gelbooru_mcp.py"
