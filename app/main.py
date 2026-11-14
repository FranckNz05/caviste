from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401  (enregistre les tables)
from . import sync
from .config import BASE_DIR, DEMO, MODE, SHOP_NAME
from .database import Base, SessionLocal, engine, ensure_columns
from .routers import router
from .seed import ensure_demo, ensure_minimal

STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    if MODE == "miroir":
        # Le miroir ne contient que ce que le poste de la boutique envoie : aucune donnée de démo.
        # Tant que le poste n'a rien envoyé, un compte Patron (code 0000) permet d'entrer ;
        # le premier envoi complet du poste le remplace par les vrais comptes.
        sync.make_constraints_deferrable()
        Base.metadata.create_all(engine)
        ensure_columns()
        with SessionLocal() as db:
            ensure_minimal(db)
    else:
        if MODE == "poste":
            sync.install_capture()
        Base.metadata.create_all(engine)
        ensure_columns()
        with SessionLocal() as db:
            ensure_demo(db) if DEMO else ensure_minimal(db)
        if MODE == "poste":
            sync.worker.start()
    yield
    if MODE == "poste":
        sync.worker.stop()


app = FastAPI(title=f"Caviste - {SHOP_NAME}", lifespan=lifespan)

# Miroir : consultation seule. Seuls la connexion du patron et l'envoi du poste écrivent.
_MIRROR_WRITABLE = {"/api/auth/login", "/api/sync/push"}


@app.middleware("http")
async def mirror_read_only(request: Request, call_next):
    if (
        MODE == "miroir"
        and request.method not in ("GET", "HEAD", "OPTIONS")
        and request.url.path.startswith("/api/")
        and request.url.path not in _MIRROR_WRITABLE
    ):
        return JSONResponse(
            {"detail": "Consultation seule : les modifications se font sur le poste de la boutique."},
            status_code=403,
        )
    return await call_next(request)


app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    # Toujours revalider la page : les scripts et styles portent un numéro de version.
    return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})
