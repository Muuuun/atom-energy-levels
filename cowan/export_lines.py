"""Fitted Cowan lines on NIST levels -> CSV (A scaled to the NIST transition energy): python3 export_lines.py <El> <OUTG11> <out.csv>"""
import sys, csv, re, collections
sys.path.insert(0, '.')
from cowan_util import nist_levels
from parse_rcg import parse
el, out, dst = sys.argv[1:4]
nist = nist_levels(el); lines = parse(out)
L = open(out, encoding='latin-1').read().split('\n')
i0 = next(i for i, l in enumerate(L) if 'ELEC DIP SPECTRUM' in l and 'ENERGIES IN UNITS' in l)
cfg = {1: {}, 2: {}}
for l in L[i0 + 1:i0 + 40]:
    m = re.match(r'\s*(\d+)\s+\S+ I\s+(\S+)\s+---\s+\S+ I\s+(\S+)', l)
    if m:
        cfg[1][int(m.group(1))] = m.group(2); cfg[2][int(m.group(1))] = m.group(3)
calc = {}
for ln in lines:
    u, lo = ln['up'], ln['lo']
    calc.setdefault((2, u['E'], u['J']), dict(conf=cfg[2][u['cfg']], term=u['term'], E=u['E'], J=u['J'], par=2))
    calc.setdefault((1, lo['E'], lo['J']), dict(conf=cfg[1][lo['cfg']], term=lo['term'], E=lo['E'], J=lo['J'], par=1))
def parity_odd(conf):
    return sum(int(m.group(3) or 1) * ('spdfg'.index(m.group(2)) % 2) for m in re.finditer(r'(\d+)([spdfg])(\d*)', conf)) % 2 == 1
groups = collections.defaultdict(list)
for c in calc.values():
    groups[(c['par'], c['J'], c['conf'])].append(c)
used = set()
for (par, J, conf), cs in groups.items():
    cs.sort(key=lambda c: c['E'])
    cand = sorted([n for n in nist if n['J'] == J and n['conf'] == conf and n['odd'] == parity_odd(conf)], key=lambda n: n['E'])
    for c in cs:
        same = [n for n in cand if n['term'] == c['term'] and id(n) not in used]
        if same:
            c['nist'] = same[0]; used.add(id(same[0]))
    for c in cs:
        if 'nist' not in c:
            rest = [n for n in cand if id(n) not in used]
            if rest:
                c['nist'] = rest[0]; used.add(id(rest[0]))
rows = []
for ln in lines:
    u = calc[(2, ln['up']['E'], ln['up']['J'])]; lo = calc[(1, ln['lo']['E'], ln['lo']['J'])]
    if 'nist' not in u or 'nist' not in lo:
        continue
    a, b = (lo, u) if lo['nist']['E'] < u['nist']['E'] else (u, lo)  # a = lower level
    sig_obs, sig_calc = b['nist']['E'] - a['nist']['E'], abs(ln['dE']) * 1000
    if sig_obs <= 0 or sig_calc <= 0:
        continue
    gf = 10 ** ln['loggf'] * sig_obs / sig_calc
    A = 6.6703e13 * gf / ((2 * b['J'] + 1) * (1e7 / sig_obs) ** 2)
    rows.append((1e7 / sig_obs, a['nist'], b['nist'], gf, A, ln['cf']))
rows.sort()
with open(dst, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['wavelength_vac_nm', 'lower_E_cm', 'lower_J', 'lower_level', 'upper_E_cm', 'upper_J', 'upper_level', 'gf', 'A_s', 'cancellation_factor'])
    for lam, a, b, gf, A, cf in rows:
        w.writerow([f'{lam:.4f}', a['E'], a['J'], a['raw'], b['E'], b['J'], b['raw'], f'{gf:.4g}', f'{A:.4g}', cf])
print(len(rows), 'lines written')
