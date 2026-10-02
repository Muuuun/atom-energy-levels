# Verification of the page-reader lifetime tables (2026-10-01)

Tables: Tm (Anderson 1996, 194 levels), Ho (Den Hartog 1999, 29), Dy (Curry 1997, 28), Co (Nitz 1995, 45), Ni (Bergeson & Lawler 1993, 40).
They were transcribed from tables embedded in the publisher abstract pages, not from the PDFs.

## Check 1: against NIST rates (offline, all levels)
A lifetime cannot exceed 1 / (sum of NIST A values out of the level). Levels with NIST rates: Tm 136, Ho 12, Dy 26, Co 45, Ni 40 (259).
Stored lifetime longer than 1/sum(A) by more than 10 %: 10 levels (Tm 39560.41; Ho 23498.57; Co 28777.27, 29216.37, 31871.15;
Ni 30922.734, 43933.408, 44206.099, 44565.037, 45122.383). All others are consistent (median ratio 0.90-0.99 per element).

## Check 2: second independent read of the publisher tables (25 values)
The same pages were read again, asking only for named rows, copied verbatim. Every value equals the stored one:
- Ni: 30922.7 182(9); 43933.4 23.3(12); 44206.1 42.5(21); 44336.1 3.5(2); 44565.1 2.0(2); 45122.4 2.1(2); 47208.2 7.5(4);
  47328.8 33.0(17); 47424.8 13.8(7); 48735.3 21.8(11); 49403.4 23.7(12) ns.
  The table's "other work" column prints 137, <18.2, <33.2, <1.7, 1.7 ns for the five flagged levels: exactly the NIST 1/sum(A)
  values, so the disagreement is between Bergeson & Lawler and the older data NIST uses, not a transcription error.
- Co: 28777.27 79.0(40); 29216.37 82.3(41); 31871.15 51.1(26); 41101.80 3.4(2); 42796.67 2.9(2) ns.
- Tm: 39560.41 29.4; 41576.146 22.5 (settles the earlier 22.5 / 57.1 double read); 24348.692 15.7; 23781.698 41.1; 18837.385 459 ns.
- Ho: 23498.57 100 (other work: 102(6)); 24360.81 4.9; 24660.80 5.0; 24014.22 9.4 ns.
- Dy: no level failed check 1; not re-read.

## What this does not establish
- No PDF or independent printing was opened: later open papers (Wood 2014 for Ni, arXiv:1402.4457) use these lifetimes but do
  not reprint them. Rows not covered by check 2 rest on check 1 only; levels without NIST rates (Tm 58, Ho 17, Dy 2) rest on the
  original single or double read.
- Tm 50563.91 cm^-1 J=15/2 (2.2 ns) matches no NIST level and is not used by the site.

## Ta and W (Den Hartog, Duquette, Lawler, J. Opt. Soc. Am. B 4, 48 (1987)), added after round 4
Same route (publisher HTML tables). Second independent read: W lifetimes 31323.48: 158(8), 34354.08: 305(15), 29393.49: 71.4(3.6) ns;
Ta lifetimes 26585.93: 261(13), 23363.09: 390(20), 28689.31: 138(7), 26363.69: 128(6), 28133.88: 157(8), 30664.66: 57.9(2.9) ns:
all equal the stored values. The gA column of the second read (W: 0.097, 0.020, 0.020; 0.113, 0.049; 0.26, 0.21, 0.180 x 10^8 s^-1)
equals (2J+1) x stored branching ratio / stored lifetime for all 8 stored lines of those three levels. The branching-ratio column
of the second read came out shifted and was not used. The two identical rows of level 34354.08 (0.081(6), 0.0185(16)) are printed
twice in both reads and are below the 0.10 cut, so they are not in W.json. All other Ta / W rows rest on the single read plus the
internal gA check.

## La, Sm, Pb, Bi (checked 2026-10-02)
- La (Den Hartog, Palmer, Lawler 2015, 69 lifetimes): all 69 levels have NIST rates; lifetime x sum(NIST A) has median 0.994 and no
  level lies outside 0.3-1.1. NIST's La I rates are built on these lifetimes, so a misread lifetime would show up here. No re-read needed.
