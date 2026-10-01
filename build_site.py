#!/usr/bin/env python3
"""Generate the static site in docs/: one crawlable page per species plus landing page, sitemap, robots.txt.

    python3 build_site.py

Every page carries its numbers as plain HTML tables (search engines and people without JavaScript see
them); the interactive diagram is loaded on top by assets/viewer.js.
"""
import datetime
import html
import json
import os
import re

import atomlib as al
from elements import ELEMENTS
from species import SPECIES

BASE = "https://muuuun.github.io/atom-energy-levels"
REPO = "https://github.com/Muuuun/atom-energy-levels"
DOCS = os.path.join(al.HERE, "docs")
SITE = "Atomic energy level diagrams"
TIER = {"exp": "measured", "nist": "NIST", "theory": "theory", "model": "model calc."}
ION_USE = {"Be", "Mg", "Ca", "Sr", "Ba", "Yb"}
PRIMARY = {"Li": 7, "Be": 9, "Na": 23, "Mg": 24, "K": 39, "Ca": 40, "Rb": 87, "Sr": 88, "Cs": 133, "Ba": 138, "Yb": 174, "Dy": 164}
CATEGORY = {"alkali": "Alkali metal", "alkaline-earth": "Alkaline earth", "transition": "Transition metal",
            "post-transition": "Post-transition metal", "metalloid": "Metalloid", "nonmetal": "Nonmetal", "noble-gas": "Noble gas",
            "lanthanide": "Lanthanide", "actinide": "Actinide"}


def pname(p):
    return f"{p['element']}-{p['A']}" if p["A"] else p["element"]


def cell(s):
    """Table cell text with $mathtext$ segments -> HTML."""
    parts = re.split(r"(\$[^$]*\$)", str(s))
    return "".join(al.tex_to_html(p[1:-1]) if p.startswith("$") else html.escape(p) for p in parts)


def badge(t):
    return f' <span class="tier {t}">{TIER[t]}</span>' if t in TIER else ""


def fmt_tau(ns):
    for lim, k, u in ((1e3, 1, "ns"), (1e6, 1e3, "µs"), (1e9, 1e6, "ms"), (float("inf"), 1e9, "s")):
        if ns < lim:
            return f"{ns / k:.4g} {u}"


def fmt_d(d):
    return f"{d:.2f}" if d >= 10 else f"{d:.3f}" if d >= 0.1 else f"{d:.3g}"


def cite(atom, s):
    """Citation text linked to its URL (NIST or the literature entry it starts with)."""
    if not s:
        return "–"
    s = re.sub(r"\s*\((from A|via ARC)\)", "", s).strip()
    url = "https://physics.nist.gov/asd" if s.startswith("NIST ASD") else ""
    best = max((k for k in atom.get("sources", {}) if s.startswith(k)), key=len, default=None)
    if best:
        url = atom["sources"][best]
    short = html.escape(s if len(s) <= 90 else s[:89] + "…")
    return f'<a href="{html.escape(url)}" rel="noopener">{short}</a>' if url else short


def table(header, rows, left=(0,), wrap=()):
    th = "".join(f'<th class="{"l" if k in left else ""}" scope="col">{h}</th>' for k, h in enumerate(header))
    body = []
    for r in rows:
        rid = f' id="{r["id"]}"' if isinstance(r, dict) else ""
        cells = r["cells"] if isinstance(r, dict) else r
        tds = "".join(f'<td class="{"l " if k in left else ""}{"wrapcell" if k in wrap else ""}">{c}</td>' for k, c in enumerate(cells))
        body.append(f"<tr{rid}>{tds}</tr>")
    return f'<div class="scroll"><table class="data"><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def nav(pages, current=None):
    cur = ' aria-current="page"'
    links = "".join(f'<a href="../{p["slug"]}/"{cur if p["slug"] == current else ""}>'
                    f'<sup>{p["A"]}</sup>{p["symbol"]}</a>' for p in pages if p["A"])
    return (f'<header class="top"><a class="brand" href="../">{SITE}</a><nav aria-label="Atoms">'
            f'<a href="../">Periodic table</a>{links}</nav></header>')


