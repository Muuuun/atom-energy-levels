"""List the E2 / M1 lines of an RCG output that end on the lowest level, rescaled to the observed transition energy."""
import re, sys
out, kind = sys.argv[1], sys.argv[2]           # kind: 'ELEC QUD' or 'MAG DIP'
OBS = {("3D", 1.0): 9033.966, ("3D", 2.0): 9215.501, ("3D", 3.0): 9596.533, ("1D", 2.0): 11395.350}
txt = open(out, encoding="latin-1").read().split("\n")
i0 = next(i for i, l in enumerate(txt) if kind + " SPECTRUM" in l)
i1 = next((i for i in range(i0 + 1, len(txt)) if "SPECTRUM" in txt[i] and kind not in txt[i]), len(txt))
up = None; n = 0
for l in txt[i0:i1]:
    m = re.match(r"\s+\* \* \*\s+(-?\d+\.\d+)\s+(\d+\.\d)\s+(\d+) \((\S+)\) (\S+)\s+(\d+) (Ba I\s+\S+)", l)
    if m:
        up = dict(E=float(m.group(1)), J=float(m.group(2)), term=m.group(5), conf=m.group(7).split()[-1]); continue
    m = re.match(r"\s+\d+\s+(-?\d+\.\d+)\s+(\d+\.\d)\s+(\d+) \((\S+)\) (\S+)\s+(-?\d+\.\d+)\s+(\d+\.\d+)\s+(-?\d+\.\d+)\s+(\S+)\s+(-?\d+\.\d+)", l)
    if m and up:
        lo = dict(E=float(m.group(1)), J=float(m.group(2)), term=m.group(5)); dE, lam, gA, cf = float(m.group(6)), float(m.group(7)), float(m.group(9)), float(m.group(10))
        hi, low = (up, lo) if up["E"] > lo["E"] else (lo, up)
        if low["term"] == "1S" and low["J"] == 0 and (hi["term"], hi["J"]) in OBS and n < 12 and hi["E"] - low["E"] < 20:
            n += 1
            wn = OBS[(hi["term"], hi["J"])]; power = 5 if "QUD" in kind else 3
            A = gA / (2 * hi["J"] + 1); A_obs = A * (wn / (abs(dE) * 1000)) ** power
            lamA = 1e8 / wn
            S = A_obs * (2 * hi["J"] + 1) * lamA ** power / (1.11995e18 if power == 5 else 2.69735e13)
            print(f"{kind}: {hi['conf'] if 'conf' in hi else ''} {hi['term']}{hi['J']:.0f} -> 1S0   calc dE {abs(dE)*1000:8.0f} cm-1 (obs {wn:.0f})  A_calc {A:.4g}  A at observed energy {A_obs:.4g} s^-1  "
                  f"lifetime {(f'{1/A_obs:.4g}' if A_obs else 'infinite')} s  sqrt(S) {S**0.5:.4g}  CF {cf}")
