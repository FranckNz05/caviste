"""Données de démonstration : une cave, trois personnes, deux semaines d'activité.

Scénario volontairement parlant pour le client :
- Aline : honnête, quelques petites erreurs de caisse.
- Bénédicte : encaisse des bouteilles sans les enregistrer. Sa caisse est toujours juste,
  mais son rayon ne l'est pas. C'est exactement le cas que le client décrit.
- Le patron tient la boutique le mercredi et fait l'inventaire complet ce jour-là.
"""
from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import services
from .auth import hash_pin
from .models import Product, User
from .schemas import SaleLineIn

PRODUCTS = [
    # (nom, alias, catégorie, format, prix achat, prix vente, poids de vente)
    ("Johnnie Walker Red Label", "jw red, red label, johnny rouge", "Whisky", "75cl", 12500, 18000, 6),
    ("Johnnie Walker Black Label", "jw black, black label, johnny noir", "Whisky", "75cl", 25000, 35000, 4),
    ("Jack Daniel's Old No.7", "jack, jd", "Whisky", "70cl", 20000, 28000, 4),
    ("Chivas Regal 12 ans", "chivas", "Whisky", "70cl", 27000, 38000, 3),
    ("Jameson", "jameson irlandais", "Whisky", "70cl", 18000, 25000, 3),
    ("Ballantine's Finest", "ballantines", "Whisky", "70cl", 12000, 17000, 5),
    ("Glenfiddich 12 ans", "glen", "Whisky", "70cl", 33000, 45000, 1),
    ("Label 5", "label", "Whisky", "70cl", 8500, 12000, 6),
    ("William Lawson's", "william, lawson", "Whisky", "70cl", 8500, 12000, 6),
    ("Black & White", "black and white, b&w", "Whisky", "70cl", 8000, 11000, 4),
    ("J&B Rare", "jb, j and b", "Whisky", "70cl", 12000, 16000, 3),
    ("Hennessy VS", "hennessy, henessy", "Cognac", "70cl", 33000, 45000, 2),
    ("Rémy Martin VSOP", "remy martin, remy", "Cognac", "70cl", 48000, 65000, 1),
    ("Moët & Chandon Brut", "moet, moët", "Champagne", "75cl", 45000, 60000, 1),
    ("Veuve Clicquot Brut", "veuve, clicquot", "Champagne", "75cl", 56000, 75000, 1),
    ("Mumm Cordon Rouge", "mumm", "Champagne", "75cl", 40000, 55000, 1),
    ("Freixenet Cordon Negro", "freixenet, mousseux", "Champagne", "75cl", 8500, 12000, 3),
    ("Mouton Cadet Rouge", "mouton cadet, mouton", "Vin", "75cl", 8500, 12000, 3),
    ("Baron de Lestac Rouge", "lestac, baron", "Vin", "75cl", 6500, 9000, 4),
    ("Côtes du Rhône Cellier des Dauphins", "cotes du rhone, dauphins", "Vin", "75cl", 5500, 8000, 4),
    ("Casillero del Diablo Cabernet", "casillero, diablo", "Vin", "75cl", 7000, 10000, 3),
    ("JP Chenet Rouge", "jp chenet rouge, chenet", "Vin", "75cl", 4200, 6000, 6),
    ("JP Chenet Blanc", "jp chenet blanc, chenet blanc", "Vin", "75cl", 4200, 6000, 4),
    ("JP Chenet Rosé", "jp chenet rose, chenet rose", "Vin", "75cl", 4200, 6000, 4),
    ("Castel Rouge", "castel vin", "Vin", "75cl", 3500, 5000, 6),
    ("Bacardi Carta Blanca", "bacardi, rhum blanc", "Spiritueux", "70cl", 10500, 15000, 3),
    ("Captain Morgan Spiced", "captain, morgan", "Spiritueux", "70cl", 10500, 15000, 3),
    ("Smirnoff Vodka", "smirnoff, vodka", "Spiritueux", "70cl", 8500, 12000, 5),
    ("Absolut Vodka", "absolut", "Spiritueux", "70cl", 11500, 16000, 3),
    ("Gordon's Gin", "gordons, gin", "Spiritueux", "70cl", 10000, 14000, 3),
    ("Martini Rosso", "martini", "Spiritueux", "1L", 7000, 10000, 4),
    ("Baileys", "bailey", "Spiritueux", "70cl", 13000, 18000, 2),
    ("Ricard", "pastis", "Spiritueux", "1L", 11500, 16000, 2),
    ("Malibu", "malibu coco", "Spiritueux", "70cl", 9500, 13000, 3),
    ("Primus", "primus biere", "Bière", "65cl", 650, 1000, 14),
    ("Ngok", "ngok biere", "Bière", "65cl", 650, 1000, 14),
    ("Heineken", "heineken biere", "Bière", "33cl", 650, 1000, 12),
    ("Guinness", "guiness", "Bière", "33cl", 800, 1200, 8),
    ("Desperados", "despe", "Bière", "33cl", 1000, 1500, 8),
    ("Castel Beer", "castel biere", "Bière", "65cl", 650, 1000, 10),
    ("Red Bull", "redbull, energy", "Soft", "25cl", 1000, 1500, 8),
    ("Coca-Cola", "coca, cola", "Soft", "1.5L", 800, 1200, 10),
    ("Orangina", "orangina", "Soft", "33cl", 500, 800, 8),
    ("Jus Ceres", "ceres, jus", "Soft", "1L", 1400, 2000, 6),
    ("Eau Mayo", "eau, mayo", "Soft", "1.5L", 300, 500, 12),
]

