# Literature campaign

Round 1 (done, curated isotopes): Li Be Na Mg K Ca Rb Sr Cs Ba Yb Dy
Round 2 (done 2026-10-01): Er Tm Ho | Eu Cr Ti | Hg Cd Zn | Ra Fr | Ag Au Cu | Al Ga In Tl | He Ne Ar Kr Xe
Round 3 (done 2026-10-01): H B C | N O F | Cl Br I | Si P S | Ge As Se | Sc V Mn | Fe Co Ni | Y Zr Nb
Round 3b (done 2026-10-01): Mo Tc Ru | Rh Pd Sn
Round 4 (done 2026-10-01, 106 web searches): Sb Te Pb Bi | La Ce Pr | Nd Pm Sm | Gd Tb Lu | Hf Ta W | Re Os Ir Pt | Po At Rn Ac Th
Round 6 (done 2026-10-02): Pa U Np | Pu Am Cm | Bk Cf Es from literature levels (`levels_not_in_nist`), pages published. Beyond Es: not done (owner's decision).

Round 5 (done 2026-10-01, 62 web searches): second pass on As Se Ga Zn | Au Cu Mo Er | C Cl Br I | Ne Ar Kr Xe. Much better: Zn Cu As Ne Kr C; little or nothing new: Se Ga(drawn levels) Au Er Mo Br I Ar Xe.
Still thin, blocked by paywalled / bot-protected papers (listed in each file's not_found), a further web pass will not help: Se Ga Au Er Mo Br I Ar Xe, and from round 4: Nd Ce Te Gd Tb Ir Pt Rn Th (key papers paywalled or bot-blocked; each file lists them under not_found).
Decided by the user 2026-10-01: keep the page-reader lifetime tables (Tm, Ho, Dy, Co, Ni) but verify them; measured energies of the last 20 years override NIST, older ones do not. Still open: boron 249.75 nm isotope-shift sign.
2026-10-02: Kr 819 nm branching set to 0.751(8); 95 old measured rates that differ from NIST moved to `A_s_older_measurement`; La, Sm, Pb, Bi lifetimes verified. Waiting for the owner's PDFs (待下载论文清单.md).

## Round 7 (2026-10-02, evening): finish the table

- Fm.json, No.json (measured levels, hyperfine constants, isotope shifts; each re-read by a second agent) -> pages.
- heaviest_elements.json: Md, Lr, Rf-Og have no measured excited level -> 17 fact pages.
- Open-access hunt for the 18 thin elements, with an independent verification pass: Ce 153 + Gd 136 + Pt 58 + Ir 62 + Nd 96 +
  Er 103 lifetimes, Mo 14 lifetimes and 129 rates, Tb hyperfine constants of 95 levels, Ar 4p lifetimes and isotope shifts,
  Xe and Rn hyperfine constants, Te and Ga lifetimes. Se: nothing. Still closed: see 待下载论文清单.md.
- Fixed on the way: Xe 110 nm frequency stored in GHz instead of THz; two-digit multiplicities; random hyperfine isotope.

## Round 8 (2026-10-02, night): publisher pages through WebFetch

- None of the 17 starred papers: IOP, Springer, APS, Elsevier now answer automated requests with a bot check or login (not bypassed).
- Got from other open sources (each verified by a second agent): Nd 38 lifetimes (Gorshkov 1982) + isotope shifts of 8 lines,
  Gd isotope shifts of 43 lines (Ankush & Deo 2013), Pt-195 hyperfine constants (Neu 1987) + isotope shifts (LaBelle 1989),
  Ar 13 lifetimes, Xe 30+ lifetimes and two transitions (Sterr 1995), Sm 61 lifetimes (Zhang 2010).
- Tb: 7 plasma-estimated rates (Irvine 2023) stored as A_s_other_measurement, not shown.
- Route that works: plain curl on opg.optica.org abstract pages (tables are in the HTML).
