# This site's own Cowan-code calculations (tier `hfr`, drawn with ≈)

Semi-empirical Hartree-Fock-relativistic (HFR) calculations with R. D. Cowan's programs RCN, RCN2, RCG, RCE (A. Kramida's 2021
package), parameters fitted to the NIST energies, rates compared with the NIST values.  Owner's decision 2026-10-07: these rates go
on the site as their own tier `hfr` ("HFR fit (this site)", ≈), used only where neither a measurement, NIST nor the Kurucz list
gives a rate; lines with |cancellation factor| < 0.05 are left out (`semi.cowan_rates()` in the pipeline).  Done: 19 elements, see the table.
The owner's instruction of 2026-10-07: leave the high Rydberg levels out (a reachable level outside the configuration list simply has no
calculated line; the leak then stays a lower limit).

    COWAN_BIN=<build dir> python3 cowan/run_element.py Cd      # one command per element (configurations in run_element.py)

writes `cowan/<El>/` (IN36, IN2, decks before and after the fit, LEVELS1 = observed vs fitted levels, PARVALS, fit_assignment.txt,
`<El>_compare_hfr.txt` / `<El>_compare_fit.txt` = rates against NIST before / after the fit) and `data/cowan/<El>_lines.csv` +
`index.json` (every calculated line between NIST levels, A scaled to the NIST transition energy, cancellation factor).

## Getting and building the code (macOS, GNU Fortran from Homebrew `gcc`)

