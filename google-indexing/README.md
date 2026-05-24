# Google Indexing API - dsdepannage.fr

Ce dossier permet d'envoyer une liste d'URLs de `dsdepannage.fr` a la Google Indexing API avec Node.js.

Important: l'API d'indexation Google est officiellement prevue pour certains contenus specifiques, notamment les offres d'emploi et les evenements livestream. Pour un site local classique, le sitemap et Google Search Console restent la methode normale.

## Installation

1. Activer la Google Indexing API dans Google Cloud.
2. Creer un compte de service.
3. Telecharger la cle JSON du compte de service.
4. Renommer la cle en `service-account.json`.
5. Placer `service-account.json` dans ce dossier `google-indexing`.
6. Ajouter l'email du compte de service dans Google Search Console comme proprietaire ou utilisateur complet.
7. Ajouter les URLs a envoyer dans `urls.txt`, une URL par ligne.
8. Installer les dependances:

```bash
npm install
```

9. Lancer l'envoi:

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
- `.gitignore`: exclut la cle privee et `node_modules`.
