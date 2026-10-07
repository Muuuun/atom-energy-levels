#!/usr/bin/env python3
"""Run the Cowan chain for one element and compare with NIST:  COWAN_BIN=<build dir> python3 cowan/run_element.py Hg

COWAN_BIN holds the compiled rcn, rcn2, rcg, rce and cfp/FOR072, FOR073, FOR074, cfp/SENIOR (see README.md).  Work is done in
COWAN_WORK/<el> (default: a 'work' directory next to COWAN_BIN); the results go to cowan/<El>/ (inputs, fitted deck, fit report,
comparison tables) and data/cowan/<El>_lines.csv + index.json (every calculated line whose two levels are NIST levels).
Configurations: first the parity of the ground configuration, then the other; (orbitals on the RCN card, label as NIST writes
the configuration without dots).  RCN fills the closed core only up to the shell before the first listed one, so list every
shell NIST shows and the 4f14 / 4d10 shells explicitly.
"""
import os, sys, shutil, subprocess, json, datetime
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
        lines.append(f"   {cfg['Z']:2d}    1{(el + ' I  ' + label)[:18].ljust(18)}      {cfg['core']}{orb}")
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
    fit_report = subprocess.run(py + [os.path.join(HERE, "make_ine.py"), el, "OUTG11", "OUTGINE.orig", "OUTGINE"], cwd=work, capture_output=True, text=True)
    if fit_report.returncode:
        sys.exit(fit_report.stderr)
    run([os.path.join(binp, "rce")], work, "rce.log")
    subprocess.run(py + [os.path.join(HERE, "parvals_to_ing11.py"), "ING11.hfr", "PARVALS", "ING11"], cwd=work, check=True)
    for f in ("OUTG11", "OUTGINE", "TAPE2E"):
        os.remove(os.path.join(work, f))
    run([os.path.join(binp, "rcg")], work, "rcg_fit.log")
    shutil.copy(os.path.join(work, "OUTG11"), os.path.join(work, "OUTG11.fit"))
    out = os.path.join(HERE, el); os.makedirs(out, exist_ok=True)
    for f in ("IN36", "IN2", "ING11.hfr", "LEVELS1", "PARVALS"):
        shutil.copy(os.path.join(work, f), out)
    shutil.copy(os.path.join(work, "ING11"), os.path.join(out, "ING11.fit")); shutil.copy(os.path.join(work, "OUTGINE"), os.path.join(out, "OUTGINE.fit"))
    open(os.path.join(out, "fit_assignment.txt"), "w").write(fit_report.stdout)
    for tag in ("hfr", "fit"):
        r = subprocess.run(py + [os.path.join(HERE, "compare_nist.py"), el, f"OUTG11.{tag}"], cwd=work, capture_output=True, text=True)
        open(os.path.join(out, f"{el}_compare_{tag}.txt"), "w").write(r.stdout + r.stderr)
    os.makedirs(os.path.join(ROOT, "data", "cowan"), exist_ok=True)
    csv_path = os.path.join(ROOT, "data", "cowan", f"{el}_lines.csv")
    subprocess.run(py + [os.path.join(HERE, "export_lines.py"), el, "OUTG11.fit", csv_path], cwd=work, check=True)
    idx_path = os.path.join(ROOT, "data", "cowan", "index.json")
    idx = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
    idx[el] = dict(date=datetime.date.today().isoformat(), configurations=[l for _, l in cfg["first"] + cfg["second"]],
                   lines=sum(1 for _ in open(csv_path)) - 1, fit=fit_report.stdout.strip().split("\n")[-1])
    json.dump(dict(sorted(idx.items())), open(idx_path, "w"), indent=1)
    print(open(os.path.join(out, f"{el}_compare_fit.txt")).read()[:1500])
    print("fit:", [l for l in fit_report.stdout.split("\n") if l.startswith("parity")])


if __name__ == "__main__":
    main(sys.argv[1])