USERS = [
    ("Patron", "proprietaire", "0000", "#0f766e"),
    ("Aline", "caissiere", "1111", "#7c3aed"),
    ("Bénédicte", "caissiere", "2222", "#db2777"),
]


def ensure_demo(db: Session) -> None:
    if db.scalar(select(User).limit(1)):
        return
    random.seed(20261113)
    users = {}
    for name, role, pin, color in USERS:
        u = User(name=name, role=role, pin_hash=hash_pin(pin), color=color)
        db.add(u)
        users[name] = u
    db.flush()
    owner, aline, bene = users["Patron"], users["Aline"], users["Bénédicte"]

    weights: dict[str, int] = {}
    products: list[Product] = []
    for name, aliases, category, size, pp, sp, weight in PRODUCTS:
        p = Product(
            name=name,
            aliases=aliases,
            category=category,
            size=size,
            purchase_price=pp,
            sale_price=sp,
            shelf_min=6 if category in ("Bière", "Soft") else 2,
        )
        if category == "Bière":
            p.units_per_case = 12 if size == "65cl" else 24
        elif category == "Soft":
            p.units_per_case = 6 if size == "1.5L" else (12 if size == "1L" else 24)
        else:
            p.units_per_case = 6
        if category in ("Bière", "Soft"):
            # Petit prix de gros sur le carton entier (environ 4 % de remise).
            p.case_price = round(p.units_per_case * sp * 0.96 / 100) * 100
        # Ce qui se vend par carton : bières, softs, vins et spiritueux courants ; pas le champagne.
        p.sold_by_case = category in ("Bière", "Soft", "Vin", "Spiritueux", "Whisky")
        p.allow_half = p.sold_by_case
        p.allow_quarter = p.sold_by_case and p.units_per_case % 4 == 0
        if category == "Bière" and size == "33cl":
            p.pack_size = 6
            p.pack_price = round(6 * sp * 0.98 / 100) * 100
        db.add(p)
        products.append(p)
        weights[name] = weight
    db.flush()

    start = (datetime.now() - timedelta(days=15)).replace(hour=8, minute=0, second=0, microsecond=0)

    # Approvisionnement initial en réserve, puis premier garnissage du rayon.
    for p in products:
        qty = 48 if p.category in ("Bière", "Soft") else random.randint(8, 18)
        services.receive_stock(db, owner, p, qty, p.purchase_price, "Stock initial", at=start)
    services.recompute_abc(db)

    def refill(at: datetime) -> None:
        for p in products:
            target = 24 if p.category in ("Bière", "Soft") else (4 if p.abc_class == "A" else 6)
            if p.shelf_qty < target and p.reserve_qty > 0:
                services.transfer_stock(db, owner, p, min(target - p.shelf_qty, p.reserve_qty), "Garnissage rayon", at=at)

    def restock(at: datetime) -> None:
        for p in products:
            if p.reserve_qty < 6:
                qty = 48 if p.category in ("Bière", "Soft") else 12
                services.receive_stock(db, owner, p, qty, p.purchase_price, "Livraison fournisseur", at=at)

    refill(start + timedelta(minutes=30))

    # Décalage entre le stock informatique et le stock physique (bouteilles sorties sans vente).
    physical_offset: dict[str, int] = defaultdict(int)
    pool = [p for p in products for _ in range(weights[p.name])]
    a_products = [p for p in products if p.abc_class == "A"]
    c_products = [p for p in products if p.abc_class == "C"]

    def run_session(user: User, day: datetime, h_start: float, h_end: float, cash: float, leak: str | None) -> float:
        cash = 50000.0  # fond de caisse fixe : le patron retire l'excédent à chaque clôture
        opened = day + timedelta(hours=h_start)
        closed = day + timedelta(hours=h_end)
        services.open_session(db, user, cash, at=opened)
        n_sales = random.randint(10, 18) if h_end - h_start < 6 else random.randint(16, 30)
        times = sorted(opened + timedelta(seconds=random.randint(300, int((closed - opened).total_seconds()) - 300)) for _ in range(n_sales))
        for t in times:
            lines: dict[str, int] = defaultdict(int)
            for _ in range(random.choice([1, 1, 1, 2, 2, 3])):
                p = random.choice(pool)
                if p.shelf_qty - lines[p.id] > 0:
                    lines[p.id] += 1 if p.category not in ("Bière", "Soft") else random.choice([1, 2, 3, 6])
            lines = {k: min(v, db.get(Product, k).shelf_qty) for k, v in lines.items() if v > 0}
            lines = {k: v for k, v in lines.items() if v > 0}
            if not lines:
                continue
            sale = services.create_sale(db, user, [SaleLineIn(product_id=k, qty=v) for k, v in lines.items()], random.choice(["especes"] * 2 + ["mobile"]), at=t)
            # Bénédicte annule parfois un ticket après coup : signal discret pour le patron.
            if leak == "bouteilles" and random.random() < 0.05:
                services.cancel_sale(db, sale, user, random.choice(["Client parti", "Erreur de saisie"]), at=t + timedelta(minutes=random.randint(2, 20)))
        if leak == "bouteilles" and random.random() < 0.7:
            # Une ou deux bouteilles de gamme moyenne, rarement une bouteille chère.
            cheap_a = [p for p in a_products if p.sale_price <= 20000]
            for p in random.sample(cheap_a, random.randint(1, 2)):
                if p.shelf_qty + physical_offset[p.id] > 0:
                    physical_offset[p.id] -= 1
            if random.random() < 0.15:
                p = random.choice([p for p in a_products if p.sale_price > 20000])
                if p.shelf_qty + physical_offset[p.id] > 0:
                    physical_offset[p.id] -= 1
            if random.random() < 0.5:
                p = random.choice(c_products)
                if p.shelf_qty + physical_offset[p.id] >= 2:
                    physical_offset[p.id] -= random.randint(1, 2)
        session = services.get_open_session(db)
        count = services.prepare_handover_count(db, session, user, at=closed)
        counted = {}
        for line in count.lines:
            value = line.expected_qty + physical_offset[line.product_id]
            if leak == "erreurs" and line.product.category in ("Bière", "Soft") and random.random() < 0.06:
                value += random.choice([-1, 1])
            counted[line.product_id] = max(value, 0)
        services.submit_count(db, count, counted, user, at=closed)
        for pid in counted:
            physical_offset[pid] = 0
        closing_cash = session.opening_cash + session.sales_cash
        if leak == "erreurs" and random.random() < 0.3:
            closing_cash += random.choice([-1000, -500, 500])
        validator = owner if user is owner else (bene if user is aline else aline)
        services.close_session(db, session, closing_cash, validator, at=closed + timedelta(minutes=10))
        return closing_cash

    cash = 50000.0
    for d in range(1, 15):
        day = start.replace(hour=0) + timedelta(days=d)
        if day.date() >= datetime.now().date():
            break
        if day.weekday() == 0:
            restock(day + timedelta(hours=8))
        refill(day + timedelta(hours=8, minutes=30))
        if day.weekday() == 2:
            cash = run_session(owner, day, 9, 20, cash, None)
            inv = services.prepare_inventory(db, owner, at=day + timedelta(hours=20, minutes=30))
            counted = {l.product_id: max(l.expected_qty + physical_offset[l.product_id], 0) for l in inv.lines}
            services.submit_count(db, inv, counted, owner, at=day + timedelta(hours=21))
            physical_offset.clear()
        elif day.weekday() == 6:
            continue
        else:
            cash = run_session(aline, day, 9, 15, cash, "erreurs")
            # Bénédicte prend son poste en retard une fois sur trois, et ferme parfois tard.
            start2 = 15 + (random.choice([0.2, 0.35, 0.5]) if random.random() < 0.33 else 0)
            end2 = 21 + (random.choice([0.17, 0.4]) if random.random() < 0.25 else -1)  # parfois au-delà de la fermeture (21h)
            cash = run_session(bene, day, start2, end2, cash, "bouteilles")

    services.recompute_abc(db)
    services.audit(db, owner, "demo_initialisee")
    db.commit()
