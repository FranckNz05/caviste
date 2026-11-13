from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Utilisateurs / connexion -------------------------------------------------
class UserOut(ORM):
    id: str
    name: str
    role: str
    color: str
    active: bool


class UserIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    pin: str = Field(min_length=4, max_length=8, pattern=r"^\d+$")
    role: str = Field(pattern=r"^(proprietaire|caissiere)$")
    color: str = "#7c3aed"


class UserUpdate(BaseModel):
    name: str | None = None
    pin: str | None = Field(default=None, min_length=4, max_length=8, pattern=r"^\d+$")
    role: str | None = Field(default=None, pattern=r"^(proprietaire|caissiere)$")
    color: str | None = None
    active: bool | None = None


class LoginIn(BaseModel):
    user_id: str
    pin: str


class LoginOut(BaseModel):
    token: str
    user: UserOut


# --- Produits ------------------------------------------------------------------
class ProductOut(ORM):
    id: str
    name: str
    aliases: str
    category: str
    size: str
    purchase_price: float
    sale_price: float
    abc_class: str
    shelf_qty: int
    reserve_qty: int
    shelf_min: int
    units_per_case: int
    case_price: float | None
    sold_by_case: bool
    allow_half: bool
    allow_quarter: bool
    pack_size: int | None
    pack_price: float | None
    defective_qty: int
    active: bool


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    aliases: str = ""
    category: str = "Divers"
    size: str = ""
    purchase_price: float = 0
    sale_price: float = Field(ge=0)
    abc_class: str | None = Field(default=None, pattern=r"^[ABC]$")
    shelf_qty: int = 0
    reserve_qty: int = 0
    shelf_min: int = 2
    units_per_case: int = Field(default=1, ge=1)
    case_price: float | None = None
    sold_by_case: bool = False
    allow_half: bool = False
    allow_quarter: bool = False
    pack_size: int | None = Field(default=None, ge=2)
    pack_price: float | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    aliases: str | None = None
    category: str | None = None
    size: str | None = None
    purchase_price: float | None = None
    sale_price: float | None = None
    abc_class: str | None = Field(default=None, pattern=r"^[ABC]$")
    shelf_min: int | None = None
    units_per_case: int | None = Field(default=None, ge=1)
    case_price: float | None = None
    clear_case_price: bool = False
    sold_by_case: bool | None = None
    allow_half: bool | None = None
    allow_quarter: bool | None = None
    pack_size: int | None = Field(default=None, ge=2)
    pack_price: float | None = None
    clear_pack: bool = False
    active: bool | None = None


# --- Stock ----------------------------------------------------------------------
class ReceiveIn(BaseModel):
    product_id: str
    qty: int = Field(gt=0)
    unit_cost: float | None = None
    note: str = ""


class TransferIn(BaseModel):
    """Réserve vers rayon (qty > 0) ou rayon vers réserve (qty < 0)."""

    product_id: str
    qty: int
    note: str = ""


class LossIn(BaseModel):
    product_id: str
    qty: int = Field(gt=0)
    location: str = Field(pattern=r"^(rayon|reserve)$")
    note: str = ""


class AdjustIn(BaseModel):
    product_id: str
    shelf_qty: int | None = None
    reserve_qty: int | None = None
    note: str = ""


class MovementOut(ORM):
    id: str
    product_id: str
    product_name: str = ""
    kind: str
    shelf_delta: int
    reserve_delta: int
    shelf_after: int
    reserve_after: int
    user_name: str = ""
    reference: str
    note: str
    created_at: datetime


# --- Sessions de caisse ----------------------------------------------------------
class SessionOpenIn(BaseModel):
    opening_cash: float = Field(ge=0)


