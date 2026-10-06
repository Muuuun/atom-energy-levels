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
PRIMARY = {"Li": 7, "Be": 9, "Na": 23, "Mg": 24, "K": 39, "Ca": 40, "Rb": 87, "Sr": 88, "Cs": 133, "Ba": 138, "Yb": 174, "Dy": 164,
           "Cr": 52, "Cd": 114, "Er": 166, "Tm": 169, "Hg": 202}  # the isotope a periodic-table cell and /<element>/ lead to
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


def nav():
    return f'<header class="top"><a class="brand" href="../">{SITE}</a><nav><a href="../">Periodic table</a></nav></header>'


def isotope_switch(pages, slug):
    """Segmented control under the title: the isotope pages of this element, with quantum statistics and nuclear spin."""
    here = next(p for p in pages if p["slug"] == slug)
    sibs = [p for p in pages if p["symbol"] == here["symbol"] and p["A"]]
    if len(sibs) < 2:
        return ""
    items = "".join(
        f'<a href="../{p["slug"]}/"{" aria-current=" + chr(34) + "page" + chr(34) if p is here else ""}>'
        f'<b><sup>{p["A"]}</sup>{p["symbol"]}</b>'
        # a neutral atom has as many electrons as protons, so the neutron number decides its statistics
        f'<small><span>{"boson" if (p["A"] - p["Z"]) % 2 == 0 else "fermion"}</span><span><i>I</i> = {p["I"]}</span></small></a>' for p in sibs)
    return f'<nav class="iso" aria-label="Isotopes of {here["element"].lower()}"><span>Isotope</span><div>{items}</div></nav>\n'


