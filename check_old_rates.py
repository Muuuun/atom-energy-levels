#!/usr/bin/env python3
"""Lines whose displayed transition rate is a measurement older than 20 years although NIST rates the same line.

    python3 check_old_rates.py        # -> data/old_measured_rates.md

The owner's age rule (measurements of the last 20 years override NIST, older ones do not) was applied by hand to carbon
only. This lists the other candidates; nothing is changed.
"""
import json
import os
import re

import atomlib as al
from species import SPECIES

MIN_YEAR = 2006


def main():
    out, total = [], 0
    for key, cfg in SPECIES.items():
        p = os.path.join(al.DATA, key, "atom.json")
        if not os.path.exists(p) or cfg["kind"] == "alkali":
            continue
        with open(p) as f:
            atom = json.load(f)
        L = atom["levels"]
        try:
            lines = [ln for ln in al.nist_lines(cfg["symbol"], 1) if ln["A"]]
        except Exception:
            continue
        rows = []
        for t in atom["transitions"]:
            if t.get("A_tier") != "exp" or "upper" not in t:
                continue
            years = [int(y) for y in re.findall(r"\b((?:19|20)\d\d)\b", t.get("A_src", ""))]
            if not years or max(years) >= MIN_YEAR:
                continue
            lo, up = L[t["lower"]], L[t["upper"]]
            elo, eup = lo.get("E_nist", lo["E"]), up.get("E_nist", up["E"])
            hit = [ln for ln in lines if abs(ln["Ei"] - elo) < 0.05 and abs(ln["Ek"] - eup) < 0.05
                   and ln["Ji"] in (None, lo["J"]) and ln["Jk"] in (None, up["J"])]
            if not hit:
                continue
            n = max(hit, key=lambda ln: ln["A"])
            rows.append(f"| {lo['plain']} – {up['plain']} | {t['lam']:.3f} | {t['A']:.3e} | {n['A']:.3e} ({n['acc'] or '–'}) | "
                        f"{(t['A'] / n['A'] - 1) * 100:+.1f} % | {t['A_src'][:90]} |")
        if rows:
            total += len(rows)
            out.append(f"\n## {cfg['element']} ({key}): {len(rows)} lines\n\n| Line | λ vac (nm) | A shown (s⁻¹) | A NIST (accuracy) | "
                       "difference | Source of the shown value |\n|---|---|---|---|---|---|\n" + "\n".join(rows))
    head = (f"# Measured transition rates older than {MIN_YEAR} shown instead of a NIST rate\n\n{total} lines. "
            "Written by `check_old_rates.py`; nothing has been changed.\n")
    with open(os.path.join(al.DATA, "old_measured_rates.md"), "w") as f:
        f.write(head + "\n".join(out) + "\n")
    print(head)
    for o in out:
        print(o.split("\n")[1])


if __name__ == "__main__":
    main()
