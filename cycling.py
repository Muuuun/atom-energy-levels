#!/usr/bin/env python3
"""Closed (cycling) transition analysis: does the upper level of a line decay back to the level it was excited from?

For a drawn electric-dipole line lower -> upper, the decay lines of the upper level (drawn lines, further NIST and
literature lines, for the alkalis the complete ARC set) are compared with the levels an electric-dipole decay can reach
at all: lower energy, opposite parity, |dJ| <= 1, not J = 0 -> 0.

    closed   no other level can be reached: the line is closed for electric-dipole decay (needs no rate at all)
    leak     the other decay lines take a known share: leak per scattered photon, photons scattered before a leak = 1 / leak
    open     other levels can be reached, but no rate is known for them

The decays are then followed further (cascade): a level that an electric-dipole decay can leave is short-lived, and
its own decay lines are followed in turn, down to the ground level or to a level no electric-dipole decay can leave
(long-lived).  Every drawn level gets its decay lines as shares (l["decay"]), every line the levels the atom ends in
(cyc["end"]).

Every number here is derived, never measured as such: it carries the weakest tier of its inputs, and it is a lower
limit ("bound") whenever a reachable level has no listed rate.  Fine-structure levels only: hyperfine and Zeeman dark
states, and forbidden decays without a listed rate, are not looked at.
"""
RANK = {"exp": 0, "nist": 1, "theory": 2, "model": 3}
MAX_CHANNELS, MAX_OPEN, MAX_END = 8, 5, 6


def sig(x, n=3):
    return float(f"{x:.{n}g}")


def worst(tiers):
    known = [t for t in tiers if t in RANK]
    return max(known, key=RANK.get) if known else None


def e1_allowed(a, b):
    """Parity and J rules of an electric-dipole line (no LS rule: intercombination lines do occur)."""
    return a["parity"] != b["parity"] and abs(a["J"] - b["J"]) <= 1 and a["J"] + b["J"] > 0


