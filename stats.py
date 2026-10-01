#!/usr/bin/env python3
"""Where do the numbers come from? Counts per species, written to data/provenance.md and printed.

    python3 stats.py
"""
import json
import os

import atomlib as al
from species import SPECIES

COLS = ["nist", "exp", "theory", "model", "none"]


def count(items, key):
    c = dict.fromkeys(COLS, 0)
    for it in items:
        t = it.get(key) or "none"
        c[t if t in c else "none"] += 1
    return c


def main():
    rows, total_A, total_tau = [], dict.fromkeys(COLS, 0), dict.fromkeys(COLS, 0)
    auto_n, auto_A = 0, dict.fromkeys(COLS, 0)
    for key, cfg in SPECIES.items():
        p = os.path.join(al.DATA, key, "atom.json")
        if not os.path.exists(p):
            continue
        with open(p) as f:
            atom = json.load(f)
        lines = [t for t in atom["transitions"] if t["kind"] != "rydberg"]
        levels = [l for l in atom["levels"] if l["tau_tier"] != "stable"]
        a, tau = count(lines, "A_tier"), count(levels, "tau_tier")
        if cfg.get("auto"):  # NIST-only element pages: summarised in one line below
            auto_n += 1
            for c in COLS:
                auto_A[c] += a[c]
            continue
        n_freq = sum(1 for t in lines if t.get("freq_tier") == "exp")
        n_hfs = sum(1 for l in atom["levels"] if l.get("hfs"))
        rows.append((f"{cfg['element']}-{cfg['A']}", len(lines), a, len(levels), tau, n_freq, n_hfs, key))
    # one row per element for the totals (isotopes share the same lines)
    seen = set()
    for name, n, a, nl, tau, *_ , key in rows:
        sym = SPECIES[key]["symbol"]
        if sym in seen:
            continue
        seen.add(sym)
        for c in COLS:
            total_A[c] += a[c]
            total_tau[c] += tau[c]
    out = ["# Provenance of the numbers", "",
           "Level energies and wavelengths: NIST ASD for every species (a measured isotope-specific frequency replaces the NIST value",
           "where the literature file has one; column *ν meas.*).", "",
           "| Species | Lines | A / matrix element: NIST | measured | theory | model | none | Excited levels | Lifetime: measured | theory | model | none | ν meas. | Levels with hyperfine A |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, n, a, nl, tau, n_freq, n_hfs, _ in rows:
        out.append(f"| {name} | {n} | {a['nist']} | {a['exp']} | {a['theory']} | {a['model']} | {a['none']} | {nl} | "
                   f"{tau['exp']} | {tau['theory']} | {tau['model']} | {tau['none']} | {n_freq} | {n_hfs} |")
    sa, st = sum(total_A.values()), sum(total_tau.values())
    out += ["", f"Totals over the {len(seen)} curated elements (one isotope each):", "",
            "- transition rates / matrix elements: " + ", ".join(f"{k} {v} ({100 * v / sa:.0f}%)" for k, v in total_A.items()),
            "- lifetimes of excited levels: " + ", ".join(f"{k} {v} ({100 * v / st:.0f}%)" for k, v in total_tau.items() if k != "nist"),
            "", f"NIST-only element pages ({auto_n} elements, no literature compiled yet): {sum(auto_A.values())} lines drawn, "
            f"{auto_A['nist']} with a NIST transition rate, {auto_A['none']} wavelength only; no lifetimes.",
            "", "nist = NIST ASD compilation; exp = measurement from data/literature; theory = high-accuracy calculation quoted from the",
            "literature; model = ARC model potential; none = no value (wavelength only / no lifetime)."]
    with open(os.path.join(al.DATA, "provenance.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
