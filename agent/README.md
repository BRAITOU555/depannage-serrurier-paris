# Agent de pages locales

Chaque jour, l'agent crée de nouvelles pages locales pour dsdepannage.fr et les publie tout seul.

## Ce qu'il fait à chaque passage
1. Choisit les pages manquantes (service × commune, listées dans `targets.json` et `config.json`).
2. Récupère quelques faits locaux sûrs sur la commune. Il n'utilise aucun lieu qui ne soit pas dans cette liste.
3. Rédige la page avec Claude, au gabarit des pages existantes.
4. Contrôle avant publication : expressions « trop IA », prix / délais / garanties / avis inventés, longueur,
   présence de la commune et du code postal, et similarité MinHash avec toutes les pages du site (seuil 0,30).
   Si la page est refusée, il la réécrit en tenant compte des raisons (3 essais maximum), sinon il l'abandonne.
5. Écrit la page, met à jour `sitemap.xml`, `urls-a-indexer.txt` et la page du département, puis pousse sur GitHub.

Le rapport de la dernière exécution est dans `agent/state/last_run.md`, l'historique dans `agent/state/log.jsonl`.

## Mise en route (une seule fois)
1. Dépôt GitHub → Settings → Secrets and variables → Actions → New repository secret : `ANTHROPIC_API_KEY`.
2. Onglet Actions → « Agent pages locales » → Run workflow pour un premier essai (par exemple limite 2).
3. Ensuite il tourne seul chaque jour (05h17 UTC).

## Réglages (`config.json`)
- `daily_limit` : pages par jour (8 par défaut). Montez progressivement, et surveillez l'indexation dans Search Console.
- `similarity_threshold` : plus bas = plus strict.
- `banned_phrases` et `forbidden_claims_regex` : ajoutez ici tout ce qui sonne faux ou « IA ».
- `services` : les types de pages créés pour chaque commune.
- `use_web_search` : passer à `true` pour que l'agent vérifie les faits locaux sur le web (si disponible sur votre compte API).

## Ajouter des communes
Ajoutez-les dans `targets.json` (nom, code postal, département). Pour un nouveau département, ajoutez-le aussi dans `departments`.

## Test sans API
`python agent/agent.py --mock --limit 3 --dry-run`
