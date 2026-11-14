/* Caviste : interface caissière et propriétaire. Vue 3, sans étape de build. */
const { createApp } = Vue;

function normalize(s) {
  return (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}

const ICONS = {
  wine: '<path d="M8 22h8"/><path d="M7 10h10"/><path d="M12 15v7"/><path d="M12 15a5 5 0 0 0 5-5c0-2-.5-4-2-8H9c-1.5 4-2 6-2 8a5 5 0 0 0 5 5Z"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  cart: '<circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/>',
  banknote: '<rect width="20" height="12" x="2" y="6" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/>',
  phone: '<rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><path d="M12 18h.01"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
  minus: '<path d="M5 12h14"/>',
  "arrow-left": '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
  "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  "log-out": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>',
  dashboard: '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
  clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  package: '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
  clipboard: '<rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/><path d="M8 16h.01"/>',
  scroll: '<path d="M15 12h-5"/><path d="M15 8h-5"/><path d="M19 17V5a2 2 0 0 0-2-2H4"/><path d="M8 21h12a2 2 0 0 0 2-2v-1a1 1 0 0 0-1-1H11a1 1 0 0 0-1 1v1a2 2 0 1 1-4 0V5a2 2 0 1 0-4 0v2a1 1 0 0 0 1 1h3"/>',
  shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
  alert: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  swap: '<path d="m16 3 4 4-4 4"/><path d="M20 7H4"/><path d="m8 21-4-4 4-4"/><path d="M4 17h16"/>',
  backspace: '<path d="M21 4H8l-7 8 7 8h13a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z"/><line x1="18" x2="12" y1="9" y2="15"/><line x1="12" x2="18" y1="9" y2="15"/>',
  refresh: '<path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/>',
  receipt: '<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/><path d="M12 17.5v-11"/>',
  "lock-open": '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>',
  sliders: '<line x1="4" x2="4" y1="21" y2="14"/><line x1="4" x2="4" y1="10" y2="3"/><line x1="12" x2="12" y1="21" y2="12"/><line x1="12" x2="12" y1="8" y2="3"/><line x1="20" x2="20" y1="21" y2="16"/><line x1="20" x2="20" y1="12" y2="3"/><line x1="2" x2="6" y1="14" y2="14"/><line x1="10" x2="14" y1="8" y2="8"/><line x1="18" x2="22" y1="16" y2="16"/>',
  flag: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/>',
  book: '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/><path d="M8 7h8"/><path d="M8 11h6"/>',
  "eye-off": '<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/>',
};

const app = createApp({
  data() {
    return {
      config: { shop_name: "Caviste", currency: "FCFA" },
      users: [],
      token: localStorage.getItem("caviste_token"),
      me: null,
      view: "login",
      loginUser: null,
      pin: "",
      toast: null,
      busy: false,
      shake: false,
      settings: { shop_name: "", opening_time: "08:00", shift_change_time: "15:00", closing_time: "21:00", momo_fee_rate: 0.035 },
      settingsForm: { shop_name: "", opening_time: "08:00", shift_change_time: "15:00", closing_time: "21:00", momo_fee_pct: 3.5 },
      wave: { shown: false, kind: null, minutes: 0, snoozeUntil: 0 },
      auditFilter: "",
      modal: null,
      // caisse
      session: null,
      isMine: false,
      suggestedCash: null,
      openingCash: 0,
      products: [],
      pos: { mode: "vente", query: "", cursor: 0, payment: "especes", mobilePart: "" },
      ret: { sale_number: "", ticket: null, query: "", product: null, qty: 1, kind: "echange", condition: "defectueux", refund_method: "especes", reason: "" },
      returns: [],
      cart: [],
      sales: [],
      flash: null,
      handover: { step: 1, count: null, counted: {}, closingCash: null, validatorId: null, pin: "", result: null, closing: false },
      // gestion
      admin: { tab: "tableau", days: 30, search: "", expanded: null },
      adminTabs: [
        { id: "tableau", label: "Tableau de bord", icon: "dashboard", sub: "Vue d'ensemble de la boutique, aujourd'hui et cette semaine." },
        { id: "sessions", label: "Sessions", icon: "clock", sub: "Chaque session de caisse avec son écart de caisse et ses manquants au rayon." },
        { id: "caissieres", label: "Caissières", icon: "users", sub: "Comparatif par personne : ventes, écarts, produits sous-vendus." },
        { id: "produits", label: "Produits", icon: "package", sub: "Catalogue, prix, classement ABC, réserve et rayon." },
        { id: "inventaire", label: "Inventaire", icon: "clipboard", sub: "Comptage complet du rayon et historique des comptages." },
        { id: "cahier", label: "Cahier", icon: "book", sub: "Ventes notées à la main pendant une coupure : ressaisie et vérification." },
        { id: "journal", label: "Journal", icon: "scroll", sub: "Toutes les actions, horodatées et signées." },
        { id: "equipe", label: "Équipe", icon: "shield", sub: "Comptes, codes et rôles." },
        { id: "reglages", label: "Réglages", icon: "sliders", sub: "Horaires du magasin et frais Mobile Money." },
      ],
      dash: null,
      dashSel: null,
      sessionsReport: [],
      cashiers: null,
      productsReport: [],
      counts: [],
      inventory: null,
      invCounted: {},
      audit: [],
      team: [],
      cahier: { list: [], filter: "a_verifier", sel: {}, showForm: false },
      syncState: null,
      syncForm: { url: "", key: "" },
      favorites: JSON.parse(localStorage.getItem("caviste_fav") || "{}"),
    };
  },
  computed: {
    isOwner() { return this.me && this.me.role === "proprietaire"; },
    syncClass() {
      const s = this.syncState;
      if (!s || !s.configured) return "idle";
      if (s.online === false) return "off";
      if (s.last_error) return "warn";
      return s.pending > 0 || !s.full_done ? "warn" : "ok";
    },
    syncLabel() {
      const s = this.syncState;
      if (!s || !s.configured) return "Synchro web non configurée";
      if (s.online === false) return s.pending ? `Hors ligne · ${s.pending} en attente` : "Hors ligne";
      if (s.last_error) return "Synchro en erreur";
      if (!s.full_done) return "Premier envoi en cours…";
      return s.pending > 0 ? `Envoi en cours · ${s.pending}` : "Synchronisé";
    },
    pageTitle() { const t = this.adminTabs.find((x) => x.id === this.admin.tab); return t ? t.label : ""; },
    pageSub() { const t = this.adminTabs.find((x) => x.id === this.admin.tab); return t ? t.sub : ""; },
    lowShelfCount() { return this.products.filter((p) => p.active && p.shelf_qty <= p.shelf_min).length; },
    results() {
      const q = normalize(this.pos.query);
      if (!q) return [];
      const words = q.split(/\s+/).filter(Boolean);
      const scored = [];
      for (const p of this.products) {
        const hay = normalize(`${p.name} ${p.aliases} ${p.category} ${p.size}`);
        if (!words.every((w) => hay.includes(w))) continue;
        const nameN = normalize(p.name);
        const score = (nameN.startsWith(q) ? 0 : nameN.includes(q) ? 1 : 2) * 1000 - (this.favorites[p.id] || 0);
        scored.push({ p, score });
      }
      scored.sort((a, b) => a.score - b.score);
      return scored.slice(0, 8).map((s) => s.p);
    },
    quickProducts() {
      const fav = Object.entries(this.favorites).sort((a, b) => b[1] - a[1]).map(([id]) => this.productById(id)).filter(Boolean);
      if (fav.length >= 8) return fav.slice(0, 12);
      const fill = this.products.filter((p) => !this.favorites[p.id] && ["Bière", "Soft"].includes(p.category));
      return [...fav, ...fill].slice(0, 12);
    },
    cartTotal() { return this.cart.reduce((t, l) => t + this.lineTotal(l), 0); },
    mobilePart() {
      if (this.pos.payment === "mobile") return this.cartTotal;
      if (this.pos.payment === "mixte") { const v = Number(this.pos.mobilePart) || 0; return Math.min(Math.max(v, 0), this.cartTotal); }
      return 0;
    },
    cashPart() { return this.cartTotal - this.mobilePart; },
    momoFee() { return Math.round(this.mobilePart * this.settings.momo_fee_rate); },
    momoToSend() { return this.mobilePart + this.momoFee; },
    amountDue() { return this.cartTotal + this.momoFee; },
    mixteInvalid() { return this.pos.payment === "mixte" && (this.mobilePart <= 0 || this.mobilePart >= this.cartTotal); },
    retResults() {
      const q = normalize(this.ret.query);
      if (!q) return [];
      const words = q.split(/\s+/).filter(Boolean);
      return this.products.filter((p) => words.every((w) => normalize(`${p.name} ${p.aliases} ${p.category}`).includes(w))).slice(0, 6);
    },
    filledCount() {
      if (!this.handover.count) return 0;
      return this.handover.count.lines.filter((l) => this.handover.counted[l.product_id] !== "" && this.handover.counted[l.product_id] !== undefined && this.handover.counted[l.product_id] !== null).length;
    },
    invFilled() {
      if (!this.inventory) return 0;
      return this.inventory.lines.filter((l) => this.invCounted[l.product_id] !== "" && this.invCounted[l.product_id] !== undefined).length;
    },
    gapLines() {
      const c = this.handover.result && this.handover.result._count;
      return c ? c.lines.filter((l) => l.gap_qty) : [];
    },
    validators() { return this.users.filter((u) => u.id !== (this.session && this.session.user_id) || u.role === "proprietaire"); },
    filteredProducts() {
      const q = normalize(this.admin.search);
      return this.products.filter((p) => !q || normalize(`${p.name} ${p.aliases} ${p.category}`).includes(q));
    },
    categories() { return [...new Set(this.products.map((p) => p.category))].sort(); },
  },
  mounted() {
    setInterval(() => this.checkWave(), 20000);
    // Poste de bureau : signe de vie pour l'application, et état de la synchro pour le patron.
    setInterval(() => {
      if (this.config.mode !== "poste") return;
      fetch("/api/ping").catch(() => {});
      if (this.isOwner) this.loadSync();
    }, 15000);
    // Saisie des codes au clavier (connexion et validation de passation).
    window.addEventListener("keydown", (e) => {
      const k = e.key;
      if (this.flash) this.flash = null;
      if (this.modal) { if (k === "Escape") this.modal = null; return; }
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (this.view === "standby") { if (k === "Enter" || k === "Escape") this.view = "login"; return; }
      if (this.view === "login" && this.loginUser) {
        if (/^\d$/.test(k)) this.pinKey(k);
        else if (k === "Backspace") this.pin = this.pin.slice(0, -1);
        else if (k === "Escape") { this.loginUser = null; this.pin = ""; }
      } else if (this.view === "caisse" && this.pos.mode === "passation" && this.handover.step === 3 && this.handover.validatorId) {
        if (/^\d$/.test(k) && this.handover.pin.length < 8) this.handover.pin += k;
        else if (k === "Backspace") this.handover.pin = this.handover.pin.slice(0, -1);
        else if (k === "Enter" && this.handover.pin.length >= 4) this.closeSession();
      }
    });
  },
  watch: {
    "admin.days"() {
      if (this.admin.tab === "sessions") this.loadSessionsReport();
      if (this.admin.tab === "caissieres") this.loadCashiers();
    },
  },
  async created() {
    this.config = await this.api("GET", "/api/config");
    this.users = await this.api("GET", "/api/users/login-list");
    if (this.token) {
      try {
        this.me = await this.api("GET", "/api/me");
        await this.enter();
      } catch (e) { this.logout(); }
    }
  },
  methods: {
    // ---- infrastructure
    async api(method, path, body) {
      const headers = { "Content-Type": "application/json" };
      if (this.token) headers.Authorization = "Bearer " + this.token;
      const r = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
      if (r.status === 401 && this.me) { this.logout(); throw new Error("Session expirée, reconnectez-vous"); }
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        const d = data.detail;
        throw new Error(typeof d === "string" ? d : d ? JSON.stringify(d) : "Erreur " + r.status);
      }
      return data;
    },
    async run(fn) {
      if (this.busy) return;
      this.busy = true;
      try { return await fn(); }
      catch (e) { this.notify(e.message, "error"); }
      finally { this.busy = false; }
    },
    notify(text, type = "") {
      this.toast = { text, type };
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => (this.toast = null), 3500);
    },
    money(v) {
      if (v === null || v === undefined) return "—";
      const n = Math.round(Number(v));
      return n.toLocaleString("fr-FR") + " " + this.config.currency;
    },
    fmtTime(d) { return d ? new Date(d).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }) : ""; },
    fmtDate(d) { return d ? new Date(d).toLocaleString("fr-FR", { weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : ""; },
    initials(name) { return (name || "?").split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase(); },
    gapClass(v) { return !v ? "gap-zero" : v < 0 ? "gap-neg" : "gap-pos"; },
    reasonLabel(r) { return { A: "Produit A", vendu: "Vendu ce quart", aleatoire: "Tiré au sort", inventaire: "Inventaire" }[r] || r; },
    fmtDetails(a) {
      // Rend les détails du journal lisibles : "ticket N° 148 · 12 000 FCFA · 2× Primus · espèces".
      let d;
      try { d = JSON.parse(a.details); } catch (e) { return a.details || ""; }
      if (!d || typeof d !== "object") return String(a.details || "");
      const money = (v) => this.money(v);
      const labels = {
        ticket: (v) => "ticket N° " + v, number: (v) => "ticket N° " + v, total: (v) => money(v), articles: (v) => v,
        paiement: (v) => v, motif: (v) => "motif : " + v, reason: (v) => "motif : " + v, caissiere: (v) => v, par: (v) => "par " + v,
        minutes: (v) => v + " min de retard", fin_prevue: (v) => "prévu à " + v, prevu: (v) => "prévu à " + v,
        produit: (v) => v, qty: (v) => "qté " + v, kind: (v) => ({ echange: "échange", remboursement: "remboursement" }[v] || v),
        condition: (v) => ({ defectueux: "défectueux", revendable: "revendable" }[v] || v), rembourse: (v) => (v ? "remboursé " + money(v) : null),
        opening_cash: (v) => "fond de caisse " + money(v), cash_gap: (v) => "écart caisse " + money(v), missing_value: (v) => (v ? "manquants " + money(v) : null),
        missing: (v) => (v ? "manquants " + money(v) : null), surplus: (v) => (v ? "surplus " + money(v) : null), with_gap: (v) => v + " ligne(s) en écart",
        lines: (v) => v + " lignes", name: (v) => v, sale_price: (v) => "prix " + money(v), unit_cost: (v) => (v ? "coût " + money(v) : null),
        shelf_delta: (v) => (v ? "rayon " + (v > 0 ? "+" : "") + v : null), reserve_delta: (v) => (v ? "réserve " + (v > 0 ? "+" : "") + v : null),
        location: (v) => v, role: (v) => v, note: (v) => v, shop_name: (v) => "nom : " + v, opening_time: (v) => "ouverture " + v,
        page: (v) => "cahier " + v, ventes: (v) => v + " vente(s)", total_note: (v) => "total noté " + money(v),
        ecart_avec_cahier: (v) => (v ? "écart avec le cahier " + money(v) : "conforme au cahier"), tickets: (v) => "tickets N° " + v.join(", "),
        apres_cloture: (v) => (v ? "saisi après clôture de la session" : null),
        shift_change_time: (v) => "changement de vague " + v, closing_time: (v) => "fermeture " + v, momo_fee_rate: (v) => "frais MoMo " + (v * 100).toFixed(1) + " %",
      };
      const parts = [];
      for (const [k, v] of Object.entries(d)) {
        if (v === null || v === undefined || v === "" || k === "pin") continue;
        const f = labels[k];
        const out = f ? f(v) : k + " : " + v;
        if (out) parts.push(out);
      }
      return parts.join(" · ");
    },
    statusLabel(st) { return { fermee: "fermée", ouverte: "ouverte", cloture_en_cours: "clôture en cours" }[st] || st; },
    levelLabel(l) { return { ok: "Rien à signaler", attention: "À surveiller", alerte: "Alerte", aucune: "Pas de session" }[l] || l; },
    productById(id) { return this.products.find((p) => p.id === id); },
    barHeights(values) {
      const max = Math.max(...values, 1);
      return values.map((v) => Math.max(6, Math.round((100 * v) / max)));
    },
    sparkPath(values, w = 220, h = 56) {
      if (!values.length) return { line: "", area: "", points: [] };
      const max = Math.max(...values, 1), min = 0;
      const step = w / Math.max(values.length - 1, 1);
      const pts = values.map((v, i) => [Math.round(i * step), Math.round(h - 6 - ((h - 12) * (v - min)) / (max - min || 1))]);
      const line = pts.map((p, i) => (i ? "L" : "M") + p[0] + " " + p[1]).join(" ");
      const area = line + ` L${pts[pts.length - 1][0]} ${h} L0 ${h} Z`;
      return { line, area, points: pts };
    },
    shortMoney(v) {
      const n = Math.round(Number(v) || 0);
      if (Math.abs(n) >= 1000000) return (n / 1000000).toFixed(1).replace(".0", "") + " M";
      if (Math.abs(n) >= 1000) return Math.round(n / 1000) + " k";
      return String(n);
    },

    // ---- connexion
    pickLoginUser(u) { this.loginUser = u; this.pin = ""; },
    async pinKey(k) {
      if (this.pin.length >= 8) return;
      this.pin += k;
      if (this.pin.length === 4) await this.login();
    },
    async login() {
      try {
        const r = await this.api("POST", "/api/auth/login", { user_id: this.loginUser.id, pin: this.pin });
        this.token = r.token;
        localStorage.setItem("caviste_token", r.token);
        this.me = r.user;
        this.pin = "";
        await this.enter();
      } catch (e) {
        this.pin = "";
        this.shakeNow();
        this.notify(e.message, "error");
      }
    },
    shakeNow() { this.shake = false; requestAnimationFrame(() => { this.shake = true; setTimeout(() => (this.shake = false), 450); }); },
    isFilled(v) { return v !== "" && v !== undefined && v !== null; },
    async enter() {
      if (this.isOwner) this.loadSync();
      this.products = await this.api("GET", "/api/products");
      try { this.settings = await this.api("GET", "/api/settings"); } catch (e) { /* valeurs par défaut */ }
      if (this.isOwner) { this.view = "admin"; await this.setAdminTab("tableau"); }
      else { await this.goCaisse(); }
    },
    logout(toProfiles = false) {
      const who = this.me ? { ...this.me } : null;
      this.token = null; this.me = null; this.pin = "";
      this.loginUser = toProfiles || !who ? null : who;
      localStorage.removeItem("caviste_token");
      this.view = "login"; this.session = null; this.cart = []; this.modal = null;
      this.handover = { step: 1, count: null, counted: {}, closingCash: null, validatorId: null, pin: "", result: null };
      this.pos.mode = "vente";
    },

    // ---- caisse
    async goCaisse() {
      this.view = "caisse";
      await this.refreshSession();
      this.focusSearch();
    },
    async refreshSession() {
      const r = await this.api("GET", "/api/session/current");
      this.session = r.session;
      this.isMine = r.is_mine;
      this.suggestedCash = r.suggested_opening_cash;
      if (!this.session) this.openingCash = r.suggested_opening_cash || 0;
      if (this.session && this.session.status === "cloture_en_cours" && (this.isMine || this.isOwner) && this.pos.mode !== "passation") {
        await this.startHandover();
      }
      this.checkWave();
    },
    focusSearch() { this.$nextTick(() => this.$refs.search && this.$refs.search.focus()); },
    checkWave() {
      if (this.view !== "caisse" || !this.session || !this.isMine || this.session.status !== "ouverte" || this.pos.mode === "passation" || this.modal) return;
      if (Date.now() < this.wave.snoozeUntil) return;
      const hm = (d) => { const x = new Date(d); return x.getHours() * 60 + x.getMinutes(); };
      const toMin = (s) => { const [h, m] = String(s).split(":").map(Number); return h * 60 + m; };
      const wave1 = hm(this.session.opened_at) < toMin(this.settings.shift_change_time);
      const end = wave1 ? toMin(this.settings.shift_change_time) : toMin(this.settings.closing_time);
      const nowMin = hm(new Date());
      if (nowMin >= end) { this.wave = { shown: true, kind: wave1 ? "vague" : "fermeture", minutes: nowMin - end, snoozeUntil: 0 }; }
    },
    continueWave() {
      const kind = this.wave.kind;
      this.wave.shown = false;
      this.wave.snoozeUntil = Date.now() + 10 * 60 * 1000;
      this.api("POST", "/api/session/overrun", { kind }).catch(() => {});
      this.focusSearch();
    },
    waveHandover() {
      const closing = this.wave.kind === "fermeture";
      this.wave.shown = false;
      this.wave.snoozeUntil = Date.now() + 60 * 60 * 1000;
      this.startHandover(closing);
    },
    openSession() {
      return this.run(async () => {
        this.session = await this.api("POST", "/api/session/open", { opening_cash: Number(this.openingCash) || 0 });
        this.isMine = true;
        this.pos.mode = "vente";
        this.notify("Session ouverte. Bonne vente !");
        this.focusSearch();
      });
    },
    addResult() {
      const p = this.results[this.pos.cursor] || this.results[0];
      if (p) this.addToCart(p);
    },
    packOptions(p) {
      const upc = p.units_per_case || 1;
      const opts = [{ id: "unite", label: "Unité", units: 1, price: p.sale_price }];
      if (p.sold_by_case && upc > 1) {
        const casePrice = p.case_price || p.sale_price * upc;
        if (p.allow_quarter && upc % 4 === 0) opts.push({ id: "quart", label: "¼ carton", units: upc / 4, price: Math.round(casePrice * 0.25) });
        if (p.allow_half && upc % 2 === 0) opts.push({ id: "demi", label: "½ carton", units: upc / 2, price: Math.round(casePrice * 0.5) });
        opts.push({ id: "carton", label: "Carton", units: upc, price: Math.round(casePrice) });
      }
      if (p.pack_size > 1) opts.push({ id: "pack", label: "Pack de " + p.pack_size, units: p.pack_size, price: Math.round(p.pack_price || p.sale_price * p.pack_size) });
      return opts;
    },
    packUnits(p, pack) { const o = this.packOptions(p).find((x) => x.id === pack); return o ? o.units : 1; },
    packPrice(p, pack) { const o = this.packOptions(p).find((x) => x.id === pack); return o ? o.price : p.sale_price; },
    packLabel(pack) { return { unite: "unité", quart: "¼ carton", demi: "½ carton", carton: "carton", pack: "pack" }[pack] || pack; },
    lineUnits(l) { return l.qty * this.packUnits(l.product, l.pack); },
    lineTotal(l) { return l.qty * this.packPrice(l.product, l.pack); },
    setPack(l, pack) {
      const other = this.cart.find((x) => x !== l && x.product.id === l.product.id && x.pack === pack);
      if (other) { other.qty += l.qty; this.cart = this.cart.filter((x) => x !== l); } else { l.pack = pack; }
    },
    addToCart(p, qty = 1) {
      const line = this.cart.find((l) => l.product.id === p.id && l.pack === "unite");
      if (line) line.qty += qty; else this.cart.push({ product: p, qty, pack: "unite" });
      this.pos.query = ""; this.pos.cursor = 0;
      this.focusSearch();
    },
    changeQty(line, d) {
      line.qty += d;
      if (line.qty <= 0) this.cart = this.cart.filter((l) => l !== line);
    },
    checkout() {
      return this.run(async () => {
        if (this.mixteInvalid) throw new Error("Indiquez la part Mobile Money, entre 0 et le total");
        const sale = await this.api("POST", "/api/sales", {
          lines: this.cart.map((l) => ({ product_id: l.product.id, qty: l.qty, pack: l.pack })),
          payment_method: this.pos.payment,
          mobile_part: this.pos.payment === "mixte" ? this.mobilePart : null,
        });
        for (const l of this.cart) {
          const units = this.lineUnits(l);
          this.favorites[l.product.id] = (this.favorites[l.product.id] || 0) + units;
          const p = this.productById(l.product.id);
          if (p) p.shelf_qty -= units;
        }
        localStorage.setItem("caviste_fav", JSON.stringify(this.favorites));
        this.cart = [];
        this.pos.payment = "especes";
        this.pos.mobilePart = "";
        this.session.sales_count += 1;
        this.session.sales_total += sale.total;
        this.flash = sale;
        setTimeout(() => { if (this.flash === sale) this.flash = null; }, 3000);
        this.focusSearch();
      });
    },
    async loadSales() { this.sales = await this.api("GET", "/api/sales?session_id=" + this.session.id); },
    async openReturns() {
      this.pos.mode = "retour";
      this.returns = await this.api("GET", "/api/returns?limit=50");
    },
    lookupTicket() {
      return this.run(async () => {
        const n = parseInt(this.ret.sale_number, 10);
        if (!n) { this.ret.ticket = null; return; }
        this.ret.ticket = await this.api("GET", "/api/sales/by-number/" + n);
        if (this.ret.ticket.lines.length === 1) this.ret.product = this.productById(this.ret.ticket.lines[0].product_id);
      });
    },
    pickReturnProduct(p) { this.ret.product = p; this.ret.query = ""; },
    submitReturn() {
      return this.run(async () => {
        if (!this.ret.product) throw new Error("Choisissez le produit rendu");
        const n = parseInt(this.ret.sale_number, 10);
        await this.api("POST", "/api/returns", {
          product_id: this.ret.product.id, qty: Number(this.ret.qty) || 1, kind: this.ret.kind,
          condition: this.ret.kind === "echange" ? "defectueux" : this.ret.condition,
          refund_method: this.ret.refund_method, sale_number: n || null, reason: this.ret.reason,
        });
        this.notify(this.ret.kind === "echange" ? "Échange enregistré : produit neuf remis, défectueux mis de côté." : "Remboursement enregistré.");
        this.ret = { sale_number: "", ticket: null, query: "", product: null, qty: 1, kind: "echange", condition: "defectueux", refund_method: "especes", reason: "" };
        this.products = await this.api("GET", "/api/products");
        this.returns = await this.api("GET", "/api/returns?limit=50");
      });
    },
    claimDefective(p) {
      return this.run(async () => {
        await this.api("POST", "/api/stock/defective-clear", { product_id: p.id, qty: p.defective_qty, note: "Réclamé au fournisseur" });
        this.dash = await this.api("GET", "/api/reports/dashboard");
        this.notify("Marqué comme réclamé au fournisseur.");
      });
    },
    askCancel(sale) { this.modal = { type: "cancel", sale, reason: "", pin: "" }; },
    confirmCancel() {
      return this.run(async () => {
        await this.api("POST", `/api/sales/${this.modal.sale.id}/cancel`, { reason: this.modal.reason });
        this.modal = null;
        this.notify("Vente annulée.");
        if (this.view === "admin" && this.admin.tab === "cahier") { await this.loadCahier(); return; }
        await this.refreshSession();
        await this.loadSales();
        this.products = await this.api("GET", "/api/products");
      });
    },

    // ---- passation
    startHandover(closing = false) {
      return this.run(async () => {
        const count = await this.api("POST", "/api/session/close/prepare");
        const counted = {};
        for (const l of count.lines) counted[l.product_id] = "";
        const resumed = count.status === "termine";
        this.handover = { step: resumed ? 2 : 1, count, counted, closingCash: null, validatorId: closing ? this.me.id : null, pin: "", result: null, closing };
        this.pos.mode = "passation";
        await this.refreshSessionQuiet();
        if (resumed) {
          this.handover.closingCash = this.session.opening_cash + this.session.sales_cash - (this.session.refunds_cash || 0);
          this.notify("Le comptage du rayon est déjà validé : il reste les espèces et la confirmation.");
        } else {
          this.$nextTick(() => { const el = document.getElementById("cnt-0"); el && el.focus(); });
        }
      });
    },
    async refreshSessionQuiet() {
      const r = await this.api("GET", "/api/session/current");
      this.session = r.session; this.isMine = r.is_mine;
    },
    cancelHandover() {
      // Le comptage reste préparé côté serveur (statut clôture en cours) : on peut y revenir.
      this.pos.mode = "vente";
      this.notify("Comptage mis en pause. La vente est bloquée tant que la passation n'est pas terminée.");
    },
    focusNext(i) {
      const el = document.getElementById("cnt-" + (i + 1));
      if (el) { el.focus(); el.select && el.select(); }
    },
    submitCount() { this.modal = { type: "confirm-count" }; },
    doSubmitCount() {
      this.modal = null;
      return this.run(async () => {
        const lines = this.handover.count.lines.map((l) => ({ product_id: l.product_id, counted_qty: Number(this.handover.counted[l.product_id]) }));
        try {
          this.handover.count = await this.api("POST", `/api/counts/${this.handover.count.id}/submit`, { lines });
        } catch (e) {
          if (!String(e.message).includes("déjà terminé")) throw e;
          this.handover.count = await this.api("GET", `/api/counts/${this.handover.count.id}`);
          this.notify("Le comptage était déjà validé, on passe aux espèces.");
        }
        this.handover.closingCash = this.session.opening_cash + this.session.sales_cash - (this.session.refunds_cash || 0);
        this.handover.step = 2;
      });
    },
    switchToClosing() { this.handover.closing = true; this.handover.validatorId = this.me.id; this.handover.pin = ""; },
    closeSession() {
      return this.run(async () => {
        const result = await this.api("POST", "/api/session/close", {
          closing_cash: Number(this.handover.closingCash) || 0,
          validator_id: this.handover.validatorId,
          validator_pin: this.handover.pin,
          closing: this.handover.closing,
        });
        result._count = this.handover.count;
        this.handover.result = result;
        this.handover.step = 4;
      }).then(() => { if (this.handover.step === 3) { this.handover.pin = ""; this.shakeNow(); } });
    },
    async finishHandover() {
      const closing = this.handover.closing;
      this.pos.mode = "vente";
      this.handover = { step: 1, count: null, counted: {}, closingCash: null, validatorId: null, pin: "", result: null, closing: false };
      if (this.isOwner) { await this.goAdmin(); }
      else if (closing) { this.logout(true); this.view = "standby"; }
      else { this.logout(true); this.notify("Passation terminée. La personne suivante peut se connecter."); }
    },

    // ---- gestion
    async goAdmin() { this.view = "admin"; await this.setAdminTab(this.admin.tab); },
    async setAdminTab(tab) {
      this.admin.tab = tab;
      try {
        if (tab === "tableau") {
          this.dash = await this.api("GET", "/api/reports/dashboard");
          this.products = await this.api("GET", "/api/products");
          if (!this.dashSel || !this.dash.recent_sessions.some((s) => s.id === this.dashSel.id)) this.dashSel = this.dash.recent_sessions[0] || null;
        }
        if (tab === "sessions") await this.loadSessionsReport();
        if (tab === "caissieres") await this.loadCashiers();
        if (tab === "produits") this.products = await this.api("GET", "/api/products?include_inactive=true");
        if (tab === "inventaire") this.counts = await this.api("GET", "/api/counts?limit=30");
        if (tab === "journal") await this.loadAudit();
        if (tab === "cahier") await this.loadCahier();
        if (tab === "reglages") {
          await this.loadSync();
          if (this.syncState) this.syncForm = { url: this.syncState.url, key: "" };
          this.settings = await this.api("GET", "/api/settings");
          this.settingsForm = { shop_name: this.settings.shop_name, opening_time: this.settings.opening_time, shift_change_time: this.settings.shift_change_time, closing_time: this.settings.closing_time, momo_fee_pct: Math.round(this.settings.momo_fee_rate * 1000) / 10 };
        }
        if (tab === "equipe") this.team = await this.api("GET", "/api/users");
      } catch (e) { this.notify(e.message, "error"); }
    },
    async loadCahier(filter) {
      if (filter) this.cahier.filter = filter;
      this.cahier.list = await this.api("GET", "/api/cahier?status=" + this.cahier.filter);
      this.cahier.sel = {};
    },
    verifyCahier(ids) {
      return this.run(async () => {
        if (!ids.length) throw new Error("Cochez les ventes vérifiées sur le cahier");
        const r = await this.api("POST", "/api/cahier/verify", { sale_ids: ids });
        this.notify(r.verified + " vente(s) marquée(s) vérifiée(s).");
        await this.loadCahier();
      });
    },
    async loadSync() {
      if (this.config.mode !== "poste" || !this.isOwner) return;
      try { this.syncState = await this.api("GET", "/api/sync/status"); } catch (e) { /* ignoré */ }
    },
    saveSync() {
      return this.run(async () => {
        this.syncState = await this.api("PUT", "/api/sync/config", { url: this.syncForm.url, key: this.syncForm.key || null });
        this.syncForm.key = "";
        this.notify("Réglages de synchronisation enregistrés");
        setTimeout(() => this.loadSync(), 4000);
      });
    },
    syncNow() {
      return this.run(async () => {
        try {
          this.syncState = await this.api("POST", "/api/sync/now");
          this.notify("Synchronisation terminée");
        } finally { await this.loadSync(); }
      });
    },
    async loadAudit(filter) {
      if (filter !== undefined) this.auditFilter = filter;
      this.audit = await this.api("GET", "/api/audit?limit=300" + (this.auditFilter ? "&filter=" + this.auditFilter : ""));
    },
    saveSettings() {
      return this.run(async () => {
        this.settings = await this.api("PUT", "/api/settings", {
          shop_name: this.settingsForm.shop_name,
          opening_time: this.settingsForm.opening_time,
          shift_change_time: this.settingsForm.shift_change_time,
          closing_time: this.settingsForm.closing_time,
          momo_fee_rate: Number(this.settingsForm.momo_fee_pct) / 100,
        });
        this.config = await this.api("GET", "/api/config");
        document.title = this.config.shop_name + " · Caviste";
        this.notify("Réglages enregistrés.");
      });
    },
    async loadSessionsReport() { this.sessionsReport = await this.api("GET", "/api/reports/sessions?days=" + this.admin.days); },
    async loadCashiers() {
      this.cashiers = await this.api("GET", "/api/reports/cashiers?days=" + this.admin.days);
      this.productsReport = await this.api("GET", "/api/reports/products?days=" + this.admin.days);
    },
    async openSessionDetail(s) {
      const sales = await this.api("GET", "/api/sales?session_id=" + s.id + "&limit=500");
      this.modal = { type: "session", session: s, sales };
    },
    async viewCount(c) { this.modal = { type: "count", count: c }; },
    async viewCountById(id) {
      const count = await this.api("GET", "/api/counts/" + id);
      this.modal = { type: "count", count };
    },
    editProduct(p) {
      this.modal = { type: "product", data: p ? { ...p } : { name: "", aliases: "", category: "", size: "", purchase_price: 0, sale_price: 0, abc_class: "C", shelf_min: 2, shelf_qty: 0, reserve_qty: 0, units_per_case: 1, case_price: null, sold_by_case: false, allow_half: false, allow_quarter: false, pack_size: null, pack_price: null } };
    },
    saveProduct() {
      return this.run(async () => {
        const d = this.modal.data;
        const num = (v) => (v === "" || v === null || v === undefined ? null : Number(v));
        const casePrice = num(d.case_price), packSize = num(d.pack_size), packPrice = num(d.pack_price);
        if (d.id) {
          const { id, shelf_qty, reserve_qty, defective_qty, ...payload } = d;
          payload.case_price = casePrice; payload.clear_case_price = casePrice === null;
          payload.pack_size = packSize; payload.pack_price = packPrice; payload.clear_pack = !packSize;
          await this.api("PUT", "/api/products/" + id, payload);
        } else {
          await this.api("POST", "/api/products", { ...d, case_price: casePrice, pack_size: packSize, pack_price: packPrice });
        }
        this.modal = null;
        this.products = await this.api("GET", "/api/products?include_inactive=true");
        this.notify("Produit enregistré.");
      });
    },
    stockAction(p, action) {
      this.modal = { type: "stock", product: p, action, qty: action === "transfert" ? Math.max(1, Math.min(p.reserve_qty, (p.shelf_min || 2) * 3 - p.shelf_qty)) : 1, unit_cost: null, location: "rayon", note: "" };
    },
    saveStock() {
      return this.run(async () => {
        const m = this.modal;
        const path = { achat: "/api/stock/receive", transfert: "/api/stock/transfer", perte: "/api/stock/loss" }[m.action];
        const body = { product_id: m.product.id, qty: Number(m.qty), note: m.note };
        if (m.action === "achat" && m.unit_cost) body.unit_cost = Number(m.unit_cost);
        if (m.action === "perte") body.location = m.location;
        await this.api("POST", path, body);
        this.modal = null;
        this.products = await this.api("GET", "/api/products?include_inactive=true");
        if (this.admin.tab === "tableau") this.dash = await this.api("GET", "/api/reports/dashboard");
        this.notify("Mouvement enregistré.");
      });
    },
    recomputeAbc() {
      return this.run(async () => {
        const r = await this.api("POST", "/api/products/recompute-abc");
        this.products = await this.api("GET", "/api/products?include_inactive=true");
        this.notify(`Classement recalculé : ${r.A} produits A, ${r.B} B, ${r.C} C.`);
      });
    },
    startInventory() {
      return this.run(async () => {
        this.inventory = await this.api("POST", "/api/counts/inventory");
        this.invCounted = {};
        for (const l of this.inventory.lines) this.invCounted[l.product_id] = "";
        this.$nextTick(() => { const el = document.getElementById("inv-0"); el && el.focus(); });
      });
    },
    focusNextInv(i) { const el = document.getElementById("inv-" + (i + 1)); if (el) el.focus(); },
    submitInventory() {
      return this.run(async () => {
        const lines = this.inventory.lines.map((l) => ({ product_id: l.product_id, counted_qty: this.invCounted[l.product_id] === "" ? null : Number(this.invCounted[l.product_id]) }));
        const done = await this.api("POST", `/api/counts/${this.inventory.id}/submit`, { lines });
        this.inventory = null;
        this.counts = await this.api("GET", "/api/counts?limit=30");
        this.products = await this.api("GET", "/api/products");
        this.modal = { type: "count", count: done };
        this.notify(`Inventaire terminé : ${done.lines_with_gap} écart(s).`);
      });
    },
    editUser(u) {
      this.modal = { type: "user", data: u ? { ...u, pin: "" } : { name: "", role: "caissiere", pin: "", color: "#7c3aed", active: true } };
    },
    saveUser() {
      return this.run(async () => {
        const d = this.modal.data;
        if (d.id) {
          const payload = { name: d.name, role: d.role, color: d.color, active: d.active };
          if (d.pin) payload.pin = d.pin;
          await this.api("PUT", "/api/users/" + d.id, payload);
        } else {
          await this.api("POST", "/api/users", { name: d.name, role: d.role, color: d.color, pin: d.pin });
        }
        this.modal = null;
        this.team = await this.api("GET", "/api/users");
        this.users = await this.api("GET", "/api/users/login-list");
        this.notify("Enregistré.");
      });
    },
  },
});
// ---- Cahier de secours : ressaisie des ventes notées à la main pendant une coupure.
const pad = (n) => String(n).padStart(2, "0");
const todayISO = () => { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };
const blankPaperSale = (time = "") => ({ key: Math.random().toString(36).slice(2), time, query: "", cursor: 0, lines: [], payment_method: "especes", mobile_part: "" });

