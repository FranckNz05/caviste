from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import services
from .auth import check_user_pin, create_token, current_user, hash_pin, owner_only, verify_pin
from .config import CURRENCY, HANDOVER_RANDOM_SAMPLE, SHOP_NAME
from .database import get_db
from .models import AuditLog, CashSession, Product, Return, Sale, StockCount, StockMovement, User
from .schemas import (
    AdjustIn,
    CountOut,
    CountSubmitIn,
    DefectiveClearIn,
    OverrunIn,
    ReturnIn,
    ReturnOut,
    LoginIn,
    LoginOut,
    LossIn,
    MovementOut,
    ProductIn,
    ProductOut,
    ProductUpdate,
    ReceiveIn,
    SaleCancelIn,
    SaleIn,
    SaleOut,
    SessionCloseIn,
    SessionOpenIn,
    SessionOut,
    SettingsIn,
    SettingsOut,
    TransferIn,
    UserIn,
    UserOut,
    UserUpdate,
)

router = APIRouter(prefix="/api")


# --- Divers ----------------------------------------------------------------------
@router.get("/config")
def get_config(db: Session = Depends(get_db)):
    return {"shop_name": services.get_settings(db)["shop_name"], "currency": CURRENCY, "handover_sample": HANDOVER_RANDOM_SAMPLE}


@router.get("/settings", response_model=SettingsOut)
def get_settings(_: User = Depends(current_user), db: Session = Depends(get_db)):
    return services.get_settings(db)


@router.put("/settings", response_model=SettingsOut)
def update_settings(data: SettingsIn, owner: User = Depends(owner_only), db: Session = Depends(get_db)):
    if not (data.opening_time < data.shift_change_time < data.closing_time):
        raise HTTPException(400, "Il faut : ouverture < changement de vague < fermeture")
    out = services.set_settings(db, owner, data.model_dump())
    db.commit()
    return out


# --- Connexion -------------------------------------------------------------------
@router.get("/users/login-list", response_model=list[UserOut])
def login_list(db: Session = Depends(get_db)):
    return list(db.scalars(select(User).where(User.active.is_(True)).order_by(User.role.desc(), User.name)))


