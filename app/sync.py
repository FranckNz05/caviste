"""Synchronisation du poste boutique vers le serveur web du patron.

Principe : le poste de la boutique est la référence. Il fonctionne entièrement
hors ligne (SQLite local). Chaque écriture en base est notée dans une file
d'attente (sync_outbox). Un fil de fond tente régulièrement d'envoyer cette
file au serveur web ; dès que la connexion revient, tout ce qui a été fait
hors ligne part d'un coup. Le serveur web (mode miroir) recopie les lignes
telles quelles, par identifiant : l'envoi peut être répété sans risque.

Côté serveur (mode miroir) : POST /api/sync/push, protégé par CAVISTE_SYNC_KEY.
Le premier envoi d'un poste est complet : le miroir est vidé puis rempli.
"""
from __future__ import annotations

import gzip
import json
import logging
import threading
import urllib.error
import urllib.request
import warnings
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    delete,
    event,
    func,
    insert,
    inspect,
    select,
    text,
)
from sqlalchemy.orm import Session

from .config import DATA_DIR
from .database import Base, SessionLocal, engine

log = logging.getLogger("caviste.sync")

# File d'attente locale, hors du schéma métier : elle n'est jamais envoyée ni créée sur le miroir.
local_meta = MetaData()
outbox = Table(
    "sync_outbox",
    local_meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("tbl", String(60), nullable=False),
    Column("pk", Text, nullable=False),  # valeurs de clé primaire, en JSON
    Column("at", DateTime, nullable=False),
)

STATE_FILE = DATA_DIR / "sync.json"
INTERVAL_IDLE = 10  # secondes entre deux vérifications quand tout va bien
INTERVAL_MAX = 30  # au plus 30 s d'attente quand le serveur est injoignable
BATCH_MAX = 5000  # lignes par envoi


def ordered_tables() -> list[Table]:
    """Tables métier, parents avant enfants (le cycle sessions/comptages est toléré)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return list(Base.metadata.sorted_tables)


def _table_rank() -> dict[str, int]:
    return {t.name: i for i, t in enumerate(ordered_tables())}


# --------------------------------------------------------------------------- état
_state_lock = threading.Lock()


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(**changes) -> dict:
    with _state_lock:
        state = load_state()
        state.update(changes)
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        return state


# ------------------------------------------------------------- capture des écritures
def _record_changes(session: Session, _flush_context) -> None:
    rows = []
    stamp = datetime.now().replace(microsecond=0)
    for obj in list(session.new) + list(session.dirty) + list(session.deleted):
        state = inspect(obj)
        table = getattr(state.mapper, "local_table", None)
        if table is None or table.metadata is not Base.metadata:
            continue
        if obj in session.dirty and not session.is_modified(obj, include_collections=False):
            continue
        pk = state.mapper.primary_key_from_instance(obj)
        if any(v is None for v in pk):
            continue
        rows.append({"tbl": table.name, "pk": json.dumps(pk), "at": stamp})
    if rows:
        session.connection().execute(insert(outbox), rows)


def install_capture() -> None:
    """Poste boutique : crée la file d'attente et branche la capture des écritures."""
    local_meta.create_all(engine)
    if not event.contains(Session, "after_flush", _record_changes):
        event.listen(Session, "after_flush", _record_changes)


