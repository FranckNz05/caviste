"""Règles métier : stock, sessions, ventes, comptages, classement ABC, rapports."""
from __future__ import annotations

import json
import random
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .config import ABC_A_SHARE, ABC_B_SHARE, ABC_MIN_PRICE_A, HANDOVER_RANDOM_SAMPLE, SHOP_NAME
from .models import (
    AuditLog,
    CashSession,
    Product,
    Return,
    Sale,
    SaleLine,
    Setting,
    StockCount,
    StockCountLine,
    StockMovement,
    User,
    now,
)


def normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


DEFAULT_SETTINGS = {"shop_name": SHOP_NAME, "opening_time": "08:00", "shift_change_time": "15:00", "closing_time": "21:00", "momo_fee_rate": "0.035"}
LATE_TOLERANCE_MIN = 15


def get_settings(db: Session) -> dict:
    values = dict(DEFAULT_SETTINGS)
    for row in db.scalars(select(Setting)):
        values[row.key] = row.value
    return {
        "shop_name": values["shop_name"],
        "opening_time": values["opening_time"],
        "shift_change_time": values["shift_change_time"],
        "closing_time": values["closing_time"],
        "momo_fee_rate": float(values["momo_fee_rate"]),
    }


def _hm_minutes(hm: str) -> int:
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


def _minutes_of(at: datetime) -> int:
    return at.hour * 60 + at.minute


def wave_of(session: CashSession, settings: dict) -> tuple[int, str]:
    """(numéro de vague, heure de fin de vague) pour une session, d'après son heure d'ouverture."""
    if _minutes_of(session.opened_at) < _hm_minutes(settings["shift_change_time"]):
        return 1, settings["shift_change_time"]
    return 2, settings["closing_time"]


def record_overrun(db: Session, user: User, session: CashSession, kind: str, at: datetime | None = None) -> int:
    """La caissière prolonge sa vague (clients encore présents). Le patron en est informé."""
    settings = get_settings(db)
    wave, end = wave_of(session, settings)
    minutes = max(_minutes_of(at or now()) - _hm_minutes(end), 0)
    action = "vague_prolongee" if wave == 1 else "fermeture_prolongee"
    audit(db, user, action, "session", session.id, {"caissiere": session.user.name, "minutes": minutes, "fin_prevue": end}, at=at)
    return minutes


def set_settings(db: Session, user: User, values: dict) -> dict:
    for key, value in values.items():
        row = db.get(Setting, key)
        if row:
            row.value = str(value)
        else:
            db.add(Setting(key=key, value=str(value)))
    audit(db, user, "reglages_modifies", details=values)
    return get_settings(db)


def is_out_of_hours(db: Session, at: datetime | None = None) -> bool:
    """Vrai si l'instant est en dehors des horaires d'ouverture définis par le propriétaire."""
    settings = get_settings(db)
    t = (at or now()).strftime("%H:%M")
    return not (settings["opening_time"] <= t <= settings["closing_time"])


def audit(db: Session, user: User | None, action: str, entity: str = "", entity_id: str = "", details: dict | str = "", at: datetime | None = None) -> None:
    if isinstance(details, dict):
        details = json.dumps(details, ensure_ascii=False, default=str)
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=details,
            out_of_hours=is_out_of_hours(db, at),
            created_at=at or now(),
        )
    )


# Conditionnements : ce que le propriétaire a autorisé sur la fiche produit.
PACK_FRACTIONS = {"quart": 0.25, "demi": 0.5, "carton": 1.0}
PACK_LABELS = {"unite": "unité", "quart": "quart de carton", "demi": "demi-carton", "carton": "carton", "pack": "pack"}


