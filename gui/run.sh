#!/usr/bin/env bash
# EchoOS GUI — Linux / Ubuntu Launcher
set -e
cd "$(dirname "$0")"

# Check for EchoOS virtual environment
if [ -f "../.venv/bin/python" ]; then
    PYTHON="../.venv/bin/python"
elif [ -f "../../EchoOS/.venv/bin/python" ]; then
    PYTHON="../../EchoOS/.venv/bin/python"
else
    PYTHON="python3"
fi

echo ""
echo "  [EchoOS GUI] Verifying dependencies..."
$PYTHON -m pip install -q -r requirements.txt

echo ""
echo "  [EchoOS GUI] Starting web interface..."
echo "  Open your browser at: http://localhost:5050"
echo ""
$PYTHON app.py
