#!/usr/bin/env python3
"""Agent de création de pages locales pour dsdepannage.fr.

Chaque exécution : choisit les pages manquantes, rédige avec Claude, contrôle (style, affirmations, doublons),
publie (fichier HTML, sitemap, liste d'indexation, page de département) et écrit un rapport.
Les écritures se font dans le dépôt ; le commit et le push sont faits par le workflow GitHub Actions.
"""
import argparse
import datetime
import json
import os
import random
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import similarity  # noqa: E402
import render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
AGENT = Path(__file__).resolve().parent
STATE = AGENT / "state"


def slugify(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf8"))
    except FileNotFoundError:
        return default


# ---------------------------------------------------------------- état du site

def page_text(html):
    """Texte éditorial d'une page : sans nav, formulaire, liens, scripts, pied de page."""
    m = re.search(r"<main>(.*?)</main>", html, re.S)
    body = m.group(1) if m else html
    for tag in ("script", "form", "a", "nav", "style"):
        body = re.sub(r"<%s\b.*?</%s>" % (tag, tag), " ", body, flags=re.S)
    body = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", body).strip()


def build_index():
    index = {}
    for p in ROOT.rglob("*.html"):
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith((".git/", "agent/", "google-indexing/", "boutique/", "node_modules/")):
            continue
        try:
            txt = page_text(p.read_text(encoding="utf8", errors="ignore"))
        except OSError:
            continue
        if len(txt.split()) > 80:
            index[rel] = similarity.signature(txt)
    return index


# ---------------------------------------------------------------- planification

def plan_jobs(cfg, targets, limit, failed):
    depts = {d["slug"]: d for d in targets["departments"]}
    today = datetime.date.today()
    jobs = []
    # une page par service d'abord pour chaque commune, en commençant par les communes les moins couvertes
    entries = []
    for c in targets["communes"]:
        c = dict(c, slug=slugify(c["name"]))
        existing = sum(1 for s in cfg["services"] if (ROOT / c["dept"] / ("%s-%s-%s.html" % (s["slug"], c["slug"], c["cp"]))).exists())
        entries.append((existing, c))
    entries.sort(key=lambda x: x[0])
    for existing, c in entries:
        for s in cfg["services"]:
            rel = "%s/%s-%s-%s.html" % (c["dept"], s["slug"], c["slug"], c["cp"])
            if (ROOT / rel).exists():
                continue
            last = failed.get(rel)
            if last and (today - datetime.date.fromisoformat(last)).days < cfg["retry_failed_after_days"]:
                continue
            jobs.append({
                "rel": rel, "url": "%s/%s" % (cfg["site"]["base_url"], rel), "commune": c["name"], "commune_slug": c["slug"],
                "cp": c["cp"], "dept": c["dept"], "dept_name": depts[c["dept"]]["name"], "service": s["slug"],
                "service_label": s["label"], "topic": s["topic"], "hero_image": s["hero_image"], "form_message": s["form_message"],
            })
            break  # un service par commune et par passage : la couverture avance de façon régulière
        if len(jobs) >= limit:
            break
    return jobs


# ---------------------------------------------------------------- rédaction

def _str(desc):
    return {"type": "string", "description": desc}


def _arr(items, n, desc=""):
    return {"type": "array", "items": items, "minItems": n, "maxItems": n, "description": desc}


SCHEMA = {
    "type": "object",
    "properties": {
        "title": _str("balise title, 55 à 65 caractères, avec la commune"),
        "meta_description": _str("120 à 155 caractères, concrète, sans slogan"),
        "h1": _str("titre H1 avec le service et la commune"),
        "offer_lead": _str("début de phrase courte avant le point fort, finit par deux-points"),
        "offer_strong": _str("point fort court, vrai et vérifiable (par ex. devis annoncé avant travaux)"),
        "hero_lead": _str("une à deux phrases d'accroche"),
        "image_alt": _str("texte alternatif de la photo, descriptif"),
        "stats": _arr({"type": "object", "properties": {"strong": _str("mot ou 2 mots"), "span": _str("précision courte")}, "required": ["strong", "span"]}, 3),
        "ribbon": _arr({"type": "object", "properties": {"h3": _str("étape"), "p": _str("une phrase")}, "required": ["h3", "p"]}, 4,
                       "quatre étapes réelles de l'intervention"),
        "intro_h2": _str("titre de la première section"),
        "intro_p": _arr(_str("paragraphe de 2 à 4 phrases"), 2),
        "places": {"type": "array", "items": {"type": "string"}, "maxItems": 6,
                   "description": "lieux ou quartiers de la commune, UNIQUEMENT pris dans la liste de faits fournie ; vide si aucun"},
        "context_h2": _str("titre"),
        "context_p": _arr(_str("paragraphe"), 2),
        "note_title": _str("titre de l'encadré"),
        "note_items": _arr(_str("information utile à donner au serrurier"), 5),
        "long_h2": _str("titre"),
        "long_intro": _arr(_str("paragraphe"), 2),
        "long_articles": _arr({"type": "object", "properties": {"h3": _str("titre"), "p": _arr(_str("paragraphe"), 2)}, "required": ["h3", "p"]}, 2),
        "details_h2": _str("titre"),
        "details_intro": _str("une phrase"),
        "details": _arr({"type": "object", "properties": {"summary": _str("question courte ou point technique"), "p": _str("réponse de 1 à 3 phrases")},
                         "required": ["summary", "p"]}, 5),
        "faq_h2": _str("titre de la FAQ"),
        "faq": _arr({"type": "object", "properties": {"q": _str("question que se pose vraiment un client"), "a": _str("réponse de 2 à 3 phrases")},
                     "required": ["q", "a"]}, 6),
        "local_h2": _str("titre de la section locale"),
        "local_p": _arr(_str("paragraphe"), 3),
        "contact_h2": _str("titre"),
        "contact_text": _str("ce qu'il faut préciser à l'appel, 2 phrases"),
        "form_options": _arr(_str("option du formulaire"), 4),
    },
    "required": ["title", "meta_description", "h1", "offer_lead", "offer_strong", "hero_lead", "image_alt", "stats", "ribbon", "intro_h2",
                 "intro_p", "places", "context_h2", "context_p", "note_title", "note_items", "long_h2", "long_intro", "long_articles",
                 "details_h2", "details_intro", "details", "faq_h2", "faq", "local_h2", "local_p", "contact_h2", "contact_text", "form_options"],
}

SYSTEM = """Tu rédiges des pages pour le site d'un serrurier de dépannage en Île-de-France.

Voix : un artisan qui explique son métier à un voisin. Phrases courtes et concrètes. Vouvoiement. Aucune formule publicitaire.
Écris comme une personne, pas comme une brochure : pas de « véritable », « incontournable », « au cœur de », « n'hésitez pas »,
« solutions adaptées », « garantir », « sérénité ». Pas de tiret long (—), pas de points d'exclamation, pas de listes d'adjectifs.
Varie la longueur des phrases. Commence les paragraphes de manières différentes.

Règles de fond, impératives :
- Tu n'inventes RIEN sur la commune. Pour les lieux, quartiers, gares, monuments, types d'habitat : seulement ce qui figure dans la liste de faits fournie.
  Si la liste est courte ou vide, parle surtout du métier (serrures, portes, situations) et cite la commune sans anecdote locale.
- Aucun prix chiffré, aucun délai chiffré, aucune garantie, certification, ancienneté, nombre de clients, avis. Tu peux dire que le devis est annoncé avant l'intervention.
- Le contenu technique doit être juste : décris ce qu'un serrurier fait réellement (diagnostic, technique d'ouverture, mesure du cylindre, test de fermeture).
- Chaque page doit apporter des informations précises propres à son service : types de portes, causes de panne, erreurs à éviter, ce qu'il faut préparer.
- Le numéro de téléphone n'apparaît pas dans les textes (il est ajouté par le gabarit).
Réponds uniquement en appelant l'outil fournis."""


def build_prompt(job, facts, feedback):
    facts_txt = "\n".join("- " + f for f in facts) if facts else "(aucun fait local vérifié : ne cite aucun lieu précis)"
    p = (
        "Page à écrire\n"
        "- Commune : %s (%s), département : %s\n"
        "- Service : %s\n"
        "- Contenu du service : %s\n\n"
        "Faits locaux vérifiés (seule source autorisée pour les lieux) :\n%s\n\n"
        "Longueur visée : environ 900 à 1200 mots au total sur l'ensemble des champs. "
        "Le titre et le H1 contiennent le service et le nom de la commune ; le code postal %s apparaît au moins une fois dans le texte."
        % (job["commune"], job["cp"], job["dept_name"], job["service_label"], job["topic"], facts_txt, job["cp"])
    )
    if feedback:
        p += "\n\nLa version précédente a été refusée pour ces raisons, corrige-les :\n" + "\n".join("- " + f for f in feedback)
    return p


def call_claude(cfg, job, facts, feedback):
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=cfg["model"], max_tokens=8000, system=SYSTEM,
        tools=[{"name": "ecrire_page", "description": "Renvoie la page rédigée.", "input_schema": SCHEMA}],
        tool_choice={"type": "tool", "name": "ecrire_page"},
        messages=[{"role": "user", "content": build_prompt(job, facts, feedback)}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Réponse sans contenu structuré")


def get_facts(cfg, job):
    """Faits locaux : mis en cache ; vide si le modèle n'est pas certain."""
    cache = STATE / "facts" / ("%s-%s.json" % (job["commune_slug"], job["cp"]))
    cached = load_json(cache)
    if cached is not None:
        return cached
    import anthropic
    client = anthropic.Anthropic()
    prompt = (
        "Pour la commune de %s (%s, %s), donne au plus 6 faits locaux SÛRS et neutres utiles pour une page de serrurier : "
        "quartiers, gares ou lignes de transport, grands types d'habitat. N'inclus un fait que si tu en es certain. "
        "Réponds par une liste JSON de phrases courtes, rien d'autre. Si tu as le moindre doute : []." % (job["commune"], job["cp"], job["dept_name"])
    )
    kwargs = {}
    if cfg.get("use_web_search"):
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]
    resp = client.messages.create(model=cfg["model"], max_tokens=1200, messages=[{"role": "user", "content": prompt}], **kwargs)
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    m = re.search(r"\[.*\]", text, re.S)
    try:
        facts = [str(x) for x in json.loads(m.group(0))][:6] if m else []
    except ValueError:
        facts = []
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf8")
    return facts


# ---------------------------------------------------------------- mode test sans API

def mock_content(job):
    rnd = random.Random(job["rel"])
    vocab = ("porte serrure cylindre clé barillet pêne gâche palier immeuble étage diagnostic ouverture technicien outil pose mesure test "
             "fermeture blindée verrou poignée rosace bâti vantail ressort came entrée logement voisin gardien couloir").split()

    def sent(n=14):
        return " ".join(rnd.choice(vocab) for _ in range(n)).capitalize() + "."

    def para(k=4):
        return " ".join(sent(rnd.randint(9, 16)) for _ in range(k))
    c, cp = job["commune"], job["cp"]
    return {
        "title": "%s %s : %s" % (job["service_label"], c, cp), "meta_description": "Test %s %s %s" % (job["service_label"], c, cp),
        "h1": "%s à %s" % (job["service_label"], c), "offer_lead": "Devis :", "offer_strong": "annoncé avant intervention",
        "hero_lead": sent(), "image_alt": "illustration %s" % c,
        "stats": [{"strong": "Devis", "span": sent(3)}, {"strong": cp, "span": c}, {"strong": "Test", "span": sent(3)}],
        "ribbon": [{"h3": "Étape %d" % i, "p": sent()} for i in range(1, 5)],
        "intro_h2": "Intro %s" % c, "intro_p": [para(), para()], "places": [],
        "context_h2": "Contexte", "context_p": [para(), para()], "note_title": "À préciser", "note_items": [sent(4) for _ in range(5)],
        "long_h2": "Détail", "long_intro": [para(), para()],
        "long_articles": [{"h3": "Cas %d" % i, "p": [para(), para()]} for i in (1, 2)],
        "details_h2": "Points techniques", "details_intro": sent(),
        "details": [{"summary": "Point %d" % i, "p": para(2)} for i in range(5)],
        "faq_h2": "FAQ %s" % c, "faq": [{"q": "Question %d %s ?" % (i, c), "a": para(2)} for i in range(6)],
        "local_h2": "Sur place à %s (%s)" % (c, cp), "local_p": [para(), para(), para()],
        "contact_h2": "Contact", "contact_text": sent(), "form_options": ["%s %s" % (job["service_label"], c), "Autre", "Urgence", "Devis"],
    }


# ---------------------------------------------------------------- contrôle qualité

def all_text(c):
    parts = []

    def walk(x):
        if isinstance(x, str):
            parts.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(c)
    return "\n".join(parts)


def validate(cfg, c, job, facts, index):
    problems = []
    txt = all_text(c)
    low = txt.lower().replace("’", "'")
    for ph in cfg["banned_phrases"]:
        if ph.lower().replace("’", "'") in low:
            problems.append("expression interdite : « %s »" % ph)
    for rx in cfg["forbidden_claims_regex"]:
        m = re.search(rx, txt, re.I)
        if m:
            problems.append("affirmation interdite (prix, délai, garantie, avis, tiret long…) : « %s »" % m.group(0))
    if txt.count("!") > 0:
        problems.append("point d'exclamation interdit")
    n = len(similarity.words(txt))
    if n < cfg["min_words"]:
        problems.append("texte trop court (%d mots, minimum %d)" % (n, cfg["min_words"]))
    if job["commune"].lower() not in (c["title"] + " " + c["h1"]).lower():
        problems.append("la commune doit figurer dans le title et le H1")
    if job["cp"] not in txt:
        problems.append("le code postal %s doit figurer dans le texte" % job["cp"])
    fact_blob = " ".join(facts).lower()
    for place in c["places"]:
        if place.lower() not in fact_blob:
            problems.append("lieu « %s » absent de la liste de faits vérifiés : à retirer" % place)
    sig = similarity.signature(page_text_from_content(c))
    path, score = similarity.most_similar(sig, index)
    if score > cfg["similarity_threshold"]:
        problems.append("trop proche de %s (similarité %.2f, maximum %.2f) : reformule avec d'autres exemples et un autre plan" % (path, score, cfg["similarity_threshold"]))
    return problems, sig, (path, score)


def page_text_from_content(c):
    return all_text(c)


# ---------------------------------------------------------------- publication

def sibling_links(cfg, job, existing_pages):
    """Liens vers le même service dans d'autres communes du département, et autres services dans la commune."""
    labels = {s["slug"]: s["label"] for s in cfg["services"]}
    sib, same = [], []
    for rel in sorted(existing_pages):
        if not rel.startswith(job["dept"] + "/") or rel.endswith("/index.html"):
            continue
        name = rel.split("/")[1][:-5]
        m = re.match(r"(.+?)-(\d{5})$", name)
        if not m:
            continue
        stem = m.group(1)
        for slug in sorted(labels, key=len, reverse=True):
            if stem.startswith(slug + "-"):
                commune_slug = stem[len(slug) + 1:]
                break
        else:
            continue
        label = labels[slug]
        cname = commune_slug.replace("-", " ").title()
        if slug == job["service"] and commune_slug != job["commune_slug"]:
            sib.append((os.path.basename(rel), "%s %s" % (label, cname)))
        elif commune_slug == job["commune_slug"] and slug != job["service"]:
            same.append((os.path.basename(rel), "%s %s" % (label, job["commune"])))
    random.Random(job["rel"]).shuffle(sib)
    return sib[:8], same[:4]


def update_sitemap(urls, today):
    sm = ROOT / "sitemap.xml"
    s = sm.read_text(encoding="utf8")
    add = ""
    for u in urls:
        if "<loc>%s</loc>" % u not in s:
            add += "  <url><loc>%s</loc><lastmod>%s</lastmod></url>\n" % (u, today)
    if add:
        s = s.replace("</urlset>", add + "</urlset>")
        sm.write_text(s, encoding="utf8")


def update_indexing_list(urls):
    f = ROOT / "urls-a-indexer.txt"
    cur = f.read_text(encoding="utf8") if f.exists() else ""
    have = set(cur.split())
    new = [u for u in urls if u not in have]
    if new:
        f.write_text(cur.rstrip("\n") + "\n" + "\n".join(new) + "\n", encoding="utf8")


def rebuild_hubs(cfg, targets):
    labels = {s["slug"]: s["label"] for s in cfg["services"]}
    changed = []
    for d in targets["departments"]:
        folder = ROOT / d["slug"]
        if not folder.exists():
            continue
        by_commune = {}
        for p in sorted(folder.glob("*.html")):
            if p.name == "index.html":
                continue
            m = re.match(r"(.+?)-(\d{5})\.html$", p.name)
            if not m:
                continue
            for slug in sorted(labels, key=len, reverse=True):
                if m.group(1).startswith(slug + "-"):
                    cs = m.group(1)[len(slug) + 1:]
                    by_commune.setdefault((cs, m.group(2)), []).append((p.name, labels[slug]))
                    break
        names = {slugify(c["name"]): c["name"] for c in targets["communes"]}
        groups = [(names.get(cs, cs.replace("-", " ").title()), cp, links) for (cs, cp), links in sorted(by_commune.items())]
        if groups:
            (folder / "index.html").write_text(render.render_hub(cfg["site"], d["name"], d["slug"], groups, ""), encoding="utf8")
            changed.append("%s/%s/" % (cfg["site"]["base_url"], d["slug"]))
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="nombre de pages à créer (défaut : daily_limit)")
    ap.add_argument("--mock", action="store_true", help="test sans API : contenu factice")
    ap.add_argument("--dry-run", action="store_true", help="ne rien écrire")
    args = ap.parse_args()

    cfg = load_json(AGENT / "config.json")
    targets = load_json(AGENT / "targets.json")
    STATE.mkdir(exist_ok=True)
    failed = load_json(STATE / "failed.json", {})
    limit = args.limit or cfg["daily_limit"]
    if not args.mock and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY absent : ajoutez-le dans les secrets du dépôt GitHub.")

    index = build_index()
    jobs = plan_jobs(cfg, targets, limit, failed)
    today = datetime.date.today().isoformat()
    report, published = [], []
    for job in jobs:
        facts = [] if args.mock else get_facts(cfg, job)
        feedback, ok = [], False
        for attempt in range(1, cfg["max_attempts"] + 1):
            try:
                content = mock_content(job) if args.mock else call_claude(cfg, job, facts, feedback)
            except Exception as exc:  # erreur d'API : on s'arrête proprement, rien n'est à moitié publié
                report.append("ERREUR API sur %s : %s" % (job["rel"], exc))
                break
            problems, sig, (near, score) = validate(cfg, content, job, facts, index)
            if not problems:
                ok = True
                break
            feedback = problems
        if not ok:
            if not any(r.startswith("ERREUR API sur " + job["rel"]) for r in report):
                report.append("REFUSÉE %s : %s" % (job["rel"], " | ".join(feedback)))
                failed[job["rel"]] = today
            else:
                break
            continue
        existing = set(index.keys())
        sib, same = sibling_links(cfg, job, existing)
        html = render.render_page(content, job, cfg["site"], sib, same, "index.html")
        if not args.dry_run:
            out = ROOT / job["rel"]
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(html, encoding="utf8")
        index[job["rel"]] = sig  # les pages du même lot comptent pour le contrôle de doublon suivant
        published.append(job["url"])
        report.append("PUBLIÉE %s (essai %d, similarité max %.2f avec %s)" % (job["rel"], attempt, score, near))
        with open(STATE / "log.jsonl", "a", encoding="utf8") as fh:
            fh.write(json.dumps({"date": today, "url": job["url"], "attempts": attempt, "max_similarity": round(score, 3)}, ensure_ascii=False) + "\n")

    if published and not args.dry_run:
        hubs = rebuild_hubs(cfg, targets)
        update_sitemap(published + hubs, today)
        update_indexing_list(published + hubs)
    if not args.dry_run:
        (STATE / "failed.json").write_text(json.dumps(failed, indent=1), encoding="utf8")
        (STATE / "last_run.md").write_text("# Dernière exécution : %s\n\n%s\n" % (today, "\n".join("- " + r for r in report) or "- aucune page à créer"), encoding="utf8")
    print("\n".join(report) or "Aucune page à créer.")
    print("%d page(s) publiée(s)." % len(published))


if __name__ == "__main__":
    main()
