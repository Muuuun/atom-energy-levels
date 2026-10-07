#!/usr/bin/env python3
"""Semi-empirical transition rates (tier "semi", drawn with ≈): Kurucz's Cowan-code line lists of the neutral atoms he has completed.

    python3 semi.py fetch [Sym ...]    # cache http://kurucz.harvard.edu/atoms/<ZZ00>/gf<ZZ00>.pos in data/semi/ (files git-ignored)

Each file lists every electric-dipole line between experimentally known levels, at all wavelengths, with log gf from a
least-squares fit of the Cowan-code parameters to the observed energies (R. L. Kurucz, Can. J. Phys. 89, 417, 2011).
compute.py uses these rates only where neither a measurement nor NIST gives one: for a drawn line without a rate, and for
the decay lines of the closed-transition analysis (cycling.py), so that a leak becomes an estimate instead of a lower limit.
Checked against NIST on 2026-10-07 (14 elements): median offset below 0.1 dex; within a factor 2 for 80-100 % of the lines
NIST rates A or B, 60-80 % of C or D, 40-60 % of E.  Weak lines with strong cancellation can be off by a factor 10.
Lifetimes are not taken from these files (1 / radiative width is 25 % too short on average, outliers up to a factor 40).
"""
import datetime
import json
import os
import sys
import urllib.request

import atomlib as al

SEMI_DIR = os.path.join(al.DATA, "semi")
INDEX = os.path.join(SEMI_DIR, "index.json")
# neutral atoms in Kurucz's "completed ions" list (kurucz.harvard.edu/atoms/completed.txt, read 2026-10-07); H and He have no gf file
KURUCZ = ("Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Zn Sr Y Zr Nb Mo Tc Ru Rh Pd Ba").split()
FILE = {"B": "gf050011.pos", "Al": "gf1300.all", "Sr": "gf3800z.pos"}  # directories without a plain gf<ZZ00>.pos (B: the 11B list)
E_TOL = 0.5  # cm^-1: a Kurucz level is a NIST level when the energies agree this closely and J is the same
A_CONST = 6.6703e13  # A = A_CONST gf / ((2J'+1) lambda_nm^2)  [2 pi e^2 / (m_e c eps0) in nm^2 / s]


def code_of(symbol):
    from species import SPECIES
    z = next(c["Z"] for c in SPECIES.values() if c["symbol"] == symbol)
    return f"{z:02d}00"


def _index():
    if os.path.exists(INDEX):
        with open(INDEX) as f:
            return json.load(f)
    return {}


def fetch(symbols):
    os.makedirs(SEMI_DIR, exist_ok=True)
    index = _index()
    for sym in symbols:
        code = code_of(sym)
        name = FILE.get(sym, f"gf{code}.pos")
        url = f"http://kurucz.harvard.edu/atoms/{code}/{name}"
        path = os.path.join(SEMI_DIR, name)
        if os.path.exists(path) and sym in index:
            print(f"{sym}: cached ({index[sym]['lines']} lines, file of {index[sym]['modified']})")
            continue
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=300) as r:
                body, modified = r.read(), r.headers.get("Last-Modified", "")
        except Exception as ex:
            print(f"{sym}: not downloaded ({ex})")
            continue
        if not body or b"<html" in body[:500].lower():
            print(f"{sym}: no line list on the server")
            continue
        with open(path, "wb") as f:
            f.write(body)
        try:
            modified = datetime.datetime.strptime(modified, "%a, %d %b %Y %H:%M:%S %Z").strftime("%Y-%m-%d")
        except ValueError:
            pass
        index[sym] = dict(file=name, url=url, modified=modified, lines=body.count(b"\n"), fetched=datetime.date.today().isoformat())
        print(f"{sym}: {index[sym]['lines']} lines, file of {modified}")
    with open(INDEX, "w") as f:
        json.dump(dict(sorted(index.items())), f, indent=1)


def lines(symbol):
    """[(E_lower, J_lower, E_upper, J_upper, log gf)] of the cached Kurucz list, or [] when there is none."""
    entry = _index().get(symbol)
    path = entry and os.path.join(SEMI_DIR, entry["file"])
    if not path or not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="latin-1") as f:
        for ln in f:  # fixed format: wavelength, log gf, code, E1, J1, label1, E2, J2, label2, log of three damping widths, reference
            if len(ln) < 70:
                continue
            try:
                loggf, e1, j1, e2, j2 = float(ln[11:18]), float(ln[24:36]), float(ln[36:41]), float(ln[52:64]), float(ln[64:69])
            except ValueError:
                continue
            if e1 < 0 or e2 < 0 or e1 == e2:
                continue  # a negative energy marks a predicted level
            (el, jl), (eu, ju) = sorted([(e1, j1), (e2, j2)])
            out.append((el, jl, eu, ju, loggf))
    return out


def citation(symbol):
    entry = _index().get(symbol)
    if not entry:
        return None, None
    code = code_of(symbol)
    return (f"Kurucz, R. L., Can. J. Phys. 89, 417 (2011); semi-empirical line list {entry['file']} of {entry['modified']} (Cowan-code fit)",
            f"http://kurucz.harvard.edu/atoms/{code}/")


def rates(symbol, nist):
    """Kurucz rates on NIST levels: {(lower i, upper i): A in s^-1} for every line whose two levels are NIST levels (energy within
    E_TOL, same J, opposite parity; a level that fits two NIST levels is skipped), with citation, URL and counts.
    nist: energy-ordered NIST levels with E, J, conf, term, i.  Everything empty when no file is cached."""
    raw = lines(symbol)
    if not raw:
        return {}, None, None, None
    by_e = {}
    for l in nist:
        if l["J"] is not None:
            by_e.setdefault(round(l["E"]), []).append(l)
    parity = {l["i"]: al.parity_of(l["conf"], l["term"]) for l in nist}

    def find(e, j):
        c = [l for k in (round(e) - 1, round(e), round(e) + 1) for l in by_e.get(k, []) if l["J"] == j and abs(l["E"] - e) <= E_TOL]
        return c[0] if len(c) == 1 else None

    out, n = {}, 0
    for el, jl, eu, ju, loggf in raw:
        lo, up = find(el, jl), find(eu, ju)
        if not lo or not up or parity[lo["i"]] == parity[up["i"]] or up["E"] <= lo["E"]:
            continue
        n += 1
        a = A_CONST * 10 ** loggf / ((2 * ju + 1) * (1e7 / (up["E"] - lo["E"])) ** 2)
        key = (lo["i"], up["i"])
        out[key] = max(out.get(key, 0.0), float(f"{a:.4g}"))
    src, url = citation(symbol)
    return out, src, url, dict(lines=len(raw), matched=n)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["fetch"]:
        fetch(args[1:] or KURUCZ)
    else:
        print(__doc__)
