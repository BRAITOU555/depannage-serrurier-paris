#!/usr/bin/env bash
set -euo pipefail

URLS_FILE="${1:-indexation-google-manuelle/urls-prioritaires.txt}"

if [[ ! -f "$URLS_FILE" ]]; then
  echo "Fichier introuvable: $URLS_FILE" >&2
  exit 1
fi

total=$(grep -cve '^[[:space:]]*$' "$URLS_FILE")
current=0

echo "Assistant indexation Google"
echo "---------------------------"
echo "URLs a traiter: $total"
echo "Chaque URL est copiee dans le presse-papiers."
echo "Dans Search Console: colle l'URL, lance l'inspection, clique Demander une indexation."
echo "Reviens ici et appuie sur Entree pour copier la suivante."
echo ""

while IFS= read -r url; do
  [[ -z "${url// }" ]] && continue
  current=$((current + 1))

  printf '%s' "$url" | pbcopy
  echo "[$current/$total] URL copiee:"
  echo "$url"
  echo ""

  if [[ "$current" -lt "$total" ]]; then
    read -r -p "Quand tu as valide celle-ci, appuie sur Entree pour la suivante..."
    echo ""
  fi
done < "$URLS_FILE"

echo "Termine: toutes les URLs prioritaires ont ete copiees une par une."
