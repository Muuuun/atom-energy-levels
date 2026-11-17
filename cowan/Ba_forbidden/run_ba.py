"""Ba I with the Cowan chain, E2 and M1 lines of the even parity switched on.  Scratch only: nothing is written into the repo."""
import os, re, sys, shutil, subprocess
BIN = sys.argv[1]; WORK = sys.argv[2]; TAG = sys.argv[3] if len(sys.argv) > 3 else "full"
HERE = "/Users/muqiao/Documents/rb_energy_levels/cowan"
el, Z = "Ba", 56
first = [("5p6 6s2", "6s2"), ("5p6 5d 6s", "6s5d"), ("5p6 5d2", "5d2"), ("5p6 6p2", "6p2"), ("5p6 6s 7s", "6s7s"), ("5p6 6s 6d", "6s6d"),
         ("5p6 5d 7s", "5d7s"), ("5p6 5d 6d", "5d6d"), ("5p6 6s 8s", "6s8s"), ("5p6 6s 7d", "6s7d")]
if TAG == "small":   # the two-configuration-plus-6p2 space of Migdalek & Baylis (their MCDF-II)
    first = first[:4]
second = [("5p6 6s 6p", "6s6p"), ("5p6 5d 6p", "5d6p"), ("5p6 6s 7p", "6s7p")]
RCN_CARD = "200-90 0 2  01.  4.0    5.E-08    1.E-11-2 00190 0 1.0  0.65  0.0 1.00   -6"
c = list("G5INP  0 10 0 0.00000         0011111 1 00000000  8599858585 2.00   1 02200  0.0")
c[48], c[49] = "1", "1"            # IMAG = 1, IQUAD = 1: M1 and E2 lines of the first parity
c[60:65] = list(" 0.00")           # DMIN = 0: keep every line
IN2_CARD = "".join(c)
os.makedirs(WORK, exist_ok=True)
for f in ("FOR072", "FOR073", "FOR074", "SENIOR"):
    shutil.copy(os.path.join(BIN, "cfp", f), WORK)
lines = [RCN_CARD] + [f"   {Z:2d}    1{((el + ' I').ljust(6) + label)[:18].ljust(18)}      {orb}" for orb, label in first + second] + ["   -1"]
open(os.path.join(WORK, "IN36"), "w").write("\n".join(lines) + "\n")
open(os.path.join(WORK, "IN2"), "w").write(IN2_CARD + "\n        -1\n")
def run(cmd, log):
    with open(os.path.join(WORK, log), "w") as f:
        r = subprocess.run(cmd, cwd=WORK, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode: sys.exit(f"{cmd} failed, see {log}")
for f in ("out36", "tape2n", "OUT2", "ING11", "OUTG11", "OUTGINE", "TAPE2E", "PARVALS", "LEVELS1"):
    if os.path.exists(os.path.join(WORK, f)): os.remove(os.path.join(WORK, f))
for p in ("rcn", "rcn2", "rcg"):
    run([os.path.join(BIN, p)], p + ".log")
    print(p, open(os.path.join(WORK, p + ".log")).read().strip().split("\n")[-1])
shutil.copy(os.path.join(WORK, "OUTG11"), os.path.join(WORK, "OUTG11.hfr")); shutil.copy(os.path.join(WORK, "ING11"), os.path.join(WORK, "ING11.hfr"))
shutil.copy(os.path.join(WORK, "OUTGINE"), os.path.join(WORK, "OUTGINE.orig"))
