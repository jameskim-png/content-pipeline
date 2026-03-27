#!/bin/bash
# content-pipeline — One-command setup
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "=== content-pipeline Setup ==="

# 1. Check Python 3.10+
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.10+ first."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python: $PY_VERSION"

# 2. Check ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "Installing ffmpeg..."
    if command -v brew &>/dev/null; then
        brew install ffmpeg
    else
        echo "ERROR: ffmpeg not found and brew not available."
        echo "Install ffmpeg: https://ffmpeg.org/download.html"
        exit 1
    fi
else
    echo "ffmpeg: OK"
fi

# 3. Create venv if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# 4. Install dependencies
echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$PROJECT_DIR/requirements.txt"

# 5. Create .env if missing
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo ""
    echo "=== API Key Setup ==="
    echo ""

    read -p "fal.ai API key (FAL_KEY): " FAL_KEY

    {
        echo "FAL_KEY=$FAL_KEY"
    } > "$PROJECT_DIR/.env"

    echo ".env created"
else
    echo ".env: OK"
fi

# 6. Create data dirs
mkdir -p "$PROJECT_DIR/data" "$PROJECT_DIR/output" "$PROJECT_DIR/personas"

echo ""
echo "=== Setup Complete ==="
echo "Run: /content-pipeline"
