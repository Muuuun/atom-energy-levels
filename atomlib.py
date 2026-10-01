"""Shared helpers: NIST ASD download / parsing, unit conversions, level naming."""
import csv
import io
import os
import re
import urllib.request
from fractions import Fraction

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
NIST_DIR = os.path.join(DATA, "nist")
LIT_DIR = os.path.join(DATA, "literature")

C = 299792458.0  # m/s
EV_TO_CM = 8065.543937  # cm^-1 per eV
L_LETTERS = "SPDFGHIKLMNOQ"

_LEVELS_URL = (
    "https://physics.nist.gov/cgi-bin/ASD/energy1.pl?de=0&spectrum={sp}+I&units=0&format=3&output=0"
    "&page_size=15&multiplet_ordered=0&conf_out=on&term_out=on&level_out=on&unc_out=1&j_out=on"
    "&lande_out=on&perc_out=on&biblio=on&temp=&submit=Retrieve+Data"
)
_LINES_URL = (
    "https://physics.nist.gov/cgi-bin/ASD/lines1.pl?spectra={sp}+I&output_type=0&low_w=200&upp_w=2000&unit=1"
    "&de=0&plot_out=0&I_scale_type=1&format=3&line_out=0&remove_js=on&en_unit=0&output=0&bibrefs=1"
    "&page_size=15&show_obs_wl=1&show_calc_wl=1&unc_out=1&order_out=0&max_low_enrg=&show_av=3"
    "&max_upp_enrg=&tsb_value=0&min_str=&A_out=0&intens_out=on&max_str=&allowed_out=1&forbid_out=1"
    "&min_accur=&min_intens=&conf_out=on&term_out=on&enrg_out=on&J_out=on&submit=Retrieve+Data"
)


def _fetch(url, path):
    """Download a NIST ASD table once; later runs reuse the cached copy."""
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
            f.write(r.read())
    with open(path) as f:
        rows = list(csv.reader(io.StringIO(f.read()), delimiter="\t"))
    head = rows[0]
    return [dict(zip(head, [c.strip().strip('"').strip() for c in r])) for r in rows[1:] if len(r) >= 5]


def _num(s):
    """NIST decorates numbers with brackets, '+', '?', letters: keep the number."""
    m = re.search(r"\d+\.?\d*(?:[eE][+-]?\d+)?", s or "")
    return float(m.group(0)) if m else None


def _j(s):
    try:
        return float(Fraction(s))
    except (ValueError, ZeroDivisionError):
        return None


def nist_levels(symbol):
    """Levels of the neutral atom: list of dicts (conf, term, J, E, unc, g) and the first ionisation limit."""
    rows = _fetch(_LEVELS_URL.format(sp=symbol), os.path.join(NIST_DIR, f"{symbol}_I_levels.tsv"))
    levels, limit = [], None
    for r in rows:
        e = _num(r.get("Level (cm-1)"))
        if r["Term"] == "Limit":
            if limit is None and e is not None:
                limit = e
            continue
        j = _j(r["J"])
        if e is None or j is None or (limit is not None and e > limit):
            continue
        levels.append(dict(conf=r["Configuration"], term=r["Term"], J=j, E=e,
                           unc=_num(r.get("Uncertainty (cm-1)")), g=_num(r.get("Lande"))))
    levels.sort(key=lambda l: l["E"])
    return levels, limit


def nist_lines(symbol):
    """Classified lines 200-2000 nm: list of dicts (Ei, Ek, obs, A, acc, type)."""
    rows = _fetch(_LINES_URL.format(sp=symbol), os.path.join(NIST_DIR, f"{symbol}_I_lines.tsv"))
    out = []
    for r in rows:
        ei, ek = _num(r.get("Ei(cm-1)")), _num(r.get("Ek(cm-1)"))
        if ei is None or ek is None or ek <= ei:
            continue
        out.append(dict(Ei=ei, Ek=ek, obs=_num(r.get("obs_wl_vac(nm)")), A=_num(r.get("Aki(s^-1)")),
                        acc=r.get("Acc", ""), type=r.get("Type", ""), intens=_num(r.get("intens"))))
    return out