# ----------------------------------------------------------------- sérialisation
def _encode(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _row_dict(row) -> dict:
    return {k: _encode(v) for k, v in row._mapping.items()}


def _pk_clause(table: Table, pk: list):
    return and_(*[col == val for col, val in zip(table.primary_key.columns, pk)])


def pending_count() -> int:
    with engine.connect() as conn:
        return conn.scalar(select(func.count()).select_from(outbox)) or 0


def _collect_pending(conn) -> tuple[int, list[dict]]:
    """Lit la file (au plus BATCH_MAX lignes distinctes) et renvoie l'état actuel de chaque ligne."""
    tables = Base.metadata.tables
    rank = _table_rank()
    entries = conn.execute(select(outbox.c.id, outbox.c.tbl, outbox.c.pk).order_by(outbox.c.id)).all()
    seen: dict[tuple[str, str], int] = {}
    upto = 0
    for oid, tbl, pk in entries:
        if (tbl, pk) not in seen and len(seen) >= BATCH_MAX:
            break
        seen.setdefault((tbl, pk), oid)
        upto = oid
    keys = sorted(seen, key=lambda k: (rank.get(k[0], 999), seen[k]))
    out = []
    for tbl, pk_json in keys:
        table = tables.get(tbl)
        if table is None:
            continue
        pk = json.loads(pk_json)
        row = conn.execute(select(table).where(_pk_clause(table, pk))).first()
        if row is None:
            out.append({"t": tbl, "op": "delete", "pk": pk})
        else:
            out.append({"t": tbl, "op": "upsert", "data": _row_dict(row)})
    return upto, out


def _collect_all(conn) -> list[dict]:
    out = []
    for table in ordered_tables():
        for row in conn.execute(select(table)):
            out.append({"t": table.name, "op": "upsert", "data": _row_dict(row)})
    return out


# -------------------------------------------------------------------- envoi (poste)
class SyncError(Exception):
    pass


def _post(url: str, key: str, payload: dict, timeout: int = 60) -> dict:
    body = gzip.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    req = urllib.request.Request(
        url.rstrip("/") + "/api/sync/push",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Content-Encoding": "gzip", "X-Sync-Key": key},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8")).get("detail", "")
        except Exception:  # noqa: BLE001
            detail = ""
        if e.code == 403:
            raise SyncError("Clé de synchronisation refusée par le serveur") from e
        raise SyncError(f"Le serveur a répondu {e.code}{' : ' + str(detail) if detail else ''}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ConnectionError("Serveur injoignable (pas de connexion ?)") from e


def sync_once() -> dict:
    """Un passage : envoi complet la première fois, puis la file d'attente. Renvoie le nombre de lignes."""
    state = load_state()
    url, key = (state.get("url") or "").strip(), (state.get("key") or "").strip()
    if not url or not key:
        return {"sent": 0, "skipped": "non configurée"}
    sent = 0
    if not state.get("full_done"):
        with engine.connect() as conn:
            upto = conn.scalar(select(func.max(outbox.c.id))) or 0
            rows = _collect_all(conn)
        _post(url, key, {"full": True, "rows": rows}, timeout=180)
        with engine.begin() as conn:
            conn.execute(delete(outbox).where(outbox.c.id <= upto))
        save_state(full_done=True)
        sent += len(rows)
    while True:
        with engine.connect() as conn:
            upto, rows = _collect_pending(conn)
        if not upto:
            break
        if rows:
            _post(url, key, {"full": False, "rows": rows})
            sent += len(rows)
        with engine.begin() as conn:
            conn.execute(delete(outbox).where(outbox.c.id <= upto))
    return {"sent": sent}


class SyncWorker:
    """Fil de fond du poste : réessaie sans cesse, avec une attente courte, tant que l'appli tourne."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self.online: bool | None = None
        self.running = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, name="caviste-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def trigger(self) -> None:
        self._wake.set()

    def run_now(self) -> dict:
        with self._lock:
            return self._attempt()

    def _attempt(self) -> dict:
        self.running = True
        save_state(last_attempt=datetime.now().isoformat(timespec="seconds"))
        try:
            result = sync_once()
            if "skipped" not in result:
                self.online = True
                save_state(last_ok=datetime.now().isoformat(timespec="seconds"), last_error="")
            return result
        except ConnectionError as e:
            self.online = False
            save_state(last_error=str(e))
            raise
        except SyncError as e:
            self.online = True
            save_state(last_error=str(e))
            raise
        except Exception as e:  # noqa: BLE001
            log.exception("Synchronisation")
            save_state(last_error=f"Erreur inattendue : {e}")
            raise SyncError(str(e)) from e
        finally:
            self.running = False

    def _loop(self) -> None:
        wait = INTERVAL_IDLE
        while not self._stop.is_set():
            state = load_state()
            needed = state.get("url") and state.get("key") and (not state.get("full_done") or pending_count() > 0)
            if needed:
                try:
                    with self._lock:
                        self._attempt()
                    wait = INTERVAL_IDLE
                except (ConnectionError, SyncError):
                    wait = min(wait * 2, INTERVAL_MAX)
            self._wake.wait(wait)
            self._wake.clear()


worker = SyncWorker()


def status() -> dict:
    state = load_state()
    return {
        "url": state.get("url", ""),
        "has_key": bool(state.get("key")),
        "configured": bool(state.get("url") and state.get("key")),
        "full_done": bool(state.get("full_done")),
        "pending": pending_count(),
        "online": worker.online,
        "running": worker.running,
        "last_ok": state.get("last_ok"),
        "last_attempt": state.get("last_attempt"),
        "last_error": state.get("last_error", ""),
    }


def configure(url: str, key: str | None) -> dict:
    state = load_state()
    url = url.strip().rstrip("/")
    changes: dict = {"url": url}
    if key:
        changes["key"] = key.strip()
    if url != state.get("url") or (key and key.strip() != state.get("key")):
        # Nouveau serveur ou nouvelle clé : on renvoie tout.
        changes.update(full_done=False, last_error="")
    save_state(**changes)
    worker.trigger()
    return status()


# ---------------------------------------------------------------- réception (miroir)
def make_constraints_deferrable() -> None:
    """Miroir : les clés étrangères ne sont vérifiées qu'à la fin de chaque envoi."""
    for table in Base.metadata.tables.values():
        for fk in table.foreign_key_constraints:
            fk.deferrable = True
            fk.initially = "DEFERRED"


def reset_mirror() -> None:
    """Vide entièrement le miroir et recrée le schéma (premier envoi d'un poste)."""
    tables = list(reversed(ordered_tables()))
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            for t in tables:
                conn.execute(text(f'DROP TABLE IF EXISTS "{t.name}" CASCADE'))
    else:
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
            for t in tables:
                conn.exec_driver_sql(f'DROP TABLE IF EXISTS "{t.name}"')
            conn.commit()
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)


