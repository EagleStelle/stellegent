#!/usr/bin/env bash
# RPi 5 / Bookworm 64-bit setup. Run with: bash scripts/install_rpi.sh
set -euo pipefail

sudo apt update
sudo apt install -y python3-pip python3-venv python3-picamera2 \
    libgl1 libglib2.0-0 sqlite3 build-essential

# --system-site-packages so the venv can import apt-installed picamera2 (CSI cam)
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt

# Ollama
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi
ollama pull phi3:mini

python -m stellegent.cli initdb
echo "Done. Activate venv with: source .venv/bin/activate"
