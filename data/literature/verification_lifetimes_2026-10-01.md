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
