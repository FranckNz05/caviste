"""Caviste, application de bureau (poste de la boutique).

Lance le serveur en local (base SQLite dans %LOCALAPPDATA%\\Caviste), puis ouvre
l'interface dans une fenêtre dédiée (Microsoft Edge en mode application, présent
sur tout Windows 10/11). Fonctionne sans Internet ; la synchronisation vers
l'espace en ligne du patron se fait toute seule dès que la connexion revient.

    Caviste.exe           -> la boutique
    Caviste.exe --demo    -> une cave de démonstration, séparée, jamais synchronisée
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

DEMO = "--demo" in sys.argv
APP_DIR = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Caviste"
DATA_DIR = APP_DIR / ("demo" if DEMO else "boutique")
PORT = int(os.environ.get("CAVISTE_PORT", 8766 if DEMO else 8765))
URL = f"http://127.0.0.1:{PORT}/"
IDLE_EXIT_SECONDS = 60  # sans fenêtre ni signe de vie pendant 1 min, on s'arrête

DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("CAVISTE_DATA_DIR", str(DATA_DIR))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'caviste.db').as_posix()}")
os.environ["CAVISTE_MODE"] = "web" if DEMO else "poste"
os.environ["CAVISTE_DEMO"] = "1" if DEMO else "0"

# Application sans console : les sorties vont dans un fichier journal.
if sys.stdout is None or sys.stderr is None:
    _log = open(DATA_DIR / "caviste.log", "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or _log
    sys.stderr = sys.stderr or _log


def _responds() -> bool:
    try:
        with urllib.request.urlopen(URL + "api/config", timeout=2) as r:
            return r.status == 200
    except OSError:
        return False


def _port_free() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", PORT)) != 0


def _find_edge() -> str | None:
    candidates = [
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), r"Microsoft\Edge\Application\msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), r"Microsoft\Edge\Application\msedge.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Edge\Application\msedge.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return shutil.which("msedge")


def open_window() -> subprocess.Popen | None:
    edge = _find_edge()
    if not edge:
        webbrowser.open(URL)
        return None
    profile = APP_DIR / ("fenetre-demo" if DEMO else "fenetre")
    return subprocess.Popen(
        [
            edge,
            f"--app={URL}",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-features=Translate",
            "--window-size=1366,860",
        ]
    )


def main() -> None:
    # Déjà lancé : on se contente de rouvrir une fenêtre.
    if not _port_free():
        if _responds():
            open_window()
            return
        raise SystemExit(f"Le port {PORT} est occupé par un autre programme.")

    import uvicorn

    from app.main import app

    last_seen = [time.time()]

    @app.middleware("http")
    async def _heartbeat(request, call_next):
        last_seen[0] = time.time()
        return await call_next(request)

    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning", log_config=None, loop="asyncio", http="h11", ws="none")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(300):
        if server.started:
            break
        if not thread.is_alive():
            raise SystemExit("Le serveur local n'a pas pu démarrer (voir caviste.log).")
        time.sleep(0.1)

    window = open_window()
    # On s'arrête quand la fenêtre est fermée et que plus aucune page ne donne signe de vie.
    while thread.is_alive():
        time.sleep(3)
        window_open = window is not None and window.poll() is None
        if not window_open and time.time() - last_seen[0] > IDLE_EXIT_SECONDS:
            break
    server.should_exit = True
    thread.join(timeout=10)


if __name__ == "__main__":
    main()
