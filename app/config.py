"""Configuration de l'application.

Tout se règle par variables d'environnement, avec des valeurs par défaut
pensées pour la démo locale :
- DATABASE_URL : sqlite par défaut (poste boutique), PostgreSQL pour le central.
- CAVISTE_SECRET : clé de signature des jetons de connexion.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

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
SECRET_KEY: str = os.environ.get("CAVISTE_SECRET", "demo-caviste-change-me")
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
