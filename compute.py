#!/usr/bin/env python3
"""Build data/<key>/atom.json for one species (or all): levels, transitions, tables, provenance.

    python3 compute.py rb87 cs133      # or: python3 compute.py all

Priority of sources for every number: measurement from data/literature/<El>.json > NIST ASD >
high-accuracy theory quoted in the literature file > ARC (alkalis only; literature table, then model potential).
Each value carries a tier: "exp", "nist", "theory", "semi" (Kurucz semi-empirical line list, semi.py; only where nothing
else gives a rate), "model".
"""
import csv
import datetime
import json
import os
import re
import sys
import warnings
from fractions import Fraction

import numpy as np

import atomlib as al
import cycling
import semi
from species import SPECIES

warnings.filterwarnings("ignore")
LAMBDA_MAX_NM = 2000.0
RYDBERG_N = [30, 40, 50, 70, 100]
TIER_OF = {"experiment": "exp", "compilation": "exp", "theory": "theory"}
ENERGY_MAX_AGE_YR = 20  # measured level energies older than this do not replace the NIST value
ENERGY_MIN_YEAR = datetime.date.today().year - ENERGY_MAX_AGE_YR
ISOTOPE_SHIFT_MAX_CM = 2.0


# ----------------------------------------------------------------------------- literature lookup
class Literature:
    def __init__(self, symbol, isotope):
        self.raw = al.load_literature(symbol)
        self.iso = str(isotope)

    def source_urls(self):
        """{citation: url} for every sourced entry of the literature file."""
        out = {}

        def walk(x):
            if isinstance(x, dict):
                if isinstance(x.get("source"), str) and isinstance(x.get("url"), str):
                    out.setdefault(x["source"], x["url"])
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)

        walk(self.raw)
        return out

    @staticmethod
    def _j_ok(entry_j, j):
        """True unless the entry states a J that differs (some doublets share one NIST energy)."""
        if entry_j is None or j is None:
            return True
        try:
            return abs(float(Fraction(str(entry_j))) - j) < 0.01
        except (ValueError, ZeroDivisionError):
            return True

    def level(self, e, j=None):
        best = None
        for l in self.raw.get("levels", []):
            d = abs(l.get("nist_energy_cm", -1e9) - e)
            if d < 0.6 and self._j_ok(l.get("J"), j) and (best is None or d < best[0]):
                best = (d, l)
        return best[1] if best else {}

    def transition(self, elo, eup, jlo=None, jup=None):
        best = None  # closest pair wins: F5/2 and F7/2 lie 0.02 cm^-1 apart
        for t in self.raw.get("transitions", []):
            d = abs(t.get("lower_cm", -1e9) - elo) + abs(t.get("upper_cm", -1e9) - eup)
            if d < 0.6 and self._j_ok(t.get("lower_J"), jlo) and self._j_ok(t.get("upper_J"), jup) and (best is None or d < best[0]):
                best = (d, t)
        return best[1] if best else {}

    @staticmethod
    def val(entry):
        """(value, unc, tier, source) of a sourced entry, or None."""
        if not isinstance(entry, dict) or not isinstance(entry.get("value"), (int, float)):
            return None
        return entry["value"], entry.get("unc"), TIER_OF.get(entry.get("method"), "exp"), entry.get("source", "")

    @classmethod
    def rme(cls, lt):
        """Reduced matrix element entry under any of the names the literature files use."""
        for k in ("rme_J_ea0", "reduced_matrix_element_ea0", "reduced_matrix_element_au", "reduced_dipole_au"):
            v = cls.val(lt.get(k)) if lt else None
            if v:
                return abs(v[0]), v[1], v[2], v[3]
        return None

    def lifetime_ns(self, e, j=None):
        v = self.val(self.level(e, j).get("lifetime"))
        if not v:
            return None
        unit = self.level(e, j)["lifetime"].get("unit", "s")
        k = {"s": 1e9, "ms": 1e6, "us": 1e3, "µs": 1e3, "ns": 1.0}.get(unit, 1e9)
        note = str(self.level(e, j)["lifetime"].get("note", ""))
        src = v[3] + (f". Note: {note}" if re.search(r"derived|bound|limit", note, re.I) else "")
        return v[0] * k, (v[1] * k if isinstance(v[1], (int, float)) else None), v[2], src

    def energy(self, e, j=None, nist_unc=None):
        """Measured level energy that replaces the NIST one: (value, unc, source) or None.
        Owner's rule: a direct measurement published within ENERGY_MAX_AGE_YR years wins, older ones leave NIST in place.
        A value measured in another isotope is used only where NIST is off by more than any isotope shift;
        the nearest isotope is taken."""
        l = self.level(e, j)
        cands = []
        for raw in (l.get("measured_energy_cm"), l.get("level_energy_measured")):
            if isinstance(raw, dict) and "value" not in raw:
                raw = [dict(v, isotope=k) for k, v in raw.items() if isinstance(v, dict)]
            for x in raw if isinstance(raw, list) else [raw]:
                year = re.search(r"\(((?:19|20)\d\d)\)", x.get("source", "")) if isinstance(x, dict) else None
                if (not year or x.get("method") != "experiment" or not isinstance(x.get("value"), (int, float))
                        or int(x.get("year", year.group(1))) < ENERGY_MIN_YEAR):
                    continue
                iso = str(x.get("isotope", self.iso))
                d, u = abs(x["value"] - l["nist_energy_cm"]), x.get("unc") or 0
                if iso != self.iso and d < ISOTOPE_SHIFT_MAX_CM:
                    continue
                if d <= u + (nist_unc or 0) and (not u or u >= (nist_unc or 1e9)):
                    continue  # agrees with NIST and is no more precise: nothing to gain
                src = x.get("source", "") + (f" (measured in isotope {iso})" if iso != self.iso else "")
                far = abs(int(iso) - int(self.iso)) if iso.isdigit() and self.iso.isdigit() else 0
                cands.append((far, x.get("unc") or 1e9, x["value"], x.get("unc"), src))
        return min(cands)[2:] if cands else None

    def hyperfine(self, e, j=None):
        h = self.level(e, j).get("hyperfine", {}).get(self.iso)
        if not h or not isinstance(h.get("A_MHz"), (int, float)):
            return None
        return dict(A=h["A_MHz"], A_unc=h.get("A_unc"), B=h.get("B_MHz"), B_unc=h.get("B_unc"),
                    tier=TIER_OF.get(h.get("method"), "exp"), src=h.get("source", ""))

    def frequency_THz(self, t):
        for f in (t.get(f"frequency_THz_{self.iso}"), t.get("frequency_THz")):
            if (isinstance(f, dict) and isinstance(f.get("value"), (int, float)) and str(f.get("isotope", self.iso)) == self.iso
                    and "not verified" not in f.get("source", "")):
                return f["value"], f.get("unc"), f.get("source", "")
        return None


def sig(x, n=4):
    return float(f"{x:.{n}g}")


def hfs_shifts(I, J, A, B):
    """Hyperfine shift (MHz) of each F level from the centre of gravity."""
    out = []
    for F in np.arange(abs(I - J), I + J + 0.5):
        K = F * (F + 1) - I * (I + 1) - J * (J + 1)
        e = 0.5 * A * K
        if B and I >= 1 and J >= 1:
            e += B * (1.5 * K * (K + 1) - 2 * I * (I + 1) * J * (J + 1)) / (4 * I * (2 * I - 1) * J * (2 * J - 1))
        out.append((al.jstr(F), round(float(e), 3)))
    return out


