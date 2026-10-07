#!/usr/bin/env python3
"""Run the Cowan chain for one element and compare with NIST:  COWAN_BIN=<build dir> python3 cowan/run_element.py Hg

COWAN_BIN holds the compiled rcn, rcn2, rcg, rce and cfp/FOR072, FOR073, FOR074, cfp/SENIOR (see README.md).  Work is done in
COWAN_WORK/<el> (default: a 'work' directory next to COWAN_BIN); the results go to cowan/<El>/ (inputs, fitted deck, fit report,
comparison tables) and data/cowan/<El>_lines.csv + index.json (every calculated line whose two levels are NIST levels).
Configurations: first the parity of the ground configuration, then the other; (orbitals on the RCN card, label as NIST writes
the configuration without dots).  RCN fills the closed core only up to the shell before the first listed one, so list every
shell NIST shows and the 4f14 / 4d10 shells explicitly.
"""
import os, re, sys, shutil, subprocess, json, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONFIGS = {
    "Hg": dict(Z=80, core="4f14 ",
               first=[("5d10 6s2", "5d106s2"), ("5d10 6s 7s", "5d106s7s"), ("5d10 6s 8s", "5d106s8s"), ("5d10 6s 9s", "5d106s9s"),
                      ("5d10 6s 6d", "5d106s6d"), ("5d10 6s 7d", "5d106s7d"), ("5d10 6s 8d", "5d106s8d"), ("5d10 6p2", "5d106p2")],
               second=[("5d10 6s 6p", "5d106s6p"), ("5d10 6s 7p", "5d106s7p"), ("5d10 6s 8p", "5d106s8p"), ("5d10 6s 9p", "5d106s9p"),
                       ("5d10 6s 5f", "5d106s5f"), ("5d10 6s 6f", "5d106s6f"), ("5d9 6s2 6p", "5d96s26p"), ("5d9 6s2 7p", "5d96s27p")]),
    "Cd": dict(Z=48, core="",
               first=[("4d10 5s2", "4d105s2"), ("4d10 5s 6s", "4d105s6s"), ("4d10 5s 7s", "4d105s7s"), ("4d10 5s 8s", "4d105s8s"),
                      ("4d10 5s 5d", "4d105s5d"), ("4d10 5s 6d", "4d105s6d"), ("4d10 5s 7d", "4d105s7d"), ("4d10 5p2", "4d105p2")],
               second=[("4d10 5s 5p", "4d105s5p"), ("4d10 5s 6p", "4d105s6p"), ("4d10 5s 7p", "4d105s7p"), ("4d10 5s 8p", "4d105s8p"),
                       ("4d10 5s 4f", "4d105s4f"), ("4d10 5s 5f", "4d105s5f"), ("4d9 5s2 5p", "4d95s25p"), ("4d9 5s2 6p", "4d95s26p")]),
    "In": dict(Z=49, core="4d10 ",
               first=[("5s2 5p", "5s25p"), ("5s2 6p", "5s26p"), ("5s2 7p", "5s27p"), ("5s2 8p", "5s28p"), ("5s2 9p", "5s29p"),
                      ("5s2 4f", "5s24f"), ("5s2 5f", "5s25f"), ("5s2 6f", "5s26f")],
               second=[("5s2 6s", "5s26s"), ("5s2 7s", "5s27s"), ("5s2 8s", "5s28s"), ("5s2 9s", "5s29s"), ("5s2 5d", "5s25d"),
                       ("5s2 6d", "5s26d"), ("5s2 7d", "5s27d"), ("5s2 8d", "5s28d"), ("5s 5p2", "5s5p2")]),
    "Ga": dict(Z=31, core="3d10 ",
               first=[("4s2 4p", "3d104s24p"), ("4s2 5p", "4s25p"), ("4s2 6p", "4s26p"), ("4s2 7p", "4s27p"), ("4s2 4f", "4s24f"), ("4s2 5f", "4s25f"), ("4s2 6f", "4s26f")],
               second=[("4s2 5s", "4s25s"), ("4s2 6s", "4s26s"), ("4s2 7s", "4s27s"), ("4s2 8s", "4s28s"), ("4s2 4d", "4s24d"), ("4s2 5d", "4s25d"),
                       ("4s2 6d", "4s26d"), ("4s2 7d", "4s27d"), ("4s 4p2", "4s4p2")]),
    "Tl": dict(Z=81, core="4f14 5d10 ",
               first=[("6s2 6p", "6s26p"), ("6s2 7p", "6s27p"), ("6s2 8p", "6s28p"), ("6s2 9p", "6s29p"), ("6s2 5f", "6s25f"), ("6s2 6f", "6s26f"), ("6s2 7f", "6s27f")],
               second=[("6s2 7s", "6s27s"), ("6s2 8s", "6s28s"), ("6s2 9s", "6s29s"), ("6s2 10s", "6s210s"), ("6s2 6d", "6s26d"), ("6s2 7d", "6s27d"),
                       ("6s2 8d", "6s28d"), ("6s2 9d", "6s29d"), ("6s 6p2", "6s6p2")]),
    "Cu": dict(Z=29, core="",
               first=[("3d10 4s", "3d104s"), ("3d9 4s2", "3d94s2"), ("3d10 5s", "3d105s"), ("3d10 6s", "3d106s"), ("3d10 7s", "3d107s"), ("3d10 4d", "3d104d"), ("3d10 5d", "3d105d")],
               second=[("3d10 4p", "3d104p"), ("3d9 4s 4p", "3d94s4p"), ("3d10 5p", "3d105p"), ("3d10 6p", "3d106p"), ("3d10 7p", "3d107p"), ("3d10 4f", "3d104f"), ("3d10 5f", "3d105f")]),
    "Ag": dict(Z=47, core="",
               first=[("4d10 5s", "4d105s"), ("4d9 5s2", "4d95s2"), ("4d10 6s", "4d106s"), ("4d10 7s", "4d107s"), ("4d10 8s", "4d108s"), ("4d10 5d", "4d105d"), ("4d10 6d", "4d106d")],
               second=[("4d10 5p", "4d105p"), ("4d9 5s 5p", "4d95s5p"), ("4d10 6p", "4d106p"), ("4d10 7p", "4d107p"), ("4d10 8p", "4d108p"), ("4d10 4f", "4d104f"), ("4d10 5f", "4d105f")]),
    "Au": dict(Z=79, core="4f14 ",
               first=[("5d10 6s", "5d106s"), ("5d9 6s2", "5d96s2"), ("5d10 7s", "5d107s"), ("5d10 8s", "5d108s"), ("5d10 6d", "5d106d"), ("5d10 7d", "5d107d")],
               second=[("5d10 6p", "5d106p"), ("5d9 6s 6p", "5d96s6p"), ("5d10 7p", "5d107p"), ("5d10 8p", "5d108p"), ("5d10 5f", "5d105f")]),
    "Sn": dict(Z=50, core="4d10 ",
               first=[("5s2 5p2", "5s25p2"), ("5s2 5p 6p", "5s25p6p"), ("5s2 5p 7p", "5s25p7p"), ("5s2 5p 4f", "5s25p4f"), ("5s2 5p 5f", "5s25p5f")],
               second=[("5s2 5p 6s", "5s25p6s"), ("5s2 5p 7s", "5s25p7s"), ("5s2 5p 8s", "5s25p8s"), ("5s2 5p 5d", "5s25p5d"), ("5s2 5p 6d", "5s25p6d"),
                       ("5s2 5p 7d", "5s25p7d"), ("5s 5p3", "5s5p3")]),
    "Pb": dict(Z=82, core="4f14 5d10 ",
               first=[("6s2 6p2", "6s26p2"), ("6s2 6p 7p", "6s26p7p"), ("6s2 6p 8p", "6s26p8p"), ("6s2 6p 5f", "6s26p5f"), ("6s2 6p 6f", "6s26p6f")],
               second=[("6s2 6p 7s", "6s26p7s"), ("6s2 6p 8s", "6s26p8s"), ("6s2 6p 9s", "6s26p9s"), ("6s2 6p 6d", "6s26p6d"), ("6s2 6p 7d", "6s26p7d"), ("6s2 6p 8d", "6s26p8d")]),
    "Xe": dict(Z=54, core="4d10 5s2 ",
               first=[("5p6", "5p6"), ("5p5 6p", "5p56p"), ("5p5 7p", "5p57p"), ("5p5 8p", "5p58p"), ("5p5 4f", "5p54f"), ("5p5 5f", "5p55f")],
               second=[("5p5 6s", "5p56s"), ("5p5 7s", "5p57s"), ("5p5 8s", "5p58s"), ("5p5 5d", "5p55d"), ("5p5 6d", "5p56d"), ("5p5 7d", "5p57d")]),
    "Kr": dict(Z=36, core="3d10 ",
               first=[("4s2 4p6", "4s24p6"), ("4s2 4p5 5p", "4s24p55p"), ("4s2 4p5 6p", "4s24p56p"), ("4s2 4p5 7p", "4s24p57p"), ("4s2 4p5 4f", "4s24p54f"), ("4s2 4p5 5f", "4s24p55f")],
               second=[("4s2 4p5 5s", "4s24p55s"), ("4s2 4p5 6s", "4s24p56s"), ("4s2 4p5 7s", "4s24p57s"), ("4s2 4p5 4d", "4s24p54d"), ("4s2 4p5 5d", "4s24p55d"), ("4s2 4p5 6d", "4s24p56d")]),
    "Ge": dict(Z=32, core="3d10 ",
               first=[("4s2 4p2", "4s24p2"), ("4s2 4p 5p", "4s24p5p"), ("4s2 4p 6p", "4s24p6p"), ("4s2 4p 4f", "4s24p4f"), ("4s2 4p 5f", "4s24p5f")],
               second=[("4s2 4p 5s", "4s24p5s"), ("4s 4p3", "4s4p3"), ("4s2 4p 4d", "4s24p4d"), ("4s2 4p 6s", "4s24p6s"), ("4s2 4p 5d", "4s24p5d"),
                       ("4s2 4p 7s", "4s24p7s"), ("4s2 4p 6d", "4s24p6d")]),
    "Sb": dict(Z=51, core="4d10 5s2 ",
               first=[("5p3", "5p3"), ("5p2 6p", "5p26p"), ("5p2 7p", "5p27p"), ("5p2 4f", "5p24f"), ("5p2 8p", "5p28p")],
               second=[("5p2 6s", "5p26s"), ("5p2 5d", "5p25d"), ("5p2 7s", "5p27s"), ("5p2 6d", "5p26d"), ("5p2 8s", "5p28s"), ("5p2 7d", "5p27d")]),
    "Bi": dict(Z=83, core="4f14 5d10 6s2 ",
               first=[("6p3", "6p3"), ("6p2 7p", "6p27p"), ("6p2 8p", "6p28p"), ("6p2 9p", "6p29p")],
               second=[("6p2 7s", "6p27s"), ("6p2 6d", "6p26d"), ("6p2 8s", "6p28s"), ("6p2 7d", "6p27d"), ("6p2 9s", "6p29s"), ("6p2 8d", "6p28d")]),
    "Te": dict(Z=52, core="4d10 5s2 ",
               first=[("5p4", "5p4"), ("5p3 6p", "5p36p"), ("5p3 7p", "5p37p"), ("5p3 4f", "5p34f"), ("5p3 8p", "5p38p"), ("5p3 5f", "5p35f")],
               second=[("5p3 6s", "5p36s"), ("5p3 5d", "5p35d"), ("5p3 7s", "5p37s"), ("5p3 6d", "5p36d"), ("5p3 8s", "5p38s"), ("5p3 7d", "5p37d")]),
    "Se": dict(Z=34, core="3d10 ",
               first=[("4s2 4p4", "4s24p4"), ("4s2 4p3 5p", "4s24p35p"), ("4s2 4p3 6p", "4s24p36p"), ("4s2 4p3 4f", "4s24p34f"), ("4s2 4p3 7p", "4s24p37p"), ("4s2 4p3 5f", "4s24p35f")],
               second=[("4s2 4p3 5s", "4s24p35s"), ("4s2 4p3 4d", "4s24p34d"), ("4s2 4p3 6s", "4s24p36s"), ("4s2 4p3 5d", "4s24p35d"), ("4s2 4p3 7s", "4s24p37s"), ("4s2 4p3 6d", "4s24p36d")]),
    "Br": dict(Z=35, core="3d10 ",
               first=[("4s2 4p5", "4s24p5"), ("4s2 4p4 5p", "4s24p45p"), ("4s2 4p4 6p", "4s24p46p"), ("4s2 4p4 4f", "4s24p44f"), ("4s2 4p4 7p", "4s24p47p"), ("4s2 4p4 5f", "4s24p45f")],
               second=[("4s2 4p4 5s", "4s24p45s"), ("4s2 4p4 4d", "4s24p44d"), ("4s2 4p4 6s", "4s24p46s"), ("4s 4p6", "4s4p6"), ("4s2 4p4 5d", "4s24p45d"),
                       ("4s2 4p4 7s", "4s24p47s"), ("4s2 4p4 6d", "4s24p46d")]),
    "I": dict(Z=53, core="4d10 ",
              first=[("5s2 5p5", "5s25p5"), ("5s2 5p4 6p", "5s25p46p"), ("5s2 5p4 7p", "5s25p47p"), ("5s2 5p4 4f", "5s25p44f"), ("5s2 5p4 8p", "5s25p48p"), ("5s2 5p4 5f", "5s25p45f")],
              second=[("5s2 5p4 6s", "5s25p46s"), ("5s2 5p4 5d", "5s25p45d"), ("5s2 5p4 7s", "5s25p47s"), ("5s2 5p4 6d", "5s25p46d"), ("5s2 5p4 8s", "5s25p48s"), ("5s2 5p4 7d", "5s25p47d")]),
}
RCN_CARD = "200-90 0 2  01.  4.0    5.E-08    1.E-11-2 00190 0 1.0  0.65  0.0 1.00   -6"  # HFR (col 46 = 1), as the NIST sample otherwise
IN2_CARD = "G5INP  0 10 0 0.00000         0011111 1 00000000  8599858585 2.00   1 02200  0.0"  # IABG 0; scale 85/99/85/85/85; keep gA >= 100/s


