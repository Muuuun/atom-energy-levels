# Atom energy-level diagram site — handoff notes

Site: https://muuuun.github.io/atom-energy-levels/ · Repo: https://github.com/Muuuun/atom-energy-levels (gh account `Muuuun`,
GitHub Pages from `docs/` on `main`). This folder is its own git repo, nested inside the untracked home-directory repo.
The owner reads Chinese; reply in Chinese and spell out abbreviations.

**Remaining work: see `PLAN.md` (written 2026-10-02) and follow it.**

## The owner's rules

- Numbers must be experimental or NIST wherever possible. Priority for every value:
  measurement (`data/literature/<El>.json`) > NIST ASD > high-accuracy theory from the literature > ARC model potential.
- Every literature value carries its citation and URL; every value carries a tier (`exp`, `nist`, `theory`, `semi`, `hfr`, `model`).
  On diagrams `*` marks theory and `≈` a model or semi-empirical value. Never present a calculated or derived number as measured.
- Semi-empirical rates (owner's decision 2026-10-07): Kurucz's Cowan-code line lists (`semi.py`; `python3 semi.py fetch` caches
  `gf<ZZ00>.pos` of 37 neutral atoms in `data/semi/`, git-ignored except `index.json` with URL and file date) fill a rate only where
  neither a measurement nor NIST gives one: for a drawn line (label and card then show ≈, source cites Kurucz 2011 and the file)
  and for the decay lines of the cycling analysis, so a leak becomes an estimate instead of a lower limit. Tier `semi`, ranked below
  `theory` and above `model`; it never replaces a NIST or literature rate, and lifetimes are not taken from Kurucz (25 % too short on
  average). Checked against NIST (14 elements): median offset < 0.1 dex, within a factor 2 for 80-100 % of NIST class A/B lines,
  60-80 % of C/D, 40-60 % of E; a weak line with strong cancellation can be off by a factor 10. Matching: energy within 0.5 cm^-1,
  same J, opposite parity; a level that fits two NIST levels is skipped. Not covered: Cu, Ag, Au, Cd, Hg, In, Cs, lanthanides, Hf-Pt,
  actinides (DREAM at Mons has neutral tables only for La I and Lu I, with mixed measured / calculated values: not used).
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
    python3 semi.py fetch                 # cache Kurucz semi-empirical line lists (data/semi, 88 MB, git-ignored)
    python3 compute.py all|curated|auto|<key>...   # -> data/<key>/atom.json, levels.csv, transitions.csv, validation.txt
    python3 plot.py    all|curated|auto|<key>...   # -> docs/<slug>/diagram.svg|pdf, preview.png, data.json
    python3 build_site.py                 # -> docs/index.html (periodic table), docs/<slug>/index.html, sitemap.xml
    python3 stats.py                      # -> data/provenance.md
    ./publish.sh "commit message" key1 key2 ...    # compute + plot + build + stats + commit + push

- `species.py`: 39 isotope pages, 27 curated (`kind="alkali"` uses ARC so every E1-allowed pair gets a matrix element;
  `kind="nist"` is NIST + literature). Every other element gets an automatic entry (`auto=True`, key = lowercase symbol,
  slug = element name): strongest classified NIST lines 1 nm – 2 µm, plus annotated literature lines.
- `_iso()` in `species.py` (added 2026-10-06: Er 166/167/168, Cr 52/53, Tm 169, Hg 199/201/202, Cd 111/113/114): isotope page
  of an automatically drawn element, same lines as the element page it replaces, hyperfine constants and measured
  frequencies of that isotope. `build_site.py` writes a forwarding page at `docs/<element>/` for every element that has
  only isotope pages (target: `PRIMARY`). Hg-199 has no hyperfine table: no measured constant could be opened (`Hg.json`).
- Isotope pages of one element are linked by the switch under the page title (`isotope_switch()` in `build_site.py`:
  mass number, boson / fermion from the neutron number, nuclear spin); the header no longer lists every isotope.
- `cycling.py` (added 2026-10-06): closed-transition analysis, called at the end of both builders in `compute.py`; writes
  `t["cyc"]` on every drawn E1 line. "closed" = no other level below the upper level with opposite parity and |ΔJ| ≤ 1 in the
  NIST level list (needs no rate); otherwise leak per scattered photon = 1 − branching ratio when the line's own ratio is in
  the literature file, else the sum over the other decay lines (drawn lines, undrawn NIST lines, literature lines beyond
  2 µm, Kurucz semi-empirical lines where nothing else gives a rate, for alkalis the full ARC set), flagged as a lower limit while a
  reachable level has no rate. Shown in the transition
  card (`cycleCard` in `viewer.js`), in the "Closed and nearly closed transitions" table (`cycling_section` in
  `build_site.py`, page only, not in the figure) and in the last columns of `transitions.csv`. These numbers are derived:
  their tag reads "from measured data" etc., never "measured". Fine structure only (no hyperfine / Zeeman dark states).
  While a line is pinned, `decayArrows()` in `viewer.js` draws the decay channels of its upper level as wavy arrows
  (spontaneous emission) labelled with their share, in the SVG group `#decay`: next to the straight arrow of a drawn line,
  bar to bar for a line that is not drawn; sizes follow the zoom so the shares stay readable in the full view. Pinned only,
  never on hover. `enlarge()` does the same for the label of the pinned line and the captions of its levels (a `transform`
  on `trl-i`, `lvn-k`, `lvd-k`, class `grown`): about 12 px on screen in the full view, back to the drawn size once zoomed in.
  Enlarging every label of the figure is not possible (they would overlap), and the fonts of the figure itself were not changed.
  Cascade (added 2026-10-06, owner's request): the decays are followed down to the ground level or to a level that no
  electric-dipole decay can leave ("long-lived"; a forbidden line of such a level is not followed). `cycling.py` writes
  `l["decay"]` on every drawn short-lived level (its decay lines as shares, normalised to at most 1) and `cyc["end"]` on every
  line (where the atom ends up, followed through levels that are not drawn too; `end_lost` = share the listed rates do not
  cover). `cascade(i)` in `viewer.js` turns this into the arrows (those of later steps in the group class `next`, at most 24,
  a share that has no room is hidden until the view is zoomed in) and into the card tables "Further decays" and "Where the
  atom ends up". The arrows of the pinned line's own upper level still come from `cyc` (leak = what the card states).
- `elements.py`: periodic-table layout. `atomlib.py`: NIST download/parsing, conversions, naming.
- `docs/assets/viewer.js`, `style.css`: hover-to-preview, click-to-pin, zoom/pan, filter by transition type.
  A pinned card changes on clicks only (diagram, rows and level names in the card, Back, ×, Esc); hovering changes only the
  emphasis in the diagram (`pinned` / `hover` / `rowHover`, classes `hl` strong and `sf` soft). Keep it that way.
  SVG ids: `tr-i` arrow, `trl-i` label, `hit-i` hover target, `lv-k` / `lvn-k` / `lvd-k` level.
  Picking a level (2026-10-07, owner's request: the bars are about 1 px thick in the full view): `target()` takes the nearest
  level within 8 screen px (16 for touch) of its bar or caption (`levelNear()`, `zones`), also over the lines that end there;
  a line label keeps its ground beyond 3 px, a short line the middle 30 % of its length. `frames()` draws a frame (`rect.lvbox`)
  around the level the pointer would pick (`.hov`) and around the pinned level (`.pin`). Hover follows `pointermove`.
  The list of lines in a level card is sorted by a click on a column head (`SORTS`, `lineTable()`: other level, wavelength,
  matrix element, Einstein A; second click reverses; lines without the value stay last); the order is kept from card to card.
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
owner (Bing / IndexNow was notified on 2026-10-02; the key file is in `docs/`). Search Console ownership was verified on
2026-10-06 (URL-prefix property) through `docs/google94bc483eee0b4f32.html`: never remove that file.

## Status (2026-10-07)

- Kurucz semi-empirical rates added (see the owner's rules). Of the 7407 drawn E1 lines the cycling analysis classed 1709 as
  "open" and 3397 as a lower limit before; now 1348 and 1720. Pages of the 37 Kurucz elements: 2553 complete, 273 lower limits,
  16 open (reachable levels Kurucz did not compute). 176 drawn lines without any rate got a ≈ matrix element (Tc 58, Zn 37).

- Infrared decay channels (2026-10-07): `atomlib.nist_lines_ir()` caches the NIST lines from 2 µm to 1 mm
  (`<El>_I_lines_2000nm_to_1000000nm.tsv`, fetched by `fetch_all.py`); `compute.py` feeds the cycling analysis every NIST line from
  1 nm to 1 mm whatever range a page draws (curated pages used to start at 200 nm). Hydrogen and helium gained most.
- This site's own Cowan-code fits (owner's decision 2026-10-07): tier `hfr` ("HFR fit (this site)", ≈), ranked below `semi`
  (Kurucz) and above `model`; used only where nothing else gives a rate, lines with |cancellation factor| < 0.05 left out
  (`semi.cowan_rates()`, `data/cowan/<El>_lines.csv` + `index.json`, source string names the date and `cowan/<El>`). Done for
  12 elements: Hg, Cd, In, Ga, Tl, Cu, Ag, Au, Sn, Pb, Xe, Kr (`cowan/README.md`: how the NIST Cowan package was built on this
  Mac, the pipeline `cowan/run_element.py` with a two-stage fit, the accuracy table: 50-100 % of the NIST-rated lines within x2
  after the cut, strong lines within 1.5). A further element needs a configuration list in `run_element.py` and a look at
  `<El>/LEVELS1` and `fit_assignment.txt` before publishing. The compiled programs live outside the repo (scratchpad of
  2026-10-07); rebuilding takes 10 minutes with the README.

## Known limitations

- NIST lists some unresolved fine-structure doublets at one energy (B, O, Zn, Al, Be): levels are identified by their index in
  the NIST list and lines are matched with J, never by energy alone; the diagram draws one bar with a caption naming both J.

- Literature values were checked for format, level matching and unit convention, not value-by-value against the papers;
  subagent-reported doubts are in each file's `conflicts` / `notes`.
- NIST energies refer to the natural isotope mixture; minority-isotope wavelengths are off by the isotope shift unless a
  measured frequency exists.
- `docs/robots.txt` is not at the domain root, so crawlers ignore it; the sitemap must be submitted in Google Search
  Console by the owner.