def atom_page(key, pages):
    cfg = SPECIES[key]
    slug = cfg["slug"]
    with open(os.path.join(al.DATA, key, "atom.json")) as f:
        atom = json.load(f)
    meta, L, T = atom["meta"], atom["levels"], atom["transitions"]
    bound = [t for t in T if t["kind"] != "rydberg"]
    auto = not meta["A"]
    name = f"{meta['element']}-{meta['A']}" if meta["A"] else meta["element"]
    iso = f"<sup>{meta['A']}</sup>{meta['symbol']}" if meta["A"] else meta["symbol"]
    n_d = sum(1 for t in bound if t.get("d") is not None)
    url = f"{BASE}/{slug}/"

    # strongest / best-known lines for the description and the lead paragraph
    ground = sorted([t for t in bound if t["lower"] == 0 and t.get("A")], key=lambda t: -t["A"])[:3]
    lines_txt = ", ".join(f"{t['lam']:.1f} nm" for t in sorted(ground, key=lambda t: t["lam"]))
    title = f"{name} energy level diagram – transitions, wavelengths, dipole matrix elements"
    desc = (f"Interactive energy level (Grotrian) diagram of {name} ({meta['symbol']} I): {len(L)} levels and {len(bound)} transitions "
            f"below 2 µm with vacuum wavelengths, frequencies, dipole matrix elements, lifetimes and hyperfine constants"
            + (f", including the {lines_txt} lines" if lines_txt else "") + ". Measured and NIST data, with sources.")
    ion = (f" Neutral {meta['element'].lower()} is also the starting point for loading {meta['symbol']}<sup>+</sup> ion traps by photoionisation."
           if meta["symbol"] in ION_USE else "")
    counts = {}
    for t in bound:
        counts[t.get("A_tier", "none")] = counts.get(t.get("A_tier", "none"), 0) + 1
    prov = ", ".join(f"{v} {TIER[k]}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]) if k in TIER)

    if auto:
        lead = (f"Energy levels and transitions of neutral {meta['element'].lower()} ({meta['symbol']} I): the {len(bound)} strongest classified "
                f"lines below 2 µm from the NIST Atomic Spectra Database and the {len(L)} levels they connect, each line with its vacuum "
                f"wavelength, frequency and, for {n_d} of them, the reduced dipole matrix element derived from the NIST transition rate. "
                f"Lifetimes, hyperfine constants and isotope shifts from the literature have not been compiled for this element yet.")
    else:
        lead = (f"Energy levels and transitions of neutral {iso} ({meta['symbol']} I, nuclear spin <i>I</i> = {meta['I']}): {len(L)} levels and "
                f"{len(bound)} lines below 2 µm, each with its vacuum wavelength, frequency and, for {n_d} of them, the reduced dipole matrix "
                f"element. Level energies come from the NIST Atomic Spectra Database; transition rates are {prov}.{ion}")
    parts = [f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{url}">
<link rel="icon" href="data:,">
<link rel="stylesheet" href="../assets/style.css">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{url}preview.png">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps({
        "@context": "https://schema.org", "@type": "Dataset",
        "name": f"{name} energy levels and transitions",
        "description": desc, "url": url,
        "keywords": [f"{meta['element']} energy levels", f"{meta['symbol']} energy level diagram", f"{name} transitions",
                     f"{meta['element']} Grotrian diagram", "dipole matrix elements", "atomic transition wavelengths", "hyperfine structure"],
        "isAccessibleForFree": True,
        "creator": {"@type": "Person", "name": "Muuuun", "url": "https://github.com/Muuuun"},
        "distribution": [
            {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{REPO}/blob/main/data/{key}/transitions.csv"},
            {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{REPO}/blob/main/data/{key}/levels.csv"},
            {"@type": "DataDownload", "encodingFormat": "application/pdf", "contentUrl": f"{url}diagram.pdf"}],
        "variableMeasured": ["transition wavelength", "transition frequency", "reduced dipole matrix element", "Einstein A coefficient",
                             "radiative lifetime", "hyperfine constants"],
        "isBasedOn": "https://physics.nist.gov/asd"}, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": SITE, "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": name, "item": url}]})}</script>
</head>
<body>
{nav(pages, slug)}
<main>
<div class="wrap">
<h1>{name} energy level diagram</h1>
<p class="lead">{lead}</p>
<p class="hint">Hover a line or a level to isolate it, click to keep it selected. Scroll to zoom, drag to move.</p>
</div>
<div id="stage">
  <div class="loading"><img src="preview.png" alt="{name} energy level diagram with transition wavelengths and dipole matrix elements" width="1800"></div>
  <div id="zoom">
    <button id="zin" title="Zoom in" aria-label="Zoom in">+</button>
    <button id="zout" title="Zoom out" aria-label="Zoom out">−</button>
    <button id="zfit" class="wide" title="Show the whole diagram">Fit</button>
  </div>
  <div id="filters"></div>
  <div id="info"></div>
</div>
<div class="wrap">
<p class="downloads">Download: <a href="diagram.pdf">diagram (PDF)</a> <a href="diagram.svg">diagram (SVG)</a>
<a href="{REPO}/blob/main/data/{key}/transitions.csv">transitions (CSV)</a>
<a href="{REPO}/blob/main/data/{key}/levels.csv">levels (CSV)</a> <a href="{REPO}">source code</a></p>
"""]

    # ---- tables prepared by compute.py (key transitions, Rydberg, hyperfine, isotope shifts)
    for tb in atom["tables"]:
        if not tb["rows"]:
            continue
        left = [k for k, a in enumerate(tb["aligns"]) if a == "l"]
        parts.append(f"<h2>{cell(tb['title'])} of {iso if not auto else meta['element'].lower()}</h2>"
                     if tb["title"].startswith(("Key", "Strongest")) else f"<h2>{cell(tb['title'])}</h2>")
        parts.append(table([cell(h) for h in tb["header"]], [[cell(c) for c in r] for r in tb["rows"]], left=left, wrap=[len(tb["header"]) - 1]))
        if tb.get("note"):
            parts.append(f'<p class="note">{html.escape(tb["note"])}</p>')

    # ---- all transitions
    rows = []
    for i, t in enumerate(T):
        up = L[t["upper"]] if "upper" in t else None
        up_html = al.tex_to_html(up["name"]) if up else al.tex_to_html(t["upper_name"]) + " (Rydberg)"
        rows.append(dict(id=f"line-{i}", cells=[
            al.tex_to_html(L[t["lower"]]["name"]), up_html, f"{t['lam']:.4f}", f"{t['air']:.4f}" if t.get("air") else "–",
            f"{t['freq']:.4f}", t.get("type", "E1"),
            (fmt_d(t["d"]) + badge(t.get("d_tier"))) if t.get("d") is not None else "–",
            (f"{t['A']:.3e}" + badge(t.get("A_tier"))) if t.get("A") else "–",
            f"{t['br'] * 100:.3g}" if t.get("br") is not None else "–", cite(atom, t.get("d_src") or t.get("A_src"))]))
    parts.append(f"<h2>{'Listed' if auto else 'All'} {iso} transitions below 2 µm</h2>")
    parts.append(table(["Lower level", "Upper level", "λ vacuum (nm)", "λ air (nm)", "ν (THz)", "Type", "|⟨J‖er‖J′⟩| (ea₀)", "A (s⁻¹)", "Branching (%)",
                        "Source of matrix element / A"], rows, left=(0, 1, 5, 9), wrap=(9,)))
    parts.append('<p class="note">Reduced dipole matrix elements follow the convention A = ω³|d|²/(3πε₀ħc³(2J′+1)), with J′ the upper level.\n'
                 "Tags show where a number comes from: measured, NIST compilation, high-accuracy theory, or a model calculation.</p>")

    # ---- levels
    rows = []
    for l in L:
        if l["tau_tier"] == "stable":
            tau = "stable"
        elif l.get("tau_ns") is None:
            tau = "–"
        else:
            tau = fmt_tau(l["tau_ns"]) + badge(l["tau_tier"])
        h = l.get("hfs") or {}
        rows.append(dict(id=f"level-{l['id']}", cells=[al.tex_to_html(l["name"]), f"{l['E']:.3f}", al.jstr(l["J"]), l["parity"], tau,
                                                       f"{l['g']:.5g}" if l.get("g") else "–",
                                                       f"{h['A']:g}" if h else "–", f"{h['B']:g}" if h.get("B") else "–",
                                                       cite(atom, l.get("tau_src")), cite(atom, h.get("src"))]))
    parts.append(f"<h2>{iso} energy levels</h2>")
    parts.append(table(["Level", "Energy (cm⁻¹)", "J", "Parity", "Lifetime", "g<sub>J</sub>", "Hyperfine A (MHz)", "Hyperfine B (MHz)",
                        "Lifetime source", "Hyperfine source"], rows, left=(0, 8, 9), wrap=(8, 9)))
    parts.append(f'<p class="note">{html.escape(meta["limit_text"].replace("$", "").replace("^{-1}", "⁻¹").replace("^+", "⁺"))}</p>')

    # ---- sources
    srcs = {}
    for t in T:
        for k in ("d_src", "A_src", "freq_src"):
            if t.get(k):
                srcs[re.sub(r"\s*\((from A|via ARC|accuracy [^)]*)\)", "", t[k]).strip()] = 1
    for l in L:
        for s in (l.get("tau_src"), (l.get("hfs") or {}).get("src")):
            if s:
                srcs[s.strip()] = 1
    parts.append("<h2>Sources</h2><ul class=\"sources\">" + "".join(f"<li>{cite(atom, s)}</li>" for s in sorted(srcs) if len(s) > 3) + "</ul>")
    if meta.get("notes"):
        parts.append(f'<p class="note">{html.escape(str(meta["notes"])[:1500])}</p>')

    others = "".join(f'<li><a class="card" href="../{p["slug"]}/"><div><strong>{pname(p)}</strong>'
                     f'<span>{p["levels"]} levels, {p["lines"]} lines</span></div></a></li>' for p in pages if p["slug"] != slug and p["A"])
    parts.append(f'<h2>Atoms with measured data</h2><ul class="grid">{others}</ul>'
                 '<p><a href="../">All elements: periodic table</a></p>')
    parts.append(f'<footer>Data: NIST Atomic Spectra Database and the cited measurements. Built {datetime.date.today().isoformat()}. '
                 f'<a href="{REPO}">Code and data on GitHub</a>.</footer></div></main>\n<script src="../assets/viewer.js"></script>\n</body></html>\n')
    with open(os.path.join(DOCS, slug, "index.html"), "w") as f:
        f.write("".join(parts))


def landing(pages):
    title = "Atomic energy level diagrams – interactive periodic table of Grotrian diagrams"
    n_el = len({p["symbol"] for p in pages})
    desc = (f"Interactive energy level diagrams for {n_el} elements of the periodic table: transitions below 2 µm with wavelengths, "
            "frequencies and dipole matrix elements from the NIST Atomic Spectra Database, plus measured lifetimes, hyperfine constants and "
            "isotope shifts for the atoms used in cold-atom, optical-clock and ion-trap experiments.")
    by_sym = {}
    for p in pages:
        by_sym.setdefault(p["symbol"], []).append(p)
    cells = []
    for e in ELEMENTS:
        ps = by_sym.get(e["symbol"], [])
        row = e["row"] + (1 if e["row"] >= 9 else 0)  # blank grid row between the main table and the f-block
        style = f'style="grid-row:{row};grid-column:{e["col"]}"'
        inner = f'<span class="z">{e["Z"]}</span><span class="sym">{e["symbol"]}</span><span class="nm">{e["name"]}</span>'
        if not ps:
            cells.append(f'<div class="el none {e["category"]}" {style} title="{e["name"]}: no classified lines in NIST ASD">{inner}</div>')
            continue
        main = next((p for p in ps if p["A"] == PRIMARY.get(e["symbol"])), ps[0])
        curated = bool(main["A"])
        info = f'{main["lines"]} lines' + (" · measured data" if curated else "")
        cells.append(f'<a class="el {e["category"]}{" curated" if curated else ""}" {style} href="{main["slug"]}/" '
                     f'data-name="{e["name"].lower()} {e["symbol"].lower()}" title="{e["name"]}: {main["levels"]} levels, {info}">'
                     f'{inner}<span class="ct">{main["lines"]} lines</span></a>')
    for r, lab in ((6, "57–71"), (7, "89–103")):
        cells.append(f'<div class="el gap" style="grid-row:{r};grid-column:3">{lab}</div>')
    legend = "".join(f'<li class="{k}"><span></span>{v}</li>' for k, v in CATEGORY.items())
    cards = "".join(
        f'<li><a class="card" href="{p["slug"]}/"><img src="{p["slug"]}/preview.png" loading="lazy" width="1800" height="1350" '
        f'alt="{pname(p)} energy level diagram"><div><strong>{pname(p)} (<sup>{p["A"]}</sup>{p["symbol"]})</strong>'
        f'<span>{p["levels"]} levels, {p["lines"]} transitions below 2 µm</span></div></a></li>' for p in pages if p["A"])
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": SITE, "url": BASE + "/", "description": desc,
          "hasPart": [{"@type": "Dataset", "name": f"{pname(p)} energy levels and transitions",
                       "url": f"{BASE}/{p['slug']}/"} for p in pages]}
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{BASE}/">
<link rel="icon" href="data:,">
<link rel="stylesheet" href="assets/style.css">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{BASE}/">
<meta property="og:image" content="{BASE}/rubidium-87/preview.png">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<header class="top"><a class="brand" href="./">{SITE}</a></header>
<main>
<div class="wrap">
<h1>Energy level diagrams of the elements</h1>
<p class="lead">Pick an element to open its interactive Grotrian diagram: every drawn transition carries its vacuum wavelength and
reduced dipole matrix element, and pointing at a line isolates it and shows frequency, Einstein coefficient and source.</p>
<div class="ptools">
  <label>Find an element <input id="q" type="search" placeholder="name or symbol" autocomplete="off"></label>
  <ul class="legend">{legend}<li class="cur"><span></span>Measured lifetimes, hyperfine data and isotope shifts included</li></ul>
</div>
</div>
<div class="pscroll"><div class="ptable" id="ptable">{"".join(cells)}</div></div>
<div class="wrap">
<h2>Atoms with measured data</h2>
<p>For the atoms that cold-atom, optical-tweezer, optical-clock and ion-trap experiments work with, each isotope has its own page.
Beyond the NIST level energies these include measured lifetimes, transition rates, hyperfine constants and isotope shifts, each
with its citation; calculated values are tagged as such.</p>
<ul class="grid">{cards}</ul>
<h2>What each page contains</h2>
<p>A zoomable diagram (also as PDF and SVG), a table of the key or strongest transitions, the transition list with wavelengths in
vacuum and air, frequencies, dipole matrix elements and Einstein A coefficients, and the level energies. Level energies and most
transition rates come from the <a href="https://physics.nist.gov/asd">NIST Atomic Spectra Database</a>. All tables are downloadable
as CSV from the <a href="{REPO}">GitHub repository</a>.</p>
<footer>Data: NIST Atomic Spectra Database and the measurements cited on each page. Built {datetime.date.today().isoformat()}.</footer>
</div>
</main>
<script>
document.getElementById('q').addEventListener('input', e => {{
  const q = e.target.value.trim().toLowerCase();
  document.querySelectorAll('#ptable a.el').forEach(a => {{
    const hit = !q || a.dataset.name.split(' ').some(w => w.startsWith(q));
    a.classList.toggle('dimmed', !hit);
  }});
}});
</script>
</body></html>
"""
    with open(os.path.join(DOCS, "index.html"), "w") as f:
        f.write(page)


def main():
    pages = []
    for key, cfg in SPECIES.items():
        p = os.path.join(al.DATA, key, "atom.json")
        if not os.path.exists(p) or not os.path.exists(os.path.join(DOCS, cfg["slug"], "diagram.svg")):
            continue
        with open(p) as f:
            atom = json.load(f)
        pages.append(dict(key=key, slug=cfg["slug"], element=cfg["element"], symbol=cfg["symbol"], A=cfg["A"], Z=cfg["Z"],
                          levels=len(atom["levels"]), lines=sum(1 for t in atom["transitions"] if t["kind"] != "rydberg")))
    pages.sort(key=lambda p: (p["Z"], p["A"] or 0))
    for p in pages:
        atom_page(p["key"], pages)
    landing(pages)
    today = datetime.date.today().isoformat()
    urls = [BASE + "/"] + [f"{BASE}/{p['slug']}/" for p in pages]
    with open(os.path.join(DOCS, "sitemap.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    with open(os.path.join(DOCS, "robots.txt"), "w") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    open(os.path.join(DOCS, ".nojekyll"), "w").close()
    print(f"site: {len(pages)} atom pages + landing, sitemap, robots.txt")


if __name__ == "__main__":
    main()
