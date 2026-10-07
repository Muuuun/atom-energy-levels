"""Parse the ELEC DIP SPECTRUM of an RCG OUTG11 (ISPECC=2: blocks per second-parity level) -> list of lines, and the eigenvalue lists."""
import re, sys

def parse(path):
    L = open(path, encoding='latin-1').read().split('\n')
    i0 = next(i for i, l in enumerate(L) if 'ELEC DIP SPECTRUM' in l and 'ENERGIES IN UNITS' in l)
    lines, up = [], None
    blk = re.compile(r'^\s*\* \* \*\s+(-?\d+\.\d+)\s+(\d+\.\d)\s+(\d+)\s+\(([^)]*)\)\s*(\S+)\s+(\d+)\s+(.*?)\s+\* \* \*')
    ln = re.compile(r'^\s*(\d+)\s+(-?\d+\.\d+)\s+(\d+\.\d)\s+(\d+)\s+\(([^)]*)\)\s*(\S+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\S+E[+-]\d+)\s+(-?\d\.\d+)')
    for l in L[i0:]:
        m = blk.match(l)
        if m:
            E, J, cfg, par, term, rank, label = m.groups()
            up = dict(E=float(E), J=float(J), cfg=int(cfg), term=term, rank=int(rank), label=label.replace('Hg I', '').strip())
            continue
        m = ln.match(l)
        if m and up:
            n, E, J, cfg, par, term, dE, lam, loggf, gA, cf = m.groups()
            lines.append(dict(up=up, lo=dict(E=float(E), J=float(J), cfg=int(cfg), term=term), dE=float(dE), lam=float(lam),
                              loggf=float(loggf), gA=float(gA), cf=float(cf)))
    return lines

if __name__ == '__main__':
    ls = parse(sys.argv[1]); print(len(ls), 'lines'); print(ls[0]); print(ls[-1])