def fmt_unc(v, u, digits=None, max_digits=6):
    """1.234(5)-style string."""
    if not isinstance(u, (int, float)) or u <= 0:
        return f"{v:.{digits}f}" if digits is not None else f"{v:g}"
    d = max(0, -int(np.floor(np.log10(u))) + (1 if u / 10 ** np.floor(np.log10(u)) < 2.95 else 0))
    if d > max_digits:  # uncertainty far below anything worth printing
        return f"{v:.{max_digits}f}"
    return f"{v:.{d}f}({round(u * 10 ** d):d})"


def finish_transition(t, lo, up, lit, tau_ns):
    """Fill wavelength-derived fields and the literature overrides shared by both kinds of atom."""
    wn = up["E"] - lo["E"]
    lt = lit.transition(lo.get("E_nist", lo["E"]), up.get("E_nist", up["E"]), lo["J"], up["J"])
    f = lit.frequency_THz(lt) if lt else None
    if f:
        t.update(freq=f[0], freq_unc=f[1], freq_src=f[2], freq_tier="exp")
        wn = f[0] * 1e12 / al.C / 100
    elif lo.get("E_tier") == "exp" or up.get("E_tier") == "exp":
        t.update(freq=round(wn * 100 * al.C / 1e12, 5), freq_tier="exp",
                 freq_src="; ".join(l["E_src"] for l in (lo, up) if l.get("E_tier") == "exp") + " (measured level energy)")
    else:
        t.update(freq=round(wn * 100 * al.C / 1e12, 5), freq_tier="nist", freq_src="NIST ASD level energies")
    lam = 1e7 / wn
    t.update(lower=lo["id"], upper=up["id"], wn=round(wn, 4), lam=round(lam, 5 if f else 4),
             air=round(al.air_wavelength_nm(lam), 4) if lam >= 200 else None)
    if lt.get("use"):
        t["use"] = lt["use"]
    if lt.get("type") in ("M1", "E2", "M2", "clock"):
        t.update(kind="forbidden", type=lt["type"])
    br = lit.val(lt.get("branching")) if lt else None
    if br:
        t.update(br=br[0], br_tier=br[2], br_src=br[3])
    shifts = lt.get("isotope_shift_MHz") if lt else None
    if isinstance(shifts, dict):
        t["isotope_shifts"] = {k: dict(value=v["value"], unc=v.get("unc"), src=v.get("source", ""), url=v.get("url", ""))
                               for k, v in shifts.items() if isinstance(v, dict) and isinstance(v.get("value"), (int, float))}
    if tau_ns:
        t["gamma_MHz"] = sig(1e3 / (2 * np.pi * tau_ns), 4)
    return lt


