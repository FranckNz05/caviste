@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Creation de l'environnement...
  python -m venv .venv
  .venv\Scripts\python -m pip install -q -r requirements.txt
)
echo Caviste demarre sur http://127.0.0.1:8765
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8765
