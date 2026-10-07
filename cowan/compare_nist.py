"""Compare RCG (Cowan) E1 rates with NIST for one element: python3 compare_nist.py <El> <OUTG11>"""
import os, csv, re, sys, math, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_rcg import parse
from cowan_util import parity_odd
el, out = sys.argv[1], sys.argv[2]
NIST = '/Users/muqiao/Documents/rb_energy_levels/data/nist'
def jnum(s):
    s = s.strip('"').strip()
    return float(s.split('/')[0]) / float(s.split('/')[1]) if '/' in s else float(s)
def conf_key(c):  # NIST "5d10.6s.6p" / "5d9.6s2.(2D<5/2>).6p" -> "5d106s6p" / "5d96s26p"
    return re.sub(r'\([^)]*\)', '', c.strip('"')).replace('.', '')
def term_key(t):
    t = t.strip('"').replace('*', '').replace('?', '').strip()
    m = re.search(r'(\d[A-Z])', t)
    return m.group(1) if m else t
nist = []
for r in csv.DictReader(open(f'{NIST}/{el}_I_levels.tsv'), delimiter='\t'):
    try:
        E = float(re.sub(r'[^\d.]', '', r['Level (cm-1)'])); J = jnum(r['J'])
    except ValueError:
        continue
    if r['Term'].strip('"') == 'Limit':
        continue
    nist.append(dict(E=E, J=J, conf=conf_key(r['Configuration']), term=term_key(r['Term']), odd='*' in r['Term']))
lines = parse(out)
# configuration labels per parity from the spectrum header table "k  El I  conf1  ---  El I  conf2"
L = open(out, encoding='latin-1').read().split('\n')
i0 = next(i for i, l in enumerate(L) if 'ELEC DIP SPECTRUM' in l and 'ENERGIES IN UNITS' in l)
cfg = {1: {}, 2: {}}
for l in L[i0 + 1:i0 + 40]:
    m = re.match(r'\s*(\d+)\s+(?:\S+ I\s+(\S+))?\s*---\s*(?:\S+ I\s+(\S+))?', l)
    if m and (m.group(2) or m.group(3)):
        if m.group(2):
            cfg[1][int(m.group(1))] = m.group(2)
        if m.group(3):
            cfg[2][int(m.group(1))] = m.group(3)
# calculated levels: parity 2 = upper levels of the blocks, parity 1 = lower levels of the lines
calc = {}
for ln in lines:
    u, lo = ln['up'], ln['lo']
    calc.setdefault((2, u['E'], u['J']), dict(conf=cfg[2][u['cfg']], term=u['term'], E=u['E'], J=u['J'], par=2))
    calc.setdefault((1, lo['E'], lo['J']), dict(conf=cfg[1][lo['cfg']], term=lo['term'], E=lo['E'], J=lo['J'], par=1))
odd_par = 2 if parity_odd(cfg[2][1], nist) else 1  # which parity group is odd
# assign NIST levels: same parity, J, configuration; same term where NIST has that term; otherwise energy order within the group
groups = collections.defaultdict(list)
for k, c in calc.items():
    groups[(c['par'], c['J'], c['conf'])].append(c)
used = set()
for (par, J, conf), cs in groups.items():
    cs.sort(key=lambda c: c['E'])
    cand = sorted([n for n in nist if n['J'] == J and n['conf'] == conf and n['odd'] == (par == odd_par)], key=lambda n: n['E'])
    for c in cs:  # term match first
        same = [n for n in cand if n['term'] == c['term'] and id(n) not in used]
        if same:
            c['nist'] = same[0]; used.add(id(same[0]))
    for c in cs:
        if 'nist' not in c:
            rest = [n for n in cand if id(n) not in used]
            if rest:
                c['nist'] = rest[0]; used.add(id(rest[0]))
