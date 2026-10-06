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
- `docs/assets/viewer.js`, `style.css`: hover-to-preview, click-to-pin, zoom/pan, filter by transition type.
  A pinned card changes on clicks only (diagram, rows and level names in the card, Back, ×, Esc); hovering changes only the
  emphasis in the diagram (`pinned` / `hover` / `rowHover`, classes `hl` strong and `sf` soft). Keep it that way.
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

## Status (2026-10-02, evening)

- All 118 cells of the periodic table open a page. 101 elements (hydrogen to einsteinium, fermium, nobelium) have a diagram
  page and a literature file; the 17 elements with no measured excited level (Md, Lr, Rf-Og) have a fact page (ground state,
  ionisation energy, calculated lines marked theory) built by `fact_pages()` in `build_site.py` from
  `data/literature/heaviest_elements.json`. Campaign log: `data/literature/QUEUE.md`.
- Pa-Es, Fm, No pages are built from `levels_not_in_nist`: NIST lists only their ground level. `meta.lit_levels` (most excited
  levels literature-only) switches the page wording to "from the literature". Fm and No are registered through `LIT_ONLY` in
  `species.py` (the owner reversed the earlier "do not add" decision on 2026-10-02).
- Lifetime limits carry `tau_bound` ("<" / ">"); calculated g factors carry `g_tier: "theory"` and are tagged on the page.
- Old measured rates (owner's decision 2026-10-02): where a measurement older than 20 years differs from the NIST rate of the
  same line, NIST is shown; `check_old_rates.py` lists candidates, `revert_old_rates.py` moves them to `A_s_older_measurement`.
- Round 6 (2026-10-02): an open-access hunt (repositories, theses, Wayback copies; no pirate sites) filled much of the 18 thin
  elements, each ingest re-read by a second agent. What is still closed is in `data/literature/待下载论文清单.md` (17 starred
  papers); only owner-supplied PDFs help now. PDFs live in `data/literature/pdf/` (git-ignored: never publish them).
- Useful routes found: Wayback copies of Optica abstract pages embed full tables; HAL serves PDFs to plain curl; OpenAlex and
  Semantic Scholar key-less quotas run out after a few hundred calls per day.
- Research subagents sometimes store 1/sum(A) from NIST as a "lifetime": move such values out of `lifetime` (see Hf.json).
  A second-hand lifetime with lifetime x sum(A_NIST) well above 1 is not shown (Xe 89860.015, Nd 21345.572).
- NIST attaches a few E1 lines to a level whose J forbids them (Nd 468.48 nm); `build_nist` moves such a line to the level
  within 1 cm^-1 that allows it, or drops it.
- The hyperfine isotope of an element page is chosen deterministically (abundance, number of levels, then heaviest).
- Web-search cap: a session can make at most 200 WebSearch calls, shared with every subagent; WebFetch / curl do not count.
  The owner can raise it with `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`. Do not change the owner's settings yourself.

## Decisions still owed by the owner

None. (Boron 249.75 nm isotope-shift sign: resolved 2026-10-02, Tables I and II of Maass et al. 2019 define nu(10B) - nu(11B)
and print it positive. Copper 4P3/2 lifetime: the direct 1968 measurement 318(16) ns is shown.)
Owner's decision 2026-10-02 (night): the elements whose papers stay closed are left as they are; do not run further
literature passes unless the owner supplies PDFs or asks. The sitemap still has to be submitted in Google Search Console by the
owner (Bing / IndexNow was notified on 2026-10-02; the key file is in `docs/`).

## Known limitations

- NIST lists some unresolved fine-structure doublets at one energy (B, O, Zn, Al, Be): levels are identified by their index in
  the NIST list and lines are matched with J, never by energy alone; the diagram draws one bar with a caption naming both J.

- Literature values were checked for format, level matching and unit convention, not value-by-value against the papers;
  subagent-reported doubts are in each file's `conflicts` / `notes`.
- NIST energies refer to the natural isotope mixture; minority-isotope wavelengths are off by the isotope shift unless a
  measured frequency exists.
- `docs/robots.txt` is not at the domain root, so crawlers ignore it; the sitemap must be submitted in Google Search
  Console by the owner.
