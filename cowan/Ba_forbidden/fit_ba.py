"""Second half of the chain: fit the HFR parameters to the NIST energies (the repo's two-stage scheme), rerun RCG.  Scratch only."""
import os, re, sys, shutil, subprocess
BIN, WORK = sys.argv[1], sys.argv[2]
HERE = "/Users/muqiao/Documents/rb_energy_levels/cowan"; el = "Ba"; py = [sys.executable, "-I"]
def run(cmd, log):
    with open(os.path.join(WORK, log), "w") as f:
        r = subprocess.run(cmd, cwd=WORK, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode: sys.exit(f"{cmd} failed, see {log}")
f1 = subprocess.run(py + [os.path.join(HERE, "make_ine.py"), el, "OUTG11.hfr", "OUTGINE.orig", "OUTGINE", "1"], cwd=WORK, capture_output=True, text=True)
if f1.returncode: sys.exit(f1.stderr)
run([os.path.join(BIN, "rce")], "rce1.log"); shutil.copy(os.path.join(WORK, "PARVALS"), os.path.join(WORK, "PARVALS.stage1"))
f2 = subprocess.run(py + [os.path.join(HERE, "make_ine.py"), el, "OUTG11.hfr", "OUTGINE.orig", "OUTGINE", "2", "PARVALS.stage1"], cwd=WORK, capture_output=True, text=True)
if f2.returncode: sys.exit(f2.stderr)
run([os.path.join(BIN, "rce")], "rce.log")
def sane(p):
    txt = open(p, encoding="latin-1").read(); cards = txt[txt.find("FOR RCG INPUT"):] if "FOR RCG INPUT" in txt else ""
    return bool(cards) and "*" not in cards and all(abs(float(x)) < 1000 for x in re.findall(r"-?\d+\.\d+", cards))
used = "stage 2"
if not sane(os.path.join(WORK, "PARVALS")):
    shutil.copy(os.path.join(WORK, "PARVALS.stage1"), os.path.join(WORK, "PARVALS")); used = "stage 1 only"
    if not sane(os.path.join(WORK, "PARVALS")): sys.exit("both fits ran away")
shutil.copy(os.path.join(WORK, "LEVELS1"), os.path.join(WORK, "LEVELS1." + used.replace(" ", "")))
subprocess.run(py + [os.path.join(HERE, "parvals_to_ing11.py"), "ING11.hfr", "PARVALS", "ING11"], cwd=WORK, check=True)
for f in ("OUTG11", "OUTGINE", "TAPE2E"):
    os.remove(os.path.join(WORK, f))
run([os.path.join(BIN, "rcg")], "rcg_fit.log"); shutil.copy(os.path.join(WORK, "OUTG11"), os.path.join(WORK, "OUTG11.fit"))
open(os.path.join(WORK, "fit_assignment.txt"), "w").write(f2.stdout + "\nfit used: " + used + "\n")
print("fit used:", used); print("\n".join(l[:230] for l in f2.stdout.split("\n") if l.startswith("parity"))[:1500])
