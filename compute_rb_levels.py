#!/usr/bin/env python3
"""Rb I level and E1-transition data, cross-checked between NIST ASD, ARC and pairinteraction.

Outputs (all in data/):
  levels.csv             low-lying fine-structure levels (NIST energy, ARC / pairinteraction check, lifetimes)
  transitions.csv        every E1-allowed line between those levels with vacuum wavelength < LAMBDA_MAX
  rydberg_series.csv     wavelengths from each low level to the nS / nP / nD / nF Rydberg series
  hyperfine_87Rb.csv     87Rb hyperfine A, B constants and F-level shifts of the low levels
  validation.txt         summary of the cross-source agreement

Energies are centre-of-gravity fine-structure energies (hyperfine structure averaged out).
Wavelengths are vacuum wavelengths unless the column name says "air".
"""
import csv
import io
import os
import re
import sys
import urllib.request
import warnings
from fractions import Fraction

import numpy as np

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

C = 299792458.0  # m/s
EV_TO_CM = 8065.543937  # cm^-1 per eV (CODATA 2018)
LAMBDA_MAX_NM = 2000.0
E_CUT_CM = 31700.0  # keep levels up to 10S / 10P / 8D / 7F
L_LETTERS = "SPDFGH"
RYDBERG_N = [20, 30, 40, 50, 53, 60, 70, 80, 100]

NIST_LEVELS_URL = (
    "https://physics.nist.gov/cgi-bin/ASD/energy1.pl?de=0&spectrum=Rb+I&units=0&format=3&output=0"
    "&page_size=15&multiplet_ordered=0&conf_out=on&term_out=on&level_out=on&unc_out=1&j_out=on"
    "&lande_out=on&perc_out=on&biblio=on&temp=&submit=Retrieve+Data"
)
NIST_LINES_URL = (
    "https://physics.nist.gov/cgi-bin/ASD/lines1.pl?spectra=Rb+I&output_type=0&low_w=&upp_w=&unit=1"
    "&de=0&plot_out=0&I_scale_type=1&format=3&line_out=0&remove_js=on&en_unit=0&output=0&bibrefs=1"
    "&page_size=15&show_obs_wl=1&show_calc_wl=1&unc_out=1&order_out=0&max_low_enrg=&show_av=3"
    "&max_upp_enrg=&tsb_value=0&min_str=&A_out=0&intens_out=on&max_str=&allowed_out=1&forbid_out=1"
    "&min_accur=&min_intens=&conf_out=on&term_out=on&enrg_out=on&J_out=on&submit=Retrieve+Data"
)


def fetch(url, path):
    """Download a NIST ASD table once; later runs reuse the cached copy."""
    if not os.path.exists(path):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
            f.write(r.read())
    with open(path) as f:
        return list(csv.reader(io.StringIO(f.read()), delimiter="\t"))


def air_wavelength_nm(lam_vac_nm):
    """Vacuum -> standard air (Ciddor 1996, as used by NIST ASD). Valid above 200 nm."""
    s2 = (1e3 / lam_vac_nm) ** 2  # (1/um)^2
    n = 1 + 0.05792105 / (238.0185 - s2) + 0.00167917 / (57.362 - s2)
    return lam_vac_nm / n


def rme_from_rate(A, wavenumber_cm, j_upper):
    """|<J||er||J'>| in e*a0 from an Einstein A coefficient: A = w^3 |d|^2 / (3 pi eps0 hbar c^3 (2J'+1))."""
    eps0, hbar, ea0 = 8.8541878128e-12, 1.054571817e-34, 8.4783536255e-30
    w = 2 * np.pi * wavenumber_cm * 100 * C
    return float(np.sqrt(A * 3 * np.pi * eps0 * hbar * C**3 * (2 * j_upper + 1) / w**3) / ea0)


def jstr(j):
    return str(Fraction(j).limit_denominator(2))


def label(n, l, j):
    return f"{n}{L_LETTERS[l]}{jstr(j)}"


def parse_nist_levels(rows):
    """Return {(n, l, j): (E_cm, unc_cm)} for the 4p6 nl valence levels, plus the ionisation limit."""
    levels, limit = {}, None
    for r in rows[1:]:
        r = [c.strip('"') for c in r]
        if len(r) < 7:
            continue
        if r[1] == "Limit":
            limit = float(r[4])
            continue
        m = re.fullmatch(r"4p6\.(\d+)([spdfgh])", r[0])
        if not m:
            continue
        n, l = int(m.group(1)), "spdfgh".index(m.group(2))
        levels[(n, l, float(Fraction(r[2])))] = (float(r[4]), float(r[6]))
    return levels, limit


