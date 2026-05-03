# Windows dev setup. Run from repo root: powershell -ExecutionPolicy Bypass -File scripts\install_dev.ps1
$ErrorActionPreference = "Stop"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip wheel
pip install -r requirements.txt
pip install pytest
python -m stellegent.cli initdb
Write-Host "Dev setup complete. Activate: .\.venv\Scripts\Activate.ps1"