# ----------------------------------------------------------------------------- alkali atoms
def build_alkali(key, cfg):
    import arc
    atom = getattr(arc, cfg["arc"])()
    sym = cfg["symbol"]
    lit = Literature(sym, cfg["A"])
    nist, limit = al.nist_levels(sym)
    nist_A = {(round(l["Ei"], 1), round(l["Ek"], 1)): l for l in al.nist_lines(sym)}
    core = cfg["core"][0]

    def nlj(l):
        m = re.fullmatch(re.escape(core) + r"(\d+)([spdf])", l["conf"])
        return (int(m.group(1)), "spdf".index(m.group(2)), l["J"]) if m else None

    def name(n, l, j):
        return f"{n}{al.L_LETTERS[l]}{al.jstr(j)}"

    e_gs = atom.getEnergy(*nlj(nist[0])[:2], 0.5)
    arc_cm = lambda n, l, j: (atom.getEnergy(n, l, j) - e_gs) * al.EV_TO_CM
    # Rydberg terms: ARC binding energy (quantum defects) hung from the NIST ionisation limit
    arc_ryd_cm = lambda n, l, j: limit + atom.getEnergy(n, l, j) * al.EV_TO_CM
    pi = None
    if cfg.get("pi_species"):
        import pairinteraction
        pi = lambda n, l, j: pairinteraction.KetAtom(cfg["pi_species"], n=n, l=l, j=j, m=0.5)
        pi_cm = lambda n, l, j: pi(n, l, j).get_energy(unit="GHz") * 1e9 / al.C / 100
    ryd_cm = pi_cm if cfg["rydberg_source"] == "pairinteraction" else arc_ryd_cm
    dev = [ryd_cm(*nlj(l)) - l["E"] for l in nist if nlj(l) and 15 <= nlj(l)[0] <= 45 and (l["unc"] or 1) <= 0.011]
    ryd_check = (f"Rydberg terms ({cfg['rydberg_source']}) vs NIST, n = 15-45, {len(dev)} levels with NIST unc <= 0.01 cm^-1: "
                 f"max |d| = {max(map(abs, dev)):.4f} cm^-1") if dev else "Rydberg terms: no precise NIST levels at n >= 15 to compare with"

    col_keys = [(0, 0.5), (1, 0.5), (1, 1.5), (2, 1.5), (2, 2.5), (3, 2.5), (3, 3.5)]
    columns = [dict(key=f"{al.L_LETTERS[l]}{al.jstr(j)}", header=rf"^2{al.L_LETTERS[l]}_{{{al.jstr(j)}}}", group=None, width=1.0)
               for l, j in col_keys]
    levels, by_name, check = [], {}, []
    for lv in nist:
        q = nlj(lv)
        if not q or lv["E"] > cfg["E_cut"]:
            continue
        n, l, j = q
        ground = lv["E"] == 0
        L = dict(id=len(levels), col=col_keys.index((l, j)), E=lv["E"], unc=lv["unc"], J=j, n=n, l=l,
                 name=rf"{n}{al.L_LETTERS[l]}_{{{al.jstr(j)}}}", plain=name(n, l, j), parity="odd" if l % 2 else "even")
        tau = lit.lifetime_ns(lv["E"], lv["J"])
        if ground:
            L.update(tau_ns=None, tau_tier="stable")
        elif tau:
            L.update(tau_ns=sig(tau[0], 6), tau_unc=tau[1], tau_tier=tau[2], tau_src=tau[3])
        else:
            L.update(tau_ns=sig(atom.getStateLifetime(n, l, j) * 1e9, 4), tau_tier="model", tau_src="ARC (sum of calculated rates, 0 K)")
        if not ground:
            L["tau_arc_ns"] = sig(atom.getStateLifetime(n, l, j) * 1e9, 4)
        h = lit.hyperfine(lv["E"], lv["J"])
        if not h:
            try:
                A, B = atom.getHFSCoefficients(n, l, j)
                if A:
                    h = dict(A=round(A / 1e6, 5), B=round(B / 1e6, 5) if B else None, tier="exp", src="compiled in ARC")
            except Exception:
                pass
        if h:
            L["hfs"] = h
        check.append((L["plain"], lv["E"], arc_cm(n, l, j) - lv["E"], (pi_cm(n, l, j) - lv["E"]) if pi else None))
        by_name[L["plain"]] = L
        levels.append(L)

    transitions = []
    for lo in levels:
        for up in levels:
            if up["E"] <= lo["E"] or abs(lo["l"] - up["l"]) != 1 or abs(lo["J"] - up["J"]) > 1:
                continue
            wn = up["E"] - lo["E"]
            if 1e7 / wn >= LAMBDA_MAX_NM:
                continue
            a, b = (lo["n"], lo["l"], lo["J"]), (up["n"], up["l"], up["J"])
            t = dict(kind="E1")
            lt = finish_transition(t, lo, up, lit, up.get("tau_ns"))
            wn = t["wn"]
            d_arc = abs(atom.getReducedMatrixElementJ(*a, *b))
            arc_lit = atom.getLiteratureDME(*a, *b)
            nl = nist_A.get((round(lo["E"], 1), round(up["E"], 1)), {})
            cands = []  # (priority, d, tier, source)
            v = Literature.rme(lt)
            if v:
                cands.append((0 if v[2] == "exp" else 3, v[0], v[2], v[3], v[1]))
            v = Literature.val(lt.get("A_s")) if lt else None
            if v:
                cands.append((1 if v[2] == "exp" else 3.5, al.rme_from_rate(v[0], wn, up["J"]), v[2], v[3] + " (from A)", None))
            if nl.get("A"):
                cands.append((2, al.rme_from_rate(nl["A"], wn, up["J"]), "nist", f"NIST ASD A = {nl['A']:.3g} s^-1 (accuracy {nl['acc'] or 'n/a'})", None))
            if arc_lit[0]:
                ref = str(arc_lit[2][3]) if len(arc_lit[2]) > 3 else "ARC literature table"
                steck = "D Line Data" in ref or "steck" in str(arc_lit[2]).lower()
                cands.append((2.5 if steck else 4, d_arc, "exp" if steck else "theory", ref + " (via ARC)", None))
            else:
                cands.append((5, d_arc, "model", "ARC model potential", None))
            cands.sort(key=lambda c: c[0])
            _, d, tier, src, unc = cands[0]
            t.update(d=sig(d, 5), d_tier=tier, d_src=src, d_arc=sig(d_arc, 5),
                     A=sig(al.rate_from_rme(d, wn, up["J"]), 4), A_tier=tier)
            if unc:
                t["d_unc"] = unc
            if "br" not in t:
                # share of the upper level's decays, from the ARC rate set (consistent normalisation)
                t.update(br=sig(atom.getTransitionRate(*b, *a, temperature=0) * atom.getStateLifetime(*b), 4), br_tier="model")
            t["lam_arc"] = round(abs(atom.getTransitionWavelength(*a, *b)) * 1e9, 4)
            if nl.get("obs"):
                t["lam_obs"] = nl["obs"]
            transitions.append(t)
    # forbidden lines that NIST lists between the drawn levels (E2, M1, ...)
    by_E = {round(l["E"], 1): l for l in levels}
    for ln in al.nist_lines(sym):
        lo, up = by_E.get(round(ln["Ei"], 1)), by_E.get(round(ln["Ek"], 1))
        if not lo or not up or ln["type"] in ("", "2P") or 1e7 / (up["E"] - lo["E"]) >= LAMBDA_MAX_NM:
            continue
        t = dict(kind="forbidden", type=ln["type"])
        finish_transition(t, lo, up, lit, up.get("tau_ns"))
        if ln["A"]:
            t.update(A=sig(ln["A"], 4), A_tier="nist", A_src=f"NIST ASD (accuracy {ln['acc'] or 'n/a'})")
        transitions.append(t)
    for t in transitions:
        t.setdefault("type", "E1")
    transitions.sort(key=lambda t: t["lam"])
    # closed-transition analysis: ARC supplies the decay lines that are not drawn (beyond 2 um), so the set is complete
    have = {(t["lower"], t["upper"]) for t in transitions}
    extra = [dict(upper=up["id"], lower=lo["id"], tier="model",
                  br=atom.getTransitionRate(up["n"], up["l"], up["J"], lo["n"], lo["l"], lo["J"], temperature=0) * atom.getStateLifetime(up["n"], up["l"], up["J"]))
             for up in levels for lo in levels
             if lo["E"] < up["E"] and abs(lo["l"] - up["l"]) == 1 and abs(lo["J"] - up["J"]) <= 1 and (lo["id"], up["id"]) not in have]
    cycling.annotate(levels, transitions, levels, {l["id"]: l["id"] for l in levels}, extra, None)
    n0 = levels[0]["n"]
    P = sorted({l["n"] for l in levels if l["l"] == 1})[:2]
    if "rydberg_draw" not in cfg:
        cfg = dict(cfg, rydberg_draw=[(levels[0]["plain"], "P3/2")] + [(f"{n}P{j}", s_) for n in P for j, s_ in
                                      (("1/2", "S1/2"), ("1/2", "D3/2"), ("3/2", "S1/2"), ("3/2", "D5/2")) if f"{n}P{j}" in by_name])
        cfg["rydberg_table"] = [l["plain"] for l in levels if 1e7 / (limit - l["E"]) < LAMBDA_MAX_NM and l["J"] in (0.5, 1.5, 2.5, 3.5)
                                and not (l["l"] >= 1 and l["J"] < l["l"])][:11]
    if "key" not in cfg:
        first_p = {f"{P[0]}P1/2", f"{P[0]}P3/2"}
        pick = [t for t in transitions if t["kind"] == "E1" and (t["lower"] == 0 or levels[t["lower"]]["plain"] in first_p)]
        cfg["key"] = [(levels[t["lower"]]["plain"], levels[t["upper"]]["plain"], short_use(t.get("use", "")))
                      for t in sorted(pick, key=lambda t: -t["A"])[:17]]

    # ---- Rydberg series
    ryd_tr, ryd_rows = [], []
    lowers = [l for l in levels if 1e7 / (limit - l["E"]) < LAMBDA_MAX_NM]
    series_cache = {}

    def series(lo, l2, j2):
        k = (lo["plain"], l2, j2)
        if k not in series_cache:
            q = (lo["n"], lo["l"], lo["J"])
            lam = {n: 1e7 / (ryd_cm(n, l2, j2) - lo["E"]) for n in RYDBERG_N}
            d_arc = abs(atom.getReducedMatrixElementJ(*q, 70, l2, j2))
            d_pi = None
            if pi:
                me_arc = atom.getDipoleMatrixElement(*q, 0.5, 70, l2, j2, 0.5, 0)
                me_pi = pi(*q).get_matrix_element(pi(70, l2, j2), "electric_dipole", q=0, unit="e*a0")
                d_pi = abs(me_pi / me_arc) * d_arc
            series_cache[k] = dict(lam=lam, limit=1e7 / (limit - lo["E"]), d_arc=d_arc, d_pi=d_pi)
        return series_cache[k]

    for lo_name, ser in cfg["rydberg_draw"]:
        lo = by_name[lo_name]
        l2, j2 = al.L_LETTERS.index(ser[0]), float(Fraction(ser[1:]))
        s = series(lo, l2, j2)
        lam = s["lam"][70]
        d = s["d_pi"] if s["d_pi"] is not None else s["d_arc"]
        ryd_tr.append(dict(kind="rydberg", lower=lo["id"], upper_col=col_keys.index((l2, j2)), upper_name=rf"70{ser[0]}_{{{ser[1:]}}}",
                           upper_plain=f"70{ser}", lam=round(lam, 4), freq=round(al.C / lam / 1e3, 4), limit_nm=round(s["limit"], 3),
                           d=sig(d, 4), d_tier="model", d_src="pairinteraction" if s["d_pi"] is not None else "ARC model potential",
                           d_arc=sig(s["d_arc"], 4), uncertain=bool(s["d_pi"] is not None and not 0.7 < s["d_pi"] / s["d_arc"] < 1.43)))
    for lo_name in cfg["rydberg_table"]:
        lo = by_name[lo_name]
        for l2 in (lo["l"] - 1, lo["l"] + 1):
            if not 0 <= l2 <= 3:
                continue
            j2 = min(l2 + 0.5, lo["J"] + 1)
            s = series(lo, l2, j2)
            row = [rf"${lo['name']}$ → $n{al.L_LETTERS[l2]}_{{{al.jstr(j2)}}}$"] + [f"{s['lam'][n]:.3f}" for n in RYDBERG_N] + [f"{s['limit']:.3f}"]
            row += ([f"{s['d_pi']:.4f}"] if pi else []) + [f"{s['d_arc']:.4f}"]
            ryd_rows.append(row)
    n_top = {c: max([l["n"] for l in levels if l["col"] == c], default=0) for c in range(len(col_keys))}
    ryd_levels = [dict(col=c, n=n, E=round(ryd_cm(n, l, j), 3)) for c, (l, j) in enumerate(col_keys) for n in range(n_top[c] + 1, 61)
                  if ryd_cm(n, l, j) > max(l_["E"] for l_ in levels)]

    # ---- tables
    tr_by = {(levels[t["lower"]]["plain"], levels[t["upper"]]["plain"]): t for t in transitions}
    rows = []
    for lo, up, use in cfg["key"]:
        t = tr_by.get((lo, up))
        if not t:
            continue
        use = use or short_use(t.get("use", ""))
        rows.append([rf"${by_name[lo]['name']}$ – ${by_name[up]['name']}$", f"{t['lam']:.4f}", f"{t['air']:.4f}", f"{t['freq']:.4f}",
                     f"{t['wn']:.3f}", fmt_d(t), f"{t['A']:.3e}", f"{t.get('gamma_MHz', 0):.3f}", f"{t['br'] * 100:.1f}", use])
    tables = [dict(title="Key transitions",
                   header=["Transition", "λ vac (nm)", "λ air (nm)", "ν (THz)", "ν̃ (cm⁻¹)", "|⟨J‖er‖J′⟩| (ea₀)", "A (s⁻¹)", "Γ/2π up. (MHz)", "branch (%)", "Typical use"],
                   aligns="lrrrrrrrrl", rows=rows,
                   note="λ and ν from NIST level energies (centre of gravity, no hyperfine structure); λ air uses standard air (Ciddor).\n"
                        "Γ/2π: natural linewidth of the upper level, 1/(2πτ).  Branch: share of the upper level's decays that takes this line.")]
    src = "pairinteraction" if cfg["rydberg_source"] == "pairinteraction" else "ARC quantum defects + NIST ionisation limit"
    tables.append(dict(title="Rydberg excitation wavelengths  (vacuum, nm)",
                       header=["Lower → series"] + [f"n = {n}" for n in RYDBERG_N] + ["n → ∞"] + (["d₇₀ pairint."] if pi else []) + ["d₇₀ ARC"],
                       aligns="l" + "r" * (len(RYDBERG_N) + 2 + (1 if pi else 0)), rows=ryd_rows,
                       note=f"Rydberg term energies from {src}, lower level from NIST.  d₇₀ = |⟨J‖er‖J′⟩| to n = 70 in ea₀ (calculated).\n"
                            "S → nP values come from a near-cancelling integral: treat them as an order of magnitude."))
    I = float(atom.I)
    rows = []
    for L in levels:
        h = L.get("hfs")
        if not h or L["n"] > nist_n0(levels) + 2:
            continue
        shifts = "   ".join(f"F={f}: {e:+.2f}" for f, e in hfs_shifts(I, L["J"], h["A"], h.get("B") or 0))
        rows.append([f"${L['name']}$", fmt_unc(h["A"], h.get("A_unc"), 3), fmt_unc(h["B"], h.get("B_unc"), 3) if h.get("B") else "–", shifts])
    tables.append(dict(title=rf"$^{{{cfg['A']}}}${sym} hyperfine structure  ($I$ = {al.jstr(I)})",
                       header=["Level", "A (MHz)", "B (MHz)", "Shift of each F level from the centre of gravity (MHz)"],
                       aligns="lrrl", rows=rows, note="A, B: magnetic-dipole and electric-quadrupole constants (measured; see data file for sources)."))

    dev_arc = max(abs(c[2]) for c in check)
    validation = [f"levels: {len(levels)}   lines < {LAMBDA_MAX_NM:.0f} nm: {len(transitions)}",
                  f"level energy, ARC - NIST: max |d| = {dev_arc:.3f} cm^-1"]
    validation.append(ryd_check)
    if pi:
        validation.append(f"level energy, pairinteraction - NIST: max |d| = {max(abs(c[3]) for c in check):.3f} cm^-1")
    tiers = {}
    for t in transitions:
        tiers[t.get("d_tier", "forbidden line")] = tiers.get(t.get("d_tier", "forbidden line"), 0) + 1
    validation.append("matrix-element provenance: " + ", ".join(f"{k}: {v}" for k, v in sorted(tiers.items())))
    lt = {}
    for l in levels:
        lt[l["tau_tier"]] = lt.get(l["tau_tier"], 0) + 1
    validation.append("lifetime provenance: " + ", ".join(f"{k}: {v}" for k, v in sorted(lt.items())))
    for t in transitions:
        if t.get("d_tier") in ("exp", "nist") and not 0.8 < t["d_arc"] / t["d"] < 1.25:
            validation.append(f"  ARC differs from {t['d_tier']} on {levels[t['lower']]['plain']}-{levels[t['upper']]['plain']}: "
                              f"{t['d_arc']:.4g} vs {t['d']:.4g} ea0")
    meta = dict(key=key, slug=cfg["slug"], element=cfg["element"], symbol=sym, A=cfg["A"], Z=cfg["Z"], I=al.jstr(I), kind="alkali",
                limit_cm=limit, scale=cfg["scale"], spectrum=f"{sym} I",
                limit_text=rf"{sym}$^+$ ionisation limit   {limit:.2f} cm$^{{-1}}$  =  {limit / al.EV_TO_CM:.5f} eV  =  {limit * al.C / 1e10:.3f} THz  ({1e7 / limit:.3f} nm)",
                rydberg_note=f"Rydberg series drawn to $n$ = 60 ({src})",
                guide_tau="Level caption:  NIST energy and lifetime (measured where a value exists, otherwise ARC, marked ≈).")
    return dict(meta=meta, columns=columns, levels=levels, transitions=transitions + ryd_tr, rydberg_levels=ryd_levels,
                tables=tables, validation=validation, sources=lit.source_urls())


