# Déployer la démo sur Render

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

## 4. Variables d'environnement

| Variable | Rôle | Valeur sur Render |
| --- | --- | --- |
| `DATABASE_URL` | Base PostgreSQL | Fournie par la base `caviste-db` |
| `CAVISTE_SECRET` | Signature des jetons | Générée |
| `CAVISTE_SHOP_NAME` | Nom par défaut de la cave | `La Cave` (modifiable ensuite dans Réglages) |
| `CAVISTE_CURRENCY` | Devise affichée | `FCFA` |
| `PYTHON_VERSION` | Version Python | `3.12.8` |