app.component("cahier-form", {
  emits: ["saved"],
  data() {
    const root = this.$root;
    return {
      sellerId: root.isOwner ? "" : root.me.id,
      day: todayISO(),
      paperRef: "",
      declared: "",
      sales: [blankPaperSale()],
      result: null,
    };
  },
  computed: {
    r() { return this.$root; },
    today() { return todayISO(); },
    sellers() { return this.r.users; },
    validSales() { return this.sales.filter((s) => s.lines.length); },
    total() { return this.validSales.reduce((t, s) => t + this.saleTotal(s), 0); },
    gap() { return this.declared === "" || this.declared === null ? null : this.total - Number(this.declared); },
    missingTimes() { return this.validSales.some((s) => !/^\d{2}:\d{2}$/.test(s.time)); },
    canSave() { return this.sellerId && this.validSales.length && !this.missingTimes; },
  },
  methods: {
    results(s) {
      const q = normalize(s.query);
      if (!q) return [];
      const words = q.split(/\s+/).filter(Boolean);
      return this.r.products.filter((p) => p.active !== false && words.every((w) => normalize(`${p.name} ${p.aliases} ${p.category}`).includes(w))).slice(0, 6);
    },
    pick(s, p) {
      const same = s.lines.find((l) => l.product.id === p.id && l.pack === "unite");
      if (same) same.qty += 1; else s.lines.push({ product: p, qty: 1, pack: "unite" });
      s.query = ""; s.cursor = 0;
    },
    onKey(e, s) {
      const res = this.results(s);
      if (e.key === "ArrowDown") { s.cursor = Math.min(s.cursor + 1, res.length - 1); e.preventDefault(); }
      else if (e.key === "ArrowUp") { s.cursor = Math.max(s.cursor - 1, 0); e.preventDefault(); }
      else if (e.key === "Enter" && res.length) { this.pick(s, res[s.cursor] || res[0]); e.preventDefault(); }
      else if (e.key === "Escape") { s.query = ""; }
    },
    lineTotal(l) { return this.r.packPrice(l.product, l.pack) * (Number(l.qty) || 0); },
    saleTotal(s) { return s.lines.reduce((t, l) => t + this.lineTotal(l), 0); },
    addSale() {
      const last = this.sales[this.sales.length - 1];
      this.sales.push(blankPaperSale(last ? last.time : ""));
      this.$nextTick(() => { const el = this.$el.querySelectorAll(".cahier-time"); if (el.length) el[el.length - 1].focus(); });
    },
    removeSale(i) { this.sales.splice(i, 1); if (!this.sales.length) this.sales.push(blankPaperSale()); },
    reset() { this.sales = [blankPaperSale()]; this.paperRef = ""; this.declared = ""; },
    save() {
      return this.r.run(async () => {
        if (!this.canSave) throw new Error(this.missingTimes ? "Indiquez l'heure de chaque vente" : "Ajoutez au moins une vente");
        for (const s of this.validSales) {
          if (s.payment_method === "mixte" && !(Number(s.mobile_part) > 0 && Number(s.mobile_part) < this.saleTotal(s))) throw new Error(`Vente de ${s.time} : indiquez la part Mobile Money`);
          if (s.lines.some((l) => !(Number(l.qty) > 0))) throw new Error(`Vente de ${s.time} : quantité invalide`);
        }
        if (this.gap !== null && Math.abs(this.gap) > 0.5 && !window.confirm(`Le total saisi (${this.r.money(this.total)}) ne correspond pas au total noté dans le cahier (${this.r.money(Number(this.declared))}).\n\nEnregistrer quand même ? L'écart sera signalé au propriétaire.`)) return;
        const body = {
          seller_id: this.sellerId,
          paper_ref: this.paperRef,
          declared_total: this.declared === "" ? null : Number(this.declared),
          sales: this.validSales.map((s) => ({
            at: `${this.day}T${s.time}:00`,
            payment_method: s.payment_method,
            mobile_part: s.payment_method === "mixte" ? Number(s.mobile_part) : null,
            lines: s.lines.map((l) => ({ product_id: l.product.id, qty: Number(l.qty), pack: l.pack })),
          })),
        };
        const res = await this.r.api("POST", "/api/cahier", body);
        this.result = { count: res.sales.length, total: res.total, gap: res.gap, numbers: res.sales.map((x) => x.number), after_close: res.after_close };
        this.reset();
        this.r.products = await this.r.api("GET", "/api/products");
        this.r.notify(`${res.sales.length} vente(s) du cahier enregistrée(s).`);
        this.$emit("saved", res);
      });
    },
  },
  template: `
  <div class="stack">
    <div class="panel stack" style="overflow: visible">
      <div><h2>Cahier de secours</h2><p class="muted small" style="margin-top: 4px">Pendant une coupure, notez chaque vente dans le cahier : l'heure, les articles, le paiement. Au retour du courant, recopiez la page ici. Chaque vente garde son heure réelle et rejoint la session de caisse de l'époque.</p></div>
      <p class="hint warn"><ico name="alert"></ico><span>Saisissez le cahier <strong>avant la passation</strong> : sinon les bouteilles vendues pendant la coupure apparaîtront comme manquantes au comptage du rayon.</span></p>
      <div class="form-grid cahier-head">
        <label v-if="r.isOwner">Vendeuse<select v-model="sellerId"><option value="" disabled>Choisir…</option><option v-for="u in sellers" :key="u.id" :value="u.id">{{ u.name }}</option></select></label>
        <label v-else>Vendeuse<input :value="r.me.name" disabled></label>
        <label>Date des ventes<input type="date" v-model="day" :max="today"></label>
        <label>Page du cahier<input v-model="paperRef" placeholder="ex. page 12" maxlength="80"></label>
        <label>Total noté en bas de la page<input type="number" min="0" step="100" v-model="declared" placeholder="facultatif"></label>
      </div>
    </div>

    <div v-for="(s, i) in sales" :key="s.key" class="panel stack cahier-sale" style="overflow: visible">
      <div class="row between nowrap" style="gap: 12px">
        <div class="row nowrap" style="gap: 10px">
          <span class="badge">Vente {{ i + 1 }}</span>
          <label class="row nowrap" style="gap: 6px">Heure<input class="cahier-time" type="time" v-model="s.time" style="width: 130px"></label>
        </div>
        <div class="row nowrap" style="gap: 10px">
          <strong class="num">{{ r.money(saleTotal(s)) }}</strong>
          <button class="ghost icon round" title="Retirer cette vente" @click="removeSale(i)"><ico name="trash"></ico></button>
        </div>
      </div>
      <div class="search"><ico name="search"></ico><input v-model="s.query" @keydown="onKey($event, s)" placeholder="Article : tapez le nom, Entrée pour l'ajouter" style="min-height: 46px; font-size: 15px; padding-left: 50px; box-shadow: none; border-color: var(--line-strong)">
        <transition name="drop"><div v-if="s.query && results(s).length" class="results" style="top: 52px"><div v-for="(p, k) in results(s)" :key="p.id" class="result" :class="{active: k === s.cursor}" @mousedown.prevent="pick(s, p)"><div class="name">{{ p.name }} <span>{{ p.size }}</span></div><span class="price">{{ r.money(p.sale_price) }}</span></div></div></transition>
      </div>
      <table v-if="s.lines.length" class="cahier-lines">
        <tr v-for="(l, j) in s.lines" :key="j">
          <td style="width: 90px"><input type="number" min="1" v-model.number="l.qty" class="qty" style="width: 76px"></td>
          <td><strong>{{ l.product.name }}</strong> <span class="muted small">{{ l.product.size }}</span>
            <div v-if="r.packOptions(l.product).length > 1" class="packsel" style="margin-top: 4px"><button v-for="o in r.packOptions(l.product)" :key="o.id" :class="{active: l.pack === o.id}" @click="l.pack = o.id">{{ o.label }}</button></div>
          </td>
          <td class="num">{{ r.money(lineTotal(l)) }}</td>
          <td class="right" style="width: 50px"><button class="ghost icon round" title="Retirer" @click="s.lines.splice(j, 1)"><ico name="x"></ico></button></td>
        </tr>
      </table>
      <div class="row" style="gap: 10px; flex-wrap: wrap">
        <div class="seg">
          <button :class="{active: s.payment_method === 'especes'}" @click="s.payment_method = 'especes'"><ico name="banknote" class="sm"></ico> Espèces</button>
          <button :class="{active: s.payment_method === 'mobile'}" @click="s.payment_method = 'mobile'"><ico name="phone" class="sm"></ico> Mobile Money</button>
          <button :class="{active: s.payment_method === 'mixte'}" @click="s.payment_method = 'mixte'">Les deux</button>
        </div>
        <label v-if="s.payment_method === 'mixte'" class="row nowrap" style="gap: 6px">Part Mobile Money<input type="number" min="0" v-model="s.mobile_part" style="width: 140px"></label>
      </div>
    </div>

    <div class="row between" style="gap: 12px; flex-wrap: wrap">
      <button @click="addSale()"><ico name="plus"></ico> Ajouter une vente</button>
      <div class="panel row nowrap cahier-summary" style="gap: 18px; padding: 12px 18px">
        <span>{{ validSales.length }} vente(s)</span>
        <span>Total saisi <strong class="num">{{ r.money(total) }}</strong></span>
        <span v-if="gap !== null" class="badge" :class="Math.abs(gap) < 0.5 ? 'ok' : 'alerte'">{{ Math.abs(gap) < 0.5 ? 'Conforme au cahier' : 'Écart ' + (gap > 0 ? '+' : '') + r.money(gap) }}</span>
        <button class="primary" :disabled="!canSave || r.busy" @click="save()"><ico name="check" class="sm"></ico> Enregistrer</button>
      </div>
    </div>

    <p v-if="result" class="hint ok"><ico name="check"></ico><span>{{ result.count }} vente(s) enregistrée(s), tickets N° {{ result.numbers.join(', ') }}, total {{ r.money(result.total) }}.<template v-if="result.gap"> Écart avec le cahier : {{ r.money(result.gap) }}.</template><template v-if="result.after_close"> Session déjà fermée : son écart de caisse a été recalculé.</template> Elles partiront vers l'espace en ligne avec la prochaine synchronisation.</span></p>
  </div>`,
});
app.component("ico", {
  props: { name: { type: String, required: true } },
  computed: { paths() { return ICONS[this.name] || ""; } },
  template: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" v-html="paths"></svg>',
});
app.mount("#app");