def short_use(u, n=58):
    u = re.split(r"[;(]", u)[0].strip()
    return u if len(u) <= n else u[:n - 1].rstrip() + "…"


def nist_n0(levels):
    return levels[0]["n"]


def fmt_d(t):
    if t.get("d") is None:
        return "–"
    d = t["d"]
    s = f"{d:.3f}" if d < 10 else f"{d:.2f}"
    return {"model": "≈" + s, "semi": "≈" + s, "theory": s + "*"}.get(t.get("d_tier"), s)


# ----------------------------------------------------------------------------- everything else
def build_nist(key, cfg):
    sym = cfg["symbol"]
    lit = Literature(sym, cfg["A"])
    hfs_iso = None
    if cfg.get("auto") and not cfg["A"] and lit.raw.get("isotopes"):
        # element page with a literature file: frequencies of the most abundant isotope,
        # hyperfine constants of the most abundant isotope that has a nuclear spin
        iso = lit.raw["isotopes"]
        ab = lambda k: iso[k].get("abundance_percent") or 0 if isinstance(iso[k], dict) else 0
        n_freq = lambda k: sum(1 for t in lit.raw.get("transitions", []) if isinstance(t.get("frequency_THz"), dict)
                               and str(t["frequency_THz"].get("isotope")) == k) + sum(1 for t in lit.raw.get("transitions", []) if f"frequency_THz_{k}" in t)
        lit.iso = max(iso, key=lambda k: (ab(k), n_freq(k)))  # radioactive elements: the isotope with most measured frequencies
        with_hfs = {k for l in lit.raw.get("levels", []) for k in (l.get("hyperfine") or {})}
        if with_hfs:
            n_hfs = lambda k: sum(1 for l in lit.raw.get("levels", []) if k in (l.get("hyperfine") or {}))
            # ties go to the heaviest isotope (a set has no fixed order, so the choice must not depend on it)
            hfs_iso = max(sorted(with_hfs), key=lambda k: (ab(k) if k in iso else -1, n_hfs(k), int(re.sub(r"\D", "", str(k)) or 0)))
            cfg = dict(cfg, I=str((iso.get(hfs_iso) or {}).get("I", "0")) if isinstance(iso.get(hfs_iso), dict) else "0")
    nist, limit = al.nist_levels(sym)
    # levels NIST does not carry (actinides: only the ground level is in ASD), taken from the literature file
    for x in lit.raw.get("levels_not_in_nist", []):
        if not isinstance(x.get("energy_cm"), (int, float)) or any(abs(l["E"] - x["energy_cm"]) < 0.05 for l in nist):
            continue
        try:
            j = float(Fraction(str(x.get("J"))))
        except (ValueError, ZeroDivisionError):
            continue
        term = x.get("term") or ""
        if x.get("parity") == "odd" and "*" not in term:
            term += "*"
        nist.append(dict(conf=x.get("configuration") or "", term=term, J=j, E=x["energy_cm"], unc=x.get("unc"), g=x.get("g_J"),
                         lit=(TIER_OF.get(x.get("method"), "exp"), x.get("source", ""))))
    nist.sort(key=lambda l: l["E"])
    for i, l in enumerate(nist):
        l["i"] = i
    lines = al.nist_lines(sym, 1 if cfg.get("auto") else 200)
    E = np.array([l["E"] for l in nist])
    # NIST occasionally attaches an electric-dipole line to a neighbouring level whose J makes the line impossible
    # (Nd 468.48 nm: lower J = 4, listed upper J = 6 at 21345.572; the J = 4 level at 21345.837 fits the wavelength).
    # Such a line goes to the level within 1 cm^-1 that allows it, or is dropped.
    fixed = []
    for ln in lines:
        if not ln["type"] and ln["Ji"] is not None and ln["Jk"] is not None and abs(ln["Ji"] - ln["Jk"]) > 1:
            ok = [l for l in nist if abs(l["E"] - ln["Ek"]) < 1.0 and l["J"] is not None and abs(l["J"] - ln["Ji"]) <= 1]
            if not ok:
                continue
            best = min(ok, key=lambda l: abs(l["E"] - ln["Ek"]))
            ln = dict(ln, Ek=best["E"], Jk=best["J"])
        fixed.append(ln)
    lines = fixed

    def find(e, tol=1.0, j=None):
        """Nearest NIST level; J decides between fine-structure components NIST lists at one energy."""
        near = [i for i in np.flatnonzero(np.abs(E - e) < tol)]
        same_j = [i for i in near if j is not None and nist[i]["J"] == j]
        return nist[min(same_j or near, key=lambda i: abs(E[i] - e))] if near else None

    jof = lambda x: float(Fraction(str(x))) if re.fullmatch(r"\d+(/2)?", str(x)) else None

    # ---- which lines are drawn
    chosen = {}
    # decay channels of the closed-transition analysis: every NIST line from 1 nm to 1 mm, whatever range is drawn
    all_lines, line_tol = (lines if cfg.get("auto") else al.nist_lines(sym, 1)) + al.nist_lines_ir(sym), 0.05 if cfg.get("auto") else 1.0
    if cfg.get("auto"):
        chosen = auto_select(nist, lines, lambda e, j: find(e, 0.05, j))
        lines = []
    for ln in lines:
        lo, up = find(ln["Ei"], j=ln["Ji"]), find(ln["Ek"], j=ln["Jk"])
        if not lo or not up or up["E"] > cfg["E_cut"] or 1e7 / (up["E"] - lo["E"]) >= LAMBDA_MAX_NM or ln["type"] == "2P":
            continue
        if ln["A"] is None and not cfg["keep_unrated"] and not lit.transition(lo["E"], up["E"], lo["J"], up["J"]):
            continue
        merge_line(chosen, (lo["i"], up["i"]), ln)
    def lit_rank(lt):  # annotated lines first, then the strongest
        v = Literature.val(lt.get("A_s"))
        inten = lt.get("relative_intensity")
        return (0 if lt.get("use") else 1, -(v[0] if v else 0), -(inten if isinstance(inten, (int, float)) else 0))

    for lt in sorted(lit.raw.get("transitions", []), key=lit_rank):
        lo, up = find(lt.get("lower_cm", -1e9), j=jof(lt.get("lower_J"))), find(lt.get("upper_cm", -1e9), j=jof(lt.get("upper_J")))
        if lo and up and up["E"] > lo["E"] and 1e7 / (up["E"] - lo["E"]) < LAMBDA_MAX_NM and up["E"] <= max(cfg["E_cut"], 0):
            if cfg.get("auto") and len(chosen) >= 90 and not lt.get("use") and (lo["i"], up["i"]) not in chosen:
                continue  # a big literature table must not flood an automatic page: only its annotated lines are added
            chosen.setdefault((lo["i"], up["i"]), {})
    used = sorted({i for pair in chosen for i in pair})  # indices into the energy-ordered NIST level list
    if not used and cfg.get("auto") and len(nist) >= 5:
        used = [l["i"] for l in nist[:40]]  # NIST has levels but no classified lines: draw the lowest levels only
    if not used:
        return None
    if cfg.get("auto"):
        used = sorted(set(used) | {0})  # the ground state is always drawn
    if cfg.get("auto"):
        # column scheme: LS terms when nearly every level has one and they fit, otherwise parity and J
        terms = [nist[i]["term"] or "" for i in used]
        n_ls = sum(1 for t in terms if re.fullmatch(al.LS_TERM, t))
        cfg = dict(cfg, columns="LS" if n_ls >= 0.8 * len(used) and len(set(terms)) <= 15 else "J")
        # closed-shell prefix shared by every drawn configuration
        confs = [nist[i]["conf"].split(".") for i in used]
        k = 0
        while all(len(c) > k + 1 for c in confs) and len({c[k] for c in confs}) == 1:
            k += 1
        cfg["core"] = [".".join(confs[0][:k]) + "."] if k else []

    def level_name(lv):
        if (lv["term"] or "").strip("*?") == "":
            # no term assigned by NIST: name the level by its energy
            return rf"({lv['E']:.0f})" + ("^{o}" if al.parity_of(lv["conf"], lv["term"]) == "odd" else "") + rf"_{{{al.jstr(lv['J'])}}}"
        return (al.conf_tex(al.short_conf(lv["conf"], cfg["core"])) + r"\ " if cfg["columns"] == "LS" else "") + al.term_tex(lv["term"], lv["J"])

    # ---- levels and columns
    levels = []
    for i in used:
        lv = nist[i]
        sc = al.short_conf(lv["conf"], cfg["core"])
        par = al.parity_of(lv["conf"], lv["term"])
        ls = re.fullmatch(al.LS_TERM, lv["term"] or "")
        if cfg["columns"] == "LS" and ls:
            group = lv["term"].replace("?", "")
            gtex = (rf"\mathrm{{{ls.group(1)}}}\," if ls.group(1) else "") + rf"^{ls.group(2)}{ls.group(3)}" + ("^{o}" if ls.group(4) else "")
        elif cfg["columns"] == "LS":
            group, gtex = f"other {par}", (r"\mathrm{other\ (odd)}" if par == "odd" else r"\mathrm{other\ (even)}")
        else:
            group, gtex = par, rf"\mathrm{{{par}}}"
        name = level_name(lv)
        L = dict(id=len(levels), E=lv["E"], unc=lv["unc"], J=lv["J"], conf=lv["conf"], term=lv["term"], parity=par, g=lv["g"],
                 name=name, plain=f"{sc.replace('.', '')} {lv['term'].replace('*', '°').replace('?', '')}{al.jstr(lv['J'])}".strip(), _group=group, _gtex=gtex, _i=i)
        em = lit.energy(lv["E"], lv["J"], lv["unc"]) if lv["E"] else None
        if em:
            L.update(E=em[0], unc=em[1], E_nist=lv["E"], E_tier="exp", E_src=em[2])
        elif lv.get("lit"):
            L.update(E_tier=lv["lit"][0], E_src=lv["lit"][1])
        tau = lit.lifetime_ns(lv["E"], lv["J"])
        if lv["E"] == 0:
            L.update(tau_ns=None, tau_tier="stable")
        elif tau:
            L.update(tau_ns=sig(tau[0], 6), tau_unc=tau[1], tau_tier=tau[2], tau_src=tau[3])
            bound = re.search(r"Note: .*?\b(upper|lower) (limit|bound)", tau[3], re.I)
            if bound:  # a limit is not a measured value: shown as "< 30 ns"
                L["tau_bound"] = "<" if bound.group(1).lower() == "upper" else ">"
        else:
            L.update(tau_ns=None, tau_tier="none")
        if hfs_iso:
            main_iso, lit.iso = lit.iso, hfs_iso
            h = lit.hyperfine(lv["E"], lv["J"])
            lit.iso = main_iso
        else:
            h = lit.hyperfine(lv["E"], lv["J"])
        if h:
            L["hfs"] = h
        g = lit.val(lit.level(lv["E"], lv["J"]).get("g_J"))
        if g and L["g"] is None:
            L["g"] = g[0]
            if g[2] == "theory":
                L["g_tier"] = "theory"  # calculated g factor: shown with the theory tag
        levels.append(L)
    groups = {}
    for L in levels:
        gkey = L["_group"] if cfg["columns"] == "LS" else (L["_group"], L["J"])
        groups.setdefault(gkey, []).append(L)
    order = sorted(groups, key=lambda g: min(l["E"] for l in groups[g]))
    if cfg["columns"] != "LS":
        ground_parity = levels[0]["parity"]
        order = sorted(groups, key=lambda g: (g[0] != ground_parity, g[1]))
    # shorten the arrows: reorder the columns (ground-state column stays first) to minimise total horizontal span
    gof = {l["_i"]: g for g, ls in groups.items() for l in ls}
    pairs = [(gof[a], gof[b]) for a, b in chosen]

    def span(o):
        x = {g: i for i, g in enumerate(o)}
        return sum(abs(x[a] - x[b]) for a, b in pairs)

    improved = True
    while improved and cfg["columns"] == "LS":
        improved = False
        for i in range(1, len(order)):
            for j in range(1, len(order)):
                if i == j:
                    continue
                trial = order[:]
                trial.insert(j, trial.pop(i))
                if span(trial) < span(order):
                    order, improved = trial, True
    columns = []
    for g in order:
        for l in groups[g]:
            l["col"] = len(columns)
        first = groups[g][0]
        if cfg["columns"] == "LS":
            columns.append(dict(key=g, header=first["_gtex"], group=None, width=1.0))
        else:
            columns.append(dict(key=f"{g[0]} J={al.jstr(g[1])}", header=rf"J = {al.jstr(g[1])}", group=first["_gtex"], width=1.0))
    by_E = {l["_i"]: l for l in levels}
    for L in levels:
        del L["_group"], L["_gtex"], L["_i"]

    # ---- semi-empirical rates (Kurucz line list, where cached): the last resort for a drawn line and for the decay lines below
    semi_A, semi_src, semi_url, semi_stat = semi.rates(sym, nist)

    # ---- transitions
    transitions = []
    for (elo, eup), ln in chosen.items():
        lo, up = by_E[elo], by_E[eup]
        t = dict(kind="E1")
        lt = finish_transition(t, lo, up, lit, up.get("tau_ns"))
        if ln.get("type"):
            t.update(kind="forbidden", type=ln["type"])
        elif lo["parity"] == up["parity"] and t["kind"] == "E1":
            t.update(kind="forbidden", type=lt.get("type") if lt.get("type") not in (None, "E1", "intercombination") else "E2 / M1")
        if "type" not in t:
            mult = [re.fullmatch(al.LS_TERM, l["term"] or "") for l in (lo, up)]
            spin_flip = all(mult) and mult[0].group(2) != mult[1].group(2)
            t["type"] = "E1 (intercombination)" if spin_flip or lt.get("type") == "intercombination" else "E1"
        cands = []
        v = Literature.val(lt.get("A_s")) if lt else None
        if v:
            cands.append((0 if v[2] == "exp" else 2, v[0], v[2], v[3], v[1]))
        if ln.get("A"):
            cands.append((1, ln["A"], "nist", f"NIST ASD (accuracy {ln['acc'] or 'n/a'})", None))
        v = Literature.rme(lt)
        if v and t["kind"] == "E1":
            cands.append((0.5 if v[2] == "exp" else 2.5, al.rate_from_rme(v[0], t["wn"], up["J"]), v[2], v[3], None))
        if not cands and t.get("br") and up.get("tau_ns") and t.get("br_tier") == "exp":
            cands.append((3, t["br"] / (up["tau_ns"] * 1e-9), up["tau_tier"], "branching ratio / lifetime", None))
        if not cands and t["kind"] == "E1" and (elo, eup) in semi_A:
            cands.append((6, semi_A[(elo, eup)], "semi", semi_src, None))
        if cands:
            cands.sort(key=lambda c: c[0])
            _, A, tier, src, unc = cands[0]
            t.update(A=sig(A, 4), A_tier=tier, A_src=src)
            note = str((lt.get("A_s") or {}).get("note", "")) if lt else ""
            if re.search(r"bound|limit|≤|>=|≥", note, re.I):
                t.update(uncertain=True, A_src=f"{src}. Note: {note}")
            if unc:
                t["A_unc"] = unc
            if t["kind"] == "E1":
                t.update(d=sig(al.rme_from_rate(A, t["wn"], up["J"]), 4), d_tier=tier, d_src=src + " (from A)")
            if "br" not in t and up.get("tau_ns"):
                t.update(br=sig(min(1.0, A * up["tau_ns"] * 1e-9), 4), br_tier=tier)
        if ln.get("obs"):
            t["lam_obs"] = ln["obs"]
        transitions.append(t)
    transitions.sort(key=lambda t: t["lam"])

    # ---- closed-transition analysis: decay lines that are not drawn (weak NIST lines, literature lines beyond 2 um), of every
    # level: a decay is followed down through levels that are not drawn too
    extra = {}
    for ln in all_lines:
        lo, up = find(ln["Ei"], line_tol, ln["Ji"]), find(ln["Ek"], line_tol, ln["Jk"])
        if lo and up and up["E"] > lo["E"] and (lo["i"], up["i"]) not in chosen and ln["A"] and ln["type"] != "2P":
            merge_line(extra, (lo["i"], up["i"]), ln)
    extra = {k: dict(A=ln["A"], tier="nist") for k, ln in extra.items()}
    for lt in lit.raw.get("transitions", []):
        lo, up = find(lt.get("lower_cm", -1e9), j=jof(lt.get("lower_J"))), find(lt.get("upper_cm", -1e9), j=jof(lt.get("upper_J")))
        if not lo or not up or up["E"] <= lo["E"] or (lo["i"], up["i"]) in chosen:
            continue
        br, A, d = Literature.val(lt.get("branching")), Literature.val(lt.get("A_s")), Literature.rme(lt)
        if not A and d and al.parity_of(lo["conf"], lo["term"]) != al.parity_of(up["conf"], up["term"]):
            A = (al.rate_from_rme(d[0], up["E"] - lo["E"], up["J"]), None, d[2])
        old = extra.get((lo["i"], up["i"]))
        if A and old and A[2] != "exp":
            A = None  # NIST ranks above a calculated rate
        if br or A:
            extra[(lo["i"], up["i"])] = dict(A=A[0] if A else old and old["A"], br=br[0] if br else None, tier=(br or A)[2])
    n_semi_extra = 0
    for pair, A in semi_A.items():  # Kurucz lines fill in only where no NIST or literature rate exists
        if pair not in chosen and pair not in extra:
            extra[pair] = dict(A=A, tier="semi")
            n_semi_extra += 1
    pool = [dict(E=l["E"], J=l["J"], parity=al.parity_of(l["conf"], l["term"])) for l in nist]
    cycling.annotate(levels, transitions, pool, {l["id"]: i for i, l in by_E.items()},
                     [dict(x, lower=lo, upper=up) for (lo, up), x in extra.items()],
                     lambda k: al.tex_to_html(level_name(nist[k])))

    # ---- tables
    I = float(Fraction(cfg["I"] or 0))
    label = lambda t: rf"${levels[t['lower']]['name']}$ – ${levels[t['upper']]['name']}$"
    keyed = [t for t in transitions if t.get("use") and not re.match(r"decay branch|calculated|leak channel", t["use"])][:24] or sorted([t for t in transitions if t.get("A")], key=lambda t: -t["A"])[:16]
    rows = [[label(t), f"{t['lam']:.4f}", f"{t['air']:.4f}" if t.get("air") else "–", fmt_unc(t["freq"], t.get("freq_unc"), 4), fmt_d(t),
             f"{t['A']:.3e}" if t.get("A") else "–", f"{t['gamma_MHz']:.4g}" if t.get("gamma_MHz") else "–",
             f"{t['br'] * 100:.3g}" if t.get("br") is not None else "–", short_use(t.get("use", ""))] for t in sorted(keyed, key=lambda t: t["lam"])]
    tables = [dict(title="Key transitions",
                   header=["Transition", "λ vac (nm)", "λ air (nm)", "ν (THz)", "|⟨J‖er‖J′⟩| (ea₀)", "A (s⁻¹)", "Γ/2π up. (MHz)", "branch (%)", "Use"],
                   aligns="lrrrrrrrl", rows=rows,
                   note="λ, ν from NIST level energies unless a measured frequency for this isotope is available.  A: measured value or NIST.\n"
                        "Γ/2π: natural linewidth of the upper level, 1/(2πτ).")]
    rows = []
    for L in levels:
        h = L.get("hfs")
        if not h:
            continue
        shifts = "   ".join(f"F={f}: {e:+.2f}" for f, e in hfs_shifts(I, L["J"], h["A"], h.get("B") or 0))
        rows.append([f"${L['name']}$", fmt_unc(h["A"], h.get("A_unc"), 3), fmt_unc(h["B"], h.get("B_unc"), 3) if h.get("B") else "–", shifts])
    if rows:
        tables.append(dict(title=rf"$^{{{cfg['A'] or hfs_iso}}}${sym} hyperfine structure  ($I$ = {cfg['I']})",
                           header=["Level", "A (MHz)", "B (MHz)", "Shift of each F level from the centre of gravity (MHz)"],
                           aligns="lrrl", rows=rows, note="Measured A, B constants; sources in the data file."))
    if cfg.get("auto") and not any(t.get("use") for t in transitions):
        tables[0]["title"] = "Strongest transitions"
        tables[0]["rows"] = tables[0]["rows"][:18]
    rows = []
    for t in transitions:
        for pair, s in (t.get("isotope_shifts") or {}).items():
            rows.append([label(t), f"{t['lam']:.3f}", pair, fmt_unc(s["value"], s.get("unc"), 2)])
    if rows:
        tables.append(dict(title="Isotope shifts", header=["Transition", "λ vac (nm)", "Isotopes", "Shift (MHz)"], aligns="lrlr",
                           rows=rows[:22], note="Shift = ν(first isotope) − ν(second isotope)."))

    n_d = sum(1 for t in transitions if t.get("d") is not None)
    # levels taken from the literature file because NIST does not list them (actinides)
    n_lit_lv = sum(1 for l in levels if l.get("E_tier") and "E_nist" not in l)
    lit_levels = n_lit_lv > (len(levels) - 1) / 2  # most excited levels are literature-only
    if lit_levels:
        tables[0]["note"] = tables[0]["note"].replace("λ, ν from NIST level energies", "λ, ν from the level energies of the cited literature (NIST lists no excited levels)")
    tiers = {}
    for t in transitions:
        k = t.get("A_tier", "wavelength only")
        tiers[k] = tiers.get(k, 0) + 1
    validation = [f"levels: {len(levels)}   lines < {LAMBDA_MAX_NM:.0f} nm: {len(transitions)}   with matrix element: {n_d}",
                  "transition-rate provenance: " + ", ".join(f"{k}: {v}" for k, v in sorted(tiers.items())),
                  f"levels with a measured lifetime: {sum(1 for l in levels if l['tau_tier'] in ('exp', 'theory'))}"]
    if semi_stat:
        validation.append(f"semi-empirical rates (Kurucz): {semi_stat['matched']} of {semi_stat['lines']} lines on NIST levels; used for "
                          f"{sum(1 for t in transitions if t.get('A_tier') == 'semi')} drawn lines and {n_semi_extra} further decay lines")
    for t in transitions:
        if t.get("lam_obs") and abs(t["lam_obs"] - t["lam"]) > 0.05:
            validation.append(f"  observed vs Ritz wavelength differ on {levels[t['lower']]['plain']} - {levels[t['upper']]['plain']}: "
                              f"{t['lam_obs']} vs {t['lam']}")
    meta = dict(key=key, slug=cfg["slug"], element=cfg["element"], symbol=sym, A=cfg["A"], Z=cfg["Z"], I=cfg["I"], kind="nist",
                limit_cm=limit, scale="auto", spectrum=f"{sym} I", auto=bool(cfg.get("auto")),
                has_lit=bool(lit.raw.get("levels") or lit.raw.get("transitions")), freq_isotope=lit.iso if cfg.get("auto") else None,
                limit_text=(rf"{sym}$^+$ ionisation limit   {limit:.2f} cm$^{{-1}}$  =  {limit / al.EV_TO_CM:.5f} eV  ({1e7 / limit:.3f} nm)"
                            if limit else "ionisation limit not listed by NIST"),
                lit_levels=n_lit_lv,
                guide_tau=("Level caption:  energy (from the cited literature; NIST lists no excited levels) and measured lifetime (where one exists)." if lit_levels else
                           "Level caption:  energy (NIST, or a measurement of the last %d years where one exists) and measured lifetime (where one exists)." % ENERGY_MAX_AGE_YR),
                notes=lit.raw.get("notes", ""), semi=semi_stat)
    sources = lit.source_urls()
    if semi_src:
        sources[semi_src] = semi_url
    return dict(meta=meta, columns=columns, levels=levels, transitions=transitions, rydberg_levels=[], tables=tables, validation=validation,
                sources=sources)