class SessionOut(ORM):
    id: str
    user_id: str
    user_name: str = ""
    status: str
    opened_at: datetime
    closed_at: datetime | None
    opening_cash: float
    closing_cash: float | None
    expected_cash: float | None
    cash_gap: float | None
    sales_total: float
    sales_cash: float
    sales_mobile: float
    sales_count: int
    refunds_cash: float
    refunds_mobile: float
    overrun_minutes: int
    missing_value: float
    surplus_value: float
    closing_count_id: str | None
    validated_by_name: str | None = None
    notes: str


class SessionCloseIn(BaseModel):
    closing_cash: float = Field(ge=0)
    validator_id: str
    validator_pin: str
    notes: str = ""
    force: bool = False  # propriétaire seulement : clôture sans comptage


# --- Ventes ---------------------------------------------------------------------
class SaleLineIn(BaseModel):
    product_id: str
    qty: int = Field(gt=0)  # nombre de conditionnements (unités, quarts, demis ou cartons)
    pack: str = Field(default="unite", pattern=r"^(unite|quart|demi|carton|pack)$")


class SaleIn(BaseModel):
    lines: list[SaleLineIn] = Field(min_length=1)
    payment_method: str = Field(default="especes", pattern=r"^(especes|mobile|mixte)$")
    mobile_part: float | None = Field(default=None, ge=0)  # règlement mixte : part de la marchandise payée par Mobile Money


class SaleLineOut(ORM):
    product_id: str
    product_name: str
    qty: int
    unit_price: float
    total: float
    stock_warning: bool
    pack: str
    packs: int


class SaleOut(ORM):
    id: str
    number: int
    session_id: str
    user_id: str
    user_name: str = ""
    created_at: datetime
    total: float
    payment_method: str
    paid_cash: float
    paid_mobile: float
    momo_fee: float
    amount_due: float
    status: str
    cancel_reason: str
    lines: list[SaleLineOut]


class SaleCancelIn(BaseModel):
    reason: str = Field(min_length=3)


class ReturnIn(BaseModel):
    product_id: str
    qty: int = Field(gt=0)
    kind: str = Field(pattern=r"^(echange|remboursement)$")
    condition: str = Field(default="defectueux", pattern=r"^(defectueux|revendable)$")
    refund_method: str = Field(default="especes", pattern=r"^(especes|mobile)$")
    sale_number: int | None = None
    reason: str = ""


class ReturnOut(ORM):
    id: str
    user_name: str = ""
    sale_number: int | None
    product_id: str
    product_name: str
    qty: int
    kind: str
    condition: str
    refund_amount: float
    refund_method: str
    reason: str
    created_at: datetime


class DefectiveClearIn(BaseModel):
    product_id: str
    qty: int = Field(gt=0)
    note: str = ""


class SettingsOut(BaseModel):
    shop_name: str
    opening_time: str
    shift_change_time: str
    closing_time: str
    momo_fee_rate: float


class SettingsIn(BaseModel):
    shop_name: str = Field(min_length=1, max_length=60)
    opening_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    shift_change_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    closing_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    momo_fee_rate: float = Field(ge=0, le=0.5)


class OverrunIn(BaseModel):
    kind: str = Field(pattern=r"^(vague|fermeture)$")


# --- Comptages -------------------------------------------------------------------
class CountLineOut(ORM):
    product_id: str
    product_name: str
    reason: str
    category: str = ""
    size: str = ""
    expected_qty: int | None  # masqué tant que le comptage n'est pas terminé (comptage à l'aveugle)
    counted_qty: int | None
    gap_qty: int | None
    unit_price: float
    gap_value: float | None


class CountOut(ORM):
    id: str
    kind: str
    status: str
    session_id: str | None
    performed_by_name: str = ""
    validated_by_name: str | None = None
    started_at: datetime
    completed_at: datetime | None
    missing_value: float
    surplus_value: float
    lines_total: int
    lines_with_gap: int
    lines: list[CountLineOut]


class CountLineIn(BaseModel):
    product_id: str
    counted_qty: int | None = Field(default=None, ge=0)


class CountSubmitIn(BaseModel):
    lines: list[CountLineIn]
