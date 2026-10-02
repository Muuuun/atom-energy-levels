#!/usr/bin/env python3
"""Draw the large-format level diagram of a species from data/<key>/atom.json.

    python3 plot.py rb87 cs133      # or: python3 plot.py all

Writes docs/<slug>/diagram.svg (element ids for the interactive page), diagram.pdf, preview.png, data.json.
"""
import json
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle

import atomlib as al
from species import SPECIES

DOCS = os.path.join(al.HERE, "docs")
plt.rcParams.update({"font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans", "pdf.fonttype": 42,
                     "axes.linewidth": 1.2, "svg.hashsalt": "atoms"})
INK, MUTED = "#1a1a1a", "#5b5b5b"
FS = 9.6          # arrow-label font size
HW_FRAC = 0.27    # half-width of a level bar, in units of its column width
HEAD_IN = 2.5


def wavelength_color(lam):
    """Approximate perceived colour of a vacuum wavelength; UV and IR get purple / maroon-to-brown ramps."""
    if lam < 380:
        t = np.clip((lam - 290) / 90, 0, 1)
        return (0.38 + 0.12 * t, 0.10 + 0.05 * t, 0.55 + 0.20 * t)
    if lam > 750:
        t = np.clip((lam - 750) / 1250, 0, 1)
        a, b = np.array([0.62, 0.05, 0.08]), np.array([0.33, 0.27, 0.24])
        return tuple(a + (b - a) * t ** 0.7)
    if lam < 440:
        r, g, b = 0.45 - 0.45 * (lam - 380) / 60, 0.0, 1.0
    elif lam < 490:
        r, g, b = 0.0, (lam - 440) / 50, 1.0
    elif lam < 510:
        r, g, b = 0.0, 1.0, -(lam - 510) / 20
    elif lam < 580:
        r, g, b = (lam - 510) / 70, 1.0, 0.0
    elif lam < 645:
        r, g, b = 1.0, -(lam - 645) / 65, 0.0
    else:
        r, g, b = 1.0, 0.0, 0.0
    lum = 0.30 * r + 0.59 * g + 0.11 * b
    k = min(1.0, 0.45 / max(lum, 1e-6))  # darken so greens and yellows stay readable on white
    return (r * k, g * k, b * k)


def fmt_tau(ns):
    if ns < 1e3:
        return f"{ns:.3g} ns"
    if ns < 1e6:
        return f"{ns / 1e3:.3g} µs"
    if ns < 1e9:
        return f"{ns / 1e6:.3g} ms"
    return f"{ns / 1e9:.3g} s"


def fmt_d(t):
    d = t.get("d")
    if d is None:
        return None
    s = f"{d:.3f}" if 0.1 <= d < 10 else f"{d:.2f}" if d >= 10 else f"{d:.4f}"
    if t.get("uncertain"):
        return "~" + s
    return {"model": "≈" + s, "theory": s + "*"}.get(t.get("d_tier"), s)


def text_len(s):
    """Rough rendered length of a mathtext string, in characters."""
    s = re.sub(r"\\[a-zA-Z]+", "x", s)
    return len(re.sub(r"[\$\{\}\^_\\]", "", s))


class EnergyScale:
    """Monotone map energy -> plot height. Manual: list of (start energy, stretch). Auto: blend of a
    linear axis with rank equalisation, so crowded regions get room without reordering anything."""

    def __init__(self, spec, energies, top, rydberg_zone):
        e = np.unique(np.round(np.asarray(energies, dtype=float), 0))
        if spec == "auto":
            y = 0.35 * e / e[-1] + 0.65 * np.arange(len(e)) / max(1, len(e) - 1)
            self.E, self.Y = list(e), list(y)
            if top > e[-1]:
                self.E.append(top)
                self.Y.append(y[-1] + (0.20 if rydberg_zone else 0.04))
        else:
            brk = [(0.0, 1.0 if spec[0][0] > 0 else spec[0][1])]
            brk = [(0.0, spec[0][1])] + [(spec[i][0], 1.0 if i == 0 else spec[i][1]) for i in range(len(spec))]
            # spec = [(E1, s_below), (E2, s_above)]: slope s_below under E1, 1 between, s_above over E2
            self.E, self.Y = [0.0, spec[0][0], spec[1][0], top], [0.0]
            self.Y.append(spec[0][0] * spec[0][1])
            self.Y.append(self.Y[-1] + spec[1][0] - spec[0][0])
            self.Y.append(self.Y[-1] + (top - spec[1][0]) * spec[1][1])
        self.E, self.Y = np.array(self.E), np.array(self.Y) / self.Y[-1]

    def __call__(self, e):
        return np.interp(e, self.E, self.Y)