- NIST package `Cowan_PC_2021.zip` (Fortran sources `FOR/`, manuals `RCN_DOC.txt`, `RCG_DOC.txt`, `RCE_DOC.txt`, `README_Kramida.txt`,
  data `CODE/SENIOR`, `CODE/ING11.CFP`): https://data.nist.gov/od/id/6CF509047B474AC9E05324570681DE731930 — the distribution server
  answered "error code: 524" all day; the archived copy worked:
  https://web.archive.org/web/2025id_/https://data.nist.gov/od/ds/6CF509047B474AC9E05324570681DE731930/Cowan_PC_2021.zip
  (Cormac McGuinness' Linux bundle of the original LANL sources is also only on the archive:
  https://web.archive.org/web/2016id_/http://www.tcd.ie/Physics/People/Cormac.McGuinness/Cowan/CowanCode.tgz).
- Compile each program: `gfortran -O2 -std=legacy -fno-backslash -fallow-argument-mismatch -w -o rcn RCN36K.F` (same for `RCN2K.F`
  -> rcn2, `RCE20K.F` -> rce, `rcg11k.f` -> rcg) in a directory that also holds `rcgpar.f` and `RCEBPAR.FOR`.
  `rcg11k.f` needs `rcg11k_macos.patch`: assumed-size arrays in SORT2 (KLAM is not declared there), `MSDOS=0`, data files in the
  working directory (`FIL='./'`).
- Fractional-parentage decks: copy `SENIOR` into a work directory, `tail -n +9 ING11.CFP > ING11`, run `rcg` once: `FOR072`, `FOR073`,
  `FOR074` appear; every later RCG run needs these three files and `SENIOR` in its directory.
- Check: `WORK/IN36` + `WORK/IN2` -> rcn, rcn2, rcg, rce all end with "NORMAL EXIT".

## Pipeline used for Hg I

    rcn        IN36 (control card = the sample's with IREL=1 for HFR; one card per configuration, 4f14 listed explicitly, else RCN
               fills the core up to 5p6 only) -> out36, tape2n
    rcn2       IN2  (G5INP card: IABG=0, scale factors 85 99 85 85 85, DMIN=2.00 = keep every line with gA >= 100 s^-1) -> ING11
    rcg        ING11 -> OUTG11 (levels, eigenvectors, E1 line list with log gf, gA, cancellation factor), OUTGINE (RCE input)
    make_ine.py El OUTG11 OUTGINE.orig OUTGINE   NIST energies in place of the eigenvalues (level <-> eigenvalue by the dominant
               LS component, configuration and J; jK-labelled NIST levels by energy order), unknown levels estimated and excluded,
               parameter flags: EAV free for every configuration with observed levels, zeta / F^k / G^k free for configurations
               with >= 4 observed levels, configuration-interaction R^k fixed; CRIT=0.85, 40 cycles
    rce        OUTGINE + TAPE2E -> LEVELS1 (observed vs fitted), PARVALS (fitted parameters as RCG cards)
    parvals_to_ing11.py ING11.hfr PARVALS ING11   fitted cards into the RCG deck
    rcg        -> OUTG11 with the fitted eigenvectors
    compare_nist.py El OUTG11      rates against NIST (A scaled to the NIST transition energy), by NIST accuracy class
    export_lines.py El OUTG11 out.csv   every calculated line whose two levels are NIST levels, with A and cancellation factor

Configurations: even 5d10 6s2, 6s7s, 6s8s, 6s9s, 6s6d, 6s7d, 6s8d, 6p2; odd 6s6p, 6s7p, 6s8p, 6s9p, 6s5f, 6s6f, 5d9 6s2 6p, 5d9 6s2 7p.

## Results (19 elements; `<El>/<El>_compare_fit.txt` has every line)

Fit: two stages (first only the configuration energies, started at the observed positions, then the Slater and spin-orbit parameters of
every configuration with at least four observed levels; configuration-interaction integrals fixed at 0.85 x HFR; levels follow
their dominant component, CRIT = 0.85; at most 5 kK parameter change per cycle; a fit that runs away falls back to the first stage).

| element | configurations | observed levels fitted (median / 90 % / worst deviation, kK) | NIST-rated lines after the cancellation cut: within x2 / x3 |
|---|---|---|---|
| Hg | 16 | 56 (0.03 / 0.3 / 0.5) | 47: 55 % / 70 % (NIST A/B lines: 20, 85 % within x2) |
| Cd | 16 | 44 (0.05 / 0.4 / 2.8) | 16: 94 % / 100 % |
| In | 17 | 30 (0.01 / 0.7 / 1.5) | 14: 71 % / 79 % (NIST A/B lines: 9, 67 % within x2) |
| Ga | 16 | 31 (0.01 / 0.5 / 2.1) | 11: 100 % / 100 % (NIST A/B lines: 5, 100 % within x2) |
| Tl | 16 | 25 (0.01 / 1.2 / 4.6) | 9: 100 % / 100 % |
| Cu | 14 | 44 (0.10 / 0.5 / 1.5) | 24: 71 % / 75 % (NIST A/B lines: 6, 67 % within x2) |
| Ag | 14 | 43 (0.55 / 1.4 / 4.5) | 7: 86 % / 100 % |
| Au | 11 | 35 (0.61 / 3.1 / 3.6) | 18: 72 % / 72 % (NIST A/B lines: 9, 89 % within x2) |
| Sn | 12 | 88 (0.24 / 1.3 / 2.9) | 38: 50 % / 58 % |
| Pb | 11 | 56 (0.54 / 3.2 / 4.4) | 25: 56 % / 72 % |
| Xe | 12 | 85 (0.18 / 1.0 / 3.5) | 95: 65 % / 74 % (NIST A/B lines: 62, 63 % within x2) |
| Kr | 12 | 86 (0.09 / 0.7 / 2.5) | 106: 69 % / 85 % (NIST A/B lines: 44, 91 % within x2) |
| Ge | 12 | 88 (0.05 / 0.3 / 1.1) | 26: 65 % / 85 % |
| Sb | 11 | 113 (0.23 / 0.9 / 3.8) | 10: 90 % / 90 % |
| Bi | 10 | 47 (0.61 / 2.8 / 5.5) | 29: 62 % / 86 % (NIST A/B lines: 11, 73 % within x2) |
| Te | 12 | 74 (0.30 / 1.0 / 1.8) | 5: 60 % / 100 % |
| Se | 12 | 92 (0.35 / 2.5 / 7.8) | no NIST-rated line to compare with |
| Br | 13 | 162 (0.14 / 0.5 / 1.4) | 42: 71 % / 95 % |
| I | 12 | 122 (0.21 / 0.7 / 2.2) | 263: 70 % / 85 % (NIST A/B lines: 8, 100 % within x2) |

Weak lines are the problem everywhere: lines with a cancellation factor below 0.05 are left out, but a line with 0.1 can still be
off by a factor 3.  Strong lines are typically within 1.5.  The resonance lines come out 1.3-1.5 x too strong (no core
polarisation).  In, Ga, Tl: the 5s 5p2-type perturbers are fitted 1-5 kK off.  Sn and Pb (p2 ground configuration) are the
weakest set; Xe and Kr (p5 nl, jK coupling) fit well but have many weak lines.  Second batch (Ge, Sb, Bi, Te, Se, Br, I: p2 to p5
ground configurations, three open-shell parents): Br and I fit well; Se has no NIST-rated line at all, so its rates are published
on the strength of the neighbours only; Bi and Se have a few levels fitted 5-8 kK off (jK-labelled levels paired by energy order).
A one-letter symbol (I) needs the element id padded to six characters in the RCN label, else RCG cuts the configuration name.

### Hg I in detail (51 lines with a NIST rate; `Hg/Hg_compare_hfr.txt`, `Hg/Hg_compare_fit.txt`)

| | HFR, no fit | HFR, parameters fitted to the NIST energies |
|---|---|---|
| level energies | 6-10 kK too low | median 0, worst 2.3 kK |
| NIST class A/B lines (20) within x2 | 85 % | 90 % |
| NIST class C/D lines (29) within x2 | 31 % | 38 % |
| all 51 within x2 / x3 | 53 % / 69 % | 57 % / 75 % |

The fit matters for lines that live on singlet-triplet mixing: 577.1 nm 6s6d 3D2 - 6s6p 1P1 went from 1/25 to 1.1 x NIST,
579.2 nm from 2.1 to 0.96, 265.6 nm from 0.18 to 1.6; the 253.7 nm intercombination line went from 1.03 to 2.5 x NIST (too much
mixing after the fit), the 184.9 nm resonance line is 1.5 x NIST (no core polarisation).  Lines with a cancellation factor below
0.1 are unreliable (773 nm: 1/300).  Of the 101 decay channels of the drawn Hg levels that have no NIST rate, the calculation
supplies 89.  About 2 hours of work per element of this kind once the tools exist; every further element needs its own
configuration list and a look at the fit (LEVELS1) before the rates are trusted.
