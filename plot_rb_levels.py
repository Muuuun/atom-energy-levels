#!/usr/bin/env python3
"""Large-format Rb I energy-level (Grotrian) diagram with every E1 line below 2 um.

Reads the tables written by compute_rb_levels.py and writes
figures/rb_energy_levels.pdf (vector) and figures/rb_energy_levels.png.
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIGS = os.path.join(HERE, "figures")
DOCS = os.path.join(HERE, "docs")
os.makedirs(FIGS, exist_ok=True)
os.makedirs(DOCS, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans",
    "pdf.fonttype": 42, "axes.linewidth": 1.2,
})

LIMIT = 33690.81
# piecewise-linear energy axis: (start energy, stretch factor)
E1, S1 = 18500.0, 0.42   # below E1 only 5S and 5P live -> compressed
E2, S3 = 32000.0, 4.2    # above E2 the Rydberg series converge -> stretched

COLS = {(0, 0.5): 0, (1, 0.5): 1, (1, 1.5): 2, (2, 1.5): 3, (2, 2.5): 4, (3, 2.5): 5, (3, 3.5): 6}
COL_NAMES = [r"$^2S_{1/2}$", r"$^2P_{1/2}$", r"$^2P_{3/2}$", r"$^2D_{3/2}$", r"$^2D_{5/2}$", r"$^2F_{5/2}$", r"$^2F_{7/2}$"]
HW = 0.27  # half-width of a level bar, in column units
INK = "#1a1a1a"
MUTED = "#5b5b5b"


def Y(e):
    e = np.asarray(e, dtype=float)
    return np.where(e < E1, e * S1, np.where(e < E2, E1 * S1 + (e - E1), E1 * S1 + (E2 - E1) + (e - E2) * S3))


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
    # darken so that greens and yellows stay readable on white
    lum = 0.30 * r + 0.59 * g + 0.11 * b
    k = min(1.0, 0.45 / max(lum, 1e-6))
    return (r * k, g * k, b * k)


def state_tex(s):
    """'6P3/2' -> '$6P_{3/2}$'"""
    i = next(k for k, c in enumerate(s) if c.isalpha())
    return rf"${s[:i + 1]}_{{{s[i + 1:]}}}$"


def fmt_tau(ns):
    return f"{ns:.1f} ns" if ns < 1000 else f"{ns / 1000:.2f} µs"


def fmt_d(d):
    return f"{d:.3f}" if d < 10 else f"{d:.2f}"


class LabelPlacer:
    """Greedy placement of rotated labels along their arrows, avoiding everything placed so far."""

    def __init__(self, ax):
        self.ax = ax
        self.obst = np.empty((0, 3))  # x, y, radius in display points

    def _discs(self, c, ang, length, height):
        n = max(2, int(np.ceil(length / (height * 0.9))))
        ts = np.linspace(-0.5, 0.5, n) * (length - height)
        d = np.array([np.cos(ang), np.sin(ang)])
        return np.column_stack([c[0] + ts * d[0], c[1] + ts * d[1], np.full(n, height * 0.62)])

    def clash(self, discs):
        if not len(self.obst):
            return 0.0
        dx = discs[:, None, 0] - self.obst[None, :, 0]
        dy = discs[:, None, 1] - self.obst[None, :, 1]
        over = discs[:, None, 2] + self.obst[None, :, 2] - np.hypot(dx, dy)
        return float(np.clip(over, 0, None).sum())

    def block(self, c, ang, length, height):
        self.obst = np.vstack([self.obst, self._discs(c, ang, length, height)])

    def place(self, p0, p1, length, height, ts):
        ang = np.arctan2(p1[1] - p0[1], p1[0] - p0[0])
        best = None
        for rank, t in enumerate(ts):
            c = p0 + (p1 - p0) * t
            discs = self._discs(c, ang, length, height)
            cost = self.clash(discs) + 0.01 * rank
            if best is None or cost < best[0]:
                best = (cost, t, discs)
            if cost < 0.05:
                break
        self.obst = np.vstack([self.obst, best[2]])
        return best[1], np.degrees(ang)


def attach_points(levels, arrows):
    """Spread the arrow ends along each level bar so that fans do not cross.

    Arrows leave/arrive on the half of the bar that faces the partner column; within that
    half the steepest arrow sits nearest the bar centre.
    """
    ends = {}  # (state, side, role) -> list of (slope, arrow index)
    for i, (lo, up) in enumerate(arrows):
        x0, y0 = levels[lo]["x"], levels[lo]["y"]
        x1, y1 = levels[up]["x"], levels[up]["y"]
        side = 1 if x1 > x0 else -1
        steep = (y1 - y0) / abs(x1 - x0)
        ends.setdefault((lo, side), []).append((steep, i, "lo"))
        ends.setdefault((up, -side), []).append((steep, i, "up"))
    xy = {}
    for (st, side), lst in ends.items():
        lst.sort(reverse=True)
        slots = np.linspace(0.10, 0.96, len(lst)) if len(lst) > 1 else [0.5]
        for slot, (_, i, role) in zip(slots, lst):
            xy[(i, role)] = levels[st]["x"] + side * slot * HW
    return xy


class ax_frac:
    """Lets draw_table() write into an axes in axes-fraction coordinates."""

    def __init__(self, ax):
        self.ax = ax

    def text(self, *a, **k):
        return self.ax.text(*a, transform=self.ax.transAxes, **k)

    def plot(self, *a, **k):
        return self.ax.plot(*a, transform=self.ax.transAxes, **k)

    def add_patch(self, p):
        p.set_transform(self.ax.transAxes)
        return self.ax.add_patch(p)


def draw_table(ax, x, y, title, header, rows, widths, row_h, fs=12, aligns=None, note=None):
    """Plain text table in axes-fraction coordinates; x, y is the top-left corner."""
    aligns = aligns or ["left"] * len(header)
    total = sum(widths)
    ax.text(x, y, title, fontsize=fs + 4, fontweight="bold", color=INK, va="top", ha="left")
    y -= row_h * 1.55
    ax.add_patch(Rectangle((x, y - row_h * 0.5), total, row_h, fc="#e6e3dc", ec="none", zorder=0))
    xs = np.concatenate([[0], np.cumsum(widths)])
    pad = 0.004 * total / 0.4
    for k, h in enumerate(header):
        xx = x + xs[k] + pad if aligns[k] == "left" else x + xs[k + 1] - pad
        ax.text(xx, y, h, fontsize=fs, fontweight="bold", color=INK, va="center", ha=aligns[k])
    for r, row in enumerate(rows):
        y -= row_h
        if r % 2 == 1:
            ax.add_patch(Rectangle((x, y - row_h * 0.5), total, row_h, fc="#f4f2ee", ec="none", zorder=0))
        for k, cell in enumerate(row):
            xx = x + xs[k] + pad if aligns[k] == "left" else x + xs[k + 1] - pad
            ax.text(xx, y, cell, fontsize=fs, color=INK, va="center", ha=aligns[k])
    ax.plot([x, x + total], [y - row_h * 0.5] * 2, color=INK, lw=0.8)
    if note:
        ax.text(x, y - row_h * 0.75, note, fontsize=fs - 1, color=MUTED, va="top", ha="left", linespacing=1.35)


def main():
    lev = pd.read_csv(os.path.join(DATA, "levels.csv"))
    tr = pd.read_csv(os.path.join(DATA, "transitions.csv"))
    ryd = pd.read_csv(os.path.join(DATA, "rydberg_series.csv"))
    rlev = pd.read_csv(os.path.join(DATA, "rydberg_levels.csv"))
    hfs = pd.read_csv(os.path.join(DATA, "hyperfine_87Rb.csv"))

    fig = plt.figure(figsize=(38, 32), facecolor="white")
    ax = fig.add_axes([0.045, 0.252, 0.945, 0.738])
    tax = fig.add_axes([0.045, 0.008, 0.945, 0.228])
    tax.set_axis_off()
    tax.set_xlim(0, 1)
    tax.set_ylim(0, 1)

    y_top = float(Y(LIMIT)) + 1150
    ax.set_xlim(-0.72, 6.86)
    ax.set_ylim(-330, y_top)
    for s in ("top", "right", "bottom"):
        ax.spines[s].set_visible(False)
    ax.set_xticks([])

    # ---- energy axis: ticks on the true energies, positions through Y()
    major = list(range(0, 18001, 2000)) + list(range(19000, 32001, 1000)) + [32500, 33000, 33500]
    minor = list(range(0, 18500, 500)) + list(range(18500, 32000, 250)) + list(range(32000, 33700, 100))
    ax.set_yticks(Y(major))
    ax.set_yticklabels([f"{e:,}".replace(",", " ") for e in major], fontsize=15)
    ax.set_yticks(Y(minor), minor=True)
    ax.tick_params(axis="y", which="major", length=9, width=1.2)
    ax.tick_params(axis="y", which="minor", length=4, width=0.8)
    ax.set_ylabel(r"Energy above $5S_{1/2}$  (cm$^{-1}$)", fontsize=20, labelpad=12)
    for e, txt in ((E1, "axis scale changes here  (× 0.42 below)"), (E2, "axis scale changes here  (× 4.2 above)")):
        ax.axhline(Y(e), color="#b9b4aa", lw=0.9, ls=(0, (2, 4)), zorder=0)
        ax.text(-0.71, float(Y(e)) + 40, txt, fontsize=10, color=MUTED, va="bottom", ha="left", style="italic")

    for c, name in enumerate(COL_NAMES):
        ax.text(c, y_top - 80, name, fontsize=32, ha="center", va="top", color=INK)

    # ---- Rydberg series and ionisation limit
    ax.axhspan(float(Y(33300)), float(Y(LIMIT)), color="#efece6", zorder=0, lw=0)
    ax.axhline(Y(LIMIT), color=INK, lw=1.6, ls=(0, (6, 3)), zorder=1)
    ax.text(6.84, float(Y(LIMIT)) + 60,
            r"Rb$^+$ ($4p^6\,^1S_0$) ionisation limit   33 690.81 cm$^{-1}$  =  4.177 13 eV  =  1010.025 THz  (296.817 nm)",
            fontsize=16, ha="right", va="bottom", color=INK)
    for _, r in rlev.iterrows():
        c = COLS[(int(r.l), r.j)]
        n = int(r.n)
        if n > 60:
            continue
        e = r.E_pairinteraction_cm
        ax.plot([c - HW, c + HW], [Y(e)] * 2, color=INK, lw=1.0 if n <= 20 else 0.6,
                alpha=float(np.clip(1.25 - n / 40, 0.25, 0.9)), zorder=2, solid_capstyle="butt")
        if n in (11, 12, 13, 14, 15, 17, 20, 25, 30, 40):
            ax.text(c + HW + 0.02, float(Y(e)), f"{n}", fontsize=9.5, color=MUTED, va="center", ha="left")
    ax.text(-0.71, float(Y(33200)), "Rydberg series\n$n$ = 11 … 60 drawn\n(pairinteraction)", fontsize=12.5, color=MUTED, va="center", ha="left", linespacing=1.3)

    # ---- levels
    levels = {}
    for _, r in lev.iterrows():
        levels[r.state] = dict(x=COLS[(int(r.l), r.j)], y=float(Y(r.E_nist_cm)), E=r.E_nist_cm, row=r, k=len(levels))
    fig.canvas.draw()
    to_pt = lambda x, y: ax.transData.transform((x, y)) * 72.0 / fig.dpi
    placer = LabelPlacer(ax)
    upp = (ax.get_ylim()[1] - ax.get_ylim()[0]) / (ax.get_position().height * fig.get_figheight() * 72)  # y units per point
    ry_draw = [("5S1/2", "nP3/2"), ("5P1/2", "nS1/2"), ("5P1/2", "nD3/2"), ("5P3/2", "nS1/2"), ("5P3/2", "nD5/2"),
               ("6P1/2", "nS1/2"), ("6P1/2", "nD3/2"), ("6P3/2", "nS1/2"), ("6P3/2", "nD5/2"),
               ("5D5/2", "nP3/2"), ("5D5/2", "nF7/2")]
    has_outgoing = set(tr.lower) | {lo for lo, _ in ry_draw}

    for st, L in levels.items():
        r = L["row"]
        ax.plot([L["x"] - HW, L["x"] + HW], [L["y"]] * 2, color=INK, lw=3.4, zorder=6, solid_capstyle="butt", gid=f"lv-{L['k']}")
        left = L["x"] == 0
        xt = L["x"] - HW - 0.035 if left else L["x"] + HW + 0.035
        tau = "stable" if not np.isfinite(r.lifetime_ns_0K_arc) else r"$\tau$ = " + fmt_tau(r.lifetime_ns_0K_arc)
        detail = f"{r.E_nist_cm:.3f} cm$^{{-1}}$"
        cap = dict(color=INK, zorder=8, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85))
        sub = dict(fontsize=10.5, color=MUTED, zorder=8, linespacing=1.25, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85))
        placer.block(to_pt(L["x"], L["y"]), 0.0, 2 * HW * (to_pt(1, 0)[0] - to_pt(0, 0)[0]), 9)
        if st in has_outgoing:
            # arrows leave upwards from the bar, so the caption sits beside it
            ha = "right" if left else "left"
            sgn = -1 if left else 1
            ax.text(xt, L["y"], state_tex(st), fontsize=19, ha=ha, va="center", gid=f"lvn-{L['k']}", **cap)
            ax.text(xt + sgn * 0.175, L["y"], f"{detail}\n{tau}", ha=ha, va="center", gid=f"lvd-{L['k']}", **sub)
            placer.block(to_pt(xt + sgn * 0.19, L["y"]), 0.0, 135, 30)
        else:
            # nothing leaves this level: the space above the bar is free
            yc = L["y"] + 6 * upp
            ax.text(L["x"] - 0.085, yc, state_tex(st), fontsize=19, ha="right", va="bottom", gid=f"lvn-{L['k']}", **cap)
            ax.text(L["x"] - 0.065, yc + 3 * upp, f"{detail}    {tau}", ha="left", va="bottom", gid=f"lvd-{L['k']}", **sub)
            placer.block(to_pt(L["x"] + 0.03, L["y"]) + np.array([0, 17]), 0.0, 190, 22)

    # ---- bound-bound transitions
    arrows = list(zip(tr.lower, tr.upper))
    att = attach_points(levels, arrows)
    a_log = np.log10(tr.A_best_s.values)
    order = sorted(range(len(tr)), key=lambda i: levels[tr.upper[i]]["y"] - levels[tr.lower[i]]["y"])
    FS = 9.6
    for i in order:
        r = tr.iloc[i]
        col = wavelength_color(r.wavelength_vac_nm)
        x0, x1 = att[(i, "lo")], att[(i, "up")]
        y0, y1 = levels[r.lower]["y"], levels[r.upper]["y"]
        lw = float(np.interp(a_log[i], [4.0, 7.6], [0.9, 3.4]))
        # wide, almost invisible line: the hover target of the web page
        ax.plot([x0, x1], [y0, y1], lw=9, color=col, alpha=0.004, zorder=5, solid_capstyle="butt", gid=f"hit-{i}")
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), gid=f"tr-{i}", arrowstyle="-|>,head_length=5.5,head_width=2.4", shrinkA=0, shrinkB=1.5,
                                     mutation_scale=1.7, lw=lw, color=col, alpha=0.88, zorder=4, capstyle="butt"))
        text = f"{r.wavelength_vac_nm:.3f} nm  |  {fmt_d(r.rme_J_best_ea0)} $ea_0$"
        p0, p1 = to_pt(x0, y0), to_pt(x1, y1)
        seg = np.hypot(*(p1 - p0))
        length = 0.66 * FS * (len(text) - 7)
        margin = min(0.45, (length / 2 + 14) / seg)
        ts = [t for t in np.arange(0.88, 0.10, -0.02) if margin <= t <= 1 - margin] or [0.5]
        t, ang = placer.place(p0, p1, length, FS * 1.25, ts)
        if ang > 90:
            ang -= 180
        ax.text(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, text, fontsize=FS, color=col, rotation=ang, rotation_mode="anchor",
                ha="center", va="center", zorder=7, fontweight="bold", gid=f"trl-{i}",
                bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.9))

    # ---- transitions into the Rydberg series (dashed)
    y_r = float(Y(33560))
    ry_slots = {}
    web_ryd = []
    for kr, (lo, ser) in enumerate(ry_draw):
        i = len(tr) + kr
        r = ryd[(ryd.lower == lo) & (ryd.series == ser)].iloc[0]
        l2, j2 = "SPDF".index(ser[1]), eval(ser[2:])
        c = COLS[(l2, j2)]
        k = ry_slots.get(c, 0)
        ry_slots[c] = k + 1
        L = levels[lo]
        side = 1 if c > L["x"] else -1
        x0 = L["x"] + side * 0.03
        x1 = c - side * (0.22 - 0.11 * k)
        lam = r.n70_pairinteraction_nm
        col = wavelength_color(lam)
        ax.plot([x0, x1], [L["y"], y_r], lw=9, alpha=0.004, zorder=5, solid_capstyle="butt", gid=f"hit-{i}")
        ax.add_patch(FancyArrowPatch((x0, L["y"]), (x1, y_r), gid=f"tr-{i}", arrowstyle="-|>,head_length=5.5,head_width=2.4", shrinkA=0, shrinkB=0,
                                     mutation_scale=1.7, lw=1.5, ls=(0, (5, 2.5)), color=col, alpha=0.9, zorder=3))
        d = r.rme_J_n70_pairinteraction_ea0
        approx = "~" if lo == "5S1/2" else ""  # pairinteraction and ARC differ by 2x on this one
        text = f"{state_tex(lo)} → 70{ser[1]}$_{{{ser[2:]}}}$   {lam:.3f} nm  |  {approx}{d:.4f} $ea_0$"
        p0, p1 = to_pt(x0, L["y"]), to_pt(x1, y_r)
        length = 0.66 * FS * 36
        ts = list(np.arange(0.80, 0.25, -0.03))
        t, ang = placer.place(p0, p1, length, FS * 1.25, ts)
        if ang > 90:
            ang -= 180
        ax.text(x0 + (x1 - x0) * t, L["y"] + (y_r - L["y"]) * t, text, fontsize=FS, color=col, rotation=ang, rotation_mode="anchor",
                ha="center", va="center", zorder=7, fontweight="bold", gid=f"trl-{i}", bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.9))
        web_ryd.append(dict(lower=lo, upper=f"70{ser[1:]}", lam=float(lam), freq=round(299792.458 / float(lam), 4),
                            d=float(d), d_arc=float(r.rme_J_n70_ea0), limit=float(r.series_limit_nm), rydberg=True))

    # ---- title, reading guide and colour key in the empty lower-right corner
    bx, by = 4.8, float(Y(E1)) - 40 * upp
    ax.text(bx, by, "Rubidium  (Rb I)", fontsize=58, fontweight="bold", color=INK, va="top", ha="left")
    ax.text(bx, by - 84 * upp, "Energy levels and electric-dipole\ntransitions below 2 µm", fontsize=27, color=INK, va="top", ha="left", linespacing=1.25)
    guide = (
        "Arrow label:  vacuum wavelength  |  reduced dipole matrix element\n"
        r"                      $|\langle J\,\Vert\,e r\,\Vert\,J'\rangle|$  in units of  $e a_0$" "\n"
        r"Arrow width grows with the Einstein coefficient $A$ (log scale)." "\n"
        "Dashed arrows:  excitation into the Rydberg series, labelled for $n$ = 70.\n"
        r"Level caption:  NIST energy and radiative lifetime $\tau$ at 0 K (ARC)." "\n"
        f"{len(lev)} levels, {len(tr)} lines.  Every number is tabulated in  data/transitions.csv."
    )
    ax.text(bx, by - 172 * upp, guide, fontsize=14.5, color=INK, va="top", ha="left", linespacing=1.6)

    # wavelength colour key
    lam_axis = np.linspace(290, 2000, 600)
    x_l, x_r = bx, 6.75
    yb0 = by - 372 * upp
    yb1 = yb0 + 20 * upp
    fpos = lambda lam: x_l + (np.log(lam) - np.log(290)) / np.log(2000 / 290) * (x_r - x_l)
    for a, b in zip(lam_axis[:-1], lam_axis[1:]):
        ax.add_patch(Rectangle((fpos(a), yb0), (fpos(b) - fpos(a)) * 1.03, yb1 - yb0, fc=wavelength_color((a + b) / 2), ec="none", zorder=2))
    for lam_t in (300, 400, 500, 600, 700, 800, 1000, 1200, 1500, 2000):
        ax.plot([fpos(lam_t)] * 2, [yb0 - 6 * upp, yb0], color=INK, lw=1.0)
        ax.text(fpos(lam_t), yb0 - 9 * upp, f"{lam_t}", fontsize=13, ha="center", va="top", color=INK)
    ax.text(x_l, yb1 + 7 * upp, "Arrow colour  =  vacuum wavelength (nm)", fontsize=14.5, ha="left", va="bottom", color=INK)

    # ---- tables
    d2 = lambda lo, up: tr[(tr.lower == lo) & (tr.upper == up)].iloc[0]
    key = [("5S1/2", "5P3/2", "D2: MOT, imaging, Rydberg lower leg"), ("5S1/2", "5P1/2", "D1: optical pumping, Λ / gray-molasses cooling"),
           ("5S1/2", "6P3/2", "blue leg of 420 + 1013 Rydberg excitation"), ("5S1/2", "6P1/2", "blue leg (421 + 1005)"),
           ("5P3/2", "5D5/2", "780 + 776 ladder; 5S–5D two-photon at 778.1 nm"), ("5P1/2", "5D3/2", "795 + 762 ladder"),
           ("5P3/2", "4D5/2", "telecom C-band ladder"), ("5P3/2", "4D3/2", "telecom C-band ladder"),
           ("5P1/2", "4D3/2", "telecom S-band ladder"), ("5P3/2", "6S1/2", "telecom E-band ladder"),
           ("5P1/2", "6S1/2", "telecom O-band ladder"), ("5P3/2", "6D5/2", "red ladder"),
           ("5P3/2", "7S1/2", "ladder to 7S"), ("6S1/2", "7P3/2", "O-band, from 6S"),
           ("4D5/2", "4F7/2", "strongest line of the diagram"), ("6P3/2", "7D5/2", "telecom C-band, from 6P"),
           ("6P3/2", "8S1/2", "longest 6P line below 2 µm")]
    rows = []
    for lo, up, use in key:
        r = d2(lo, up)
        rows.append([f"{state_tex(lo)} – {state_tex(up)}", f"{r.wavelength_vac_nm:.4f}", f"{r.wavelength_air_nm:.4f}", f"{r.frequency_THz:.4f}",
                     f"{r.wavenumber_cm:.3f}", fmt_d(r.rme_J_best_ea0), f"{r.A_best_s:.3e}", f"{r.upper_linewidth_MHz:.3f}",
                     f"{r.branching_from_upper * 100:.1f}", use])
    draw_table(tax, 0.0, 0.99, "Key transitions",
               ["Transition", "λ vac (nm)", "λ air (nm)", "ν (THz)", "ν̃ (cm⁻¹)", "|⟨J‖er‖J′⟩| (ea₀)", "A (s⁻¹)", "Γ/2π up. (MHz)", "branch (%)", "Typical use"],
               rows, [0.06, 0.045, 0.045, 0.043, 0.046, 0.062, 0.046, 0.056, 0.042, 0.15], 0.0445, fs=13.5,
               aligns=["left"] + ["right"] * 8 + ["left"],
               note="λ and ν from NIST level energies (centre of gravity, no hyperfine structure); λ air uses standard air (Ciddor).  A: NIST-compiled value where available, otherwise ARC.\n"
                    "Γ/2π: natural linewidth of the upper level, 1/(2πτ).  Branch: share of the upper level's decays that takes this line.")

    order_lo = ["5S1/2", "5P1/2", "5P3/2", "4D5/2", "6S1/2", "6P1/2", "6P3/2", "5D5/2", "7S1/2", "4F7/2", "7P3/2"]
    rows = []
    for lo in order_lo:
        sub = ryd[ryd.lower == lo]
        for l2 in "SPDF":
            s2 = sub[sub.series.str[1] == l2]
            if not len(s2):
                continue
            r = s2.iloc[-1]  # highest J of the series
            rows.append([f"{state_tex(lo)} → $n{l2}_{{{r.series[2:]}}}$"] + [f"{r[f'n{n}_pairinteraction_nm']:.3f}" for n in (30, 40, 50, 70, 100)]
                        + [f"{r.series_limit_nm:.3f}", f"{r.rme_J_n70_pairinteraction_ea0:.4f}", f"{r.rme_J_n70_ea0:.4f}"])
    draw_table(tax, 0.622, 0.99, "Rydberg excitation wavelengths  (vacuum, nm)",
               ["Lower → series", "n = 30", "n = 40", "n = 50", "n = 70", "n = 100", "n → ∞", "d₇₀ pairint.", "d₇₀ ARC"],
               rows, [0.066, 0.037, 0.037, 0.037, 0.037, 0.037, 0.037, 0.046, 0.04], 0.0445, fs=13.5,
               aligns=["left"] + ["right"] * 8,
               note="Rydberg term energies from pairinteraction (quantum defects), lower level from NIST.\n"
                    "d₇₀ = |⟨J‖er‖J′⟩| to n = 70 in ea₀, from pairinteraction and from ARC.  The two disagree\n"
                    "by a factor ≈ 2 for 5S → nP (near-cancelling integral): treat that row as an order of magnitude.")

    rows = []
    for st in ["5S1/2", "5P1/2", "5P3/2", "4D3/2", "4D5/2", "6S1/2", "6P1/2", "6P3/2", "5D3/2", "5D5/2", "7S1/2", "7P1/2", "7P3/2"]:
        s = hfs[hfs.state == st]
        if not len(s):
            continue
        r = s.iloc[0]
        shifts = "   ".join(f"F={f}: {r[f'F{f}_shift_MHz']:+.2f}" for f in range(5) if pd.notna(r[f"F{f}_shift_MHz"]))
        rows.append([state_tex(st), f"{r.A_MHz:.3f}", f"{r.B_MHz:.3f}" if r.B_MHz else "–", shifts])
    # hyperfine table sits inside the main panel, under the 5P - 4D arrows
    x0f, y0f = ax.transAxes.inverted().transform(ax.transData.transform((3.0, float(Y(E1)) - 100 * upp)))
    x1f, _ = ax.transAxes.inverted().transform(ax.transData.transform((4.66, 0)))
    w = x1f - x0f
    draw_table(ax_frac(ax), x0f, y0f, r"$^{87}$Rb hyperfine structure  ($I$ = 3/2)",
               ["Level", "A (MHz)", "B (MHz)", "Shift of each F level from the centre of gravity (MHz)"],
               rows, [0.09 * w, 0.115 * w, 0.10 * w, 0.695 * w], 23.5 * upp / (ax.get_ylim()[1] - ax.get_ylim()[0]), fs=11,
               aligns=["left", "right", "right", "left"],
               note="A, B: magnetic-dipole and electric-quadrupole constants as compiled in ARC.")
    # ---- data for the interactive page
    web_tr = [dict(lower=r.lower, upper=r.upper, lam=r.wavelength_vac_nm, air=r.wavelength_air_nm, freq=r.frequency_THz,
                   wn=r.wavenumber_cm, d=r.rme_J_best_ea0, A=r.A_best_s, A_src=r.A_best_source, d_src=r.rme_source,
                   br=r.branching_from_upper, gamma=r.upper_linewidth_MHz) for r in tr.itertuples()]
    web_lv = [dict(name=st, E=L["E"], tau=None if not np.isfinite(L["row"].lifetime_ns_0K_arc) else L["row"].lifetime_ns_0K_arc)
              for st, L in levels.items()]
    with open(os.path.join(DOCS, "data.json"), "w") as f:
        json.dump(dict(transitions=web_tr + web_ryd, levels=web_lv), f)
    return fig


if __name__ == "__main__":
    fig = main()
    fig.savefig(os.path.join(FIGS, "rb_energy_levels.pdf"))
    fig.savefig(os.path.join(FIGS, "rb_energy_levels.png"), dpi=200)
    fig.savefig(os.path.join(DOCS, "rb_energy_levels.svg"))
    fig.savefig(os.path.join(DOCS, "rb_energy_levels.pdf"))
    print("saved figures/rb_energy_levels.pdf and .png")
