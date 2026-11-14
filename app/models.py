"""Modèle de données.

Principe central : le rayon (shelf) est la variable de contrôle. Il est
certifié par un comptage à chaque passation, et toute vente le décrémente.
L'écart entre le rayon attendu et le rayon compté appartient à la session
(donc à la caissière) qui vient de se terminer.

Chaque enregistrement porte un UUID et un horodatage : prérequis pour la
synchronisation hors ligne du poste boutique vers le serveur central.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


def new_id() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    role: Mapped[str] = mapped_column(String(20))  # proprietaire | caissiere
    pin_hash: Mapped[str] = mapped_column(String(200))
    color: Mapped[str] = mapped_column(String(10), default="#7c3aed")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    sessions: Mapped[list["CashSession"]] = relationship(back_populates="user", foreign_keys="CashSession.user_id")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    aliases: Mapped[str] = mapped_column(Text, default="")  # séparés par des virgules
    category: Mapped[str] = mapped_column(String(60), default="Divers")
    size: Mapped[str] = mapped_column(String(30), default="")
    purchase_price: Mapped[float] = mapped_column(Float, default=0)
    sale_price: Mapped[float] = mapped_column(Float, default=0)
    abc_class: Mapped[str] = mapped_column(String(1), default="C")  # A | B | C
    shelf_qty: Mapped[int] = mapped_column(Integer, default=0)  # rayon, certifié par comptage
    reserve_qty: Mapped[int] = mapped_column(Integer, default=0)  # réserve fermée (proprio)
    shelf_min: Mapped[int] = mapped_column(Integer, default=2)  # seuil de réapprovisionnement rayon
    units_per_case: Mapped[int] = mapped_column(Integer, default=1)  # bouteilles par carton
    case_price: Mapped[float | None] = mapped_column(Float, nullable=True)  # prix du carton entier, sinon prix unitaire x unités
    sold_by_case: Mapped[bool] = mapped_column(Boolean, default=False)  # le carton se vend-il entier ?
    allow_half: Mapped[bool] = mapped_column(Boolean, default=False)  # demi-carton autorisé
    allow_quarter: Mapped[bool] = mapped_column(Boolean, default=False)  # quart de carton autorisé
    pack_size: Mapped[int | None] = mapped_column(Integer, nullable=True)  # pack (ex. 6 canettes), vendu tel quel
    pack_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    defective_qty: Mapped[int] = mapped_column(Integer, default=0)  # unités défectueuses rendues, à réclamer au fournisseur
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class CashSession(Base):
    """Session de caisse : une caissière, un créneau, un rayon certifié au début et à la fin."""

    __tablename__ = "cash_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="ouverte")  # ouverte | cloture_en_cours | fermee
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    opening_cash: Mapped[float] = mapped_column(Float, default=0)
    closing_cash: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_cash: Mapped[float | None] = mapped_column(Float, nullable=True)
    cash_gap: Mapped[float | None] = mapped_column(Float, nullable=True)
    sales_total: Mapped[float] = mapped_column(Float, default=0)
    sales_cash: Mapped[float] = mapped_column(Float, default=0)
    sales_mobile: Mapped[float] = mapped_column(Float, default=0)
    sales_count: Mapped[int] = mapped_column(Integer, default=0)
    refunds_cash: Mapped[float] = mapped_column(Float, default=0)  # remboursements rendus en espèces
    refunds_mobile: Mapped[float] = mapped_column(Float, default=0)
    overrun_minutes: Mapped[int] = mapped_column(Integer, default=0)  # minutes au-delà de la fin de vague ou de la fermeture
    missing_value: Mapped[float] = mapped_column(Float, default=0)  # valeur des manquants au rayon
    surplus_value: Mapped[float] = mapped_column(Float, default=0)
    closing_count_id: Mapped[str | None] = mapped_column(ForeignKey("stock_counts.id"), nullable=True)
    validated_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")

    user: Mapped[User] = relationship(back_populates="sessions", foreign_keys=[user_id])
    validated_by: Mapped[User | None] = relationship(foreign_keys=[validated_by_id])
    closing_count: Mapped["StockCount | None"] = relationship(foreign_keys=[closing_count_id])
    sales: Mapped[list["Sale"]] = relationship(back_populates="session")


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    number: Mapped[int] = mapped_column(Integer, index=True)  # numéro de ticket continu
    session_id: Mapped[str] = mapped_column(ForeignKey("cash_sessions.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    total: Mapped[float] = mapped_column(Float, default=0)
    payment_method: Mapped[str] = mapped_column(String(20), default="especes")  # especes | mobile | mixte
    paid_cash: Mapped[float] = mapped_column(Float, default=0)  # part de la marchandise réglée en espèces
    paid_mobile: Mapped[float] = mapped_column(Float, default=0)  # part réglée par Mobile Money (hors frais)
    momo_fee: Mapped[float] = mapped_column(Float, default=0)  # frais de retrait refacturés au client
    amount_due: Mapped[float] = mapped_column(Float, default=0)  # total + frais : ce que le client paie
    status: Mapped[str] = mapped_column(String(20), default="valide")  # valide | annulee
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cancel_reason: Mapped[str] = mapped_column(Text, default="")
    # Ventes notées à la main pendant une coupure, ressaisies ensuite (created_at = heure notée).
    source: Mapped[str] = mapped_column(String(10), default="caisse")  # caisse | cahier
    paper_ref: Mapped[str] = mapped_column(String(80), default="")  # page / ligne du cahier
    entered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    entered_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verified_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    session: Mapped[CashSession] = relationship(back_populates="sales")
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    lines: Mapped[list["SaleLine"]] = relationship(back_populates="sale", cascade="all, delete-orphan")


class SaleLine(Base):
    __tablename__ = "sale_lines"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    sale_id: Mapped[str] = mapped_column(ForeignKey("sales.id"))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    product_name: Mapped[str] = mapped_column(String(160))  # figé au moment de la vente
    qty: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    total: Mapped[float] = mapped_column(Float)
    stock_warning: Mapped[bool] = mapped_column(Boolean, default=False)  # vendu alors que rayon à 0
    pack: Mapped[str] = mapped_column(String(10), default="unite")  # unite | quart | demi | carton
    packs: Mapped[int] = mapped_column(Integer, default=1)  # nombre de conditionnements vendus

    sale: Mapped[Sale] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()


class StockMovement(Base):
    """Journal de tous les mouvements. Ajout seulement, jamais de modification."""

    __tablename__ = "stock_movements"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    # achat | transfert | vente | annulation | ajustement | perte
    kind: Mapped[str] = mapped_column(String(20))
    shelf_delta: Mapped[int] = mapped_column(Integer, default=0)
    reserve_delta: Mapped[int] = mapped_column(Integer, default=0)
    shelf_after: Mapped[int] = mapped_column(Integer, default=0)
    reserve_after: Mapped[int] = mapped_column(Integer, default=0)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("cash_sessions.id"), nullable=True)
    reference: Mapped[str] = mapped_column(String(80), default="")  # id vente, id comptage...
    note: Mapped[str] = mapped_column(Text, default="")
    unit_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    product: Mapped[Product] = relationship()
    user: Mapped[User | None] = relationship()


class StockCount(Base):
    """Comptage du rayon : passation (liste ABC), inventaire complet, ou contrôle ponctuel."""

    __tablename__ = "stock_counts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    kind: Mapped[str] = mapped_column(String(20))  # passation | inventaire | controle
    status: Mapped[str] = mapped_column(String(20), default="en_cours")  # en_cours | termine
    session_id: Mapped[str | None] = mapped_column(ForeignKey("cash_sessions.id"), nullable=True)
    performed_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    validated_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    missing_value: Mapped[float] = mapped_column(Float, default=0)
    surplus_value: Mapped[float] = mapped_column(Float, default=0)
    lines_total: Mapped[int] = mapped_column(Integer, default=0)
    lines_with_gap: Mapped[int] = mapped_column(Integer, default=0)

    performed_by: Mapped[User] = relationship(foreign_keys=[performed_by_id])
    validated_by: Mapped[User | None] = relationship(foreign_keys=[validated_by_id])
    lines: Mapped[list["StockCountLine"]] = relationship(back_populates="count", cascade="all, delete-orphan")


class StockCountLine(Base):
    __tablename__ = "stock_count_lines"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    count_id: Mapped[str] = mapped_column(ForeignKey("stock_counts.id"))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    product_name: Mapped[str] = mapped_column(String(160))
    reason: Mapped[str] = mapped_column(String(20), default="A")  # A | vendu | aleatoire | inventaire
    expected_qty: Mapped[int] = mapped_column(Integer)
    counted_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gap_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    gap_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    count: Mapped[StockCount] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()


class Return(Base):
    """Retour client : échange d'un produit défectueux ou remboursement."""

    __tablename__ = "returns"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("cash_sessions.id"), nullable=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    sale_id: Mapped[str | None] = mapped_column(ForeignKey("sales.id"), nullable=True)
    sale_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    product_name: Mapped[str] = mapped_column(String(160))
    qty: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20))  # echange | remboursement
    condition: Mapped[str] = mapped_column(String(20), default="defectueux")  # defectueux | revendable
    refund_amount: Mapped[float] = mapped_column(Float, default=0)
    refund_method: Mapped[str] = mapped_column(String(20), default="especes")  # especes | mobile
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    user: Mapped[User] = relationship()
    product: Mapped[Product] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    entity: Mapped[str] = mapped_column(String(40), default="")
    entity_id: Mapped[str] = mapped_column(String(32), default="")
    details: Mapped[str] = mapped_column(Text, default="")
    out_of_hours: Mapped[bool] = mapped_column(Boolean, default=False)  # action en dehors des horaires du magasin
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    user: Mapped[User | None] = relationship()


class Setting(Base):
    """Réglages du magasin définis par le propriétaire (horaires, taux Mobile Money)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[str] = mapped_column(String(200))
