"""Species definitions for the level diagrams.

Curated species (an isotope, with measured data in data/literature) are listed by hand. Every other element of the
periodic table gets an automatic NIST-only entry (auto=True): no isotope, lines chosen by strength.


kind = "alkali": one valence electron. Levels and wavelengths from NIST, every E1-allowed pair is drawn,
        matrix elements from measurements / NIST where they exist and from ARC otherwise.
kind = "nist":   everything else. Only lines that NIST classifies or that the literature file lists are drawn.
"""

_RB = dict(
    kind="alkali", symbol="Rb", element="Rubidium", Z=37, core=["4p6."], E_cut=31700.0,
    scale=[(18500.0, 0.42), (32000.0, 4.2)], rydberg_source="pairinteraction", pi_species="Rb",
    rydberg_draw=[("5S1/2", "P3/2"), ("5P1/2", "S1/2"), ("5P1/2", "D3/2"), ("5P3/2", "S1/2"), ("5P3/2", "D5/2"),
                  ("6P1/2", "S1/2"), ("6P1/2", "D3/2"), ("6P3/2", "S1/2"), ("6P3/2", "D5/2"),
                  ("5D5/2", "P3/2"), ("5D5/2", "F7/2")],
    rydberg_table=["5S1/2", "5P1/2", "5P3/2", "4D5/2", "6S1/2", "6P1/2", "6P3/2", "5D5/2", "7S1/2", "4F7/2", "7P3/2"],
    key=[("5S1/2", "5P3/2", "D2: MOT, imaging, Rydberg lower leg"), ("5S1/2", "5P1/2", "D1: optical pumping, Λ / gray-molasses cooling"),
         ("5S1/2", "6P3/2", "blue leg of 420 + 1013 Rydberg excitation"), ("5S1/2", "6P1/2", "blue leg (421 + 1005)"),
         ("5P3/2", "5D5/2", "780 + 776 ladder; 5S–5D two-photon at 778.1 nm"), ("5P1/2", "5D3/2", "795 + 762 ladder"),
         ("5P3/2", "4D5/2", "telecom C-band ladder"), ("5P3/2", "4D3/2", "telecom C-band ladder"),
         ("5P1/2", "4D3/2", "telecom S-band ladder"), ("5P3/2", "6S1/2", "telecom E-band ladder"),
         ("5P1/2", "6S1/2", "telecom O-band ladder"), ("5P3/2", "6D5/2", "red ladder"),
         ("5P3/2", "7S1/2", "ladder to 7S"), ("6S1/2", "7P3/2", "O-band, from 6S"),
         ("4D5/2", "4F7/2", "strongest line of the diagram"), ("6P3/2", "7D5/2", "telecom C-band, from 6P"),
         ("6P3/2", "8S1/2", "longest 6P line below 2 µm")],
)

_CS = dict(
    kind="alkali", symbol="Cs", element="Caesium", Z=55, core=["5p6."], E_cut=28900.0,
    scale="auto", rydberg_source="arc", pi_species=None,
    rydberg_draw=[("6S1/2", "P3/2"), ("6P1/2", "S1/2"), ("6P1/2", "D3/2"), ("6P3/2", "S1/2"), ("6P3/2", "D5/2"),
                  ("7P1/2", "S1/2"), ("7P1/2", "D3/2"), ("7P3/2", "S1/2"), ("7P3/2", "D5/2"),
                  ("5D5/2", "P3/2"), ("5D5/2", "F7/2")],
    rydberg_table=["6S1/2", "6P1/2", "6P3/2", "5D3/2", "5D5/2", "7S1/2", "7P1/2", "7P3/2", "6D5/2", "8S1/2", "4F7/2"],
    key=[("6S1/2", "6P3/2", "D2: MOT, imaging"), ("6S1/2", "6P1/2", "D1: optical pumping, Λ / gray-molasses cooling"),
         ("6S1/2", "7P3/2", "blue leg of 456 + 1038 Rydberg excitation"), ("6S1/2", "7P1/2", "blue leg (459 + 1040)"),
         ("6P3/2", "6D5/2", "852 + 917 ladder"), ("6P3/2", "8S1/2", "852 + 795 ladder"),
         ("6P3/2", "7S1/2", "telecom E-band ladder; 6S–7S parity-violation line at 539.5 nm ×2"),
         ("6P1/2", "7S1/2", "telecom O-band ladder"), ("6P3/2", "7D5/2", "852 + 698 ladder"),
         ("5D5/2", "7P3/2", "from 5D"), ("5D5/2", "4F7/2", "1.01 µm, from 5D"),
         ("6P1/2", "6D3/2", "895 + 876 ladder"),
         ("6P3/2", "9S1/2", "852 + 659 ladder"), ("6P3/2", "8D5/2", "852 + 621 ladder")],
)

