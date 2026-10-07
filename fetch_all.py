"""Download the NIST ASD level and line tables of every neutral atom (cached in data/nist): levels, lines 1 nm - 2 um, lines 2 um - 1 mm."""
import time
import atomlib as al
from elements import ELEMENTS
import os
for e in ELEMENTS:
    s = e["symbol"]
    fresh = not all(os.path.exists(os.path.join(al.NIST_DIR, f)) for f in (f"{s}_I_lines_from1nm.tsv", f"{s}_I_lines_2000nm_to_{al.IR_MAX_NM}nm.tsv"))
    try:
        lv, lim = al.nist_levels(s)
        ln = al.nist_lines(s, 1)
        ir = al.nist_lines_ir(s)
        print(s, len(lv), lim, len(ln), sum(1 for l in ln if l["A"]), "ir", len(ir), sum(1 for l in ir if l["A"]), flush=True)
    except Exception as ex:
        print(s, "ERROR", repr(ex)[:120], flush=True)
    if fresh:
        time.sleep(1.5)