class LabelPlacer:
    """Greedy placement of rotated labels along their arrows, avoiding everything placed so far."""

    def __init__(self):
        self.obst = np.empty((0, 3))  # x, y, radius in points

    def _discs(self, c, ang, length, height):
        n = max(2, int(np.ceil(length / (height * 0.9))))
        ts = np.linspace(-0.5, 0.5, n) * max(length - height, 1)
        return np.column_stack([c[0] + ts * np.cos(ang), c[1] + ts * np.sin(ang), np.full(n, height * 0.62)])

    def block(self, c, ang, length, height):
        self.obst = np.vstack([self.obst, self._discs(c, ang, length, height)])

    def place(self, p0, p1, length, height, ts):
        ang = np.arctan2(p1[1] - p0[1], p1[0] - p0[0])
        best = None
        for rank, t in enumerate(ts):
            discs = self._discs(p0 + (p1 - p0) * t, ang, length, height)
            dx = discs[:, None, 0] - self.obst[None, :, 0]
            dy = discs[:, None, 1] - self.obst[None, :, 1]
            cost = float(np.clip(discs[:, None, 2] + self.obst[None, :, 2] - np.hypot(dx, dy), 0, None).sum()) + 0.01 * rank
            if best is None or cost < best[0]:
                best = (cost, t, discs)
            if cost < 0.05:
                break
        self.obst = np.vstack([self.obst, best[2]])
        return best[1], np.degrees(ang)


def attach_points(pos, arrows):
    """Spread arrow ends along each bar: each arrow uses the half of the bar facing its partner,
    the steepest one nearest the bar centre, so fans do not cross."""
    ends = {}
    for i, (a, b) in enumerate(arrows):
        (x0, y0, _), (x1, y1, _) = pos[a], pos[b]
        side = 1 if x1 >= x0 else -1
        steep = (y1 - y0) / max(abs(x1 - x0), 0.15)
        ends.setdefault((a, side), []).append((steep, i, "lo"))
        ends.setdefault((b, -side), []).append((steep, i, "up"))
    xy = {}
    for (st, side), lst in ends.items():
        lst.sort(reverse=True)
        slots = np.linspace(0.10, 0.96, len(lst)) if len(lst) > 1 else [0.5]
        for slot, (_, i, role) in zip(slots, lst):
            xy[(i, role)] = pos[st][0] + side * slot * pos[st][2]
    return xy


def table_layout(tables, width_in, fs=13.5):
    """Flow the tables left to right, wrapping into rows. Returns placements and the strip height (inches)."""
    char = fs * 0.56 / 72
    row_h = fs * 1.75 / 72
    placed, x, y, row_height = [], 0.0, 0.0, 0.0
    for tb in tables:
        if not tb["rows"]:
            continue
        ncol = len(tb["header"])
        widths = [max([text_len(tb["header"][k])] + [text_len(r[k]) for r in tb["rows"]]) * char + 0.32 for k in range(ncol)]
        total = max(sum(widths), text_len(tb["title"]) * char * 1.3)
        note_lines = tb.get("note", "").count("\n") + 1 if tb.get("note") else 0
        height = row_h * (len(tb["rows"]) + 2.9) + note_lines * fs * 1.25 / 72 + 0.25
        if x > 0 and x + total > width_in:
            x, y, row_height = 0.0, y + row_height + 0.45, 0.0
        placed.append(dict(tb=tb, x=x, y=y, widths=widths, row_h=row_h, total=total))
        x += total + 0.7
        row_height = max(row_height, height)
    return placed, y + row_height, fs


