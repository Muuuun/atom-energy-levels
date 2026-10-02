#!/usr/bin/env python3
"""Apply the owner's decision of 2026-10-02: a measured rate older than 20 years that differs from the NIST rate of the same
line no longer overrides NIST. The entry is kept in the literature file as `A_s_older_measurement` (as in C.json).

    python3 revert_old_rates.py       # edits data/literature/*.json, prints what it moved
"""
import json
import os
import re
from fractions import Fraction

import atomlib as al
from species import SPECIES

MIN_YEAR, MIN_DIFF = 2006, 0.02


def jf(x):
    try:
        return float(Fraction(str(x)))
    except (ValueError, ZeroDivisionError):
        return None


def main():
    done = set()
    for key, cfg in SPECIES.items():
        sym = cfg["symbol"]
        p = os.path.join(al.DATA, key, "atom.json")
        if sym in done or not os.path.exists(p) or cfg["kind"] == "alkali":
            continue
        done.add(sym)
        with open(p) as f:
            atom = json.load(f)
        L = atom["levels"]
        lines = [ln for ln in al.nist_lines(sym, 1 if cfg.get("auto") else 200) if ln["A"]]
        path = os.path.join(al.DATA, "literature", f"{sym}.json")
        with open(path) as f:
            lit = json.load(f)
        moved, missed = 0, 0
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
            if not hit or abs(t["A"] / max(ln["A"] for ln in hit) - 1) < MIN_DIFF:
                continue
            found = False
            for lt in lit.get("transitions", []):
                a = lt.get("A_s")
                if (isinstance(a, dict) and abs(lt.get("lower_cm", -9e9) - elo) < 1 and abs(lt.get("upper_cm", -9e9) - eup) < 1
                        and jf(lt.get("lower_J")) in (None, lo["J"]) and jf(lt.get("upper_J")) in (None, up["J"])
                        and t["A_src"].startswith(a.get("source", "\0"))):
                    a["note"] = (a.get("note", "") + " Older than 20 years and NIST rates this line: not used as the displayed value "
                                 "(owner's decision 2026-10-02).").strip()
                    lt["A_s_older_measurement"] = lt.pop("A_s")
                    found = True
            moved += found
            missed += not found
        # a matrix element derived from the same old rate must not bring it back in
        for lt in lit.get("transitions", []):
            old = lt.get("A_s_older_measurement")
            for k in ("rme_J_ea0", "reduced_matrix_element_ea0", "reduced_matrix_element_au", "reduced_dipole_au"):
                r = lt.get(k)
                if isinstance(old, dict) and isinstance(r, dict) and (str(old.get("source", "")).startswith(str(r.get("source", "\0"))[:60])) and "A_s" not in lt:
                    lt[k + "_older_measurement"] = lt.pop(k)
                    moved += 1
        if moved or missed:
            print(f"{sym}: moved {moved}, not located in the file {missed}")
        if moved:
            with open(path, "w") as f:
                json.dump(lit, f, indent=1, ensure_ascii=False)
                f.write("\n")


if __name__ == "__main__":
    main()
