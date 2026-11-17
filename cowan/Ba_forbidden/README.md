# Barium: E2 and M1 lines to the ground level, this site's own Cowan-code check (2026-11-17)

Why: the 877.55 nm line (6s2 1S0 - 6s5d 1D2, electric quadrupole) was added to the site with the only published rate, a 1990
multiconfiguration Dirac-Fock calculation whose tables are closed (Migdalek & Baylis, Phys. Rev. A 42, 6897: lifetime "about 1/4 s",
242-296 ms as quoted in arXiv:2607.11282). No measurement exists. This is an independent check, not a number shown on the site:
barium is NOT in `data/cowan/`, so the pipeline takes no rate from here.

How: the chain of `cowan/README.md` (RCN, RCN2, RCG, RCE of the NIST 2021 package) with two switches on the RCN2 control card
(`IN2`): column 49 IMAG = 1 and column 50 IQUAD = 1 give the magnetic-dipole and electric-quadrupole lines of the first (even)
parity; DMIN = 0 keeps every line. Scale factors 85 99 85 85 85 as elsewhere; radial quadrupole integrals ab initio (not scaled).

    python3 run_ba.py <COWAN_BIN> <work dir> full|small     # RCN, RCN2, RCG (unfitted)
    python3 fit_ba.py <COWAN_BIN> <work dir>                # two-stage fit to the NIST energies, RCG again
    python3 lines.py  <work dir>/OUTG11.fit "ELEC QUD"      # rates rescaled to the observed transition energy (x lambda^-5; M1: lambda^-3)

`full`: even 6s2, 6s5d, 5d2, 6p2, 6s7s, 6s6d, 5d7s, 5d6d, 6s8s, 6s7d; odd 6s6p, 5d6p, 6s7p. `small`: the first four even
configurations (the space of the 1990 paper's larger calculation).

Results (`results.txt`), rate at the observed energy:

| line | small, unfitted | small, fitted | full, unfitted | full, fitted | literature (all calculated) |
|---|---|---|---|---|---|
| 1S0 - 1D2, 877.55 nm, E2 | 3.24 s^-1 (0.309 s) | 3.49 (0.286 s) | 3.78 (0.264 s) | 5.11 (0.196 s) | 0.242-0.296 s |
| 1S0 - 3D2, 1085.13 nm, E2 | 0.0276 (36 s) | 0.0179 (56 s) | 0.0325 (31 s) | 0.0245 (41 s) | 20 s, 44-61 s, 69 s |
| 1S0 - 3D1, 1106.93 nm, M1 | 0 | 0 | ~1e-15 | ~1e-13 | none |

- The quadrupole line to 1D2 is robust: the single-electron integral <6s||r2||5d> = 20.4 e a0^2 times sqrt(2) (two 6s electrons)
  already gives |<1S0||Q||1D2>| = 28.8 e a0^2, A = 3.6 s^-1; configuration mixing moves it between 27 and 34.
- The line to 3D2 exists only through the 1% admixture of 1D2 (spin-orbit), hence the larger spread, here as in the literature.
- The M1 line to 3D1 is zero in this model for practical purposes: in an even isotope the 3D1 level has no usable one-photon line
  to the ground level. The site draws 1106.93 nm with type M1 (what J and parity allow) and no rate.
- Dipole lines of the same fitted run against NIST: 71 lines above the cancellation cut, median ratio 1.05, 59 % within a factor 2.

A neutral element whose missing lines are E2 or M1 can be treated the same way (two columns on the control card); M2 and J = 0 - 0
lines cannot (RCG has no magnetic quadrupole).
