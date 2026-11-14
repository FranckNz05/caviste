# Caviste

Développé par Franck Nz · 064 08 88 68 / 057 66 83 71

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

## Application de bureau (poste de la boutique)

```
build.bat
```

Produit `dist\Caviste-Installation-1.0.0.exe` (PyInstaller + Inno Setup 6). L'installeur ne
demande pas de droits administrateur et installe dans `%LOCALAPPDATA%\Programs\Caviste`.

- Fonctionne sans Internet : serveur local et base SQLite dans `%LOCALAPPDATA%\Caviste\boutique`.
  La désinstallation ne supprime jamais ces données.
- La fenêtre est Microsoft Edge en mode application (présent sur Windows 10/11) ; à défaut,
  le navigateur par défaut. Fermer la fenêtre arrête l'application au bout d'une minute.
- Premier lancement : base vide, un seul compte Patron (code 0000, à changer dans Équipe).
- Raccourci facultatif "Caviste (démonstration)" : cave fictive séparée, jamais synchronisée.

## Synchronisation avec le web (espace du patron)

Le poste est la référence ; le serveur web (Render, `CAVISTE_MODE=miroir`) en est une copie
en consultation, accessible au seul propriétaire.

- Chaque écriture du poste est notée dans une file d'attente locale (`sync_outbox`).
- Un fil de fond tente l'envoi toutes les 10 à 30 secondes ; dès que la connexion revient,
  tout ce qui a été fait hors ligne part. L'envoi est idempotent (lignes recopiées par UUID).
- Premier envoi complet : le miroir est vidé puis rempli. Changer d'adresse ou de clé relance
  un envoi complet.
- Réglage sur le poste : Gestion > Réglages > Synchronisation avec le web (adresse du site et
  clé `CAVISTE_SYNC_KEY` du serveur). La pastille en haut indique l'état (synchronisé, en attente,
  hors ligne).
- Sur le miroir, toute modification est refusée : on change les prix, l'équipe, etc. sur le poste.

## Cahier de secours (coupure longue, PC éteint)

Pendant la coupure, on note chaque vente dans un cahier : heure, articles, paiement, et le total
en bas de page. Au retour du courant :

1. Caisse > onglet **Cahier** (la caissière, pour ses ventes) ou Gestion > **Cahier** (le patron,
   pour n'importe qui) : date, page, total noté, puis chaque vente avec son heure.
2. Le total saisi est comparé au total de la page ; un écart est signalé au patron.
3. Chaque vente garde son heure réelle et rejoint la session de caisse de l'époque. Si aucune
   caisse n'était ouverte à cette heure (coupure avant l'ouverture), elle va dans une
   **session de secours** fermée, pour ne pas fausser la caisse en cours.
4. Le patron compare la liste avec le cahier papier et valide (Gestion > Cahier > À vérifier) ;
   une vente mal recopiée s'annule avec un motif.

À faire **avant la passation** : sinon les bouteilles vendues pendant la coupure apparaissent
comme manquantes au comptage. Une saisie dans une session déjà fermée est réservée au patron
(l'écart de caisse de la session est alors recalculé).

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