- Sm (Den Hartog & Lawler 2013, 120 lifetimes read from the Figshare table; Lawler, Fittante, Den Hartog 2013, 299 rates parsed
  from the PDF text by regular expression): two separate documents read by two separate routes. For the 107 levels that have both,
  lifetime x sum(A of the 2013 rate paper) has median 0.999, range 0.748-1.003. A wrong lifetime or a wrongly parsed rate would break
  this. The other 13 lifetimes rest on the single read. Two upper levels with rates have no lifetime (13999.5, 14863.85).
  The 124 measured energies differ from NIST by -0.172 to +0.064 cm^-1 (median 0.05), i.e. no mismatched level.
  Sm 21813.22 (J=2): stored 7.7 ns; NIST's single old rate 1.3e7 s^-1 would allow 77 ns. The 2013 rates of the three lines sum to
  1/7.7 ns, so the stored value is right and the NIST rate is the outdated number.
- Pb (Biémont et al. 2000, 3 lifetimes): second independent read of the publisher page: 6.8(3), 6.0(3), 4.9(3) ns, equal to the stored
  values; lifetime x sum(NIST A) median 1.01.
- Bi (Andersen, Madsen, Sørensen 1972, 5 lifetimes): second read of the publisher table: 4.7(1.0), 4.3(4), 5.5(5), 27(3), 3.8(1.0) ns,
  equal to the stored values. The table has a sixth row, read as "7s 4P3/2 (second entry) 4.8(4) ns"; its level label is evidently
  misread (probably the 7s 2P level), so it is not stored. Needs the PDF.

## Sm, the 13 single-read lifetimes: second reading (2026-10-02)
The 13 levels are those of Den Hartog & Lawler, J. Phys. B 46, 185001 (2013), Table 1 that have no line in the 2013 rate paper
(and no NIST rate either, so check 1 is not available for them).

Result: no independent printing could be opened, so the check asked for is NOT done. What was done instead is a second,
machine reading of the same deposit, which rules out a transcription error but not an error in the deposit itself.