def atom_page(key, pages):
    cfg = SPECIES[key]
    slug = cfg["slug"]
    with open(os.path.join(al.DATA, key, "atom.json")) as f:
        atom = json.load(f)
    meta, L, T = atom["meta"], atom["levels"], atom["transitions"]
    bound = [t for t in T if t["kind"] != "rydberg"]
    auto = not meta["A"]
    listed = bool(meta.get("auto"))  # lines chosen by strength from NIST, not the full list below the energy cut
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

    lit_levels = (meta.get("lit_levels") or 0) > (len(L) - 1) / 2  # levels from the literature file, NIST has none (actinides)
    if lit_levels:
        desc = desc.replace("Measured and NIST data, with sources.", "Levels and lines from the cited literature.")
        lead = (f"Energy levels and transitions of neutral {meta['element'].lower()} ({meta['symbol']} I): {len(L)} levels and {len(bound)} "
                f"classified lines below 2 µm taken from the cited literature, each line with its vacuum wavelength and frequency"
                + (f" and, for {n_d} of them, the reduced dipole matrix element" if n_d else "") + ". The NIST Atomic Spectra Database "
                f"lists only the ground level and the ionisation limit of {meta['element'].lower()}, so the level energies on this page "
                "are those of the literature sources named below.")
    elif auto:
        lead = (f"Energy levels and transitions of neutral {meta['element'].lower()} ({meta['symbol']} I): the {len(bound)} strongest classified "
                f"lines below 2 µm from the NIST Atomic Spectra Database and the {len(L)} levels they connect, each line with its vacuum "
                f"wavelength, frequency and, for {n_d} of them, the reduced dipole matrix element derived from the NIST transition rate. "
                + ("Measured lifetimes, transition rates, hyperfine constants and isotope shifts from the literature are included, "
                   "each with its citation." if meta.get("has_lit") else
                   "Lifetimes, hyperfine constants and isotope shifts from the literature have not been compiled for this element yet."))
    elif listed:  # isotope page of an element drawn automatically
        lead = (f"Energy levels and transitions of neutral {iso} ({meta['symbol']} I, nuclear spin <i>I</i> = {meta['I']}): the {len(bound)} "
                f"strongest classified lines below 2 µm from the NIST Atomic Spectra Database and the {len(L)} levels they connect, each line "
                f"with its vacuum wavelength, frequency and, for {n_d} of them, the reduced dipole matrix element. Level energies come from "
                f"NIST and refer to the natural isotope mixture; transition rates are {prov}. Hyperfine constants and measured "
                f"frequencies are those of this isotope.")
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
{nav()}
<main>
<div class="wrap">
<h1>{name} energy level diagram</h1>
{isotope_switch(pages, slug)}<p class="lead">{lead}</p>
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
    parts.append(f"<h2>{'Listed' if listed else 'All'} {iso} transitions below 2 µm</h2>")
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
            tau = (l["tau_bound"] + " " if l.get("tau_bound") else "") + fmt_tau(l["tau_ns"]) + badge(l["tau_tier"])
        h = l.get("hfs") or {}
        rows.append(dict(id=f"level-{l['id']}", cells=[al.tex_to_html(l["name"]), f"{l['E']:.3f}", al.jstr(l["J"]), l["parity"], tau,
                                                       (f"{l['g']:.5g}" + (badge("theory") if l.get("g_tier") == "theory" else "")) if l.get("g") else "–",
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
    parts.append(f'<footer>Data: {"the cited literature" if lit_levels else "NIST Atomic Spectra Database and the cited measurements"}. Built {datetime.date.today().isoformat()}. '
                 f'<a href="{REPO}">Code and data on GitHub</a>.</footer></div></main>\n<script src="../assets/viewer.js"></script>\n</body></html>\n')
    with open(os.path.join(DOCS, slug, "index.html"), "w") as f:
        f.write("".join(parts))

FACTS = os.path.join(al.HERE, "data", "literature", "heaviest_elements.json")
FACT_TIER = {"experiment": "exp", "theory": "theory", "nist": "nist", "compilation": "theory"}


def fact_pages(pages):
    """Pages for the elements without any measured excited level (Md, Lr, Rf-Og): what is known, with sources; no diagram."""
    if not os.path.exists(FACTS):
        return []
    with open(FACTS) as f:
        sheet = json.load(f)
    link = lambda x: (f'<a href="{html.escape(x["url"])}" rel="noopener">{html.escape(x["source"])}</a>' if x.get("url")
                      else html.escape(x.get("source", "")))
    term = lambda t: al.tex_to_html(al.term_tex(re.sub(r"[\d/]+$", "", t["value"]), al.Fraction(t["J"]))) if t.get("J") else html.escape(t["value"])
    out = []
    for sym, e in sheet["elements"].items():
        if e.get("excited_level_measured"):
            continue
        name, slug = e["name"], e["name"].lower()
        url = f"{BASE}/{slug}/"
        ie, conf, gt, iso = e["ionization_energy_eV"], e["ground_configuration"], e["ground_term"], e.get("longest_lived_isotope") or {}
        measured = ie.get("method") == "experiment"
        title = f"{name} ({sym}, Z = {e['Z']}) – atomic energy levels: what is known"
        desc = (f"No excited level of neutral {slug} ({sym} I) has been measured. Ground state, "
                f"{'measured' if measured else 'calculated'} ionisation energy and calculated transitions, each with its source.")
        if ie.get("unc_plus"):
            ie_txt = f'{ie["value"]:g} +{ie["unc_plus"]:g} / −{ie["unc_minus"]:g} eV'
        else:
            ie_txt = f'{ie["value"]:g}' + (f' ± {ie["unc"]:g}' if ie.get("unc") else "") + " eV"
        rows = [["Ground configuration", html.escape(conf["value"]) + badge(FACT_TIER.get(conf["method"])), link(conf)],
                ["Ground term", term(gt) + badge(FACT_TIER.get(gt["method"])), link(gt)],
                ["First ionisation energy", ie_txt + badge(FACT_TIER.get(ie["method"])), link(ie)]]
        if iso.get("isotope"):
            hl = iso["half_life"]
            rows.append(["Longest-lived isotope", f'{html.escape(iso["isotope"])}, half-life {hl["value"]:g}'
                         + (f' ± {hl["unc"]:g}' if hl.get("unc") else "") + f' {html.escape(hl["unit"])}', link(iso)])
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
</head>
<body>
{nav()}
<main>
<div class="wrap">
<h1>{name} ({sym}, Z = {e['Z']}): atomic energy levels</h1>
<p class="lead">No energy level diagram can be drawn for neutral {slug}: no excited level of the atom has been measured, so there is
no observed transition to show. This page lists what is known instead, and marks every calculated number as theory.</p>
<h2>What has been measured</h2>
<p>{html.escape(e["what_has_been_measured"]["text"])}</p>
"""]
        parts.append(table(["Quantity", "Value", "Source"], rows, left=(0, 1, 2), wrap=(2,)))
        pl = e.get("predicted_lines") or []
        if pl:
            prow = [[html.escape(x.get("lower", "")), html.escape(x.get("upper", "")), f'{x["wavenumber_cm"]:g}',
                     f'{1e7 / x["wavenumber_cm"]:.1f}', html.escape(x.get("type", "")),
                     (f'{x["A_s"]:.3g}' if x.get("A_s") else "–"), link(x)] for x in pl]
            parts.append("<h2>Calculated transitions from the ground state</h2>"
                         '<p class="note">Theory only: none of these lines has been observed. Wavelengths are converted from the '
                         "calculated level energies.</p>")
            parts.append(table(["Lower level", "Upper level", "Energy (cm⁻¹)", "λ vacuum (nm)", "Type", "A (s⁻¹)" + badge("theory"),
                                "Source"], prow, left=(0, 1, 4, 6), wrap=(6,)))
        srcs = {x["source"]: x for x in e["what_has_been_measured"].get("sources", [])}
        parts.append('<h2>Sources</h2><ul class="sources">' + "".join(f"<li>{link(x)}</li>" for x in srcs.values()) + "</ul>")
        parts.append('<p><a href="../">All elements: periodic table</a></p>'
                     f'<footer>Data: the cited literature. Built {datetime.date.today().isoformat()}. '
                     f'<a href="{REPO}">Code and data on GitHub</a>.</footer></div></main>\n</body></html>\n')
        os.makedirs(os.path.join(DOCS, slug), exist_ok=True)
        with open(os.path.join(DOCS, slug, "index.html"), "w") as f:
            f.write("".join(parts))
        out.append(dict(symbol=sym, slug=slug, name=name, measured_ie=measured))
    return out


def landing(pages, facts=()):
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
        fp = next((x for x in facts if x["symbol"] == e["symbol"]), None)
        if not ps and fp:
            cells.append(f'<a class="el nolevels {e["category"]}" {style} href="{fp["slug"]}/" data-name="{e["name"].lower()} {e["symbol"].lower()}" '
                         f'title="{e["name"]}: no excited level measured; ground state and ionisation energy">{inner}<span class="ct">no spectrum</span></a>')
            continue
        if not ps:
            cells.append(f'<div class="el none {e["category"]}" {style} title="{e["name"]}: no classified lines in NIST ASD">{inner}</div>')
            continue
        main = next((p for p in ps if p["A"] == PRIMARY.get(e["symbol"])), ps[0])
        curated = bool(main["A"]) or main.get("has_lit")
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
transition rates come from the <a href="https://physics.nist.gov/asd">NIST Atomic Spectra Database</a>; for the actinides from
protactinium onwards, where NIST lists only the ground level, they come from the literature cited on the page. For mendelevium,
lawrencium and the elements from rutherfordium on, no excited level has ever been measured: their cells (dashed) open a short page with
the ground state, the ionisation energy and calculated lines, marked as theory. All tables are downloadable
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
        pages.append(dict(key=key, slug=cfg["slug"], element=cfg["element"], symbol=cfg["symbol"], A=cfg["A"], Z=cfg["Z"], I=atom["meta"].get("I"),
                          levels=len(atom["levels"]), lines=sum(1 for t in atom["transitions"] if t["kind"] != "rydberg"),
                          has_lit=atom["meta"].get("has_lit")))
    pages.sort(key=lambda p: (p["Z"], p["A"] or 0))
    for p in pages:
        atom_page(p["key"], pages)
    facts = fact_pages(pages)
    landing(pages, facts)
    # /<element>/ of an element that only has isotope pages forwards to its main isotope
    for sym in {p["symbol"] for p in pages if p["A"]}:
        ps = [p for p in pages if p["symbol"] == sym]
        main = next((p for p in ps if p["A"] == PRIMARY.get(sym)), ps[0])
        os.makedirs(os.path.join(DOCS, main["element"].lower()), exist_ok=True)
        with open(os.path.join(DOCS, main["element"].lower(), "index.html"), "w") as f:
            f.write(f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>{main["element"]} energy level diagram</title><link rel="icon" href="data:,">\n'
                    f'<link rel="canonical" href="{BASE}/{main["slug"]}/"><meta http-equiv="refresh" content="0; url=../{main["slug"]}/">\n'
                    f'</head><body><p><a href="../{main["slug"]}/">{pname(main)} energy level diagram</a></p></body></html>\n')
    today = datetime.date.today().isoformat()
    urls = [BASE + "/"] + [f"{BASE}/{p['slug']}/" for p in pages] + [f"{BASE}/{x['slug']}/" for x in facts]
    with open(os.path.join(DOCS, "sitemap.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    with open(os.path.join(DOCS, "robots.txt"), "w") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    open(os.path.join(DOCS, ".nojekyll"), "w").close()
    print(f"site: {len(pages)} atom pages + {len(facts)} fact pages + landing, sitemap, robots.txt")


if __name__ == "__main__":
    main()