@router.post("/auth/login", response_model=LoginOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.get(User, data.user_id)
    if not user or not user.active or not verify_pin(data.pin, user.pin_hash):
        raise HTTPException(401, "PIN incorrect")
    services.audit(db, user, "connexion")
    db.commit()
    return LoginOut(token=create_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


# --- Utilisateurs (propriétaire) ---------------------------------------------------
@router.get("/users", response_model=list[UserOut])
def list_users(_: User = Depends(owner_only), db: Session = Depends(get_db)):
    return list(db.scalars(select(User).order_by(User.role.desc(), User.name)))


@router.post("/users", response_model=UserOut)
def create_user(data: UserIn, owner: User = Depends(owner_only), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.name == data.name)):
        raise HTTPException(400, "Ce nom existe déjà")
    user = User(name=data.name, role=data.role, color=data.color, pin_hash=hash_pin(data.pin))
    db.add(user)
    db.flush()
    services.audit(db, owner, "utilisateur_cree", "user", user.id, {"name": user.name, "role": user.role})
    db.commit()
    return user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: str, data: UserUpdate, owner: User = Depends(owner_only), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    changes = data.model_dump(exclude_none=True)
    pin = changes.pop("pin", None)
    for k, v in changes.items():
        setattr(user, k, v)
    if pin:
        user.pin_hash = hash_pin(pin)
        changes["pin"] = "modifié"
    services.audit(db, owner, "utilisateur_modifie", "user", user.id, changes)
    db.commit()
    return user


# --- Produits ------------------------------------------------------------------------
@router.get("/products", response_model=list[ProductOut])
def list_products(include_inactive: bool = False, _: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Product).order_by(Product.category, Product.name)
    if not include_inactive:
        q = q.where(Product.active.is_(True))
    return list(db.scalars(q))


@router.post("/products", response_model=ProductOut)
def create_product(data: ProductIn, owner: User = Depends(owner_only), db: Session = Depends(get_db)):
    if db.scalar(select(Product).where(Product.name == data.name)):
        raise HTTPException(400, "Un produit porte déjà ce nom")
    payload = data.model_dump()
    shelf, reserve = payload.pop("shelf_qty"), payload.pop("reserve_qty")
    if payload["abc_class"] is None:
        payload["abc_class"] = "A" if data.sale_price >= 15000 else "C"
    product = Product(**payload)
    db.add(product)
    db.flush()
    if shelf or reserve:
        services.apply_movement(db, product, "ajustement", shelf_delta=shelf, reserve_delta=reserve, user=owner, note="Stock initial")
    services.audit(db, owner, "produit_cree", "product", product.id, {"name": product.name, "sale_price": product.sale_price})
    db.commit()
    return product


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: str, data: ProductUpdate, owner: User = Depends(owner_only), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Produit introuvable")
    changes = data.model_dump(exclude_none=True)
    clear_case_price = changes.pop("clear_case_price", False)
    clear_pack = changes.pop("clear_pack", False)
    for k, v in changes.items():
        setattr(product, k, v)
    if clear_case_price:
        product.case_price = None
        changes["case_price"] = None
    if clear_pack:
        product.pack_size = None
        product.pack_price = None
        changes["pack_size"] = None
    services.audit(db, owner, "produit_modifie", "product", product.id, changes)
    db.commit()
    return product


@router.post("/products/recompute-abc")
def recompute_abc(owner: User = Depends(owner_only), db: Session = Depends(get_db)):
    counts = services.recompute_abc(db)
    services.audit(db, owner, "abc_recalcule", details=counts)
    db.commit()
    return counts


# --- Stock ------------------------------------------------------------------------------
def _product_or_404(db: Session, product_id: str) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Produit introuvable")
    return product


@router.post("/stock/receive", response_model=ProductOut)
def receive(data: ReceiveIn, owner: User = Depends(owner_only), db: Session = Depends(get_db)):
    product = _product_or_404(db, data.product_id)
    services.receive_stock(db, owner, product, data.qty, data.unit_cost, data.note)
    db.commit()
    return product


@router.post("/stock/transfer", response_model=ProductOut)
def transfer(data: TransferIn, owner: User = Depends(owner_only), db: Session = Depends(get_db)):
    product = _product_or_404(db, data.product_id)
    services.transfer_stock(db, owner, product, data.qty, data.note)
    db.commit()
    return product


@router.post("/stock/loss", response_model=ProductOut)
def loss(data: LossIn, owner: User = Depends(owner_only), db: Session = Depends(get_db)):
    product = _product_or_404(db, data.product_id)
    services.record_loss(db, owner, product, data.qty, data.location, data.note)
    db.commit()
    return product


@router.post("/stock/adjust", response_model=ProductOut)
def adjust(data: AdjustIn, owner: User = Depends(owner_only), db: Session = Depends(get_db)):
    product = _product_or_404(db, data.product_id)
    services.adjust_stock(db, owner, product, data.shelf_qty, data.reserve_qty, data.note)
    db.commit()
    return product


@router.post("/stock/defective-clear", response_model=ProductOut)
def defective_clear(data: DefectiveClearIn, owner: User = Depends(owner_only), db: Session = Depends(get_db)):
    product = _product_or_404(db, data.product_id)
    services.clear_defective(db, owner, product, data.qty, data.note)
    db.commit()
    return product


@router.get("/stock/movements", response_model=list[MovementOut])
def movements(product_id: str | None = None, limit: int = Query(100, le=500), _: User = Depends(owner_only), db: Session = Depends(get_db)):
    q = select(StockMovement).options(selectinload(StockMovement.product), selectinload(StockMovement.user)).order_by(StockMovement.created_at.desc()).limit(limit)
    if product_id:
        q = q.where(StockMovement.product_id == product_id)
    out = []
    for m in db.scalars(q):
        d = MovementOut.model_validate(m)
        d.product_name = m.product.name
        d.user_name = m.user.name if m.user else ""
        out.append(d)
    return out


# --- Sessions -----------------------------------------------------------------------------
def _session_out(s: CashSession) -> SessionOut:
    d = SessionOut.model_validate(s)
    d.user_name = s.user.name
    d.validated_by_name = s.validated_by.name if s.validated_by else None
    return d


@router.get("/session/current")
def current_session(user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = services.get_open_session(db)
    last_closed = db.scalars(select(CashSession).where(CashSession.status == "fermee").order_by(CashSession.closed_at.desc())).first()
    return {
        "session": _session_out(s) if s else None,
        "is_mine": bool(s and s.user_id == user.id),
        "suggested_opening_cash": last_closed.opening_cash if last_closed else 0,  # fond de caisse habituel
    }


@router.post("/session/open", response_model=SessionOut)
def open_session(data: SessionOpenIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = services.open_session(db, user, data.opening_cash)
    db.commit()
    db.refresh(s)
    return _session_out(s)


@router.post("/session/close/prepare", response_model=CountOut)
def prepare_close(user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = services.get_open_session(db)
    if not s:
        raise HTTPException(409, "Aucune session ouverte")
    if s.user_id != user.id and user.role != "proprietaire":
        raise HTTPException(403, "Seule la caissière en poste ou le propriétaire peut lancer la passation")
    count = services.prepare_handover_count(db, s, user)
    db.commit()
    return _count_out(db, db.get(StockCount, count.id))


@router.post("/session/close", response_model=SessionOut)
def close_session(data: SessionCloseIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = services.get_open_session(db)
    if not s:
        raise HTTPException(409, "Aucune session ouverte")
    validator = check_user_pin(db, data.validator_id, data.validator_pin)
    if data.closing:
        if validator.id != s.user_id and validator.role != "proprietaire":
            raise HTTPException(400, "La fermeture se confirme avec votre propre code")
    elif validator.id == s.user_id and validator.role != "proprietaire":
        raise HTTPException(400, "La passation doit être validée par une autre personne (caissière entrante ou propriétaire)")
    if data.force and user.role != "proprietaire":
        raise HTTPException(403, "Seul le propriétaire peut forcer une clôture")
    services.close_session(db, s, data.closing_cash, validator, data.notes, force=data.force, closing=data.closing)
    db.commit()
    db.refresh(s)
    return _session_out(s)


@router.post("/session/overrun")
def session_overrun(data: OverrunIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = services.get_open_session(db)
    if not s or s.user_id != user.id:
        raise HTTPException(409, "Aucune session ouverte à votre nom")
    minutes = services.record_overrun(db, user, s, data.kind)
    db.commit()
    return {"minutes": minutes}


@router.get("/session/{session_id}", response_model=SessionOut)
def get_session(session_id: str, _: User = Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(CashSession, session_id)
    if not s:
        raise HTTPException(404, "Session introuvable")
    return _session_out(s)


# --- Ventes ----------------------------------------------------------------------------------
def _sale_out(s: Sale) -> SaleOut:
    d = SaleOut.model_validate(s)
    d.user_name = s.user.name
    return d


@router.get("/sales", response_model=list[SaleOut])
def list_sales(session_id: str | None = None, limit: int = Query(50, le=500), user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Sale).options(selectinload(Sale.lines), selectinload(Sale.user)).order_by(Sale.created_at.desc()).limit(limit)
    if session_id:
        q = q.where(Sale.session_id == session_id)
    elif user.role != "proprietaire":
        current = services.get_open_session(db)
        if not current:
            return []
        q = q.where(Sale.session_id == current.id)
    return [_sale_out(s) for s in db.scalars(q)]


@router.get("/sales/by-number/{number}", response_model=SaleOut)
def sale_by_number(number: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    sale = db.scalar(select(Sale).options(selectinload(Sale.lines), selectinload(Sale.user)).where(Sale.number == number))
    if not sale:
        raise HTTPException(404, f"Ticket N° {number} introuvable")
    return _sale_out(sale)


@router.post("/sales", response_model=SaleOut)
def create_sale(data: SaleIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    sale = services.create_sale(db, user, data.lines, data.payment_method, mobile_part=data.mobile_part)
    db.commit()
    db.refresh(sale)
    return _sale_out(sale)


@router.post("/sales/{sale_id}/cancel", response_model=SaleOut)
def cancel_sale(sale_id: str, data: SaleCancelIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    sale = db.get(Sale, sale_id)
    if not sale:
        raise HTTPException(404, "Vente introuvable")
    if user.role != "proprietaire" and sale.user_id != user.id:
        raise HTTPException(403, "Vous ne pouvez annuler que vos propres ventes")
    services.cancel_sale(db, sale, user, data.reason)
    db.commit()
    db.refresh(sale)
    return _sale_out(sale)


# --- Retours ------------------------------------------------------------------------------------
def _return_out(r: Return) -> ReturnOut:
    d = ReturnOut.model_validate(r)
    d.user_name = r.user.name
    return d


@router.post("/returns", response_model=ReturnOut)
def create_return(data: ReturnIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    product = _product_or_404(db, data.product_id)
    ret = services.create_return(db, user, product, data.qty, data.kind, data.condition, data.refund_method, data.sale_number, data.reason)
    db.commit()
    db.refresh(ret)
    return _return_out(ret)


@router.get("/returns", response_model=list[ReturnOut])
def list_returns(limit: int = Query(100, le=500), user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Return).options(selectinload(Return.user)).order_by(Return.created_at.desc()).limit(limit)
    if user.role != "proprietaire":
        current = services.get_open_session(db)
        if not current:
            return []
        q = q.where(Return.session_id == current.id)
    return [_return_out(r) for r in db.scalars(q)]


# --- Comptages ---------------------------------------------------------------------------------
def _count_out(db: Session, count: StockCount) -> CountOut:
    d = CountOut.model_validate(count)
    d.performed_by_name = count.performed_by.name
    d.validated_by_name = count.validated_by.name if count.validated_by else None
    blind = count.status != "termine"
    for line, src in zip(d.lines, count.lines):
        line.category = src.product.category
        line.size = src.product.size
        if blind:
            line.expected_qty = None
    return d


@router.get("/counts", response_model=list[CountOut])
def list_counts(limit: int = Query(30, le=200), _: User = Depends(owner_only), db: Session = Depends(get_db)):
    counts = db.scalars(select(StockCount).order_by(StockCount.started_at.desc()).limit(limit))
    return [_count_out(db, c) for c in counts]


@router.get("/counts/{count_id}", response_model=CountOut)
def get_count(count_id: str, _: User = Depends(current_user), db: Session = Depends(get_db)):
    count = db.get(StockCount, count_id)
    if not count:
        raise HTTPException(404, "Comptage introuvable")
    return _count_out(db, count)


@router.post("/counts/{count_id}/submit", response_model=CountOut)
def submit_count(count_id: str, data: CountSubmitIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    count = db.get(StockCount, count_id)
    if not count:
        raise HTTPException(404, "Comptage introuvable")
    services.submit_count(db, count, {l.product_id: l.counted_qty for l in data.lines}, user)
    db.commit()
    db.refresh(count)
    return _count_out(db, count)


@router.post("/counts/inventory", response_model=CountOut)
def start_inventory(owner: User = Depends(owner_only), db: Session = Depends(get_db)):
    count = services.prepare_inventory(db, owner)
    db.commit()
    return _count_out(db, db.get(StockCount, count.id))


# --- Rapports -------------------------------------------------------------------------------------
@router.get("/reports/dashboard")
def report_dashboard(_: User = Depends(owner_only), db: Session = Depends(get_db)):
    return services.dashboard(db)


@router.get("/reports/sessions")
def report_sessions(days: int = Query(30, le=365), _: User = Depends(owner_only), db: Session = Depends(get_db)):
    return services.sessions_report(db, days)


@router.get("/reports/cashiers")
def report_cashiers(days: int = Query(30, le=365), _: User = Depends(owner_only), db: Session = Depends(get_db)):
    return services.cashiers_report(db, days)


@router.get("/reports/products")
def report_products(days: int = Query(30, le=365), _: User = Depends(owner_only), db: Session = Depends(get_db)):
    return services.products_report(db, days)


@router.get("/audit")
def audit_log(limit: int = Query(200, le=1000), filter: str | None = None, _: User = Depends(owner_only), db: Session = Depends(get_db)):
    q = select(AuditLog).options(selectinload(AuditLog.user)).order_by(AuditLog.created_at.desc()).limit(limit)
    if filter == "annulations":
        q = q.where(AuditLog.action.in_(["vente_annulee", "session_forcee"]))
    elif filter == "hors_horaires":
        q = q.where(AuditLog.out_of_hours.is_(True))
    elif filter == "retards":
        q = q.where(AuditLog.action.in_(["retard_passation", "retard_fermeture", "retard_prise_de_poste", "vague_prolongee", "fermeture_prolongee"]))
    elif filter == "retours":
        q = q.where(AuditLog.action.in_(["retour_client", "defectueux_reclame"]))
    elif filter == "modifications":
        q = q.where(AuditLog.action.in_(["produit_modifie", "ajustement", "utilisateur_modifie", "reglages_modifies", "perte"]))
    rows = db.scalars(q)
    return [
        {"id": a.id, "user_name": a.user.name if a.user else "", "action": a.action, "entity": a.entity, "entity_id": a.entity_id, "details": a.details, "out_of_hours": a.out_of_hours, "created_at": a.created_at}
        for a in rows
    ]