E0 = min(c['E'] for c in calc.values() if c['par'] == 1)
nl = sum(1 for c in calc.values() if 'nist' in c)
print(f'{el}: {len(calc)} calculated levels, {nl} matched to NIST levels')
dev = [(c['E'] - E0) * 1000 - c['nist']['E'] for c in calc.values() if 'nist' in c]
print(f'  energy deviation calc - NIST (cm-1): median {sorted(dev)[len(dev)//2]:+.0f}, max |dev| {max(abs(d) for d in dev):.0f}')
# NIST lines with A
nA = {}
for fn in (f'{el}_I_lines_from1nm.tsv', f'{el}_I_lines_2000nm_to_1000000nm.tsv'):
    try:
        rows = list(csv.DictReader(open(f'{NIST}/{fn}'), delimiter='\t'))
    except Exception:
        continue
    for r in rows:
        a = (r.get('Aki(s^-1)') or '').strip()
        if not a:
            continue
        try:
            Ei, Ek = float(re.sub(r'[^\d.]', '', r['Ei(cm-1)'])), float(re.sub(r'[^\d.]', '', r['Ek(cm-1)']))
        except ValueError:
            continue
        nA[(round(Ei, 1), round(Ek, 1))] = (float(a), (r.get('Acc') or '').strip())
rows, stat = [], collections.defaultdict(list)
for ln in lines:
    u = calc[(2, ln['up']['E'], ln['up']['J'])]; lo = calc[(1, ln['lo']['E'], ln['lo']['J'])]
    if 'nist' not in u or 'nist' not in lo:
        continue
    Eu, El = u['nist']['E'], lo['nist']['E']
    if Eu < El:
        Eu, El = El, Eu  # the "upper" of the block may lie below the even level: then it is the lower level of an absorption line
    sig_obs, sig_calc = Eu - El, abs(ln['dE']) * 1000
    if sig_obs <= 0 or sig_calc <= 0:
        continue
    gu = 2 * (u['J'] if u['nist']['E'] == Eu else lo['J']) + 1
    gf = 10 ** ln['loggf'] * sig_obs / sig_calc
    A = 6.6703e13 * gf / (gu * (1e7 / sig_obs) ** 2)
    ref = nA.get((round(El, 1), round(Eu, 1)))
    rows.append((1e7 / sig_obs, lo, u, A, ref, ln['cf']))
    if ref:
        stat[ref[1][:1] or '?'].append(math.log10(A / ref[0]))
print(f'  {len(rows)} calculated lines on NIST levels; {sum(1 for r in rows if r[4])} of them have a NIST rate')
allv = [v for vs in stat.values() for v in vs]
for acc in sorted(stat):
    v = sorted(stat[acc]); n = len(v)
    print(f'  NIST class {acc}: n={n:3d} median log10(calc/NIST)={v[n//2]:+.2f}  within x1.5: {sum(abs(x)<0.176 for x in v)/n:.0%}  within x2: {sum(abs(x)<0.301 for x in v)/n:.0%}  within x3: {sum(abs(x)<0.477 for x in v)/n:.0%}')
v = sorted(allv); n = len(v)
print(f'  ALL: n={n} median {v[n//2]:+.2f} within x2 {sum(abs(x)<0.301 for x in v)/n:.0%} within x3 {sum(abs(x)<0.477 for x in v)/n:.0%}')
w = sorted(math.log10(A / ref[0]) for lam, lo, u, A, ref, cf in rows if ref and abs(cf) >= 0.05); m = len(w)
if m:
    print(f'  lines with |cancellation factor| >= 0.05 (what the site uses): n={m} median {w[m//2]:+.2f} within x1.5 {sum(abs(x)<0.176 for x in w)/m:.0%} within x2 {sum(abs(x)<0.301 for x in w)/m:.0%} within x3 {sum(abs(x)<0.477 for x in w)/m:.0%}')
print('\n  lambda(nm)  lower                      upper                       A_calc     A_NIST  acc  ratio   CF')
for lam, lo, u, A, ref, cf in sorted(rows, key=lambda r: r[0]):
    if ref:
        print(f"  {lam:9.3f}  {lo['nist']['conf']+' '+lo['nist']['term']+str(lo['J']):26s} {u['nist']['conf']+' '+u['nist']['term']+str(u['J']):26s} {A:9.3e}  {ref[0]:9.3e}  {ref[1]:3s} {A/ref[0]:6.2f}  {cf:+.2f}")
