"""Put the least-squares parameter values (PARVALS, 'FOR RCG INPUT' cards) into the RCG deck: python3 parvals_to_ing11.py ING11 PARVALS ING11.out"""
import sys, re
ing, par, out = sys.argv[1:4]
P = open(par, encoding='latin-1').read().split('\n')
cards = {}  # configuration label (cols 1-18) -> [card lines]
i = 0
while i < len(P):
    if 'FOR RCG INPUT' in P[i]:
        i += 1
        while i < len(P) and P[i].strip() and 'PARAMETER VALUES' not in P[i]:
            l = P[i]
            if re.match(r'^\S+ I\s+\S+\s+-?\d+\.\d+', l):  # "Hg I  conf   values": single-configuration card (the header line has names, not numbers)
                key = l[:18].rstrip(); cards[key] = [l]
                i += 1
                while i < len(P) and P[i].startswith(' ') and re.match(r'^\s+-?\d', P[i]):  # continuation card
                    cards[key].append(P[i]); i += 1
                continue
            i += 1
    else:
        i += 1
I = open(ing, encoding='latin-1').read().split('\n')
res, k, nrep = [], 0, 0
while k < len(I):
    l = I[k]
    key = l[:18].rstrip()
    if key in cards and re.match(r'^\S+ I\s+\S+\s+\d+\s', l[:22]):  # original single-configuration card: label, number of parameters
        n = int(l[18:20])
        res += cards[key]; nrep += 1
        k += 1
        while k < len(I) and I[k].startswith('    ') and not re.match(r'^\S', I[k]) and re.match(r'^\s+-?[\d.]', I[k]):  # skip its continuation cards
            k += 1
        continue
    res.append(l); k += 1
open(out, 'w').write('\n'.join(res))
print(f'{nrep} configuration cards replaced')
