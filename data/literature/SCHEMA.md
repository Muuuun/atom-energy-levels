# Literature data file: `data/literature/<Element>.json`

One file per element. It supplements the NIST ASD tables in `data/nist/<El>_I_levels.tsv` and
`<El>_I_lines.tsv` with measured numbers NIST does not carry: lifetimes, hyperfine constants,
isotope shifts, precise frequencies, transition rates, branching ratios.

## Hard rules

1. Every number must be copied from a source you actually opened in this session (paper, arXiv HTML/PDF,
   NIST page, Steck-style reference sheet). Nothing from memory. If you cannot open a source that
   confirms a value, leave the value out and list it under `"not_found"`.
2. Each entry carries `source` (short citation: authors, journal, volume, page/article, year),
   `url` (the page you read it on) and `method`: `"experiment"`, `"theory"` or `"compilation"`
   (a review table quoting experiments counts as `"compilation"`; give the original reference in
   `source` when the review names it).
3. Prefer experiment over theory. Include a theory value only when no measurement exists, and mark it.
4. Keep the uncertainty as printed (`unc`, same unit as the value). Omit `unc` if none is given.
5. Levels are identified by their NIST energy in cm^-1 (`nist_energy_cm`, copy it from the NIST levels
   file, centre-of-gravity value) plus a human label. Transitions are identified by the NIST energies of
   both levels.

## Schema

```json
{
  "element": "Ba",
  "isotopes": {
    "137": {"I": "3/2", "abundance_percent": 11.23, "source": "...", "url": "..."},
    "138": {"I": "0", "abundance_percent": 71.70, "source": "...", "url": "..."}
  },
  "levels": [
    {
      "nist_energy_cm": 18060.261,
      "label": "6s6p 1P1",
      "lifetime": {"value": 8.36e-9, "unc": 0.08e-9, "unit": "s", "method": "experiment", "source": "...", "url": "..."},
      "g_J": {"value": 1.003, "method": "experiment", "source": "...", "url": "..."},
      "hyperfine": {
        "137": {"A_MHz": -109.2, "A_unc": 0.2, "B_MHz": 51.0, "B_unc": 0.6, "method": "experiment", "source": "...", "url": "..."}
      }
    }
  ],
  "transitions": [
    {
      "lower_cm": 0.0,
      "upper_cm": 18060.261,
      "label": "6s2 1S0 - 6s6p 1P1",
      "use": "main cooling / imaging line",
      "type": "E1",
      "frequency_THz": {"value": 541.433, "unc": 0.001, "isotope": "138", "method": "experiment", "source": "...", "url": "..."},
      "A_s": {"value": 1.19e8, "unc": 0.01e8, "method": "experiment", "source": "...", "url": "..."},
      "branching": {"value": 0.9966, "method": "experiment", "source": "...", "url": "..."},
      "isotope_shift_MHz": {"137-138": {"value": 215.0, "unc": 0.5, "method": "experiment", "source": "...", "url": "..."}}
    }
  ],
  "not_found": ["lifetime of 6s7p 3P1: searched X and Y, no measurement located"],
  "notes": "anything the user of this file must know (sign conventions, which isotope a frequency refers to, ...)"
}
```

All fields other than the identifying ones are optional: include a field only when you have a sourced
value. `type` is `"E1"`, `"M1"`, `"E2"`, `"intercombination"` (spin-forbidden E1) or `"clock"`.
`A_s` is the Einstein A coefficient of that one decay channel in s^-1 (not the total decay rate of the
upper level; that goes in the level `lifetime`). Isotope shifts are `nu(first) - nu(second)`.
The file must be valid JSON (check it with `python3 -m json.tool`).
