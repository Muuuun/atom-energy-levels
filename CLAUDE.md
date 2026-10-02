# Atom energy-level diagram site — handoff notes

Site: https://muuuun.github.io/atom-energy-levels/ · Repo: https://github.com/Muuuun/atom-energy-levels (gh account `Muuuun`,
GitHub Pages from `docs/` on `main`). This folder is its own git repo, nested inside the untracked home-directory repo.
The owner reads Chinese; reply in Chinese and spell out abbreviations.

**Remaining work: see `PLAN.md` (written 2026-10-02) and follow it.**

## The owner's rules

- Numbers must be experimental or NIST wherever possible. Priority for every value:
  measurement (`data/literature/<El>.json`) > NIST ASD > high-accuracy theory from the literature > ARC model potential.
- Every literature value carries its citation and URL; every value carries a tier (`exp`, `nist`, `theory`, `model`).
  On diagrams `*` marks theory and `≈` a model value. Never present a calculated or derived number as measured.
- Level energies (owner's decision, 2026-10-01): a direct measurement published within the last 20 years replaces the NIST
  energy (`Literature.energy` in `compute.py`, fields `measured_energy_cm` / `level_energy_measured`, `method: "experiment"`);
  older measurements leave NIST in place. A value from another isotope is used only where NIST is off by more than 2 cm^-1.
  The level keeps `E_nist`, and the page shows both. Apply the same age test before preferring any old measurement over NIST.
- Data read from publisher pages by an automated reader is kept, but must be verified against an independent printing
  (owner's decision, 2026-10-01); see `data/literature/verification_lifetimes_2026-10-01.md`.
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

## Status (2026-10-02)

- 99 elements (hydrogen to einsteinium) have a page and a literature file. Campaign log: `data/literature/QUEUE.md`.
- Pa U Np Pu Am Cm Bk Cf Es pages are built from `levels_not_in_nist` (Blaise & Wyart tables, archived web copy): NIST lists
  only their ground level. `meta.lit_levels` switches the page wording to "from the literature". Fm, No: owner decided not to add.
- Lifetime limits carry `tau_bound` ("<" / ">") and are shown as limits.
- Old measured rates (owner's decision 2026-10-02): where a measurement older than 20 years differs from the NIST rate of the
  same line, NIST is shown; `check_old_rates.py` lists candidates, `revert_old_rates.py` moves them to `A_s_older_measurement`.
- Papers the owner has to download for the 18 thin elements: `data/literature/待下载论文清单.md`; PDFs go in `data/literature/pdf/`.
- Round 4 (the last 31 elements) was searched on 2026-10-01; every element with NIST data now has a literature file.
- Round 5 (2026-10-01) re-ran the 16 thin files. Still thin: Se Ga Au Er Mo Br I Ar Xe and Nd Ce Te Gd Tb Ir Pt Rn Th.
  Their key papers are paywalled or bot-blocked (each file lists them under `not_found`); another web pass will not help,
  the owner has to supply the PDFs.
- Old measurements vs NIST: where a subagent brings measured A values older than 20 years for lines NIST already rates,
  keep NIST (see `A_s_older_measurement` in C.json).
- Research subagents sometimes store 1/sum(A) from NIST as a "lifetime": move such values out of `lifetime` (see Hf.json).
- Why the campaign stopped: a session can make at most 200 WebSearch calls, counted across the main conversation and
  every subagent (Claude Code docs, tools reference, "session search limit"). Resuming a session does not reset the count;
  a new session or `/clear` does. The owner can raise (not remove) the cap by setting the environment variable
  `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` before launching Claude Code. Do not change the owner's settings yourself.
  Spend the budget deliberately: few research subagents at a time, and tell each one the budget is shared.

## Decisions still owed by the owner

1. (Decided 2026-10-01: keep and verify. Decided: recent measured energies override NIST; Fr 8S, 8P3/2, 9P, 10P now measured,
   Fr 7D (measured 2000) stays NIST.)
2. Boron 249.75 nm isotope-shift sign (paper text contradicts its own absolute frequencies; stored as +5031.3 MHz).

## Known limitations

- NIST lists some unresolved fine-structure doublets at one energy (B, O, Zn, Al, Be): levels are identified by their index in
  the NIST list and lines are matched with J, never by energy alone; the diagram draws one bar with a caption naming both J.

- Literature values were checked for format, level matching and unit convention, not value-by-value against the papers;
  subagent-reported doubts are in each file's `conflicts` / `notes`.
- NIST energies refer to the natural isotope mixture; minority-isotope wavelengths are off by the isotope shift unless a
  measured frequency exists.
- `docs/robots.txt` is not at the domain root, so crawlers ignore it; the sitemap must be submitted in Google Search
  Console by the owner.