def merge_line(chosen, key, ln):
    """NIST lists M1 and E2 components of one forbidden line as separate rows: keep one line, add the rates."""
    old = chosen.get(key)
    if old and old.get("type") and ln.get("type") and old["type"] != ln["type"]:
        ln = dict(ln, A=(old.get("A") or 0) + (ln.get("A") or 0) or None, type="+".join(sorted({old["type"], ln["type"]})))
    elif old and (old.get("A") or 0) > (ln.get("A") or 0):
        return
    chosen[key] = ln


def auto_select(nist, lines, find, max_lines=70):
    """NIST-only species: the strongest classified lines, favouring those that start on the lowest levels."""
    cand = []
    for ln in lines:
        lo, up = find(ln["Ei"], ln["Ji"]), find(ln["Ek"], ln["Jk"])
        if lo and up and up["E"] > lo["E"] and ln["type"] != "2P" and 1e7 / (up["E"] - lo["E"]) < LAMBDA_MAX_NM:
            cand.append((lo, up, ln))
    rated = [c for c in cand if c[2]["A"]]
    pool = rated if len(rated) >= 15 else cand
    strength = lambda c: c[2]["A"] * (2 * c[1]["J"] + 1) if c[2]["A"] else (c[2]["intens"] or 0) * 1e-3
    low_cut = sorted({l["E"] for l in nist})[:6][-1]
    first = sorted([c for c in pool if c[0]["E"] <= low_cut], key=strength, reverse=True)[:max_lines]
    if len(first) < 45:
        taken = {id(c[2]) for c in first}
        first += sorted([c for c in pool if id(c[2]) not in taken], key=strength, reverse=True)[:45 - len(first)]
    out = {}
    for lo, up, ln in first:
        merge_line(out, (lo["i"], up["i"]), ln)
    return out