def run(cmd, cwd, log):
    with open(os.path.join(cwd, log), "w") as f:
        r = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        sys.exit(f"{cmd} failed, see {cwd}/{log}")


def main(el):
    cfg = CONFIGS[el]
    binp = os.environ.get("COWAN_BIN") or sys.exit("set COWAN_BIN")
    work = os.path.join(os.environ.get("COWAN_WORK") or os.path.join(binp, "work"), el.lower())
    os.makedirs(work, exist_ok=True)
    for f in ("FOR072", "FOR073", "FOR074", "SENIOR"):
        shutil.copy(os.path.join(binp, "cfp", f), work)
    lines = [RCN_CARD]
    for orb, label in cfg["first"] + cfg["second"]:
        lines.append(f"   {cfg['Z']:2d}    1{((el + ' I').ljust(6) + label)[:18].ljust(18)}      {cfg['core']}{orb}")  # RCG takes the configuration from column 7 of the label
    lines.append("   -1")
    open(os.path.join(work, "IN36"), "w").write("\n".join(lines) + "\n")
    open(os.path.join(work, "IN2"), "w").write(IN2_CARD + "\n        -1\n")
    for f in ("out36", "tape2n", "OUT2", "ING11", "OUTG11", "OUTGINE", "TAPE2E", "OUTE", "LEVELS1", "LEVELS2", "LEVELS3", "PARVALS", "RCEOUT", "RCEINP", "RCEINP.HF"):
        p = os.path.join(work, f)
        if os.path.exists(p):
            os.remove(p)
    py = [sys.executable, "-I"]
    run([os.path.join(binp, "rcn")], work, "rcn.log")
    run([os.path.join(binp, "rcn2")], work, "rcn2.log")
    run([os.path.join(binp, "rcg")], work, "rcg.log")
    shutil.copy(os.path.join(work, "OUTG11"), os.path.join(work, "OUTG11.hfr")); shutil.copy(os.path.join(work, "ING11"), os.path.join(work, "ING11.hfr"))
    shutil.copy(os.path.join(work, "OUTGINE"), os.path.join(work, "OUTGINE.orig"))
    # two-stage least squares: first only the EAV move (this settles which eigenvalue is which level), then the planned parameters
    fit1 = subprocess.run(py + [os.path.join(HERE, "make_ine.py"), el, "OUTG11", "OUTGINE.orig", "OUTGINE", "1"], cwd=work, capture_output=True, text=True)
    if fit1.returncode:
        sys.exit(fit1.stderr)
    run([os.path.join(binp, "rce")], work, "rce1.log")
    shutil.copy(os.path.join(work, "PARVALS"), os.path.join(work, "PARVALS.stage1"))
    fit_report = subprocess.run(py + [os.path.join(HERE, "make_ine.py"), el, "OUTG11", "OUTGINE.orig", "OUTGINE", "2", "PARVALS.stage1"], cwd=work, capture_output=True, text=True)
    if fit_report.returncode:
        sys.exit(fit_report.stderr)
    run([os.path.join(binp, "rce")], work, "rce.log")

    def sane(parvals):  # a fit that ran away prints ***** or absurd values on its RCG cards
        txt = open(parvals, encoding="latin-1").read()
        cards = txt[txt.find("FOR RCG INPUT"):] if "FOR RCG INPUT" in txt else ""
        return bool(cards) and "*" not in cards and all(abs(float(x)) < 1000 for x in re.findall(r"-?\d+\.\d+", cards))
    fit_used = "stage 2 (energies, Slater and spin-orbit parameters)"
    if not sane(os.path.join(work, "PARVALS")):
        shutil.copy(os.path.join(work, "PARVALS.stage1"), os.path.join(work, "PARVALS"))
        fit_used = "stage 1 only (configuration energies; the full fit ran away)"
        if not sane(os.path.join(work, "PARVALS")):
            fit_used = "none (both fits ran away): unfitted HFR with scaled parameters"
    if fit_used.startswith("none"):
        shutil.copy(os.path.join(work, "ING11.hfr"), os.path.join(work, "ING11"))
    else:
        subprocess.run(py + [os.path.join(HERE, "parvals_to_ing11.py"), "ING11.hfr", "PARVALS", "ING11"], cwd=work, check=True)
    for f in ("OUTG11", "OUTGINE", "TAPE2E"):
        os.remove(os.path.join(work, f))
    run([os.path.join(binp, "rcg")], work, "rcg_fit.log")
    shutil.copy(os.path.join(work, "OUTG11"), os.path.join(work, "OUTG11.fit"))
    out = os.path.join(HERE, el); os.makedirs(out, exist_ok=True)
    for f in ("IN36", "IN2", "ING11.hfr", "LEVELS1", "PARVALS"):
        shutil.copy(os.path.join(work, f), out)
    shutil.copy(os.path.join(work, "ING11"), os.path.join(out, "ING11.fit")); shutil.copy(os.path.join(work, "OUTGINE"), os.path.join(out, "OUTGINE.fit"))
    open(os.path.join(out, "fit_assignment.txt"), "w").write(fit_report.stdout + "\nfit used: " + fit_used + "\n")
    for tag in ("hfr", "fit"):
        r = subprocess.run(py + [os.path.join(HERE, "compare_nist.py"), el, f"OUTG11.{tag}"], cwd=work, capture_output=True, text=True)
        open(os.path.join(out, f"{el}_compare_{tag}.txt"), "w").write(r.stdout + r.stderr)
    os.makedirs(os.path.join(ROOT, "data", "cowan"), exist_ok=True)
    csv_path = os.path.join(ROOT, "data", "cowan", f"{el}_lines.csv")
    subprocess.run(py + [os.path.join(HERE, "export_lines.py"), el, "OUTG11.fit", csv_path], cwd=work, check=True)
    idx_path = os.path.join(ROOT, "data", "cowan", "index.json")
    idx = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
    idx[el] = dict(date=datetime.date.today().isoformat(), configurations=[l for _, l in cfg["first"] + cfg["second"]],
                   lines=sum(1 for _ in open(csv_path)) - 1, fit=fit_used)
    json.dump(dict(sorted(idx.items())), open(idx_path, "w"), indent=1)
    print(open(os.path.join(out, f"{el}_compare_fit.txt")).read()[:1500])
    print("fit:", [l for l in fit_report.stdout.split("\n") if l.startswith("parity")])


if __name__ == "__main__":
    main(sys.argv[1])
