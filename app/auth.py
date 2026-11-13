"""Connexion par PIN et jetons signés (HMAC), sans dépendance externe."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .config import SECRET_KEY, TOKEN_TTL_SECONDS
from .database import get_db
from .models import User

_ITERATIONS = 120_000


def hash_pin(pin: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, _ITERATIONS)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_pin(pin: str, stored: str) -> bool:
    try:
        salt_b64, digest_b64 = stored.split("$", 1)
    except ValueError:
        return False
    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(digest_b64)
    actual = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, _ITERATIONS)
    return hmac.compare_digest(actual, expected)


def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token(user_id: str) -> str:
    payload = f"{user_id}:{int(time.time()) + TOKEN_TTL_SECONDS}"
    return f"{payload}:{_sign(payload)}"


def parse_token(token: str) -> str | None:
    try:
        user_id, exp, sig = token.rsplit(":", 2)
    except ValueError:
        return None
    payload = f"{user_id}:{exp}"
    if not hmac.compare_digest(_sign(payload), sig):
        return None
    if int(exp) < time.time():
        return None
    return user_id


def current_user(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Connexion requise")
    user_id = parse_token(authorization.split(" ", 1)[1].strip())
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expirée, reconnectez-vous")
    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utilisateur inconnu ou désactivé")
    return user


def owner_only(user: User = Depends(current_user)) -> User:
    if user.role != "proprietaire":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé au propriétaire")
    return user


def check_user_pin(db: Session, user_id: str, pin: str) -> User:
    """Vérifie le PIN d'un utilisateur donné (validation d'une passation, annulation...)."""
    user = db.get(User, user_id)
    if not user or not user.active or not verify_pin(pin, user.pin_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "PIN incorrect")
    return user
