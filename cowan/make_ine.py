"""Build the RCE input (file OUTGINE) with observed NIST energies: python3 make_ine.py <El> <OUTG11> <OUTGINE.orig> <OUTGINE>"""
import sys, re, math, collections
sys.path.insert(0, '.')
from cowan_util import *
el, outg11, src, dst = sys.argv[1:5]
MIN_FREE = 4   # a configuration frees its own Slater / spin-orbit parameters only with at least this many observed levels
nist = nist_levels(el)
blocks = eigen_blocks(outg11)
secs = outgine_sections(src)
assert len(secs) >= 2, 'two parities expected'
# which blocks belong to which parity: the OUTGINE sections list the J matrices in order; count them from the eigenvalue counts
out, bi, report = [], 0, []
for p, sec in enumerate(secs[:2], start=1):
    card1, card2 = sec[0], sec[1]
    # configuration names: 7 per line (A8,2X); first field is the element id
    rest = sec[2:]
    k = 0; fields = []
    while k < len(rest) and not re.match(r'^\s*-?\d+\.\d+', rest[k]):  # configuration and parameter names, 7 ten-character fields per line
        fields += [rest[k][i:i + 10] for i in range(0, len(rest[k].rstrip()), 10)]; k += 1
    is_par = lambda f: re.match(r'^(EAV |ZETA|ALPHA|BETA|GAMMA|[FG]\d\(|\d{3}[A-Z]\d)', f) is not None
    fields = [f for f in fields if f.strip()]
    first_par = next(i for i, f in enumerate(fields) if is_par(f))
    elid, confs, pnames = fields[0].strip(), [f.strip() for f in fields[1:first_par]], fields[first_par:]
    LMAX = len(pnames)
    # the J matrices of this parity: consecutive blocks; their sizes tell how many T / NF lines to skip
    odd = p == 2 if any(c[-2] in 'pf' and c[-1] in '0123456789' for c in confs if False) else None
    nJ = 0; jl = []
    pos = k
    while pos < len(rest) and re.match(r'^\s*-?\d+\.\d+', rest[pos]):
        b = blocks[bi + nJ]; IM = len(b['ev']); nl = math.ceil(IM / 7)
        vals = [float(x) for l in rest[pos:pos + nl] for x in re.findall(r'-?\d+\.\d+', l)]
        assert len(vals) == IM and all(abs(a - c) < 0.002 for a, c in zip(vals, b['ev'])), (p, b['J'], vals[:3], b['ev'][:3])
        jl.append(b); pos += 2 * nl; nJ += 1
    bi += nJ
    nl = math.ceil(LMAX / 7)
    LF = [int(x) for l in rest[pos:pos + nl] for x in l.split()]; pos += nl
    XMAX = rest[pos:pos + nl]; pos += nl
    X = [float(x) for l in rest[pos:pos + nl] for x in l.split()]; pos += nl
    ctrl = rest[pos]
    # parity of this section from its configurations: count of p and f electrons
    def parity_odd(conf):
        n = 0
        for m in re.finditer(r'(\d+)([spdfg])(\d*)', conf):
            n += (int(m.group(3) or 1)) * ('spdfg'.index(m.group(2)) % 2)
        return n % 2 == 1
    is_odd = parity_odd(confs[0])
    # assign observed levels: for every eigenvalue, its dominant basis state -> NIST level with same conf, term, J, parity
    obs_per_conf = collections.Counter()
    T_all, NF_all = [], []
    used = set()
    offs = []
    for b in jl:
        IM = len(b['ev']); T = [None] * IM; src_lab = [None] * IM
        cand = [n for n in nist if n['J'] == b['J'] and n['odd'] == is_odd]
        for c in range(IM):
            idx, w = dominant(b, c)
            cfg, conf, term = b['basis'][idx - 1]
            same = [n for n in cand if n['conf'] == conf and n['term'] == term and id(n) not in used]
            if same:
                T[idx - 1] = same[0]['E'] / 1000; used.add(id(same[0])); src_lab[idx - 1] = same[0]['raw']
                offs.append(same[0]['E'] / 1000 - b['ev'][c])
        for c in range(IM):  # second pass: levels NIST labels differently (jK coupling): energy order within the configuration
            idx, w = dominant(b, c)
            if T[idx - 1] is not None:
                continue
            cfg, conf, term = b['basis'][idx - 1]
            rest_n = sorted([n for n in cand if n['conf'] == conf and id(n) not in used], key=lambda n: n['E'])
            if rest_n:
                T[idx - 1] = rest_n[0]['E'] / 1000; used.add(id(rest_n[0])); src_lab[idx - 1] = rest_n[0]['raw']
                offs.append(rest_n[0]['E'] / 1000 - b['ev'][c])
        b['T'] = T; b['lab'] = src_lab
    off = sorted(offs)[len(offs) // 2] if offs else 0.0
    for b in jl:
        IM = len(b['ev']); NF = []
        for c in range(IM):  # unknown levels: estimated from the calculation, excluded from the fit (negative flag)
            idx, w = dominant(b, c)
            if b['T'][idx - 1] is None:
                b['T'][idx - 1] = round(b['ev'][c] + off, 4)
        for m in range(IM):  # a basis state that is nobody's dominant component: the eigenvalue of the same rank
            if b['T'][m] is None:
                b['T'][m] = round(b['ev'][m] + off, 4)
        for m in range(IM):
            cfg, conf, term = b['basis'][m]
            if b['lab'][m]:
                obs_per_conf[conf] += 1
        b['NF'] = [m + 1 if b['lab'][m] else -(m + 1) for m in range(IM)]
        report.append(f"parity {p} J={b['J']}: " + ', '.join(f"{b['basis'][m][1]} {b['basis'][m][2]} {b['T'][m]:.3f}{'' if b['lab'][m] else '?'}" for m in range(IM)))
    # parameter flags
    newLF, cur_conf, ci = [], None, 0
    for name, lf, x in zip(pnames, LF, X):
        nm = name.strip()
        m = re.match(r'EAV (\S+)', nm)
        if m:
            ci += 1; cur_conf = confs[ci - 1]  # EAV cards come in configuration order
            newLF.append(0 if obs_per_conf[cur_conf] >= 1 else lf); continue
        legal = re.match(r'ZETA|F[246]\(|G[0-9]\(', nm) and x != 0  # Slater and spin-orbit parameters with a non-zero value
        newLF.append(0 if legal and cur_conf and obs_per_conf[cur_conf] >= MIN_FREE else lf)
    # the ground configuration EAV sets the energy zero: keep it free too (observed = 0)
    free = sum(1 for x in newLF if x == 0); nobs = sum(obs_per_conf.values())
    report.append(f"parity {p}: {nobs} observed levels, {free} free parameters of {LMAX}; offset {off:+.3f} kK")
    # write the section
    def fmt7(vals, f):
        return [''.join(f % v for v in vals[i:i + 7]) for i in range(0, len(vals), 7)]
    c1 = list(card1.ljust(35)); c1[5:10] = list('   99'); c1[10:15] = list('   40')  # NOCYCR 99 (never reorder), NOCYCE 40 cycles
    out.append(''.join(c1).rstrip()); out.append(card2)
    out += rest[:k]  # names as they were
    for b in jl:
        out += fmt7(b['T'], '%10.4f'); out += fmt7(b['NF'], '%10d')
    out += fmt7(newLF, '%10d'); out += XMAX; out += fmt7(X, '%10.4f')
    cc = list(ctrl.ljust(80)); cc[70:75] = list(' 0.85'); out.append(''.join(cc).rstrip())  # CRIT = 0.85: levels follow their dominant component
    out.append('   -1')
open(dst, 'w').write('\n'.join(out) + '\n')
print('\n'.join(report))