def air_wavelength_nm(lam_vac_nm):
    """Vacuum -> standard air (Ciddor 1996, as used by NIST ASD). Valid above 200 nm."""
    s2 = (1e3 / lam_vac_nm) ** 2
    n = 1 + 0.05792105 / (238.0185 - s2) + 0.00167917 / (57.362 - s2)
    return lam_vac_nm / n


def rme_from_rate(A, wavenumber_cm, j_upper):
    """|<J||er||J'>| in e*a0 from an Einstein A coefficient: A = w^3 |d|^2 / (3 pi eps0 hbar c^3 (2J'+1))."""
    eps0, hbar, ea0 = 8.8541878128e-12, 1.054571817e-34, 8.4783536255e-30
    w = 2 * np.pi * wavenumber_cm * 100 * C
    return float(np.sqrt(A * 3 * np.pi * eps0 * hbar * C**3 * (2 * j_upper + 1) / w**3) / ea0)


def rate_from_rme(d, wavenumber_cm, j_upper):
    eps0, hbar, ea0 = 8.8541878128e-12, 1.054571817e-34, 8.4783536255e-30
    w = 2 * np.pi * wavenumber_cm * 100 * C
    return float(w**3 * (d * ea0) ** 2 / (3 * np.pi * eps0 * hbar * C**3 * (2 * j_upper + 1)))


def jstr(j):
    return str(Fraction(j).limit_denominator(2))


def parity_of(conf, term):
    """'odd' / 'even': from the term's '*' when there is a term, otherwise from the configuration."""
    if term and "*" in term:
        return "odd"
    if term and term not in ("", "?"):
        return "even"
    total = 0
    for nl, occ in re.findall(r"\d+([spdfgh])(\d*)", re.sub(r"\([^)]*\)", "", conf)):
        total += "spdfgh".index(nl) * (int(occ) if occ else 1)
    return "odd" if total % 2 else "even"


def short_conf(conf, core):
    """'4f14.6s.6p' -> '6s6p' (core prefix dropped, coupling brackets removed)."""
    c = conf
    for pre in core:
        if c.startswith(pre):
            c = c[len(pre):]
            break
    c = re.sub(r"<[^>]*>", "", c)
    c = re.sub(r"\.?\([^)]*\)\.?", ".", c)
    return c.replace("?", "").strip(".")


def conf_tex(c):
    """'6s.6p' or '5d2' -> mathtext with occupation superscripts."""
    parts = []
    for tok in c.split("."):
        m = re.fullmatch(r"(\d+[a-z])(\d+)?", tok)
        parts.append(m.group(1) + (f"^{{{m.group(2)}}}" if m.group(2) else "") if m else tok)
    return "".join(parts)


def term_tex(term, j):
    """LS term '3P*' + J -> '^3P^o_1'; anything else is passed through with J appended."""
    m = re.fullmatch(r"(\d)([A-Z])(\*?)\??", term or "")
    js = jstr(j)
    if m:
        odd = "^{o}" if m.group(3) else ""
        return rf"^{m.group(1)}{m.group(2)}{odd}_{{{js}}}"
    t = (term or "").replace("*", "^{o}").replace("?", "")
    return rf"{t}_{{{js}}}" if t else rf"J{{=}}{js}"


def tex_to_html(t):
    """Mathtext level name -> HTML with <sup>/<sub>."""
    t = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", t)
    t = t.replace("\\ ", " ").replace("\\,", " ").replace("{=}", "=")
    t = re.sub(r"\^\{([^}]*)\}", r"<sup>\1</sup>", t)
    t = re.sub(r"_\{([^}]*)\}", r"<sub>\1</sub>", t)
    t = re.sub(r"\^(\w)", r"<sup>\1</sup>", t)
    t = re.sub(r"_(\w)", r"<sub>\1</sub>", t)
    return t.replace("<sup>o</sup>", "<sup>°</sup>")


def load_literature(symbol):
    import json
    p = os.path.join(LIT_DIR, f"{symbol}.json")
    if not os.path.exists(p):
        return dict(levels=[], transitions=[], isotopes={})
    with open(p) as f:
        return json.load(f)
