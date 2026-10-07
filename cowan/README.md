# Cowan-code pilot (2026-10-07): can we calculate the missing rates ourselves?

Pilot on Hg I (mercury): semi-empirical Hartree-Fock-relativistic (HFR) calculation with R. D. Cowan's programs RCN, RCN2, RCG, RCE
(A. Kramida's 2021 package), parameters fitted to the NIST energies, rates compared with the NIST values.  Nothing of this is on the
site; the owner decides after reading `Hg/Hg_compare_fit.txt`.

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

## Result (Hg I, 51 lines with a NIST rate; `Hg/Hg_compare_hfr.txt`, `Hg/Hg_compare_fit.txt`)

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