def _decode_row(table: Table, data: dict) -> dict:
    out = {}
    for col in table.columns:
        if col.name not in data:
            continue
        v = data[col.name]
        if v is not None and isinstance(col.type, DateTime) and isinstance(v, str):
            v = datetime.fromisoformat(v)
        out[col.name] = v
    return out


def _upsert_stmt(table: Table):
    if engine.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    else:
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    stmt = dialect_insert(table)
    pk_names = [c.name for c in table.primary_key.columns]
    updates = {c.name: stmt.excluded[c.name] for c in table.columns if c.name not in pk_names}
    if not updates:
        return stmt.on_conflict_do_nothing(index_elements=pk_names)
    return stmt.on_conflict_do_update(index_elements=pk_names, set_=updates)


def apply_push(payload: dict) -> dict:
    tables = Base.metadata.tables
    rows = payload.get("rows") or []
    if payload.get("full"):
        reset_mirror()
    upserts: dict[str, list[dict]] = {}
    deletes: list[tuple[Table, list]] = []
    for r in rows:
        table = tables.get(r.get("t"))
        if table is None:
            continue
        if r.get("op") == "delete":
            deletes.append((table, r.get("pk") or []))
        else:
            upserts.setdefault(table.name, []).append(_decode_row(table, r.get("data") or {}))
    with engine.begin() as conn:
        for table in ordered_tables():
            batch = upserts.get(table.name)
            if batch:
                conn.execute(_upsert_stmt(table), batch)
        for table, pk in deletes:
            conn.execute(delete(table).where(_pk_clause(table, pk)))
    with SessionLocal() as db:
        from .models import Setting

        stamp = datetime.now().isoformat(timespec="seconds")
        row = db.get(Setting, "sync_last_push")
        if row:
            row.value = stamp
        else:
            db.add(Setting(key="sync_last_push", value=stamp))
        db.commit()
    return {"ok": True, "received": len(rows), "full": bool(payload.get("full"))}


def mirror_last_push(db: Session) -> str | None:
    from .models import Setting

    row = db.get(Setting, "sync_last_push")
    return row.value if row else None

