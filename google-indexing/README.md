# Google Indexing API - dsdepannage.fr

Ce dossier permet d'envoyer une liste d'URLs de `dsdepannage.fr` a la Google Indexing API avec Node.js.

Important: l'API d'indexation Google est officiellement prevue pour certains contenus specifiques, notamment les offres d'emploi et les evenements livestream. Pour un site local classique, le sitemap et Google Search Console restent la methode normale.

## Installation et lancement

1. Activer la Google Indexing API dans Google Cloud.
2. Creer un compte de service.
3. Telecharger la cle JSON du compte de service.
4. Renommer la cle en `service-account.json`.
5. Placer `service-account.json` dans ce dossier `google-indexing`.
6. Ajouter l'email du compte de service dans Google Search Console comme proprietaire ou utilisateur complet.
7. Ajouter les URLs a envoyer dans `urls.txt`, une URL par ligne.
8. Installer les dependances depuis ce dossier:

```bash
cd google-indexing
npm install
```

9. Lancer l'envoi:

```bash
npm start
```

La commande historique fonctionne aussi:

```bash
npm run index
```

## URLs autorisees

Le script accepte uniquement les URLs qui commencent par:

- `https://dsdepannage.fr/`
- `https://www.dsdepannage.fr/`

Les lignes vides sont ignorees. Les autres domaines sont ignores et affiches dans le terminal.

## Fichiers

- `indexing.js`: script Node.js d'envoi a la Google Indexing API.
- `urls.txt`: liste des URLs a envoyer.
- `service-account.json`: cle privee Google Cloud a ajouter localement uniquement.
- `sent-log.csv`: journal des envois et erreurs.
- `batches/`: fichiers de lots prepares pour reprise.
- `.gitignore`: exclut la cle privee et `node_modules`.

## Erreurs Google a verifier

- `Permission denied. Failed to verify the URL ownership.`:
  le compte de service n'a pas acces a la propriete Search Console qui couvre l'URL. Ajouter l'email `client_email` du fichier `service-account.json` dans Search Console comme proprietaire ou utilisateur complet.

- `Quota exceeded`:
  quota journalier Google Indexing API atteint. Relancer le lendemain ou demander une augmentation de quota dans Google Cloud.

- `API has not been used` ou `disabled`:
  l'API Google Indexing n'est pas activee sur le projet Google Cloud du compte de service.

## Commande exacte

Depuis la racine du projet:

```bash
cd google-indexing
npm install
npm start
```
