"""The printer's fit table (15 Nov, Spark's Scout v4 bench print: the camera did not slide into its sleeve, the head frame and the
cradle did not go together, though every part passed its gates). One table for the Bambu A1 mini printing PCTG, from the Scout v4
probe coupon (parts/scout_v4_probe_coupon, read by Spark 14 Nov; tools/scout_v4_shape.COUPON_PICK; systems/dimensions.md):
printed holes come out ~0.1-0.2 small on the diameter, outer faces slightly fat, a D bore needed +0.3 to press home, an axle bore
+0.3 to turn free. Every setup sizes its holes, bores, slots and sleeves from here instead of the bought part's nominal size, and
the assembly check (tools/assembly_check.py) holds every declared mating pair and assembly path to the same numbers.

    from topo import fit
    fit.bore(3.0, "free")      -> 3.3   a printed hole for a bought round of nominal 3.0 (diameter)
    fit.across(36.0, "slide")  -> 36.6  a printed pocket / sleeve / slot across a bought body of nominal 36.0
    fit.gap("slide")           -> 0.25  the least drawn clearance per side at a mate of the kind (the assembly check's minimum)
    fit.FIT["slide"]           -> the row: allowance (total, on the diameter or across), tag, source

allow  = what the drawn size adds to the nominal (total: diameter, or across two faces)
gap    = the least clearance per side, in the drawn geometry (the part's mesh, before the printer grows it), the assembly check
         accepts at a declared mate of that kind: half the allowance less MESH (the viewing mesh's error), and the margin a
         declared assembly path is cut wider than the piece that goes through it. Negative: an interference fit (press, tap),
         the depth the check allows the two to overlap.
"""

GROW = 0.10          # mm a printed face stands proud of the drawn one (holes ~0.1-0.2 small on the diameter, outer faces fat): coupon M
MESH = 0.05          # mm the viewing mesh (parts/<p>/part.stl) may sit off the print mesh (tools/print_mesh.py: bounds within 0.05)

FIT = {
    # kind      allow (total, mm)  tag  source
    "bond":   dict(allow=0.20, min_gap=0.0, tag="M", src="carbon rod in a resin socket: the 3.2 / 6.2 bores for 3 / 6 rods (CLAUDE.md), the resin fills the rest: it only has to go in"),
    "press":  dict(allow=0.30, tag="M", src="a D bore pressed on the N20's 3.0 / 2.5 D shaft: 3.3 / 2.8 (coupon D: 3.0..3.2 would not go or not press home)"),
    "free":   dict(allow=0.30, tag="M", src="a bore turning free on an M3 axle or a 3 mm rod: 3.3 (coupon A1, the snuggest of 3.3 / 3.4 / 3.5, all free)"),
    "slide":  dict(allow=0.60, tag="E", src="a bought body sliding into a printed pocket, sleeve or slot over its length (camera case, SG90 body): "
                                                     "the axle's +0.3 plus 0.3 for the long contact and the case's own tolerance; check on the bench"),
    "mate":   dict(allow=0.50, tag="E", src="a printed part sliding onto another printed part: both faces print GROW fat (0.2 of it gone) + 0.3 running"),
    "clear":  dict(allow=2.00, tag="E", src="parts that pass each other and must never touch (an assembly path past a neighbour, a moving part)"),
    "screw":  dict(allow=0.40, tag="E", src="a screw's shank through a printed clearance hole: M2 2.4, M3 3.4"),
    "tap":    dict(allow=-0.40, tag="E", src="a screw cutting its own thread in a printed pilot: M2 1.6, M3 2.6 (the SG90 tab pilots)"),
}


def _row(kind):
    if kind not in FIT:
        raise KeyError(f"fit kind {kind!r}: one of {sorted(FIT)} (topo/fit.py)")
    return FIT[kind]


def bore(nominal, kind):
    """the drawn diameter of a printed hole for a bought round part of `nominal` diameter"""
    return round(float(nominal) + _row(kind)["allow"], 3)


def across(nominal, kind):
    """the drawn width of a printed pocket, sleeve or slot across a bought (or printed) body `nominal` wide"""
    return round(float(nominal) + _row(kind)["allow"], 3)


def gap(kind):
    """the least drawn clearance per side at a mate of this kind (negative: the overlap an interference fit may have)"""
    r = _row(kind)
    if "min_gap" in r:
        return float(r["min_gap"])
    a = r["allow"]
    return round(a / 2.0 - MESH, 3) if a > 0 else round(a / 2.0, 3)


def table():
    """rows for a report: kind, allow, gap, tag, source"""
    return [dict(kind=k, gap=gap(k), **v) for k, v in FIT.items()]
