"""Periodic table: (Z, symbol, name, period-row, group-column) with the f-block on rows 9 and 10."""
_NAMES = """H Hydrogen;He Helium;Li Lithium;Be Beryllium;B Boron;C Carbon;N Nitrogen;O Oxygen;F Fluorine;Ne Neon;Na Sodium;Mg Magnesium;
Al Aluminium;Si Silicon;P Phosphorus;S Sulfur;Cl Chlorine;Ar Argon;K Potassium;Ca Calcium;Sc Scandium;Ti Titanium;V Vanadium;Cr Chromium;
Mn Manganese;Fe Iron;Co Cobalt;Ni Nickel;Cu Copper;Zn Zinc;Ga Gallium;Ge Germanium;As Arsenic;Se Selenium;Br Bromine;Kr Krypton;
Rb Rubidium;Sr Strontium;Y Yttrium;Zr Zirconium;Nb Niobium;Mo Molybdenum;Tc Technetium;Ru Ruthenium;Rh Rhodium;Pd Palladium;Ag Silver;
Cd Cadmium;In Indium;Sn Tin;Sb Antimony;Te Tellurium;I Iodine;Xe Xenon;Cs Caesium;Ba Barium;La Lanthanum;Ce Cerium;Pr Praseodymium;
Nd Neodymium;Pm Promethium;Sm Samarium;Eu Europium;Gd Gadolinium;Tb Terbium;Dy Dysprosium;Ho Holmium;Er Erbium;Tm Thulium;Yb Ytterbium;
Lu Lutetium;Hf Hafnium;Ta Tantalum;W Tungsten;Re Rhenium;Os Osmium;Ir Iridium;Pt Platinum;Au Gold;Hg Mercury;Tl Thallium;Pb Lead;
Bi Bismuth;Po Polonium;At Astatine;Rn Radon;Fr Francium;Ra Radium;Ac Actinium;Th Thorium;Pa Protactinium;U Uranium;Np Neptunium;
Pu Plutonium;Am Americium;Cm Curium;Bk Berkelium;Cf Californium;Es Einsteinium;Fm Fermium;Md Mendelevium;No Nobelium;
Lr Lawrencium;Rf Rutherfordium;Db Dubnium;Sg Seaborgium;Bh Bohrium;Hs Hassium;Mt Meitnerium;Ds Darmstadtium;Rg Roentgenium;
Cn Copernicium;Nh Nihonium;Fl Flerovium;Mc Moscovium;Lv Livermorium;Ts Tennessine;Og Oganesson"""
N_NIST = 99  # NIST ASD has neutral-atom tables up to einsteinium


def _position(z):
    if z == 1:
        return 1, 1
    if z == 2:
        return 1, 18
    if 57 <= z <= 71:
        return 9, z - 57 + 3
    if 89 <= z <= 103:
        return 10, z - 89 + 3
    for row, (start, end) in enumerate([(3, 10), (11, 18), (19, 36), (37, 54), (55, 86), (87, 118)], start=2):
        if start <= z <= end:
            k = z - start
            if row in (2, 3):
                return row, k + 1 if k < 2 else k + 11
            if row in (4, 5):
                return row, k + 1
            return row, k + 1 if k < 2 else k - 14 + 1  # rows 6, 7 skip the f-block
    raise ValueError(z)


def _category(z):
    if z in (3, 11, 19, 37, 55, 87):
        return "alkali"
    if z in (4, 12, 20, 38, 56, 88):
        return "alkaline-earth"
    if z in (2, 10, 18, 36, 54, 86):
        return "noble-gas"
    if 57 <= z <= 71:
        return "lanthanide"
    if 89 <= z <= 103:
        return "actinide"
    if z in (1, 6, 7, 8, 9, 15, 16, 17, 34, 35, 53):
        return "nonmetal"
    if z >= 104:
        return "superheavy"
    if z in (5, 14, 32, 33, 51, 52, 85):
        return "metalloid"
    if z in (13, 31, 49, 50, 81, 82, 83, 84):
        return "post-transition"
    return "transition"


ELEMENTS = []
for _z, _item in enumerate(_NAMES.replace("\n", "").split(";"), start=1):
    _sym, _name = _item.split()
    _r, _c = _position(_z)
    ELEMENTS.append(dict(Z=_z, symbol=_sym, name=_name, row=_r, col=_c, category=_category(_z)))
