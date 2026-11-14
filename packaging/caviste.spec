# Recette PyInstaller : python -m PyInstaller packaging/caviste.spec
# Produit dist/Caviste/Caviste.exe (dossier complet, sans console).
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent

hidden = (
    collect_submodules("uvicorn")
    + collect_submodules("app")
    + ["sqlalchemy.dialects.sqlite", "sqlalchemy.dialects.postgresql"]
)

a = Analysis(
    [str(ROOT / "desktop.py")],
    pathex=[str(ROOT)],
    datas=[(str(ROOT / "static"), "static")],
    hiddenimports=hidden,
    excludes=["tkinter", "psycopg", "psycopg_binary", "watchfiles", "websockets", "uvloop", "PIL", "PyInstaller"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Caviste",
    icon=str(ROOT / "packaging" / "caviste.ico"),
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Caviste", upx=False)
