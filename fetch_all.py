"""Download the NIST ASD level and line tables of every neutral atom (cached in data/nist)."""
import time
import atomlib as al
from elements import ELEMENTS
import os
for e in ELEMENTS:
    s = e["symbol"]
    fresh = not os.path.exists(os.path.join(al.NIST_DIR, f"{s}_I_lines_from1nm.tsv"))
    try:
        lv, lim = al.nist_levels(s)
        ln = al.nist_lines(s, 1)
        print(s, len(lv), lim, len(ln), sum(1 for l in ln if l["A"]), flush=True)
    except Exception as ex:
        print(s, "ERROR", repr(ex)[:120], flush=True)
    if fresh:
        time.sleep(1.5)
