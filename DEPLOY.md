# Déployer l'espace en ligne du patron sur Render

Le service Render fonctionne en **miroir** (`CAVISTE_MODE=miroir`) : il ne contient que ce
que le poste de la boutique lui envoie, et ne se modifie pas depuis le web. Seul le
propriétaire peut s'y connecter.

> Pour garder l'ancienne démo web autonome (avec données fictives), retirer `CAVISTE_MODE`
> des variables du service.

Render déploie depuis un dépôt Git (GitHub ou GitLab). Le dossier `Caviste` doit être
la racine du dépôt : `render.yaml`, `requirements.txt` et `app/` à la racine.

## 1. Mettre le code sur GitHub

Dans le dossier `Caviste` :

```
git init
git add .
git commit -m "Caviste : démo web"
```

Puis créer un dépôt vide sur github.com (privé convient) et pousser :

```
git remote add origin https://github.com/<ton-compte>/caviste.git
git branch -M main
git push -u origin main
```

## 2. Créer les services sur Render

1. Sur dashboard.render.com : **New** > **Blueprint**.
2. Connecter le compte GitHub si ce n'est pas fait, choisir le dépôt `caviste`.
3. Render lit `render.yaml` et propose deux ressources : le service web `caviste`
   et la base PostgreSQL `caviste-db`. Cliquer **Apply**.
4. Attendre la fin du premier déploiement (3 à 5 minutes). Le premier démarrage crée
   les tables et charge les données de démonstration.
5. L'adresse publique est de la forme `https://caviste.onrender.com`.

## 3. Ce qu'il faut savoir

- **Plan gratuit** : le service s'endort après 15 minutes sans visite et met 30 à 60
  secondes à se réveiller au premier chargement. Prévenir le client, ou ouvrir la page
  quelques minutes avant la démo.
- **Base gratuite** : Render supprime les bases PostgreSQL gratuites après 30 jours.
  Pour une démo courte c'est suffisant ; au-delà, passer la base en plan payant
  (quelques dollars par mois) ou recréer le Blueprint.
- **Données de démo** : chargées seulement si la base est vide. Pour repartir de zéro,
  supprimer et recréer la base `caviste-db` sur Render, puis redéployer.
- **Comptes de démo** : Patron 0000, Aline 1111, Bénédicte 2222. À changer dans
  l'onglet Équipe avant de laisser le client seul avec l'application.
- **Secret** : `CAVISTE_SECRET` est généré par Render ; il signe les sessions de
  connexion. Ne pas le partager.
- **Mises à jour** : chaque `git push` sur `main` redéploie automatiquement.

## 4. Relier le poste de la boutique

1. Sur Render, service `caviste` > **Environment** : copier la valeur de `CAVISTE_SYNC_KEY`.
2. Sur le poste (application de bureau), se connecter en Patron > **Réglages** >
   **Synchronisation avec le web** : adresse `https://caviste.onrender.com` et la clé. Enregistrer.
3. Le premier envoi est complet (il remplace tout le contenu du miroir), puis seuls les
   changements partent. Sans connexion, ils attendent et partent dès qu'elle revient.
4. Le patron se connecte sur le site avec son code habituel (celui du poste).

Le plan gratuit endort le service : le premier envoi après une pause peut échouer le temps
du réveil (30 à 60 s) ; le poste réessaie tout seul.

## 5. Variables d'environnement

| Variable | Rôle | Valeur sur Render |
| --- | --- | --- |
| `DATABASE_URL` | Base PostgreSQL | Fournie par la base `caviste-db` |
| `CAVISTE_SECRET` | Signature des jetons | Générée |
| `CAVISTE_MODE` | `miroir` : consultation, alimentée par le poste | `miroir` |
| `CAVISTE_SYNC_KEY` | Clé que le poste présente pour envoyer ses données | Générée |
| `TZ` | Fuseau de la boutique (filtres "aujourd'hui") | `Africa/Brazzaville` |
| `CAVISTE_SHOP_NAME` | Nom par défaut de la cave | `La Cave` (modifiable ensuite dans Réglages) |
| `CAVISTE_CURRENCY` | Devise affichée | `FCFA` |
| `PYTHON_VERSION` | Version Python | `3.12.8` |