def _alkali(symbol, element, Z, core, E_cut):
    return dict(kind="alkali", symbol=symbol, element=element, Z=Z, core=[core], E_cut=E_cut, scale="auto",
                rydberg_source="arc", pi_species=None)


SPECIES = {
    "rb87": dict(_RB, A=87, slug="rubidium-87", arc="Rubidium87"),
    "rb85": dict(_RB, A=85, slug="rubidium-85", arc="Rubidium85"),
    "cs133": dict(_CS, A=133, slug="caesium-133", arc="Caesium"),
    "yb171": dict(kind="nist", symbol="Yb", element="Ytterbium", Z=70, A=171, I="1/2", slug="ytterbium-171",
                  core=["4f14."], E_cut=45000.0, columns="LS", keep_unrated=True),
    "yb174": dict(kind="nist", symbol="Yb", element="Ytterbium", Z=70, A=174, I="0", slug="ytterbium-174",
                  core=["4f14."], E_cut=45000.0, columns="LS", keep_unrated=True),
    "sr88": dict(kind="nist", symbol="Sr", element="Strontium", Z=38, A=88, I="0", slug="strontium-88",
                 core=["4p6."], E_cut=40500.0, columns="LS", keep_unrated=False),
    "sr87": dict(kind="nist", symbol="Sr", element="Strontium", Z=38, A=87, I="9/2", slug="strontium-87",
                 core=["4p6."], E_cut=40500.0, columns="LS", keep_unrated=False),
    "ba137": dict(kind="nist", symbol="Ba", element="Barium", Z=56, A=137, I="3/2", slug="barium-137",
                  core=["5p6."], E_cut=36000.0, columns="LS", keep_unrated=False),
    "ba138": dict(kind="nist", symbol="Ba", element="Barium", Z=56, A=138, I="0", slug="barium-138",
                  core=["5p6."], E_cut=36000.0, columns="LS", keep_unrated=False),
    "dy164": dict(kind="nist", symbol="Dy", element="Dysprosium", Z=66, A=164, I="0", slug="dysprosium-164",
                  core=[], E_cut=27000.0, columns="J", keep_unrated=False),
    "dy163": dict(kind="nist", symbol="Dy", element="Dysprosium", Z=66, A=163, I="5/2", slug="dysprosium-163",
                  core=[], E_cut=27000.0, columns="J", keep_unrated=False),
    "li6": dict(_alkali("Li", "Lithium", 3, "1s2.", 41300.0), A=6, slug="lithium-6", arc="Lithium6"),
    "li7": dict(_alkali("Li", "Lithium", 3, "1s2.", 41300.0), A=7, slug="lithium-7", arc="Lithium7"),
    "na23": dict(_alkali("Na", "Sodium", 11, "2p6.", 39300.0), A=23, slug="sodium-23", arc="Sodium"),
    "k39": dict(_alkali("K", "Potassium", 19, "3p6.", 32900.0), A=39, slug="potassium-39", arc="Potassium39"),
    "k40": dict(_alkali("K", "Potassium", 19, "3p6.", 32900.0), A=40, slug="potassium-40", arc="Potassium40"),
    "k41": dict(_alkali("K", "Potassium", 19, "3p6.", 32900.0), A=41, slug="potassium-41", arc="Potassium41"),
    "be9": dict(kind="nist", symbol="Be", element="Beryllium", Z=4, A=9, I="3/2", slug="beryllium-9",
                core=["1s2."], E_cut=64000.0, columns="LS", keep_unrated=False),
    "mg24": dict(kind="nist", symbol="Mg", element="Magnesium", Z=12, A=24, I="0", slug="magnesium-24",
                 core=["2p6."], E_cut=54000.0, columns="LS", keep_unrated=False),
    "mg25": dict(kind="nist", symbol="Mg", element="Magnesium", Z=12, A=25, I="5/2", slug="magnesium-25",
                 core=["2p6."], E_cut=54000.0, columns="LS", keep_unrated=False),
    "ca40": dict(kind="nist", symbol="Ca", element="Calcium", Z=20, A=40, I="0", slug="calcium-40",
                 core=["3p6."], E_cut=42000.0, columns="LS", keep_unrated=False),
    "ca43": dict(kind="nist", symbol="Ca", element="Calcium", Z=20, A=43, I="7/2", slug="calcium-43",
                 core=["3p6."], E_cut=42000.0, columns="LS", keep_unrated=False),
}

from elements import ELEMENTS, N_NIST  # noqa: E402

CURATED = {cfg["symbol"] for cfg in SPECIES.values()}
for _e in ELEMENTS[:N_NIST]:
    if _e["symbol"] not in CURATED:
        SPECIES[_e["symbol"].lower()] = dict(kind="nist", auto=True, symbol=_e["symbol"], element=_e["name"], Z=_e["Z"], A=None, I=None,
                                             slug=_e["name"].lower(), core=[], E_cut=1e9, columns="auto", keep_unrated=False)
