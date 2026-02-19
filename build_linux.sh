#!/usr/bin/env bash
# ============================================================
#   ROI Tool - Linux Executable Builder
#   Run once on a Linux machine to produce dist/ROITool
# ============================================================
set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}============================================================"
echo -e "  ROI Tool - Linux Executable Builder"
echo -e "============================================================${NC}"
echo

# ── Check Python ─────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERROR] python3 not found. Install it with:${NC}"
    echo "        sudo apt install python3 python3-venv  # Debian/Ubuntu"
    echo "        sudo dnf install python3               # Fedora/RHEL"
    exit 1
fi

PY_VER=$(python3 --version)
echo -e "[OK] ${PY_VER} found."
echo

# ── Create isolated virtual environment ─────────────────────
echo "[1/4] Creating virtual environment..."
[ -d "build_env" ] && rm -rf build_env
python3 -m venv build_env
echo "      Done."
echo

# ── Install dependencies ─────────────────────────────────────
echo "[2/4] Installing dependencies (PyQt5, Pillow, PyInstaller)..."
echo "      This may take a few minutes on first run..."
echo
build_env/bin/pip install --quiet --upgrade pip
build_env/bin/pip install --quiet "PyQt5>=5.15" "Pillow>=10.0" "pyinstaller>=6.0"
echo "      Done."
echo

# ── Build ────────────────────────────────────────────────────
echo "[3/4] Building standalone executable..."
[ -d "build" ] && rm -rf build
[ -f "dist/ROITool" ] && rm -f dist/ROITool

build_env/bin/pyinstaller \
    --onefile \
    --windowed \
    --name ROITool \
    --exclude-module tkinter \
    --exclude-module matplotlib \
    --exclude-module numpy \
    --exclude-module scipy \
    --hidden-import PyQt5.sip \
    --hidden-import PIL.Image \
    --hidden-import PIL.ImageDraw \
    --collect-all PyQt5 \
    app.py

echo "      Done."
echo

# ── Verify ───────────────────────────────────────────────────
echo "[4/4] Verifying output..."
if [ ! -f "dist/ROITool" ]; then
    echo -e "${RED}[ERROR] dist/ROITool was not created.${NC}"
    exit 1
fi

SIZE_MB=$(du -m dist/ROITool | cut -f1)

echo
echo -e "${BOLD}============================================================"
echo -e "  BUILD SUCCESSFUL"
echo -e "============================================================${NC}"
echo
echo -e "  Executable: ${GREEN}dist/ROITool${NC}  (~${SIZE_MB} MB)"
echo
echo "  Make it executable and run:"
echo "    chmod +x dist/ROITool && ./dist/ROITool"
echo
echo "  Copy dist/ROITool to any Linux PC and run it without"
echo "  installing Python or any libraries."
echo
echo "============================================================"