- Second reading: the spreadsheet file of the Figshare deposit (Table1.xls, https://ndownloader.figshare.com/files/1480528,
  listed at https://iop.figshare.com/articles/dataset/_Radiative_lifetimes_of_120_odd_parity_levels_of_neutral_Sm/1012705)
  was downloaded and its cells read by program, not by a page reader. Table 1, columns "Energy", "J", "Laser wavelength in air (nm)",
  "This work" and "Other LIF experiment" (lifetimes in ns):
  - 25572.10 J=4: 415.121, 429.082; 441; no other value
  - 27263.07 J=7: 430.127, 705.655; 196; no other value
  - 27406.90 J=4: 385.733, 624.812; 89.5; other 27.5(10) (footnote l)
  - 27627.25 J=2: 365.732, 382.481; 59.7; other 59.6(12) (footnote j)
  - 27671.35 J=2: 365.142, 381.836; 27.2; other 28.5(8) (j)
  - 27709.40 J=2: 381.282, 591.262; 43.5; other 43.3(6) (j)
  - 27992.35 J=3: 589.896; 47.7; other 48.0(9) (j)
  - 28250.02 J=7: 412.606; 483; other 449(10) (l)
  - 28913.97 J=1: 345.755, 349.289; 54.7; other 36.0(21) (j)
  - 29023.96 J=5: 386.013, 399.834; 17.0; no other value
  - 29041.31 J=2: 347.742, 354.140; 42.8; other 42.8(10) (j)
  - 29200.62 J=2: 352.152, 360.764; 47.2; other 47.7(11) (j)
  - 29282.28 J=3: 589.141, 608.265; 30.5; other 32.0(20) (j)
  All 13 "This work" values, all 13 J values and all 10 "other experiment" values equal what Sm.json stores. Sm.json was not changed.
- Row identity: each printed laser wavelength, converted to a wavenumber and subtracted from the level energy, lands on a NIST
  even level (0, 292.58, 811.92, 1489.55, 2273.09, 3125.46, 4020.66, 10801.10, 11044.90, 11406.50, 12313.11,
  12846.64, 13095.75 cm^-1) within about 0.2 cm^-1, so no row is shifted against its energy. (This test is a calculation of mine and
  says nothing about the lifetime column.)
- Weak outside support, inside the same table only: for 7 of the 13 levels the earlier experiment quoted in the last column
  agrees with the 2013 value within 5 % (27627.25, 27671.35, 27709.40, 27992.35, 29041.31, 29200.62, 29282.28) and for 28250.02
  within 8 %. 27406.90 and 28913.97 disagree with the earlier experiment (already in the `conflicts` list of Sm.json).
  25572.10, 27263.07 and 29023.96 have no other measurement at all.
- Where an independent printing was looked for and not obtained:
  - the article itself (https://iopscience.iop.org/article/10.1088/0953-4075/46/18/185001 and /pdf): publisher robot check,
    no table reached; the Internet Archive holds only redirects to that robot check; OpenAlex and Semantic Scholar list no open copy;
    the OSTI record (https://www.osti.gov/etdeweb/biblio/22214446) is bibliographic only.
  - the nine citing papers listed by OpenAlex: the only one that plausibly reprints these lifetimes is Yu, Wang, Yang, "New branching
    fractions, transition probabilities, and oscillator strengths for Sm I levels", J. Quant. Spectrosc. Radiat. Transfer (2026),
    doi 10.1016/j.jqsrt.2026.110003 (closed access, publisher page returns "forbidden"; whether it reprints them is not verified).
    The 2013 rate paper has no line from these 13 levels; the others concern even-parity levels or do not tabulate lifetimes.
- Still open: these 13 values rest on two readings of one deposit. To close it the owner needs the PDF of the 2013 lifetime
  paper or of the 2026 paper above.

## Sm, the 13 single-read lifetimes: attempt through the publisher page (2026-10-02, later the same day)
Result: the article of Den Hartog & Lawler, J. Phys. B 46, 185001 (2013) could again NOT be opened, so the "This work" column of
the 13 rows still has no second independent printing. No value in Sm.json was corrected (nothing proves a misreading).

- Publisher route: https://iopscience.iop.org/article/10.1088/0953-4075/46/18/185001, the same address with /pdf and /meta, and
  http://stacks.iop.org/0953-4075/46/i=18/a=185001/pdf were each requested with the page reader; every one answers with a redirect
  to a robot check (validate.perfdrive.com). The redirect was not followed. The page reader cannot open web.archive.org; the
  Wayback index lists only captures of that same redirect (status 302). OpenAlex: closed, no repository copy. osti.gov: abstract only.
  Yu, Wang, Yang (2026), https://www.sciencedirect.com/science/article/pii/S0022407326001974: "forbidden".
- What was obtained instead: the paper behind footnote "j" of that table. Zhang, Feng, Dai, J. Opt. Soc. Am. B 27, 2255 (2010),
  Table 1 (79 lifetimes of odd levels with J = 0-3) is embedded in the HTML of the publisher's abstract page
  (https://opg.optica.org/josab/abstract.cfm?uri=josab-27-11-2255); its cells were extracted by program (text copy:
  data/literature/pdf/Sm_Zhang_2010.txt). One reading by the page reader of the rows 27627-28856 cm^-1 gave the same numbers; a
  second page-reader request returned no rows (it reported the table as subscriber-only), so the program extraction is the reading relied on.
  For the 8 of the 13 levels that carry footnote "j", the 2010 paper prints (level, J, lifetime in ns):
  27627.25 J=2 59.6(1.2); 27671.35 J=2 28.5(0.8); 27709.4 J=2 43.3(0.6); 27992.35 J=3 48.0(0.9); 28913.97 J=1 36.0(2.1);
  29041.31 J=2 42.8(1.0); 29200.62 J=2 47.7(1.1); 29282.68 (sic; NIST and the 2013 table 29282.28) J=3 32.0(2.0).
  These equal the "Other LIF experiment" column of the Figshare table for all 8 rows, and J agrees for all 8. So for these 8 rows the
  deposit's level, J and comparison value are confirmed by an independent printing; the 2013 lifetime itself agrees with the 2010
  measurement within 5 % for 7 of them and disagrees for 28913.97 (54.7 against 36.0(2.1) ns, a real disagreement between the two
  experiments, already in `conflicts`).
  In the whole table, all 18 levels common to both papers have a 2010 value equal to the footnote-"j" value stored in Sm.json.
- Still without any outside check: 25572.10, 27263.07, 29023.96 (no other measurement exists) and 27406.90, 28250.02 (footnote "l",
  probably Zhang, Feng, Sun, Dai, J. Phys. B 43, 235005 (2010), the J = 4-7 companion paper; iopscience.iop.org robot check, only the
  abstract on osti.gov was read, so this attribution is not verified).
- Changes to Sm.json: the 18 footnote-"j" alternatives now cite the 2010 paper directly (method "experiment"); 61 further levels
  measured only in the 2010 paper were added with their lifetime. None of those 61 has a transition rate in NIST or in the 2013 rate
  paper, so lifetime x sum(A) cannot be applied to them; they rest on the single program reading of the 2010 table.
- To close the item the owner still needs the PDF of the 2013 lifetime paper.