def draw_table(ax, p, fs):
    """ax spans the table strip with data coordinates in inches, y downwards."""
    tb, x, y, widths, row_h = p["tb"], p["x"], p["y"], p["widths"], p["row_h"]
    aligns = [{"l": "left", "r": "right"}[a] for a in tb["aligns"]]
    total = sum(widths)
    xs = np.concatenate([[0], np.cumsum(widths)])
    ax.text(x, y, tb["title"], fontsize=fs + 4, fontweight="bold", color=INK, va="top", ha="left")
    y += row_h * 1.75
    ax.add_patch(Rectangle((x, y - row_h * 0.5), total, row_h, fc="#e6e3dc", ec="none", zorder=0))
    cell = lambda k: x + xs[k] + 0.10 if aligns[k] == "left" else x + xs[k + 1] - 0.10
    for k, h in enumerate(tb["header"]):
        ax.text(cell(k), y, h, fontsize=fs, fontweight="bold", color=INK, va="center", ha=aligns[k])
    for r, row in enumerate(tb["rows"]):
        y += row_h
        if r % 2 == 1:
            ax.add_patch(Rectangle((x, y - row_h * 0.5), total, row_h, fc="#f4f2ee", ec="none", zorder=0))
        for k, c in enumerate(row):
            ax.text(cell(k), y, c, fontsize=fs, color=INK, va="center", ha=aligns[k])
    ax.plot([x, x + total], [y + row_h * 0.5] * 2, color=INK, lw=0.8)
    if tb.get("note"):
        ax.text(x, y + row_h * 0.75, tb["note"], fontsize=fs - 1, color=MUTED, va="top", ha="left", linespacing=1.35)


