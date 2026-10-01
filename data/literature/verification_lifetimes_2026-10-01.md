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