def parse_nist_lines(rows):
    """Return {(E_lower, E_upper) rounded: dict(obs, unc, A, acc)} for the observed Rb I lines."""
    out = {}
    for r in rows[1:]:
        r = [c.strip('"') for c in r]
        if len(r) < 8 or not r[6] or not r[7]:
            continue
        try:
            key = (round(float(r[6]), 2), round(float(r[7]), 2))
        except ValueError:
            continue
        out[key] = dict(obs=r[0], unc=r[1], A=r[4], acc=r[5])
    return out


def main():
    from arc import Rubidium87
    import pairinteraction as pi

    atom = Rubidium87()
    nist_levels, limit = parse_nist_levels(fetch(NIST_LEVELS_URL, os.path.join(DATA, "nist_rb1_levels.tsv")))
    nist_lines = parse_nist_lines(fetch(NIST_LINES_URL, os.path.join(DATA, "nist_rb1_lines.tsv")))

    e_gs_arc = atom.getEnergy(5, 0, 0.5)  # eV, relative to the ionisation limit

    def arc_energy_cm(n, l, j):
        return (atom.getEnergy(n, l, j) - e_gs_arc) * EV_TO_CM

    def pi_ket(n, l, j):
        return pi.KetAtom("Rb", n=n, l=l, j=j, m=0.5)

    def pi_energy_cm(n, l, j):
        return pi_ket(n, l, j).get_energy(unit="GHz") * 1e9 / C / 100.0

    # ------------------------------------------------------------------ levels
    states = sorted((k for k, v in nist_levels.items() if v[0] <= E_CUT_CM and k[1] <= 3),
                    key=lambda k: nist_levels[k][0])
    level_rows = []
    for (n, l, j) in states:
        e, unc = nist_levels[(n, l, j)]
        tau0 = atom.getStateLifetime(n, l, j) if (n, l) != (5, 0) else np.inf
        tau300 = atom.getStateLifetime(n, l, j, temperature=300, includeLevelsUpTo=n + 25) if (n, l) != (5, 0) else np.inf
        level_rows.append(dict(
            state=label(n, l, j), n=n, l=l, j=j,
            E_nist_cm=e, unc_nist_cm=unc,
            E_arc_cm=round(arc_energy_cm(n, l, j), 4),
            E_pairinteraction_cm=round(pi_energy_cm(n, l, j), 4),
            binding_cm=round(limit - e, 3),
            ionisation_wavelength_nm=round(1e7 / (limit - e), 3),
            n_eff=round(float(np.sqrt(109736.605 / (limit - e))), 5),  # R_Rb87 = 109736.605 cm^-1
            lifetime_ns_0K_arc=round(tau0 * 1e9, 3),
            lifetime_ns_300K_arc=round(tau300 * 1e9, 3),
        ))
    write_csv("levels.csv", level_rows)

    # ------------------------------------------------------------- transitions
    trans_rows = []
    for a in states:
        for b in states:
            ea, eb = nist_levels[a][0], nist_levels[b][0]
            if eb <= ea or abs(a[1] - b[1]) != 1 or abs(a[2] - b[2]) > 1:
                continue
            wn = eb - ea
            lam = 1e7 / wn
            if lam >= LAMBDA_MAX_NM:
                continue
            (n1, l1, j1), (n2, l2, j2) = a, b
            A = atom.getTransitionRate(n2, l2, j2, n1, l1, j1, temperature=0)
            rme = abs(atom.getReducedMatrixElementJ(n1, l1, j1, n2, l2, j2))
            lit = atom.getLiteratureDME(n1, l1, j1, n2, l2, j2)
            tau = atom.getStateLifetime(n2, l2, j2)
            lam_arc = abs(atom.getTransitionWavelength(n1, l1, j1, n2, l2, j2)) * 1e9
            lam_pi = 1e7 / (pi_energy_cm(n2, l2, j2) - pi_energy_cm(n1, l1, j1))
            nl = nist_lines.get((round(ea, 2), round(eb, 2)), {})
            trans_rows.append(dict(
                lower=label(*a), upper=label(*b),
                wavelength_vac_nm=round(lam, 4), wavelength_air_nm=round(air_wavelength_nm(lam), 4),
                frequency_THz=round(wn * 100 * C / 1e12, 5), wavenumber_cm=round(wn, 3),
                wavelength_arc_nm=round(lam_arc, 4), wavelength_pairinteraction_nm=round(lam_pi, 4),
                nist_observed_vac_nm=nl.get("obs", ""), nist_Aki_s=nl.get("A", ""), nist_accuracy=nl.get("acc", ""),
                A_arc_s=float(f"{A:.4g}"),
                # NIST-compiled rate where there is one; the ARC model potential is unreliable for weak 5S-nP lines
                A_best_s=float(nl["A"]) if nl.get("A") else float(f"{A:.4g}"),
                A_best_source="NIST" if nl.get("A") else "ARC",
                rme_J_best_ea0=round(rme_from_rate(float(nl["A"]), wn, j2), 4) if nl.get("A") else round(rme, 4),
                branching_from_upper=round(A * tau, 4),
                rme_J_ea0=round(rme, 4),
                rme_source="literature: " + str(lit[2][3]) if lit[0] else "ARC model potential",
                upper_lifetime_ns=round(tau * 1e9, 3),
                upper_linewidth_MHz=float(f"{1 / tau / 2 / np.pi / 1e6:.4g}"),
            ))
    trans_rows.sort(key=lambda r: r["wavelength_vac_nm"])
    write_csv("transitions.csv", trans_rows)

    # ---------------------------------------------------------- Rydberg series
    ryd_rows = []
    for a in states:
        ea = nist_levels[a][0]
        if 1e7 / (limit - ea) >= LAMBDA_MAX_NM:
            continue
        n1, l1, j1 = a
        for l2 in (l1 - 1, l1 + 1):
            if l2 < 0 or l2 > 3:
                continue
            for j2 in (l2 - 0.5, l2 + 0.5):
                if j2 < 0 or abs(j2 - j1) > 1:
                    continue
                row = dict(lower=label(*a), series=f"n{L_LETTERS[l2]}{jstr(j2)}",
                           series_limit_nm=round(1e7 / (limit - ea), 3))
                for n in RYDBERG_N:
                    # Rydberg term energy from ARC quantum defects, lower level from NIST
                    lam = 1e7 / (arc_energy_cm(n, l2, j2) - ea)
                    lam_pi = 1e7 / (pi_energy_cm(n, l2, j2) - ea)
                    row[f"n{n}_nm"] = round(lam, 3)
                    row[f"n{n}_pairinteraction_nm"] = round(lam_pi, 3)
                n = 70
                rme_arc = abs(atom.getReducedMatrixElementJ(n1, l1, j1, n, l2, j2))
                # pairinteraction returns one m-component; convert with the Wigner-Eckart factor taken from ARC
                me_arc = atom.getDipoleMatrixElement(n1, l1, j1, 0.5, n, l2, j2, 0.5, 0)
                me_pi = pi_ket(n1, l1, j1).get_matrix_element(pi_ket(n, l2, j2), "electric_dipole", q=0, unit="e*a0")
                row["rme_J_n70_ea0"] = float(f"{rme_arc:.4g}")
                row["rme_J_n70_pairinteraction_ea0"] = float(f"{abs(me_pi / me_arc) * rme_arc:.4g}")
                row["lifetime_n70_us_300K"] = round(atom.getStateLifetime(n, l2, j2, temperature=300, includeLevelsUpTo=n + 40) * 1e6, 1)
                ryd_rows.append(row)
    write_csv("rydberg_series.csv", ryd_rows)

    # ---------------------------------------------------------- Rydberg levels
    rl_rows = []
    for n in list(range(11, 31)) + [35, 40, 45, 50, 53, 60, 70, 80, 90, 100]:
        for l in range(4):
            for j in ([0.5] if l == 0 else [l - 0.5, l + 0.5]):
                nist = nist_levels.get((n, l, j), ("", ""))
                rl_rows.append(dict(state=label(n, l, j), n=n, l=l, j=j, E_nist_cm=nist[0], unc_nist_cm=nist[1],
                                    E_arc_cm=round(arc_energy_cm(n, l, j), 4),
                                    E_pairinteraction_cm=round(pi_energy_cm(n, l, j), 4)))
    write_csv("rydberg_levels.csv", rl_rows)

    # --------------------------------------------------------------- hyperfine
    hfs_rows = []
    for (n, l, j) in states:
        try:
            A, B = atom.getHFSCoefficients(n, l, j)
        except Exception:
            continue
        if A == 0:
            continue
        I = atom.I
        row = dict(state=label(n, l, j), A_MHz=round(A / 1e6, 4), B_MHz=round(B / 1e6, 4))
        for f in np.arange(abs(I - j), I + j + 1):
            row[f"F{int(f)}_shift_MHz"] = round(atom.getHFSEnergyShift(j, f, A, B) / 1e6, 3)
        hfs_rows.append(row)
    cols = ["state", "A_MHz", "B_MHz"] + [f"F{f}_shift_MHz" for f in range(0, 5)]
    write_csv("hyperfine_87Rb.csv", hfs_rows, cols)

    # -------------------------------------------------------------- validation
    lines = ["Rb I data cross-check", "=" * 60,
             f"levels: {len(level_rows)}   E1 lines < {LAMBDA_MAX_NM:.0f} nm: {len(trans_rows)}",
             f"NIST ionisation limit: {limit} cm^-1   ARC: {-e_gs_arc * EV_TO_CM:.3f} cm^-1", ""]
    d_arc = np.array([r["E_arc_cm"] - r["E_nist_cm"] for r in level_rows])
    d_pi = np.array([r["E_pairinteraction_cm"] - r["E_nist_cm"] for r in level_rows])
    lines += [f"level energy, ARC - NIST:             max |d| = {np.abs(d_arc).max():.3f} cm^-1, rms = {d_arc.std():.3f}",
              f"level energy, pairinteraction - NIST: max |d| = {np.abs(d_pi).max():.3f} cm^-1, rms = {d_pi.std():.3f}", "",
              "largest level deviations (cm^-1):"]
    for r in sorted(level_rows, key=lambda r: -max(abs(r["E_arc_cm"] - r["E_nist_cm"]), abs(r["E_pairinteraction_cm"] - r["E_nist_cm"])))[:8]:
        lines.append(f"  {r['state']:8s} NIST {r['E_nist_cm']:11.3f}  ARC {r['E_arc_cm'] - r['E_nist_cm']:+.3f}  pairinteraction {r['E_pairinteraction_cm'] - r['E_nist_cm']:+.3f}")
    d = np.array([r["E_arc_cm"] - r["E_pairinteraction_cm"] for r in rl_rows])
    lines += ["", f"Rydberg levels n = 11-100 (S, P, D, F): ARC - pairinteraction max |d| = {np.abs(d).max():.4f} cm^-1"]
    for src in ("arc", "pairinteraction"):
        for lo, hi, tag in ((0, 0.011, "NIST unc <= 0.01 cm^-1"), (0.011, 1, "NIST unc 0.05-0.3 cm^-1")):
            dn = np.array([r[f"E_{src}_cm"] - r["E_nist_cm"] for r in rl_rows if r["E_nist_cm"] != "" and lo < r["unc_nist_cm"] <= hi])
            lines.append(f"  {src:15s} - NIST ({tag}, {len(dn)} levels): max |d| = {np.abs(dn).max():.3f}, mean = {dn.mean():+.3f} cm^-1")
    lines += ["", "transition rate, ARC vs NIST A_ki (lines where NIST lists a value):"]
    ratios = []
    for r in trans_rows:
        if r["nist_Aki_s"]:
            ratio = r["A_arc_s"] / float(r["nist_Aki_s"])
            ratios.append(ratio)
            lines.append(f"  {r['lower']:7s}-{r['upper']:7s} {r['wavelength_vac_nm']:10.4f} nm  NIST {float(r['nist_Aki_s']):.3e} ({r['nist_accuracy']:2s})  ARC {r['A_arc_s']:.3e}  ratio {ratio:.3f}")
    lines += ["", "observed (NIST) vs Ritz wavelength, lines where NIST lists an observed value:"]
    dl = [(abs(float(r["nist_observed_vac_nm"]) - r["wavelength_vac_nm"]), r) for r in trans_rows if r["nist_observed_vac_nm"]]
    lines.append(f"  {len(dl)} lines, max |obs - Ritz| = {max(d for d, _ in dl):.4f} nm")
    with open(os.path.join(DATA, "validation.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def write_csv(name, rows, cols=None):
    cols = cols or list(rows[0].keys())
    with open(os.path.join(DATA, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, restval="")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote data/{name}: {len(rows)} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
