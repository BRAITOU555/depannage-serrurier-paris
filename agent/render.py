"""Gabarit HTML identique à celui des pages existantes du site (classes de styles.css / pages-virage.css)."""
import json
from html import escape as e


def j(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def header(site):
    return (
        '<header class="site-header"><nav class="nav-wrap" aria-label="Navigation principale">'
        '<a class="brand" href="/" aria-label="Accueil ' + e(site["brand"]) + '"><span class="brand-mark">D</span>'
        '<span><strong>Dépannage</strong><small>Serrurier Paris</small></span></a>'
        '<button class="menu-toggle" type="button" aria-expanded="false" aria-controls="main-menu">☰</button>'
        '<div class="main-menu" id="main-menu"><a href="/#depannage">Dépannage</a><a href="/#services">Services</a>'
        '<a href="/#zones">Zones</a><a href="#faq">FAQ</a><a href="#contact">Contact</a>'
        '<a class="phone-btn" href="tel:' + site["phone_tel"] + '">' + e(site["phone_display"]) + '</a></div></nav></header>\n'
    )


def footer_and_scripts(site, col_title, col_links, area_title, area_text, cta_label):
    links = "".join('<a href="%s">%s</a>' % (e(h), e(t)) for h, t in col_links)
    tel = site["phone_tel"]
    return (
        '<footer class="footer"><div class="footer-grid"><div><a class="brand footer-brand" href="/"><span class="brand-mark">D</span>'
        '<span><strong>Dépannage</strong><small>Serrurier Paris</small></span></a></div>'
        '<div><h3>' + e(col_title) + '</h3>' + links + '</div>'
        '<div><h3>' + e(area_title) + '</h3><p>' + e(area_text) + '</p></div>'
        '<div><h3>Appel direct</h3><p><a href="tel:' + tel + '">' + e(site["phone_display"]) + '</a></p><p>Devis annoncé avant intervention</p></div></div>'
        '<div class="footer-bottom"><span>© ' + e(site["brand"]) + ' · SIRET : ' + site["siret"] + '</span><a href="/">Accueil</a><a href="#contact">Contact</a></div></footer>\n'
        '<div class="floating-cta"><a href="tel:' + tel + '"><strong>Appel direct</strong><span>' + e(site["phone_display"]) + '</span></a>'
        '<a href="#contact"><strong>Devis</strong><span>' + e(cta_label) + '</span></a></div>\n'
        "<script>const button=document.querySelector('.menu-toggle');const menu=document.querySelector('.main-menu');"
        "button.addEventListener('click',()=>{const opened=menu.classList.toggle('is-open');"
        "button.setAttribute('aria-expanded',opened?'true':'false');});</script>\n"
        '  <script src="../assets/js/menu-fix.js"></script>\n</body>\n</html>\n'
    )


def head(title, desc, canonical, jsonld=None):
    out = (
        '<!doctype html>\n<html lang="fr">\n<head>\n  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '  <title>' + e(title) + '</title>\n'
        '  <meta name="description" content="' + e(desc, quote=True) + '">\n'
        '  <link rel="canonical" href="' + e(canonical) + '">\n'
        '  <link rel="stylesheet" href="../assets/css/styles.css">\n'
        '  <link rel="stylesheet" href="../assets/css/pages-virage.css">\n'
    )
    if jsonld:
        out += '  <script type="application/ld+json">' + j(jsonld).replace("</", "<\\/") + '</script>\n'
    return out + '</head>\n<body class="virage-page">\n'


def render_page(c, job, site, siblings, same_commune, hub_href):
    """c : contenu généré ; job : dict commune/service/url ; siblings/same_commune : listes (href, libellé)."""
    url = job["url"]
    commune, cp, dept = job["commune"], job["cp"], job["dept_name"]
    area = "%s %s" % (commune, cp)
    faq_ld = [{"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}} for q in c["faq"]]
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "LocalBusiness", "@id": url + "#business", "name": site["brand"], "url": site["base_url"] + "/",
         "telephone": site["phone_display"], "priceRange": site["price_range"], "areaServed": [commune, cp, dept],
         "address": {"@type": "PostalAddress", "addressLocality": commune, "postalCode": cp, "addressCountry": "FR"},
         "openingHoursSpecification": [{"@type": "OpeningHoursSpecification",
                                        "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                                        "opens": "00:00", "closes": "23:59"}],
         "identifier": {"@type": "PropertyValue", "propertyID": "SIRET", "value": site["siret"]}},
        {"@type": "Service", "@id": url + "#service", "name": c["h1"], "serviceType": job["service_label"],
         "description": c["meta_description"], "provider": {"@id": url + "#business"},
         "areaServed": {"@type": "AdministrativeArea", "name": area}},
        {"@type": "FAQPage", "@id": url + "#faq", "mainEntity": faq_ld},
    ]}
    img = "../images/" + job["hero_image"]
    s = head(c["title"], c["meta_description"], url, jsonld) + header(site) + "<main>\n"
    s += ('  <section class="hero local-hero refined-hero"><div class="hero-inner"><div class="hero-copy">'
          '<p class="breadcrumb"><a href="/">Accueil</a> / ' + e(commune) + '</p><h1>' + e(c["h1"]) + '</h1>'
          '<p class="offer">' + e(c["offer_lead"]) + ' <strong>' + e(c["offer_strong"]) + '</strong></p>'
          '<p>' + e(c["hero_lead"]) + '</p><div class="hero-actions"><a class="btn btn-primary" href="tel:' + site["phone_tel"] + '">Appeler maintenant</a>'
          '<a class="btn btn-light" href="#contact">Demander un devis</a></div></div><div class="hero-visual">'
          '<img class="hero-photo" src="' + e(img) + '" alt="' + e(c["image_alt"], quote=True) + '" fetchpriority="high">'
          '<div class="key-card"><span>' + e(cp) + '</span><strong>' + e(job["service_label"]) + '</strong><em>' + e(commune) + '</em></div></div></div></section>\n')
    s += '  <section class="stats refined-stats">' + "".join(
        '<div class="stat-card%s"><strong>%s</strong><span>%s</span></div>' % (" hot" if i == 0 else "", e(x["strong"]), e(x["span"]))
        for i, x in enumerate(c["stats"])) + '</section>\n'
    s += '  <section class="editorial-ribbon">' + "".join(
        '<article><span>0%d</span><h3>%s</h3><p>%s</p></article>' % (i + 1, e(x["h3"]), e(x["p"])) for i, x in enumerate(c["ribbon"])) + '</section>\n'
    s += ('  <section class="intro local-intro"><div class="section-heading"><h2>' + e(c["intro_h2"]) + '</h2>' +
          "".join("<p>%s</p>" % e(p) for p in c["intro_p"]) + '</div>' +
          ('<div class="zone-cloud">' + "".join("<span>%s</span>" % e(z) for z in c["places"]) + '</div>' if c["places"] else "") + '</section>\n')
    s += ('  <section class="local-layout gray"><div class="local-layout-inner"><div class="context-panel"><img src="' + e(img) + '" alt="' +
          e(c["image_alt"], quote=True) + '" loading="lazy"><div><h2>' + e(c["context_h2"]) + '</h2>' +
          "".join("<p>%s</p>" % e(p) for p in c["context_p"]) + '</div></div><aside class="note-card"><h3>' + e(c["note_title"]) + '</h3><ul>' +
          "".join("<li>%s</li>" % e(i) for i in c["note_items"]) + '</ul></aside></div></section>\n')
    s += ('  <section class="long-copy"><div class="section-heading"><h2>' + e(c["long_h2"]) + '</h2>' +
          "".join("<p>%s</p>" % e(p) for p in c["long_intro"]) + '</div><div class="long-grid airy">' +
          "".join("<article><h3>%s</h3>%s</article>" % (e(a["h3"]), "".join("<p>%s</p>" % e(p) for p in a["p"])) for a in c["long_articles"]) +
          '</div></section>\n')
    s += ('  <section class="detail-section"><div class="section-heading"><h2>' + e(c["details_h2"]) + '</h2><p>' + e(c["details_intro"]) +
          '</p></div><div class="detail-list refined-details">' +
          "".join("<details%s><summary>%s</summary><p>%s</p></details>" % (" open" if i == 0 else "", e(d["summary"]), e(d["p"])) for i, d in enumerate(c["details"])) +
          '</div></section>\n')
    s += ('  <section class="faq gray" id="faq"><div class="section-heading"><h2>' + e(c["faq_h2"]) + '</h2></div><div class="faq-list">' +
          "".join("<details%s><summary>%s</summary><p>%s</p></details>" % (" open" if i == 0 else "", e(q["q"]), e(q["a"])) for i, q in enumerate(c["faq"])) +
          '</div></section>\n')
    s += ('  <section class="info-content" id="contexte-local"><div class="content-grid"><div><h2>' + e(c["local_h2"]) + '</h2>' +
          "".join("<p>%s</p>" % e(p) for p in c["local_p"]) + '</div></div></section>\n')
    hubs = [("../changement-serrure-paris.html", "Changement de serrure à Paris"), ("../tarifs-serrurier-paris.html", "Tarifs serrurier Paris")]
    s += ('<section class="info-content"><div class="content-grid"><div><p>Pour aller plus loin : ' +
          " et ".join('<a href="%s">%s</a>' % (h, t) for h, t in hubs) + '.</p></div></div></section>\n')
    s += ('    <section class="zones"><div class="section-heading"><h2>Autres pages utiles autour de ' + e(commune) + '</h2></div>'
          '<div class="zone-family-grid single"><article class="zone-family-card"><h3>' + e(commune) + ' : autres interventions</h3><div>' +
          "".join('<a href="%s">%s</a>' % (e(h), e(t)) for h, t in same_commune) +
          '<a href="' + e(hub_href) + '">Toutes les communes du ' + e(dept) + '</a></div></article>' +
          ('<article class="zone-family-card wide"><h3>' + e(job["service_label"]) + ' dans les communes voisines</h3><div>' +
           "".join('<a href="%s">%s</a>' % (e(h), e(t)) for h, t in siblings) + '</div></article>' if siblings else "") +
          '</div></section>\n')
    s += ('  <section class="contact" id="contact"><div><h2>' + e(c["contact_h2"]) + '</h2><p>' + e(c["contact_text"]) +
          '</p><p class="big-phone"><a href="tel:' + site["phone_tel"] + '">' + e(site["phone_display"]) + '</a></p></div>'
          '<form class="contact-form"><input type="text" name="name" placeholder="Nom et prénom" required>'
          '<input type="email" name="email" placeholder="E-mail" required><input type="tel" name="phone" placeholder="Téléphone">'
          '<select name="service" required>' + "".join("<option>%s</option>" % e(o) for o in c["form_options"]) + '</select>'
          '<textarea name="message" placeholder="' + e(job["form_message"], quote=True) + '" required></textarea>'
          '<label class="check"><input type="checkbox" required> J\'accepte d\'être recontacté dans le cadre de ma demande.</label>'
          '<button class="btn btn-primary" type="submit">Envoyer</button></form></section>\n</main>\n')
    s += footer_and_scripts(site, job["service_label"] + " " + commune, same_commune[:3] or [(hub_href, "Communes du " + dept)],
                            "Zone d'intervention", "%s (%s), %s" % (commune, cp, dept), commune)
    return s


def render_hub(site, dept_name, dept_slug, groups, today):
    """groups : liste de (commune, cp, [(href, libellé)])"""
    title = "Serrurier en %s : communes desservies" % dept_name
    desc = "Liste des communes du %s où intervient le serrurier de dépannage, avec les pages dédiées à chaque intervention." % dept_name
    url = "%s/%s/" % (site["base_url"], dept_slug)
    s = head(title, desc, url) + header(site) + "<main>\n"
    s += ('  <section class="hero local-hero refined-hero"><div class="hero-inner"><div class="hero-copy"><p class="breadcrumb"><a href="/">Accueil</a> / ' +
          e(dept_name) + '</p><h1>Serrurier en ' + e(dept_name) + '</h1><p>' + e(desc) + '</p><div class="hero-actions"><a class="btn btn-primary" href="tel:' +
          site["phone_tel"] + '">Appeler maintenant</a></div></div></div></section>\n')
    s += '    <section class="zones"><div class="section-heading"><h2>Communes et interventions</h2></div><div class="zone-family-grid">'
    for commune, cp, links in groups:
        s += '<article class="zone-family-card"><h3>%s (%s)</h3><div>%s</div></article>' % (
            e(commune), e(cp), "".join('<a href="%s">%s</a>' % (e(h), e(t)) for h, t in links))
    s += '</div></section>\n</main>\n'
    s += footer_and_scripts(site, "Départements", [("/", "Accueil")], "Zone d'intervention", dept_name, dept_name)
    return s