def url_of(atom, src):
    """URL of the citation a (possibly suffixed) source string starts with."""
    if not src:
        return ""
    if src.startswith("NIST ASD"):
        return "https://physics.nist.gov/asd"
    best = max((s for s in atom.get("sources", {}) if src.startswith(s)), key=len, default=None)
    return atom["sources"][best] if best else ""


def write_outputs(key, atom):
    out = os.path.join(al.DATA, key)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "atom.json"), "w") as f:
        json.dump(atom, f, indent=1, ensure_ascii=False)
    L = atom["levels"]
    with open(os.path.join(out, "levels.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["level", "J", "parity", "energy_cm", "lifetime_ns", "lifetime_unc_ns", "lifetime_tier", "lifetime_source",
                    "g_J", "hfs_A_MHz", "hfs_B_MHz", "hfs_source", "lifetime_source_url", "hfs_source_url", "energy_tier", "energy_source", "nist_energy_cm"])
        for l in L:
            h = l.get("hfs") or {}
            w.writerow([l["plain"], al.jstr(l["J"]), l["parity"], l["E"], l.get("tau_ns") or "", l.get("tau_unc") or "", l["tau_tier"],
                        l.get("tau_src", ""), l.get("g") or "", h.get("A", ""), h.get("B") or "", h.get("src", ""),
                        url_of(atom, l.get("tau_src")), url_of(atom, h.get("src")),
                        l.get("E_tier", "nist" if atom["meta"]["kind"] == "nist" else ""), l.get("E_src", ""), l.get("E_nist", "")])
    with open(os.path.join(out, "transitions.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lower", "upper", "kind", "wavelength_vac_nm", "wavelength_air_nm", "frequency_THz", "frequency_source", "wavenumber_cm",
                    "rme_J_ea0", "rme_tier", "rme_source", "A_s", "A_tier", "branching", "upper_linewidth_MHz", "nist_observed_vac_nm", "use", "type", "rme_source_url",
                    "cycle_class", "cycle_lower_level", "leak_per_photon", "leak_is_lower_limit", "photons_before_leak", "leak_tier", "leak_basis"])
        for t in atom["transitions"]:
            up = L[t["upper"]]["plain"] if "upper" in t else t["upper_plain"]
            w.writerow([L[t["lower"]]["plain"], up, t["kind"], t["lam"], t.get("air", ""), t["freq"], t.get("freq_src", ""), t.get("wn", ""),
                        t.get("d", ""), t.get("d_tier", ""), t.get("d_src", ""), t.get("A", ""), t.get("A_tier", ""), t.get("br", ""),
                        t.get("gamma_MHz", ""), t.get("lam_obs", ""), t.get("use", ""), t.get("type", "Rydberg E1"),
                        url_of(atom, t.get("d_src") or t.get("A_src"))]
                       + [(t.get("cyc") or {}).get(k, "") for k in ("cls", "lower", "leak", "bound", "n", "tier", "basis")])
    with open(os.path.join(out, "validation.txt"), "w") as f:
        f.write("\n".join(atom["validation"]) + "\n")
    print(f"== {key}\n" + "\n".join(atom["validation"]))


if __name__ == "__main__":
    groups = {"all": list(SPECIES), "auto": [k for k, c in SPECIES.items() if c.get("auto")],
              "curated": [k for k, c in SPECIES.items() if not c.get("auto")]}
    keys = [k for arg in (sys.argv[1:] or ["all"]) for k in groups.get(arg, [arg])]
    for k in keys:
        cfg = SPECIES[k]
        try:
            atom = build_alkali(k, cfg) if cfg["kind"] == "alkali" else build_nist(k, cfg)
        except Exception as ex:  # an element NIST has no usable tables for
            if not cfg.get("auto"):
                raise
            atom = None
            print(f"== {k}: skipped ({ex!r})"[:160])
        if atom:
            write_outputs(k, atom)
        elif cfg.get("auto"):
            print(f"== {k}: no classified lines below 2 um in NIST")
