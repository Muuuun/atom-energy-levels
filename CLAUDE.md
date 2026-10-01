# Atom energy-level diagram site — handoff notes

Site: https://muuuun.github.io/atom-energy-levels/ · Repo: https://github.com/Muuuun/atom-energy-levels (gh account `Muuuun`,
GitHub Pages from `docs/` on `main`). This folder is its own git repo, nested inside the untracked home-directory repo.
The owner reads Chinese; reply in Chinese and spell out abbreviations.

## The owner's rules

- Numbers must be experimental or NIST wherever possible. Priority for every value:
  measurement (`data/literature/<El>.json`) > NIST ASD > high-accuracy theory from the literature > ARC model potential.
- Every literature value carries its citation and URL; every value carries a tier (`exp`, `nist`, `theory`, `model`).
  On diagrams `*` marks theory and `≈` a model value. Never present a calculated or derived number as measured.
- Each drawn transition is labelled with vacuum wavelength and reduced dipole matrix element |<J||er||J'>| (e·a0),
  convention A = ω³|d|²/(3πε₀ħc³(2J'+1)).

## Pipeline

    python3 fetch_all.py                  # cache NIST ASD tables for every neutral atom (data/nist)
    python3 compute.py all|curated|auto|<key>...   # -> data/<key>/atom.json, levels.csv, transitions.csv, validation.txt
    python3 plot.py    all|curated|auto|<key>...   # -> docs/<slug>/diagram.svg|pdf, preview.png, data.json
    python3 build_site.py                 # -> docs/index.html (periodic table), docs/<slug>/index.html, sitemap.xml
    python3 stats.py                      # -> data/provenance.md
    ./publish.sh "commit message" key1 key2 ...    # compute + plot + build + stats + commit + push

- `species.py`: 22 curated isotopes (`kind="alkali"` uses ARC so every E1-allowed pair gets a matrix element;
  `kind="nist"` is NIST + literature). Every other element gets an automatic entry (`auto=True`, key = lowercase symbol,
  slug = element name): strongest classified NIST lines 1 nm – 2 µm, plus annotated literature lines.
- `elements.py`: periodic-table layout. `atomlib.py`: NIST download/parsing, conversions, naming.
- `docs/assets/viewer.js`, `style.css`: hover-to-isolate, click-to-pin, zoom/pan, filter by transition type.
  SVG ids: `tr-i` arrow, `trl-i` label, `hit-i` hover target, `lv-k` / `lvn-k` / `lvd-k` level.
- Use system `/usr/bin/python3` (ARC 3.9.0, pairinteraction 2.3.1 — only Rb tables cached, cannot download others).
- zsh does not word-split variables: pass keys explicitly or use the `auto` / `curated` keywords.
- `publish.sh` does `git add -A`, so half-written literature files of running subagents get committed too (harmless).

## Literature files

Schema and conventions: `data/literature/SCHEMA.md` (read it before briefing a research subagent).
Matching is by NIST level energy plus `J` / `lower_J` / `upper_J`; isotope-specific frequencies in `frequency_THz`
(with `isotope`) or `frequency_THz_<A>`; a source string containing "not verified" makes the pipeline skip that frequency.
Briefs for research subagents must say: do the research yourself (no delegation), no e-mail or personal identifier in
requests, mark derived / second-hand values, list conflicts.

## Status (2026-10-01)

- 90 elements have a page; 65 have a literature file. Campaign log: `data/literature/QUEUE.md`.
- Not yet searched (31 elements, 7 groups): Sb Te Pb Bi | La Ce Pr | Nd Pm Sm | Gd Tb Lu | Hf Ta W | Re Os Ir Pt | Po At Rn Ac Th.
  Pr, Re, Os have NIST levels but no classified lines: ask the subagent for classified lines too (as done for Zr, Nb, Se).
- Thin files worth re-running: As Se Au Cu Ga C Cl Br I Ne Ar Kr Xe Zn Mo Er.
- Why the campaign stopped: a session can make at most 200 WebSearch calls, counted across the main conversation and
  every subagent (Claude Code docs, tools reference, "session search limit"). Resuming a session does not reset the count;
  a new session or `/clear` does. The owner can raise (not remove) the cap by setting the environment variable
  `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` before launching Claude Code. Do not change the owner's settings yourself.
  Spend the budget deliberately: few research subagents at a time, and tell each one the budget is shared.

## Decisions still owed by the owner

1. Keep, withdraw, or re-verify the lifetime tables that were read from "subscriber-only" tables embedded in public
   abstract pages (Tm, Ho, Dy; possibly Co, Ni).
2. Override NIST level energies with measured ones where they disagree (Fr 8S, 9P, 10P, 7D)?
3. Boron 249.75 nm isotope-shift sign (paper text contradicts its own absolute frequencies; stored as +5031.3 MHz).

## Known limitations

- Literature values were checked for format, level matching and unit convention, not value-by-value against the papers;
  subagent-reported doubts are in each file's `conflicts` / `notes`.
- NIST energies refer to the natural isotope mixture; minority-isotope wavelengths are off by the isotope shift unless a
  measured frequency exists.
- `docs/robots.txt` is not at the domain root, so crawlers ignore it; the sitemap must be submitted in Google Search
  Console by the owner.