def annotate(levels, transitions, pool, pid, extra, html):
    """Add t["cyc"] to every drawn electric-dipole line.

    pool   every known level of the atom in order of energy: dicts with E, J, parity
    pid    {id of a drawn level: its index in pool}
    extra  decay lines that are not drawn: dicts with upper, lower (pool indices), A and / or br, tier
    html   pool index -> level name as HTML (for levels that are not drawn)
    """
    drawn = {k: i for i, k in pid.items()}
    below = {}

    def reach(k):
        """Pool indices an electric-dipole decay of level k can end on."""
        if k not in below:
            below[k] = [m for m in range(k) if pool[m]["E"] < pool[k]["E"] and e1_allowed(pool[m], pool[k])]
        return below[k]

    def ref(k, ku):
        return dict(dict(lv=drawn[k]) if k in drawn else dict(html=html(k)), lam=sig(1e7 / (pool[ku]["E"] - pool[k]["E"]), 5))

    chans = {}  # pool index of the upper level -> its decay lines
    for t in transitions:
        if "upper" in t:
            chans.setdefault(pid[t["upper"]], []).append(dict(to=pid[t["lower"]], A=t.get("A"), br=t.get("br"), quoted=bool(t.get("br_src")),
                                                         tier=t.get("br_tier") or t.get("A_tier"), t=t))
    for x in extra:
        chans.setdefault(x["upper"], []).append(dict(to=x["lower"], A=x.get("A"), br=x.get("br"), quoted=x.get("br") is not None,
                                                     tier=x.get("tier")))
    for ku, cs in chans.items():
        U = levels[drawn[ku]] if ku in drawn else {}  # a level that is not drawn has no lifetime on record here
        tau = U["tau_ns"] * 1e-9 if U.get("tau_ns") and not U.get("tau_bound") else None
        sum_A = sum(c["A"] for c in cs if c["A"])
        for c in cs:  # share of the upper level's decays: stored branching ratio, rate x lifetime, or share of the listed rates
            if c["br"] is not None:
                c["f"] = c["br"]
            elif c["A"]:
                c["f"] = min(1.0, c["A"] * tau) if tau else c["A"] / sum_A
            else:
                c["f"] = None
            if tau and not c["quoted"]:
                c["tier"] = worst([c["tier"], U.get("tau_tier")])
        for c in cs:
            t = c.get("t")
            if not t or t["kind"] != "E1":
                continue
            kl, f = c["to"], c["f"]
            rated = sorted([o for o in cs if o["to"] != kl and o["f"]], key=lambda o: -o["f"])
            unrated = [m for m in reach(ku) if m != kl and m not in {o["to"] for o in rated}]
            cyc = dict(lower="ground" if kl == 0 else "decays" if reach(kl) else "metastable")
            if c["quoted"] and f is not None and f < 1:
                # the branching ratio of the line itself is on record: everything else is the leak
                cyc.update(cls="leak", leak=sig(1 - f), bound=False, basis="direct", tier=c["tier"])
                if rated:  # the listed decay lines, for comparison (a measured leak and calculated lines need not agree)
                    cyc.update(ch_sum=sig(sum(o["f"] for o in rated)), ch_tier=worst([o["tier"] for o in rated]))
            elif rated and (tau or f is not None):
                leak = sum(o["f"] for o in rated)
                cyc.update(cls="leak", leak=sig(leak / max(1.0, leak + (f or 0))), bound=bool(unrated), basis="lifetime" if tau else "rates",
                           tier=worst([o["tier"] for o in rated] + ([] if tau else [c["tier"]])))
            elif not rated and not unrated:
                cyc["cls"] = "closed"
            else:
                cyc.update(cls="open", n_open=len(unrated) + len(rated))
                unrated = sorted(unrated + [o["to"] for o in rated])
            if cyc["cls"] == "leak":
                cyc["n"] = sig(1 / cyc["leak"])
                cyc["ch"] = [dict(ref(o["to"], ku), f=sig(o["f"]), tier=o["tier"], dark=not reach(o["to"])) for o in rated[:MAX_CHANNELS]]
                if len(rated) > MAX_CHANNELS:
                    cyc["more"] = len(rated) - MAX_CHANNELS
                if unrated:
                    cyc["n_open"] = len(unrated)
            if unrated:  # lowest levels first: the largest transition energy
                cyc["open"] = [ref(m, ku) for m in unrated[:MAX_OPEN]]
            t["cyc"] = cyc

    # ---- cascade: the decay lines of every level as shares of its decays, followed down to the levels that keep the atom
    share = {}
    for ku, cs in chans.items():
        rated = sorted([c for c in cs if c["f"]], key=lambda c: -c["f"])
        total = max(1.0, sum(c["f"] for c in rated))  # rate x lifetime may add up to slightly more than 1
        if rated and reach(ku):  # a level without electric-dipole decay keeps the atom, whatever forbidden line it has
            share[ku] = [(c["to"], c["f"] / total, c["tier"]) for c in rated]
    for ku, ch in share.items():
        if ku in drawn:
            d = dict(ch=[dict(ref(to, ku), f=sig(f), tier=tier, dark=not reach(to)) for to, f, tier in ch[:MAX_CHANNELS]])
            if len(ch) > MAX_CHANNELS:
                d["more"] = len(ch) - MAX_CHANNELS
            levels[drawn[ku]]["decay"] = d
    ended = {}

    def end(ku):
        """Where an atom in level ku finally is: [(pool index, share, tier)], and the share the listed rates do not cover."""
        if ku not in ended:
            pend, out, lost = {ku: [1.0, None]}, [], 0.0
            while pend:
                k = max(pend, key=lambda m: (pool[m]["E"], m))  # highest level first: everything that feeds a level is in by then
                p, tier = pend.pop(k)
                if k not in share:
                    out.append((k, p, tier))
                    continue
                for to, f, tr in share[k]:
                    q = pend.setdefault(to, [0.0, None])
                    q[0], q[1] = q[0] + p * f, worst([q[1], tier, tr])
                lost += p * (1 - sum(f for _, f, _ in share[k]))
            ended[ku] = sorted(out, key=lambda o: -o[1]), lost
        return ended[ku]

    for t in transitions:
        cyc = t.get("cyc")
        if not cyc or cyc["cls"] == "open":
            continue
        ku = pid[t["upper"]]
        out, lost = end(ku) if ku in share else ([(pid[t["lower"]], 1.0, None)], 0.0)
        cyc["end"] = [dict(dict(lv=drawn[k]) if k in drawn else dict(html=html(k)), p=sig(p) if p < 0.99 else round(p, 10), tier=tier,
                           at="ground" if k == 0 else "open" if reach(k) else "dark") for k, p, tier in out[:MAX_END]]
        if len(out) > MAX_END:
            cyc["end_more"] = sig(sum(p for _, p, _ in out[MAX_END:]))
        if lost > 1e-9:
            cyc["end_lost"] = sig(lost)
