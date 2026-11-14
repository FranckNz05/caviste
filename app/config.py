"""Configuration de l'application.

Tout se règle par variables d'environnement, avec des valeurs par défaut
pensées pour la démo locale :
- DATABASE_URL : sqlite par défaut (poste boutique), PostgreSQL pour le central.
- CAVISTE_SECRET : clé de signature des jetons de connexion.
- CAVISTE_MODE : web (démo, par défaut), poste (application de bureau hors ligne,
  synchronisée vers le web) ou miroir (serveur web du patron, en consultation,
  alimenté par le poste de la boutique).
- CAVISTE_DATA_DIR : dossier des données (base SQLite, réglages de synchro).
- CAVISTE_DEMO : 1 pour charger les données de démonstration dans une base vide.
- CAVISTE_SYNC_KEY : (miroir) clé que le poste doit présenter pour envoyer ses données.
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

# Une fois empaqueté (PyInstaller), les fichiers de l'application sont extraits dans _MEIPASS.
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
DATA_DIR = Path(os.environ.get("CAVISTE_DATA_DIR") or (BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

MODE: str = os.environ.get("CAVISTE_MODE", "web").strip().lower()
if MODE not in ("web", "poste", "miroir"):
    MODE = "web"
DEMO: bool = os.environ.get("CAVISTE_DEMO", "0" if MODE == "poste" else "1") == "1"
SYNC_KEY: str = os.environ.get("CAVISTE_SYNC_KEY", "")

def _normalize_db_url(url: str) -> str:
    """Render (et d'autres hébergeurs) fournissent une URL en postgres:// ;
    SQLAlchemy attend postgresql+psycopg://."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL: str = _normalize_db_url(
    os.environ.get("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'caviste.db').as_posix()}")
)
def _local_secret() -> str:
    """Poste de bureau : une clé propre à l'installation, créée au premier lancement."""
    path = DATA_DIR / "secret.key"
    if not path.exists():
        path.write_text(secrets.token_hex(32), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


SECRET_KEY: str = os.environ.get("CAVISTE_SECRET") or (_local_secret() if MODE == "poste" else "demo-caviste-change-me")
TOKEN_TTL_SECONDS: int = int(os.environ.get("CAVISTE_TOKEN_TTL", 12 * 3600))

SHOP_NAME: str = os.environ.get("CAVISTE_SHOP_NAME", "La Cave")
CURRENCY: str = os.environ.get("CAVISTE_CURRENCY", "FCFA")

# Comptage de passation : nombre de produits B/C tirés au sort en plus des A
# et des produits vendus pendant la session.
HANDOVER_RANDOM_SAMPLE: int = int(os.environ.get("CAVISTE_HANDOVER_SAMPLE", 5))

# Classement ABC automatique : part du chiffre d'affaires cumulée.
ABC_A_SHARE = 0.70
ABC_B_SHARE = 0.90
# En dessous de ce prix, un produit n'est jamais classé A (trop long à compter pour peu de valeur).
ABC_MIN_PRICE_A = float(os.environ.get("CAVISTE_ABC_MIN_PRICE_A", 3000))