def draw(key):
    with open(os.path.join(al.DATA, key, "atom.json")) as f:
        atom = json.load(f)
    meta, cols, levels, trans = atom["meta"], atom["columns"], atom["levels"], atom["transitions"]
    alkali = meta["kind"] == "alkali"
    bound = [t for t in trans if t["kind"] != "rydberg"]
    ryd = [t for t in trans if t["kind"] == "rydberg"]

    # ---- geometry
    DIAG_IN = max(22.5, 0.5 * len(levels) + 5.0)
    units = sum(c["width"] for c in cols)
    unit_in = float(np.clip(38.0 / units, 3.7, 6.2))
    left_pad, right_pad = 0.75, 0.25
    fig_w = (units + left_pad + right_pad) * unit_in + 1.9
    placed, tab_h, tab_fs = table_layout(atom["tables"], fig_w - 2.2)
    fig_h = HEAD_IN + DIAG_IN + tab_h + 1.1
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([1.7 / fig_w, (tab_h + 0.9) / fig_h, 1 - 1.9 / fig_w, DIAG_IN / fig_h])
    tax = fig.add_axes([1.7 / fig_w, 0.35 / fig_h, 1 - 1.9 / fig_w, tab_h / fig_h])
    hax = fig.add_axes([1.7 / fig_w, 1 - (HEAD_IN + 0.1) / fig_h, 1 - 1.9 / fig_w, HEAD_IN / fig_h])
    for a in (tax, hax):
        a.set_axis_off()
    strip_w = fig_w - 1.9
    tax.set_xlim(0, strip_w)
    tax.set_ylim(tab_h, 0)
    hax.set_xlim(0, strip_w)
    hax.set_ylim(HEAD_IN, 0)

    x_edge = np.concatenate([[0], np.cumsum([c["width"] for c in cols])])
    for k, c in enumerate(cols):
        c["x"], c["hw"] = (x_edge[k] + x_edge[k + 1]) / 2, HW_FRAC * c["width"]
    limit = meta["limit_cm"]
    e_top_level = max(l["E"] for l in levels)
    has_ryd = bool(atom["rydberg_levels"])
    scale = EnergyScale(meta["scale"], [l["E"] for l in levels], limit if has_ryd else e_top_level * 1.0001, has_ryd)
    Y = scale
    head = 0.085 if any(c["group"] for c in cols) else 0.055
    ax.set_xlim(-left_pad, units + right_pad)
    ax.set_ylim(-0.012, 1 + head + (0.02 if has_ryd else 0.035))
    for s in ("top", "right", "bottom"):
        ax.spines[s].set_visible(False)
    ax.set_xticks([])
    upp = (ax.get_ylim()[1] - ax.get_ylim()[0]) / (DIAG_IN * 72)  # y units per point

    # ---- energy axis: round-number ticks, thinned where the scale is compressed
    e_max = limit if has_ryd else e_top_level
    majors, last = [], -1e9
    for e in np.arange(0, e_max + 1, 500):
        y = float(Y(e))
        if (y - last) / upp >= 26 and (e % 1000 == 0 or (y - last) / upp >= 60):
            majors.append(e)
            last = y
    minors, last = [], -1e9
    for e in np.arange(0, e_max + 1, 100):
        y = float(Y(e))
        if (y - last) / upp >= 5:
            minors.append(e)
            last = y
    ax.set_yticks([float(Y(e)) for e in majors])
    ax.set_yticklabels([f"{int(e):,}".replace(",", " ") for e in majors], fontsize=15)
    ax.set_yticks([float(Y(e)) for e in minors], minor=True)
    ax.tick_params(axis="y", which="major", length=9, width=1.2)
    ax.tick_params(axis="y", which="minor", length=4, width=0.8)
    ax.set_ylabel(r"Energy above the ground state  (cm$^{-1}$)   —   non-uniform scale", fontsize=19, labelpad=12)

    # ---- column headers
    y_head = 1 + head
    k = 0
    while k < len(cols):
        g = cols[k]["group"]
        if g is None:
            ax.text(cols[k]["x"], y_head, f"${cols[k]['header']}$", fontsize=32, ha="center", va="top", color=INK)
            k += 1
            continue
        m = k
        while m + 1 < len(cols) and cols[m + 1]["group"] == g:
            m += 1
        xc = (cols[k]["x"] + cols[m]["x"]) / 2
        ax.text(xc, y_head, f"${g}$", fontsize=30, ha="center", va="top", color=INK)
        if m > k:
            ax.plot([cols[k]["x"] - cols[k]["hw"], cols[m]["x"] + cols[m]["hw"]], [y_head - 46 * upp] * 2, color=INK, lw=1.0)
        for c in cols[k:m + 1]:
            ax.text(c["x"], y_head - 52 * upp, f"${c['header']}$", fontsize=15, ha="center", va="top", color=MUTED)
        k = m + 1

    # ---- Rydberg series and ionisation limit
    if has_ryd:
        ax.axhspan(float(Y(limit - (limit - e_top_level) * 0.18)), 1.0, color="#efece6", zorder=0, lw=0)
        ax.axhline(1.0, color=INK, lw=1.6, ls=(0, (6, 3)), zorder=1)
        ax.text(units + right_pad - 0.02, 1.0 + 4 * upp, meta["limit_text"], fontsize=16, ha="right", va="bottom", color=INK)
        for r in atom["rydberg_levels"]:
            c, n = cols[r["col"]], r["n"]
            ax.plot([c["x"] - c["hw"], c["x"] + c["hw"]], [Y(r["E"])] * 2, color=INK, lw=1.0 if n <= 20 else 0.6,
                    alpha=float(np.clip(1.25 - n / 40, 0.25, 0.9)), zorder=2, solid_capstyle="butt")
            if n in (11, 12, 13, 14, 15, 17, 20, 25, 30, 40):
                ax.text(c["x"] + c["hw"] + 0.02, float(Y(r["E"])), f"{n}", fontsize=9.5, color=MUTED, va="center", ha="left")
        ax.text(-left_pad + 0.02, float(Y(limit - (limit - e_top_level) * 0.3)), meta["rydberg_note"].replace(" (", "\n("),
                fontsize=12, color=MUTED, va="center", ha="left", linespacing=1.3)

    # ---- levels
    fig.canvas.draw()
    to_pt = lambda x, y: ax.transData.transform((x, y)) * 72.0 / fig.dpi
    col_pt = to_pt(1, 0)[0] - to_pt(0, 0)[0]
    placer = LabelPlacer()
    pos = {}
    for L in levels:
        c = cols[L["col"]]
        pos[L["id"]] = (c["x"], float(Y(L["E"])), c["hw"])
    has_out = {t["lower"] for t in trans}
    name_fs = 19 if alkali else 14.5
    cap = dict(color=INK, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85))
    sub = dict(fontsize=10.5, color=MUTED, linespacing=1.25, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85))
    for L in levels:
        x, y, hw = pos[L["id"]]
        k = L["id"]
        ax.plot([x - hw, x + hw], [y, y], color=INK, lw=3.4, zorder=6, solid_capstyle="butt", gid=f"lv-{k}")
        placer.block(to_pt(x, y), 0.0, 2 * hw * col_pt, 9)
        tier = L.get("tau_tier")
        if tier == "stable":
            tau = "stable"
        elif L.get("tau_ns") is None:
            tau = ""
        else:
            tau = (r"$\tau$ ≈ " if tier == "model" else rf"$\tau$ {L['tau_bound']} " if L.get("tau_bound") else r"$\tau$ = ") + fmt_tau(L["tau_ns"]) + ("*" if tier == "theory" else "")
        energy = f"{L['E']:.3f} cm$^{{-1}}$"
        name = f"${L['name']}$"
        if alkali and k in has_out:
            # arrows leave upwards from the bar, so the caption sits beside it
            left = L["col"] == 0
            sgn, ha = (-1, "right") if left else (1, "left")
            xt = x + sgn * (hw + 0.035)
            ax.text(xt, y, name, fontsize=name_fs, ha=ha, va="center", zorder=8, gid=f"lvn-{k}", **cap)
            ax.text(xt + sgn * 0.175, y, f"{energy}\n{tau}", ha=ha, va="center", zorder=8, gid=f"lvd-{k}", **sub)
            placer.block(to_pt(xt + sgn * 0.19, y), 0.0, 135, 30)
        elif alkali:
            yc = y + 6 * upp
            ax.text(x - 0.085, yc, name, fontsize=name_fs, ha="right", va="bottom", zorder=8, gid=f"lvn-{k}", **cap)
            ax.text(x - 0.065, yc + 3 * upp, f"{energy}    {tau}", ha="left", va="bottom", zorder=8, gid=f"lvd-{k}", **sub)
            placer.block(to_pt(x + 0.03, y) + np.array([0, 17]), 0.0, 190, 22)
        else:
            # fine-structure components NIST lists at one energy share a bar: one caption naming every J
            twins = [M for M in levels if M["col"] == L["col"] and M["E"] == L["E"]]
            if twins[0] is not L:
                continue
            if len(twins) > 1 and re.search(r"_\{[^{}]*\}$", L["name"]):
                name = "$" + re.sub(r"_\{[^{}]*\}$", "_{" + ",\\,".join(al.jstr(M["J"]) for M in twins) + "}", L["name"]) + "$"
            # one line above the bar; where arrows leave the bar it is drawn under them
            z = 3.5 if k in has_out else 8
            detail = f"{energy}   {tau}".rstrip()
            w_name, w_det = text_len(L["name"]) * name_fs * 0.56, text_len(detail) * 10.5 * 0.56
            x_l = x - (w_name + 8 + w_det) / 2 / col_pt
            ax.text(x_l + w_name / col_pt, y + 5 * upp, name, fontsize=name_fs, ha="right", va="bottom", zorder=z, gid=f"lvn-{k}", **cap)
            ax.text(x_l + (w_name + 8) / col_pt, y + 7 * upp, detail, ha="left", va="bottom", zorder=z, gid=f"lvd-{k}", **sub)
            if k not in has_out:
                placer.block(to_pt(x, y) + np.array([0, 14]), 0.0, w_name + 8 + w_det, 18)

    # ---- transitions between drawn levels
    arrows = [(t["lower"], t["upper"]) for t in bound]
    att = attach_points(pos, arrows)
    a_log = [np.log10(t["A"]) if t.get("A") else None for t in bound]
    order = sorted(range(len(bound)), key=lambda i: pos[bound[i]["upper"]][1] - pos[bound[i]["lower"]][1])
    web = [None] * len(trans)
    for i in order:
        t = bound[i]
        col = wavelength_color(t["lam"])
        x0, x1 = att[(i, "lo")], att[(i, "up")]
        y0, y1 = pos[t["lower"]][1], pos[t["upper"]][1]
        lw = float(np.interp(a_log[i], [4.0, 7.6], [0.9, 3.4])) if a_log[i] is not None else 1.1
        ls = (0, (1.2, 1.6)) if t["kind"] == "forbidden" else "-"
        # wide, almost invisible line: the hover target of the web page
        ax.plot([x0, x1], [y0, y1], lw=9, color=col, alpha=0.004, zorder=5, solid_capstyle="butt", gid=f"hit-{i}")
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), gid=f"tr-{i}", arrowstyle="-|>,head_length=5.5,head_width=2.4", shrinkA=0,
                                     shrinkB=1.5, mutation_scale=1.7, lw=lw, ls=ls, color=col, alpha=0.88, zorder=4, capstyle="butt"))
        d = fmt_d(t)
        text = f"{t['lam']:.3f} nm" + (f"  |  {d} $ea_0$" if d else "")
        p0, p1 = to_pt(x0, y0), to_pt(x1, y1)
        seg = np.hypot(*(p1 - p0))
        length = 0.66 * FS * (len(text) - (7 if d else 0))
        margin = min(0.45, (length / 2 + 14) / max(seg, 1))
        ts = [u for u in np.arange(0.88, 0.10, -0.02) if margin <= u <= 1 - margin] or [0.5]
        u, ang = placer.place(p0, p1, length, FS * 1.25, ts)
        ang = ang - 180 if ang > 90 else ang
        ax.text(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, text, fontsize=FS, color=col, rotation=ang, rotation_mode="anchor",
                ha="center", va="center", zorder=7, fontweight="bold", gid=f"trl-{i}", bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.9))

    # ---- excitation into the Rydberg series (dashed)
    slots = {}
    y_r = float(Y(limit - (limit - e_top_level) * 0.065)) if has_ryd else 1.0
    for kr, t in enumerate(ryd):
        i = len(bound) + kr
        c = cols[t["upper_col"]]
        n_here = slots.get(t["upper_col"], 0)
        slots[t["upper_col"]] = n_here + 1
        x0l, y0, _ = pos[t["lower"]]
        side = 1 if c["x"] > x0l else -1
        x0, x1 = x0l + side * 0.03, c["x"] - side * (0.22 - 0.11 * n_here)
        col = wavelength_color(t["lam"])
        ax.plot([x0, x1], [y0, y_r], lw=9, alpha=0.004, zorder=5, solid_capstyle="butt", gid=f"hit-{i}")
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y_r), gid=f"tr-{i}", arrowstyle="-|>,head_length=5.5,head_width=2.4", shrinkA=0,
                                     shrinkB=0, mutation_scale=1.7, lw=1.5, ls=(0, (5, 2.5)), color=col, alpha=0.9, zorder=3))
        text = f"${levels[t['lower']]['name']}$ → ${t['upper_name']}$   {t['lam']:.3f} nm  |  {fmt_d(t)} $ea_0$"
        p0, p1 = to_pt(x0, y0), to_pt(x1, y_r)
        u, ang = placer.place(p0, p1, 0.66 * FS * 36, FS * 1.25, list(np.arange(0.80, 0.25, -0.03)))
        ang = ang - 180 if ang > 90 else ang
        ax.text(x0 + (x1 - x0) * u, y0 + (y_r - y0) * u, text, fontsize=FS, color=col, rotation=ang, rotation_mode="anchor",
                ha="center", va="center", zorder=7, fontweight="bold", gid=f"trl-{i}", bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.9))

    # ---- header strip: title, reading guide, colour key
    iso = rf"$^{{{meta['A']}}}${meta['symbol']}" if meta["A"] else meta["symbol"]
    spin = f",  nuclear spin $I$ = {meta['I']}" if meta["A"] else ""
    hax.text(0, 0.05, f"{meta['element']}-{meta['A']}" if meta["A"] else meta["element"], fontsize=58, fontweight="bold", color=INK, va="top", ha="left")
    n_d = sum(1 for t in bound if t.get("d") is not None)
    hax.text(0, 1.25, f"{iso}  ({meta['spectrum']}){spin}.   "
             + ("Classified transitions below 2 µm (levels and lines from the literature):  " if (meta.get("lit_levels") or 0) > len(atom["levels"]) / 2
                else "Strongest classified transitions below 2 µm (NIST):  " if meta.get("auto") else "Energy levels and transitions below 2 µm:  ")
             + f"{len(levels)} levels, {len(bound)} lines.", fontsize=21, color=INK, va="top", ha="left")
    if not has_ryd:
        hax.text(0, 1.78, meta["limit_text"], fontsize=15, color=MUTED, va="top", ha="left")
    guide = ("Arrow label:  vacuum wavelength  |  reduced dipole matrix element  " r"$|\langle J\,\Vert\,e r\,\Vert\,J'\rangle|$  in $e a_0$" "\n"
             "Matrix elements are measured or NIST values;   *  = high-accuracy theory,   ≈  = model calculation.\n"
             r"Arrow width grows with the Einstein coefficient $A$.   Dotted: forbidden (clock, M1, E2).   Dashed: Rydberg excitation, $n$ = 70." "\n"
             + meta["guide_tau"])
    gx = max(strip_w * 0.36, 13.5)
    hax.text(gx, 0.12, guide, fontsize=14.5, color=INK, va="top", ha="left", linespacing=1.6)
    kx0, kx1 = max(strip_w - 9.5, gx + 13.4), strip_w - 0.3
    if kx1 - kx0 > 4:
        fpos = lambda lam: kx0 + (np.log(lam) - np.log(290)) / np.log(2000 / 290) * (kx1 - kx0)
        grid = np.linspace(290, 2000, 500)
        for a, b in zip(grid[:-1], grid[1:]):
            hax.add_patch(Rectangle((fpos(a), 0.75), (fpos(b) - fpos(a)) * 1.03, 0.28, fc=wavelength_color((a + b) / 2), ec="none"))
        for lam_t in (300, 400, 500, 600, 700, 800, 1000, 1200, 1500, 2000):
            hax.plot([fpos(lam_t)] * 2, [1.03, 1.11], color=INK, lw=1.0)
            hax.text(fpos(lam_t), 1.15, f"{lam_t}", fontsize=13, ha="center", va="top", color=INK)
        hax.text(kx0, 0.64, "Arrow colour  =  vacuum wavelength (nm)", fontsize=14.5, ha="left", va="bottom", color=INK)

    for p in placed:
        draw_table(tax, p, tab_fs)

    # ---- outputs
    out = os.path.join(DOCS, meta["slug"])
    os.makedirs(out, exist_ok=True)
    fig.savefig(os.path.join(out, "diagram.svg"))
    fig.savefig(os.path.join(out, "diagram.pdf"))
    fig.savefig(os.path.join(out, "preview.png"), dpi=1800 / fig_w)
    plt.close(fig)
    keep_l = ("id", "E", "J", "name", "plain", "parity", "g", "tau_ns", "tau_bound", "tau_unc", "tau_tier", "tau_src", "hfs", "conf", "term", "E_nist", "E_tier", "E_src")
    with open(os.path.join(out, "data.json"), "w") as f:
        json.dump(dict(meta={k: meta.get(k) for k in ("slug", "element", "symbol", "A", "I", "limit_cm", "spectrum", "auto")},
                       sources=atom.get("sources", {}),
                       levels=[dict({k: l[k] for k in keep_l if k in l}, html=al.tex_to_html(l["name"])) for l in levels],
                       transitions=[dict(t, upper_html=al.tex_to_html(t["upper_name"])) if "upper_name" in t else t for t in bound + ryd]),
                  f, ensure_ascii=False)
    print(f"{key}: {fig_w:.0f} x {fig_h:.0f} in, {len(levels)} levels, {len(bound)} + {len(ryd)} lines -> docs/{meta['slug']}/")


if __name__ == "__main__":
    groups = {"all": list(SPECIES), "auto": [k for k, c in SPECIES.items() if c.get("auto")],
              "curated": [k for k, c in SPECIES.items() if not c.get("auto")]}
    keys = [k for arg in (sys.argv[1:] or ["all"]) for k in groups.get(arg, [arg])]
    for k in keys:
        if os.path.exists(os.path.join(al.DATA, k, "atom.json")):
            draw(k)
