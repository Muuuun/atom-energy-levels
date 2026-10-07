"""Shared helpers for the Cowan-code pilot: NIST levels, RCG eigenvector tables, OUTGINE sections."""
import csv, re, collections
NIST = '/Users/muqiao/Documents/rb_energy_levels/data/nist'

def jnum(s):
    s = s.strip('"').strip()
    return float(s.split('/')[0]) / float(s.split('/')[1]) if '/' in s else float(s)

def conf_key(c):  # NIST "5d10.6s.6p" / "5d9.6s2.(2D<5/2>).6p" -> "5d106s6p" / "5d96s26p"
    return re.sub(r'<[^>]*>', '', re.sub(r'\([^)]*\)', '', c.strip('"'))).replace('.', '')

def term_key(t):
    t = t.strip('"').replace('*', '').replace('?', '').strip()
    m = re.search(r'(\d[A-Z])', t)
    return m.group(1) if m else t

def nist_levels(el):
    out = []
    for r in csv.DictReader(open(f'{NIST}/{el}_I_levels.tsv'), delimiter='\t'):
        try:
            E = float(re.sub(r'[^\d.]', '', r['Level (cm-1)'])); J = jnum(r['J'])
        except ValueError:
            continue
        if r['Term'].strip('"') == 'Limit':
            continue
        out.append(dict(E=E, J=J, conf=conf_key(r['Configuration']), term=term_key(r['Term']), odd='*' in r['Term'], raw=r['Configuration'].strip('"') + ' ' + r['Term'].strip('"')))
    return out

def parity_odd(label, nist=None):
    """Is the configuration with this label (NIST spelling without dots, e.g. 5s25p) odd?  Decided from the NIST levels that carry
    the configuration; without any, from the p and f occupation numbers (the label is ambiguous: 5s25p = 5s2 5p)."""
    if nist:
        odd = [n['odd'] for n in nist if n['conf'] == label]
        if odd:
            return sum(odd) * 2 > len(odd)
    n = 0
    for m in re.finditer(r'(\d{1,2})([spdfg])(\d*?)(?=\d{1,2}[spdfg]|$)', label):
        n += int(m.group(3) or 1) * ('spdfg'.index(m.group(2)) % 2)
    return n % 2 == 1


def eigen_blocks(outg11):
    """[(J, [eigenvalues], [config no.], basis=[(idx, conf, term)], vectors[col][row])] in file order (parity 1 blocks first)."""
    L = open(outg11, encoding='latin-1').read().split('\n')
    blocks, i = [], 0
    while i < len(L):
        m = re.match(r'^.\s+EIGENVALUES\s+\(J=\s*(\d+\.\d)\)', L[i])
        if not m:
            i += 1; continue
        J = float(m.group(1)); i += 1
        ev = []
        while 'CONFIG. NO.' not in L[i]:
            ev += [float(x) for x in L[i].split()]; i += 1
        i += 1; cno = []
        while len(cno) < len(ev):
            cno += [int(x) for x in L[i].split()]; i += 1
        while 'EIGENVECTORS   (    LS COUPLING)' not in L[i]:
            i += 1
        i += 1
        basis, vec = {}, collections.defaultdict(dict)  # vec[col][row]
        col0 = 0
        while i < len(L) and 'JJ COUPLING' not in L[i] and 'EIGENVALUES' not in L[i]:
            l = L[i]
            mh = re.match(r'^\s+(\d+)\s+(\S.*)$', l)
            mr = re.match(r'^\s*(\d+):(\S+)\s+\(([^)]*)\)\s*(\S+)\s+(\d+)((?:\s+-?\d\.\d+)+)\s*$', l)
            if mr:
                cfg, conf, par, term, idx, coefs = mr.groups()
                idx = int(idx); basis[idx] = (int(cfg), conf, term)
                for k, c in enumerate(coefs.split()):
                    vec[col0 + k][idx] = float(c)
            elif mh and re.match(r'^\s+\d+\s+(\S+\s+)+$', l + ' ') and not re.search(r'\(', l) and 'PURITY' not in l:
                col0 = (int(mh.group(1)) - 1) * 11  # column group header: group number g covers columns 11(g-1)+1 ...
            i += 1
        n = len(ev)
        blocks.append(dict(J=J, ev=ev, cno=cno, basis=[basis[k] for k in sorted(basis)], vec=[vec[c] for c in range(n)]))
    return blocks

def dominant(block, col):
    v = block['vec'][col]
    idx = max(v, key=lambda r: abs(v[r]))
    return idx, v[idx] ** 2  # basis index (1-based), squared component

def outgine_sections(path):
    L = open(path, encoding='latin-1').read().split('\n')
    secs, cur = [], []
    for l in L:
        if l.strip() == '-1':
            secs.append(cur); cur = []
        else:
            cur.append(l)
    return secs
