# Caviste : démo web

Gestion de cave (vins, whisky, boissons) pour une boutique à deux caissières qui se relaient.
Le rayon est la variable de contrôle : il est compté à chaque passation, et tout écart
est imputé à la session qui vient de se terminer.

## Lancer

```
run.bat
```

Puis ouvrir http://127.0.0.1:8765. La première exécution crée la base SQLite dans `data/`
et charge deux semaines de données de démonstration.

Comptes de démo : Patron (0000, propriétaire), Aline (1111), Bénédicte (2222).

## Base de données

SQLite par défaut (`data/caviste.db`). Pour PostgreSQL :

```
set DATABASE_URL=postgresql+psycopg://user:motdepasse@localhost:5432/caviste
```

## Principes métier

- Une seule session de caisse ouverte à la fois. Vendre exige sa propre session.
- Passation en quatre étapes : comptage du rayon à l'aveugle (produits A, produits vendus
  pendant le quart, quelques produits tirés au sort), comptage des espèces, validation par
  la personne entrante avec son code, résultat.
- Le comptage certifie le rayon : les quantités comptées deviennent la référence de la
  session suivante.
- Annulation d'une vente : code du propriétaire et motif obligatoires, tout est journalisé.
- Inventaire complet : à l'initiative du propriétaire ; ses écarts ne sont imputés à personne.
- Journal immuable des mouvements de stock et des actions.

## Structure

- `app/models.py` : schéma (UUID et horodatage partout, prêt pour la synchronisation).
- `app/services.py` : règles métier et rapports.
- `app/routers.py` : API REST sous `/api`.
- `app/seed.py` : données de démonstration.
- `static/` : interface (Vue 3 sans build, un seul fichier HTML + JS + CSS).

## Règles ajoutées (13 novembre 2026)

- Vente à l'unité, au quart, au demi ou au carton : chaque produit a un nombre d'unités
  par carton et, en option, un prix du carton entier. Le stock reste compté en unités.
- Mobile Money : le client envoie le total majoré des frais de retrait (3,5 % par défaut,
  réglable), pour que la boutique encaisse le prix affiché.
- Comptage du rayon : définitif. L'écran l'annonce, une confirmation est demandée,
  les manquants sont imputés à la personne en poste.
- Horaires du magasin (Réglages) : les actions hors horaires restent possibles mais
  sont signalées au propriétaire.
- Annulations : la caissière peut annuler ses propres ventes avec un motif, sans code.
  Tout est consigné et consultable par le propriétaire seul (journal filtré, carte
  "À surveiller"). Rien n'est indiqué aux employées.
- Règlement partagé : une vente peut être payée en partie par Mobile Money et en partie
  en espèces ; les frais ne portent que sur la part Mobile Money.
- Conditionnements par produit : la fiche indique si le carton se vend entier, si le demi
  et le quart sont autorisés, et s'il existe un pack (ex. 6 canettes). Une bouteille seule
  se vend toujours à l'unité.
- Connexion : "Quitter" ramène à l'écran du code de la même personne (comme une session
  expirée) ; "Sortir" sur cet écran ramène au choix du profil.
- Retours clients (caisse, onglet Retour / échange) : échange d'un produit défectueux
  (bouteille neuve sortie du rayon, bouteille rendue mise de côté pour réclamation au
  fournisseur, aucun mouvement d'argent) ou remboursement (produit remis en rayon s'il est
  intact, argent rendu depuis la caisse, pris en compte dans la caisse attendue).
- Vagues : le patron règle ouverture, changement de vague et fermeture. À la fin de sa
  vague, la caissière voit une page de pause ("tour de la seconde caissière" ou "fermeture
  du magasin") sans être déconnectée : elle peut finir ses clients ("J'ai encore des
  clients", prolongation consignée) ou passer la caisse. Les retards de prise de poste,
  de passation et de fermeture sont consignés pour le patron (tolérance 15 minutes ; le
  patron qui tient seul la boutique n'est pas concerné).
- Le nom de la cave se change dans Réglages. Le ticket se ferme d'un clic ou avec la croix.