def pack_options(product: Product) -> list[dict]:
    """Conditionnements vendables pour ce produit, avec unités et prix."""
    opts = [{"id": "unite", "label": "Unité", "units": 1, "price": product.sale_price}]
    upc = product.units_per_case or 1
    if product.sold_by_case and upc > 1:
        case = product.case_price if product.case_price else product.sale_price * upc
        if product.allow_quarter and upc % 4 == 0:
            opts.append({"id": "quart", "label": "¼ carton", "units": upc // 4, "price": round(case * 0.25)})
        if product.allow_half and upc % 2 == 0:
            opts.append({"id": "demi", "label": "½ carton", "units": upc // 2, "price": round(case * 0.5)})
        opts.append({"id": "carton", "label": "Carton", "units": upc, "price": round(case)})
    if product.pack_size and product.pack_size > 1:
        opts.append({"id": "pack", "label": f"Pack de {product.pack_size}", "units": product.pack_size, "price": round(product.pack_price if product.pack_price else product.sale_price * product.pack_size)})
    return opts


def _pack_option(product: Product, pack: str) -> dict:
    for o in pack_options(product):
        if o["id"] == pack:
            return o
    raise HTTPException(400, f"{product.name} ne se vend pas en {PACK_LABELS.get(pack, pack)}")


def pack_units(product: Product, pack: str) -> int:
    return _pack_option(product, pack)["units"]


def pack_price(product: Product, pack: str) -> float:
    return _pack_option(product, pack)["price"]


# --- Stock -------------------------------------------------------------------------
def apply_movement(
    db: Session,
    product: Product,
    kind: str,
    *,
    shelf_delta: int = 0,
    reserve_delta: int = 0,
    user: User | None = None,
    session_id: str | None = None,
    reference: str = "",
    note: str = "",
    unit_cost: float | None = None,
    at: datetime | None = None,
) -> StockMovement:
    product.shelf_qty += shelf_delta
    product.reserve_qty += reserve_delta
    movement = StockMovement(
        product_id=product.id,
        kind=kind,
        shelf_delta=shelf_delta,
        reserve_delta=reserve_delta,
        shelf_after=product.shelf_qty,
        reserve_after=product.reserve_qty,
        user_id=user.id if user else None,
        session_id=session_id,
        reference=reference,
        note=note,
        unit_cost=unit_cost,
        created_at=at or now(),
    )
    db.add(movement)
    return movement


def receive_stock(db: Session, user: User, product: Product, qty: int, unit_cost: float | None, note: str, at: datetime | None = None) -> StockMovement:
    if unit_cost is not None and unit_cost > 0:
        product.purchase_price = unit_cost
    m = apply_movement(db, product, "achat", reserve_delta=qty, user=user, note=note, unit_cost=unit_cost, at=at)
    audit(db, user, "achat", "product", product.id, {"qty": qty, "unit_cost": unit_cost})
    return m


def transfer_stock(db: Session, user: User, product: Product, qty: int, note: str, at: datetime | None = None) -> StockMovement:
    if qty == 0:
        raise HTTPException(400, "Quantité nulle")
    if qty > 0 and product.reserve_qty < qty:
        raise HTTPException(400, f"Réserve insuffisante ({product.reserve_qty} disponibles)")
    if qty < 0 and product.shelf_qty < -qty:
        raise HTTPException(400, f"Rayon insuffisant ({product.shelf_qty} disponibles)")
    m = apply_movement(db, product, "transfert", shelf_delta=qty, reserve_delta=-qty, user=user, note=note, at=at)
    audit(db, user, "transfert", "product", product.id, {"qty": qty})
    return m


def record_loss(db: Session, user: User, product: Product, qty: int, location: str, note: str) -> StockMovement:
    if location == "rayon":
        m = apply_movement(db, product, "perte", shelf_delta=-qty, user=user, note=note)
    else:
        m = apply_movement(db, product, "perte", reserve_delta=-qty, user=user, note=note)
    audit(db, user, "perte", "product", product.id, {"qty": qty, "location": location, "note": note})
    return m


def adjust_stock(db: Session, user: User, product: Product, shelf_qty: int | None, reserve_qty: int | None, note: str) -> StockMovement:
    shelf_delta = (shelf_qty - product.shelf_qty) if shelf_qty is not None else 0
    reserve_delta = (reserve_qty - product.reserve_qty) if reserve_qty is not None else 0
    m = apply_movement(db, product, "ajustement", shelf_delta=shelf_delta, reserve_delta=reserve_delta, user=user, note=note or "Ajustement manuel")
    audit(db, user, "ajustement", "product", product.id, {"shelf_delta": shelf_delta, "reserve_delta": reserve_delta, "note": note})
    return m


# --- Sessions ----------------------------------------------------------------------
def get_open_session(db: Session) -> CashSession | None:
    return db.scalars(
        select(CashSession)
        .where(CashSession.status.in_(["ouverte", "cloture_en_cours"]))
        .order_by(CashSession.opened_at.desc())
    ).first()


def open_session(db: Session, user: User, opening_cash: float, at: datetime | None = None) -> CashSession:
    current = get_open_session(db)
    if current:
        raise HTTPException(409, f"Une session est déjà ouverte au nom de {current.user.name}. Faites d'abord la passation.")
    session = CashSession(user_id=user.id, opening_cash=opening_cash, opened_at=at or now())
    db.add(session)
    db.flush()
    audit(db, user, "session_ouverte", "session", session.id, {"opening_cash": opening_cash}, at=at)
    # Prise de poste en retard sur la seconde vague : signalée au patron.
    settings = get_settings(db)
    opened = session.opened_at
    change = _hm_minutes(settings["shift_change_time"])
    if _minutes_of(opened) >= change:
        day_start = opened.replace(hour=0, minute=0, second=0, microsecond=0)
        prev_wave1 = db.scalar(
            select(func.count(CashSession.id)).where(CashSession.opened_at >= day_start, CashSession.opened_at < opened)
        )
        late = _minutes_of(opened) - change
        if prev_wave1 and late > LATE_TOLERANCE_MIN and not any(
            _minutes_of(s.opened_at) >= change
            for s in db.scalars(select(CashSession).where(CashSession.opened_at >= day_start, CashSession.opened_at < opened))
        ):
            audit(db, user, "retard_prise_de_poste", "session", session.id, {"caissiere": user.name, "minutes": late, "prevu": settings["shift_change_time"]}, at=at)
    return session


def next_sale_number(db: Session) -> int:
    return (db.scalar(select(func.max(Sale.number))) or 0) + 1


def create_sale(db: Session, user: User, lines_in, payment_method: str, at: datetime | None = None, mobile_part: float | None = None) -> Sale:
    session = get_open_session(db)
    if not session or session.user_id != user.id:
        raise HTTPException(409, "Ouvrez votre session de caisse avant de vendre")
    settings = get_settings(db)
    if session.status != "ouverte":
        raise HTTPException(409, "Clôture en cours : terminez la passation")
    sale = Sale(
        number=next_sale_number(db),
        session_id=session.id,
        user_id=user.id,
        payment_method=payment_method,
        created_at=at or now(),
    )
    total = 0.0
    for li in lines_in:
        product = db.get(Product, li.product_id)
        if not product or not product.active:
            raise HTTPException(400, "Produit inconnu")
        pack = getattr(li, "pack", "unite") or "unite"
        units = pack_units(product, pack) * li.qty
        line_total = pack_price(product, pack) * li.qty
        sale.lines.append(
            SaleLine(
                product_id=product.id,
                product_name=product.name,
                qty=units,
                unit_price=round(line_total / units, 2),
                total=line_total,
                stock_warning=product.shelf_qty < units,
                pack=pack,
                packs=li.qty,
            )
        )
        total += line_total
        apply_movement(db, product, "vente", shelf_delta=-units, user=user, session_id=session.id, reference=sale.id, at=at)
    sale.total = total
    # Répartition du règlement : espèces, Mobile Money, ou les deux.
    if payment_method == "mobile":
        sale.paid_mobile, sale.paid_cash = total, 0.0
    elif payment_method == "mixte":
        if mobile_part is None or mobile_part <= 0 or mobile_part >= total:
            raise HTTPException(400, "Règlement mixte : indiquez la part Mobile Money, entre 0 et le total")
        sale.paid_mobile, sale.paid_cash = float(mobile_part), total - float(mobile_part)
    else:
        sale.paid_mobile, sale.paid_cash = 0.0, total
    sale.momo_fee = round(sale.paid_mobile * settings["momo_fee_rate"]) if sale.paid_mobile else 0.0
    sale.amount_due = total + sale.momo_fee
    if is_out_of_hours(db, at):
        articles = ", ".join(
            f"{l.packs} {PACK_LABELS.get(l.pack, l.pack)} {l.product_name}" if l.pack != "unite" else f"{l.qty}× {l.product_name}"
            for l in sale.lines
        )
        paiement = {"especes": "espèces", "mobile": "Mobile Money", "mixte": f"mixte (MoMo {sale.paid_mobile:.0f}, espèces {sale.paid_cash:.0f})"}[payment_method]
        audit(db, user, "vente_hors_horaires", "sale", sale.id, {"ticket": sale.number, "total": total, "articles": articles, "paiement": paiement}, at=at)
    session.sales_total += total
    session.sales_count += 1
    session.sales_cash += sale.paid_cash
    session.sales_mobile += sale.paid_mobile
    db.add(sale)
    db.flush()
    return sale


def cancel_sale(db: Session, sale: Sale, actor: User, reason: str, at: datetime | None = None) -> Sale:
    """Annulation permise à la personne en poste ; consignée pour le propriétaire, sans mention côté caissière."""
    if sale.status == "annulee":
        raise HTTPException(400, "Vente déjà annulée")
    owner = actor
    sale.status = "annulee"
    sale.cancelled_at = at or now()
    sale.cancelled_by_id = owner.id
    sale.cancel_reason = reason
    for line in sale.lines:
        apply_movement(db, line.product, "annulation", shelf_delta=line.qty, user=owner, session_id=sale.session_id, reference=sale.id, note=reason, at=at)
    session = sale.session
    session.sales_total -= sale.total
    session.sales_count -= 1
    session.sales_cash -= sale.paid_cash
    session.sales_mobile -= sale.paid_mobile
    articles = ", ".join(f"{l.qty}× {l.product_name}" for l in sale.lines)
    audit(db, owner, "vente_annulee", "sale", sale.id, {"ticket": sale.number, "total": sale.total, "articles": articles, "motif": reason, "caissiere": sale.user.name, "par": owner.name}, at=at)
    return sale


# --- Retours clients --------------------------------------------------------------------
def create_return(db: Session, user: User, product: Product, qty: int, kind: str, condition: str, refund_method: str, sale_number: int | None, reason: str, at: datetime | None = None) -> Return:
    """Échange d'un produit défectueux (la bouteille rendue part en défectueux, une neuve sort du rayon)
    ou remboursement (le produit revient en rayon s'il est revendable, sinon en défectueux ; l'argent sort de la caisse)."""
    session = get_open_session(db)
    if user.role != "proprietaire" and (not session or session.user_id != user.id):
        raise HTTPException(409, "Ouvrez votre session de caisse avant un retour")
    sale = None
    unit_price = product.sale_price
    if sale_number is not None:
        sale = db.scalar(select(Sale).where(Sale.number == sale_number))
        if not sale:
            raise HTTPException(404, f"Ticket N° {sale_number} introuvable")
        line = next((l for l in sale.lines if l.product_id == product.id), None)
        if not line:
            raise HTTPException(400, f"Le ticket N° {sale_number} ne contient pas {product.name}")
        unit_price = line.unit_price
    ret = Return(
        session_id=session.id if session else None,
        user_id=user.id,
        sale_id=sale.id if sale else None,
        sale_number=sale.number if sale else None,
        product_id=product.id,
        product_name=product.name,
        qty=qty,
        kind=kind,
        condition="defectueux" if kind == "echange" else condition,
        refund_method=refund_method,
        reason=reason,
        created_at=at or now(),
    )
    if kind == "echange":
        if product.shelf_qty < qty:
            raise HTTPException(400, f"Rayon insuffisant pour remettre {qty} {product.name}")
        apply_movement(db, product, "echange", shelf_delta=-qty, user=user, session_id=ret.session_id, reference=ret.id, note=f"Échange produit défectueux : {reason}", at=at)
        product.defective_qty += qty
        apply_movement(db, product, "retour_defectueux", user=user, session_id=ret.session_id, reference=ret.id, note="Rendu par le client, à réclamer au fournisseur", at=at)
        ret.refund_amount = 0.0
    else:
        ret.refund_amount = round(unit_price * qty)
        if ret.condition == "revendable":
            apply_movement(db, product, "retour", shelf_delta=qty, user=user, session_id=ret.session_id, reference=ret.id, note=f"Retour client remboursé : {reason}", at=at)
        else:
            product.defective_qty += qty
            apply_movement(db, product, "retour_defectueux", user=user, session_id=ret.session_id, reference=ret.id, note=f"Retour défectueux remboursé : {reason}", at=at)
        if session:
            if refund_method == "especes":
                session.refunds_cash += ret.refund_amount
            else:
                session.refunds_mobile += ret.refund_amount
    db.add(ret)
    db.flush()
    audit(db, user, "retour_client", "return", ret.id, {"produit": product.name, "qty": qty, "kind": kind, "condition": ret.condition, "rembourse": ret.refund_amount, "ticket": sale_number, "motif": reason}, at=at)
    return ret


def clear_defective(db: Session, user: User, product: Product, qty: int, note: str) -> Product:
    if qty > product.defective_qty:
        raise HTTPException(400, f"Seulement {product.defective_qty} unité(s) défectueuse(s) enregistrée(s)")
    product.defective_qty -= qty
    apply_movement(db, product, "reclamation", user=user, note=note or "Réclamé au fournisseur")
    audit(db, user, "defectueux_reclame", "product", product.id, {"qty": qty, "note": note})
    return product


# --- Comptages ------------------------------------------------------------------------
def _build_count(db: Session, kind: str, session_id: str | None, user: User, items: list[tuple[Product, str]], at: datetime | None) -> StockCount:
    count = StockCount(kind=kind, session_id=session_id, performed_by_id=user.id, started_at=at or now())
    items.sort(key=lambda it: (it[0].category, normalize(it[0].name)))
    for product, reason in items:
        count.lines.append(
            StockCountLine(
                product_id=product.id,
                product_name=product.name,
                reason=reason,
                expected_qty=product.shelf_qty,
                unit_price=product.sale_price,
            )
        )
    count.lines_total = len(items)
    db.add(count)
    db.flush()
    return count


def prepare_handover_count(db: Session, session: CashSession, user: User, at: datetime | None = None) -> StockCount:
    if session.status == "cloture_en_cours" and session.closing_count_id:
        return db.get(StockCount, session.closing_count_id)
    products = list(db.scalars(select(Product).where(Product.active.is_(True))))
    sold_ids = set(
        db.scalars(
            select(SaleLine.product_id).join(Sale).where(Sale.session_id == session.id, Sale.status == "valide")
        )
    )
    chosen: dict[str, tuple[Product, str]] = {}
    for p in products:
        if p.abc_class == "A":
            chosen[p.id] = (p, "A")
    for p in products:
        if p.id in sold_ids and p.id not in chosen:
            chosen[p.id] = (p, "vendu")
    rest = [p for p in products if p.id not in chosen]
    for p in random.sample(rest, min(HANDOVER_RANDOM_SAMPLE, len(rest))):
        chosen[p.id] = (p, "aleatoire")
    count = _build_count(db, "passation", session.id, user, list(chosen.values()), at)
    session.status = "cloture_en_cours"
    session.closing_count_id = count.id
    audit(db, user, "comptage_prepare", "count", count.id, {"kind": "passation", "lines": count.lines_total})
    return count


def prepare_inventory(db: Session, user: User, at: datetime | None = None) -> StockCount:
    products = list(db.scalars(select(Product).where(Product.active.is_(True))))
    open_session = get_open_session(db)
    count = _build_count(db, "inventaire", open_session.id if open_session else None, user, [(p, "inventaire") for p in products], at)
    audit(db, user, "comptage_prepare", "count", count.id, {"kind": "inventaire", "lines": count.lines_total})
    return count


def submit_count(db: Session, count: StockCount, counted: dict[str, int | None], user: User, at: datetime | None = None) -> StockCount:
    if count.status == "termine":
        raise HTTPException(400, "Comptage déjà terminé")
    missing = surplus = 0.0
    with_gap = 0
    for line in count.lines:
        value = counted.get(line.product_id)
        if value is None:
            continue
        line.counted_qty = value
        line.gap_qty = value - line.expected_qty
        line.gap_value = line.gap_qty * line.unit_price
        if line.gap_qty != 0:
            with_gap += 1
            if line.gap_qty < 0:
                missing += -line.gap_value
            else:
                surplus += line.gap_value
            apply_movement(
                db,
                line.product,
                "ajustement",
                shelf_delta=line.gap_qty,
                user=user,
                session_id=count.session_id,
                reference=count.id,
                note=f"Comptage {count.kind}",
                at=at,
            )
    count.status = "termine"
    count.completed_at = at or now()
    count.missing_value = missing
    count.surplus_value = surplus
    count.lines_with_gap = with_gap
    audit(db, user, "comptage_termine", "count", count.id, {"missing": missing, "surplus": surplus, "with_gap": with_gap})
    return count


def close_session(
    db: Session,
    session: CashSession,
    closing_cash: float,
    validator: User,
    notes: str = "",
    force: bool = False,
    at: datetime | None = None,
) -> CashSession:
    if session.status == "fermee":
        raise HTTPException(400, "Session déjà fermée")
    count = db.get(StockCount, session.closing_count_id) if session.closing_count_id else None
    if not force and (not count or count.status != "termine"):
        raise HTTPException(400, "Le comptage du rayon doit être terminé avant la clôture")
    if count and count.status == "termine":
        count.validated_by_id = validator.id
        session.missing_value = count.missing_value
        session.surplus_value = count.surplus_value
    session.closing_cash = closing_cash
    session.expected_cash = session.opening_cash + session.sales_cash - session.refunds_cash
    session.cash_gap = closing_cash - session.expected_cash
    session.status = "fermee"
    session.closed_at = at or now()
    session.validated_by_id = validator.id
    session.notes = notes
    # Clôture au-delà de la fin de vague ou de la fermeture : retard consigné.
    settings = get_settings(db)
    wave, end = wave_of(session, settings)
    late = _minutes_of(session.closed_at) - _hm_minutes(end)
    if late > LATE_TOLERANCE_MIN and session.user.role != "proprietaire":
        session.overrun_minutes = late
        audit(
            db,
            session.user,
            "retard_passation" if wave == 1 else "retard_fermeture",
            "session",
            session.id,
            {"caissiere": session.user.name, "minutes": late, "fin_prevue": end},
            at=at,
        )
    audit(
        db,
        validator,
        "session_fermee" if not force else "session_forcee",
        "session",
        session.id,
        {"caissiere": session.user.name, "cash_gap": session.cash_gap, "missing_value": session.missing_value},
    )
    return session


# --- ABC ------------------------------------------------------------------------------
def recompute_abc(db: Session, days: int = 90) -> dict[str, int]:
    since = now() - timedelta(days=days)
    revenue = dict(
        db.execute(
            select(SaleLine.product_id, func.sum(SaleLine.total))
            .join(Sale)
            .where(Sale.status == "valide", Sale.created_at >= since)
            .group_by(SaleLine.product_id)
        ).all()
    )
    products = list(db.scalars(select(Product).where(Product.active.is_(True))))
    scored = sorted(products, key=lambda p: (revenue.get(p.id, 0.0) + p.sale_price), reverse=True)
    total = sum(revenue.get(p.id, 0.0) + p.sale_price for p in scored) or 1.0
    cumulative = 0.0
    counts = {"A": 0, "B": 0, "C": 0}
    for i, p in enumerate(scored):
        cumulative += revenue.get(p.id, 0.0) + p.sale_price
        share = cumulative / total
        if (share <= ABC_A_SHARE or i < 5) and p.sale_price >= ABC_MIN_PRICE_A:
            p.abc_class = "A"
        elif share <= ABC_B_SHARE:
            p.abc_class = "B"
        else:
            p.abc_class = "C"
        counts[p.abc_class] += 1
    return counts


# --- Rapports ---------------------------------------------------------------------------
def _hours(a: datetime, b: datetime | None) -> float:
    return max(((b or now()) - a).total_seconds() / 3600.0, 0.25)


def dashboard(db: Session) -> dict:
    today = now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now() - timedelta(days=7)
    open_s = get_open_session(db)
    today_sales = db.execute(
        select(func.coalesce(func.sum(Sale.total), 0.0), func.count(Sale.id)).where(Sale.status == "valide", Sale.created_at >= today)
    ).one()
    recent = list(
        db.scalars(
            select(CashSession)
            .options(selectinload(CashSession.user))
            .where(CashSession.status == "fermee")
            .order_by(CashSession.closed_at.desc())
            .limit(6)
        )
    )
    week_missing = db.scalar(
        select(func.coalesce(func.sum(CashSession.missing_value), 0.0)).where(CashSession.status == "fermee", CashSession.closed_at >= week_ago)
    )
    week_inventory_missing = db.scalar(
        select(func.coalesce(func.sum(StockCount.missing_value), 0.0)).where(
            StockCount.kind == "inventaire", StockCount.status == "termine", StockCount.completed_at >= week_ago
        )
    )
    low = list(
        db.scalars(select(Product).where(Product.active.is_(True), Product.shelf_qty <= Product.shelf_min).order_by(Product.shelf_qty))
    )
    # Ventes par jour sur 7 jours (aujourd'hui inclus) pour le mini-graphique.
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    daily = {d.date(): 0.0 for d in days}
    for created_at, total in db.execute(
        select(Sale.created_at, Sale.total).where(Sale.status == "valide", Sale.created_at >= days[0])
    ).all():
        key = created_at.date()
        if key in daily:
            daily[key] += total
    daily_sales = [{"day": d.strftime("%a"), "date": d.date().isoformat(), "total": daily[d.date()]} for d in days]
    recent_full = [s for s in sessions_report(db, 30) if s["status"] == "fermee"][:6]
    flagged = list(
        db.scalars(
            select(AuditLog)
            .options(selectinload(AuditLog.user))
            .where(AuditLog.created_at >= week_ago)
            .where((AuditLog.out_of_hours.is_(True)) | (AuditLog.action.in_(["vente_annulee", "session_forcee", "retard_passation", "retard_fermeture", "retard_prise_de_poste", "vague_prolongee", "fermeture_prolongee"])))
            .order_by(AuditLog.created_at.desc())
        )
    )
    returns_7d = db.scalar(select(func.count(Return.id)).where(Return.created_at >= week_ago)) or 0
    defective = [
        {"id": p.id, "name": p.name, "defective_qty": p.defective_qty}
        for p in db.scalars(select(Product).where(Product.defective_qty > 0).order_by(Product.defective_qty.desc()))
    ]
    flags = {
        "returns_7d": returns_7d,
        "defective": defective,
        "cancellations_7d": sum(1 for a in flagged if a.action == "vente_annulee"),
        "delays_7d": sum(1 for a in flagged if a.action.startswith("retard_") or a.action.endswith("_prolongee")),
        "out_of_hours_7d": sum(1 for a in flagged if a.out_of_hours),
        "recent": [
            {"id": a.id, "user_name": a.user.name if a.user else "", "action": a.action, "details": a.details, "out_of_hours": a.out_of_hours, "created_at": a.created_at}
            for a in flagged[:8]
        ],
    }
    return {
        "flags": flags,
        "open_session": _session_dict(open_s) if open_s else None,
        "today_sales_total": today_sales[0],
        "today_sales_count": today_sales[1],
        "week_missing_value": week_missing,
        "week_inventory_missing_value": week_inventory_missing,
        "daily_sales": daily_sales,
        "recent_sessions": recent_full,
        "low_shelf": [
            {"id": p.id, "name": p.name, "shelf_qty": p.shelf_qty, "reserve_qty": p.reserve_qty, "shelf_min": p.shelf_min}
            for p in low[:15]
        ],
    }


def _session_dict(s: CashSession) -> dict:
    return {
        "id": s.id,
        "user_id": s.user_id,
        "user_name": s.user.name,
        "user_color": s.user.color,
        "status": s.status,
        "opened_at": s.opened_at,
        "closed_at": s.closed_at,
        "hours": round(_hours(s.opened_at, s.closed_at), 1),
        "opening_cash": s.opening_cash,
        "closing_cash": s.closing_cash,
        "expected_cash": s.expected_cash,
        "cash_gap": s.cash_gap,
        "sales_total": s.sales_total,
        "sales_cash": s.sales_cash,
        "sales_mobile": s.sales_mobile,
        "sales_count": s.sales_count,
        "missing_value": s.missing_value,
        "surplus_value": s.surplus_value,
        "closing_count_id": s.closing_count_id,
        "validated_by_name": s.validated_by.name if s.validated_by else None,
        "notes": s.notes,
    }


def sessions_report(db: Session, days: int = 30) -> list[dict]:
    since = now() - timedelta(days=days)
    sessions = list(
        db.scalars(
            select(CashSession)
            .options(selectinload(CashSession.user), selectinload(CashSession.validated_by))
            .where(CashSession.opened_at >= since)
            .order_by(CashSession.opened_at.desc())
        )
    )
    count_ids = [s.closing_count_id for s in sessions if s.closing_count_id]
    missing_lines: dict[str, list[dict]] = defaultdict(list)
    if count_ids:
        for line in db.scalars(
            select(StockCountLine).where(StockCountLine.count_id.in_(count_ids), StockCountLine.gap_qty.is_not(None), StockCountLine.gap_qty != 0)
        ):
            missing_lines[line.count_id].append(
                {"product_name": line.product_name, "gap_qty": line.gap_qty, "gap_value": line.gap_value, "reason": line.reason}
            )
    out = []
    for s in sessions:
        d = _session_dict(s)
        d["gap_lines"] = sorted(missing_lines.get(s.closing_count_id or "", []), key=lambda x: x["gap_value"] or 0)
        out.append(d)
    return out


def cashiers_report(db: Session, days: int = 30) -> dict:
    since = now() - timedelta(days=days)
    users = list(db.scalars(select(User).where(User.active.is_(True)).order_by(User.role, User.name)))
    sessions = list(
        db.scalars(select(CashSession).where(CashSession.opened_at >= since, CashSession.status == "fermee"))
    )
    by_user: dict[str, dict] = {
        u.id: {
            "user_id": u.id,
            "name": u.name,
            "role": u.role,
            "color": u.color,
            "sessions": 0,
            "hours": 0.0,
            "sales_total": 0.0,
            "sales_count": 0,
            "cash_gap_total": 0.0,
            "cash_gap_sessions": 0,
            "missing_value": 0.0,
            "surplus_value": 0.0,
            "sessions_with_missing": 0,
            "under_sold": [],
        }
        for u in users
    }
    for s in sessions:
        row = by_user.get(s.user_id)
        if not row:
            continue
        row["sessions"] += 1
        row["hours"] += _hours(s.opened_at, s.closed_at)
        row["sales_total"] += s.sales_total
        row["sales_count"] += s.sales_count
        row["cash_gap_total"] += s.cash_gap or 0.0
        if abs(s.cash_gap or 0.0) >= 1:
            row["cash_gap_sessions"] += 1
        row["missing_value"] += s.missing_value
        row["surplus_value"] += s.surplus_value
        if s.missing_value > 0:
            row["sessions_with_missing"] += 1

    # Vitesse de vente par produit A et par personne : qty vendue par heure de session.
    session_ids = [s.id for s in sessions]
    qty_by_user_product: dict[tuple[str, str], int] = defaultdict(int)
    product_names: dict[str, str] = {}
    if session_ids:
        rows = db.execute(
            select(Sale.user_id, SaleLine.product_id, SaleLine.product_name, func.sum(SaleLine.qty))
            .join(SaleLine, SaleLine.sale_id == Sale.id)
            .join(Product, Product.id == SaleLine.product_id)
            .where(Sale.session_id.in_(session_ids), Sale.status == "valide", Product.abc_class == "A")
            .group_by(Sale.user_id, SaleLine.product_id, SaleLine.product_name)
        ).all()
        for user_id, product_id, product_name, qty in rows:
            qty_by_user_product[(user_id, product_id)] = int(qty)
            product_names[product_id] = product_name
    total_hours = sum(r["hours"] for r in by_user.values()) or 1.0
    for uid, row in by_user.items():
        if row["hours"] < 4:
            continue
        others_hours = total_hours - row["hours"]
        if others_hours < 4:
            continue
        signals = []
        for pid, pname in product_names.items():
            mine = qty_by_user_product.get((uid, pid), 0)
            others = sum(q for (u, p), q in qty_by_user_product.items() if p == pid and u != uid)
            mine_rate = mine / row["hours"]
            others_rate = others / others_hours
            if others >= 4 and others_rate > 0 and mine_rate < 0.5 * others_rate:
                signals.append(
                    {
                        "product_name": pname,
                        "mine_per_hour": round(mine_rate, 2),
                        "others_per_hour": round(others_rate, 2),
                        "ratio": round(mine_rate / others_rate, 2) if others_rate else None,
                    }
                )
        signals.sort(key=lambda s: s["ratio"] or 0)
        row["under_sold"] = signals[:5]

    flagged_rows = db.execute(
        select(AuditLog.user_id, AuditLog.action, AuditLog.out_of_hours).where(AuditLog.created_at >= since, AuditLog.user_id.is_not(None))
    ).all()
    for uid, action, out_of_hours in flagged_rows:
        row = by_user.get(uid)
        if not row:
            continue
        row.setdefault("cancellations", 0)
        row.setdefault("out_of_hours", 0)
        row.setdefault("delays", 0)
        if action == "vente_annulee":
            row["cancellations"] += 1
        if out_of_hours:
            row["out_of_hours"] += 1
        if action.startswith("retard_"):
            row["delays"] += 1
    for row in by_user.values():
        row.setdefault("cancellations", 0)
        row.setdefault("out_of_hours", 0)
        row.setdefault("delays", 0)
        row["hours"] = round(row["hours"], 1)
        row["sales_per_hour"] = round(row["sales_total"] / row["hours"], 0) if row["hours"] else 0
        row["missing_pct"] = round(100 * row["missing_value"] / row["sales_total"], 2) if row["sales_total"] else 0
        if row["sessions"] == 0:
            row["level"] = "aucune"
        elif row["missing_pct"] >= 2 or (row["sessions"] >= 3 and row["sessions_with_missing"] / row["sessions"] >= 0.5):
            row["level"] = "alerte"
        elif row["missing_pct"] >= 0.5 or (row["sessions"] >= 3 and row["sessions_with_missing"] / row["sessions"] >= 0.3):
            row["level"] = "attention"
        else:
            row["level"] = "ok"
    return {"days": days, "cashiers": list(by_user.values())}


def products_report(db: Session, days: int = 30) -> list[dict]:
    since = now() - timedelta(days=days)
    rows = db.execute(
        select(StockCountLine, StockCount, CashSession, User)
        .join(StockCount, StockCount.id == StockCountLine.count_id)
        .outerjoin(CashSession, CashSession.id == StockCount.session_id)
        .outerjoin(User, User.id == CashSession.user_id)
        .where(StockCount.status == "termine", StockCount.completed_at >= since, StockCountLine.gap_qty.is_not(None), StockCountLine.gap_qty != 0)
    ).all()
    agg: dict[str, dict] = {}
    for line, count, session, user in rows:
        entry = agg.setdefault(
            line.product_id,
            {"product_id": line.product_id, "product_name": line.product_name, "missing_qty": 0, "missing_value": 0.0, "surplus_qty": 0, "by_person": defaultdict(int), "unattributed_qty": 0},
        )
        if line.gap_qty < 0:
            entry["missing_qty"] += -line.gap_qty
            entry["missing_value"] += -(line.gap_value or 0)
            if count.kind == "passation" and user:
                entry["by_person"][user.name] += -line.gap_qty
            else:
                entry["unattributed_qty"] += -line.gap_qty
        else:
            entry["surplus_qty"] += line.gap_qty
    out = []
    for e in agg.values():
        if e["missing_qty"] <= 0:
            continue
        e["by_person"] = dict(e["by_person"])
        out.append(e)
    out.sort(key=lambda e: e["missing_value"], reverse=True)
    return out
