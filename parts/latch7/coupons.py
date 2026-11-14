"""Latch v7 fit-test coupons (14 Nov, Spark: one plate to test every fit before printing the real cartridges and receivers).
Each coupon is cut out of the real geometry (make.py's build(), standin.py's stand-in), keeps the real part's print orientation (each
parent's own pose from make.printability, the receiver's mount plane down as the engine part prints), is cropped to the fit, and stands on a
3 mm tab with its number engraved. One A1 mini plate (PCTG), plus the TPU seat strip as its own file. Nothing here changes make.py or a setup.

python3 parts/latch7/coupons.py   -> print/latch7_coupons.stl, print/latch7_coupon_strip_tpu.stl, parts/latch7/kit/latch7_coupons.png, parts/latch7/coupons.json
"""
import importlib.util, json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
_s = importlib.util.spec_from_file_location("latch7_standin", os.path.join(HERE, "standin.py"))
st = importlib.util.module_from_spec(_s); _s.loader.exec_module(st)
mk = st.mk; bl, box, cyl, U, vol = mk.bl, mk.box, mk.cyl, mk.U, mk.vol
import manifold3d as mf

BED = 180.0
TAB = dict(t=3.0, h=9.0, engrave=0.8, stroke=1.2, dw=4.4, dh=7.0, gap=1.4)     # label tab: 3 thick, digits 0.8 deep (2.2 floor), strokes 1.2


def rot_for(down):
    """make._on_bed's rotation: the part's `down` face onto the bed"""
    ax = "xyz".index(down[1]); sg = 1.0 if down[0] == "+" else -1.0; d = np.zeros(3); d[ax] = sg
    a = np.cross(d, [0, 0, -1.0]); c = float(d @ [0, 0, -1.0])
    if np.linalg.norm(a) < 1e-9: return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]]); return np.eye(3) + K + K @ K / (1 + c)


def posed(m, down):
    R = rot_for(down); M = np.hstack([R, np.zeros((3, 1))])
    t = m.transform(M.tolist()); bb = t.bounding_box()
    return t.translate([-bb[0], -bb[1], -bb[2]])


SEG = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def digits(n, x0, y0):
    """engraving cuts for the number n, 7 segments, lower left at (x0, y0) on the tab's top"""
    w, h, s = TAB["dw"], TAB["dh"], TAB["stroke"]; z0 = TAB["t"] - TAB["engrave"]; out = []
    for i, ch in enumerate(str(n)):
        x = x0 + i * (w + TAB["gap"])
        seg = {"a": (x, x + w, y0 + h - s, y0 + h), "d": (x, x + w, y0, y0 + s), "g": (x, x + w, y0 + (h - s) / 2, y0 + (h + s) / 2),
               "f": (x, x + s, y0 + h / 2, y0 + h), "b": (x + w - s, x + w, y0 + h / 2, y0 + h), "e": (x, x + s, y0, y0 + h / 2), "c": (x + w - s, x + w, y0, y0 + h / 2)}
        out += [box(seg[k][0], seg[k][1], seg[k][2], seg[k][3], z0, TAB["t"] + 1) for k in SEG[ch]]
    return U(*out)


def tagged(m, n):
    """the coupon with its numbered tab, joined at the coupon's bed contact (the tab's end runs 2.0 under the coupon's first layer)"""
    sec = m.slice(0.05); polys = sec.to_polygons()
    pts = np.vstack([np.asarray(p) for p in polys]); i = int(np.argmin(pts[:, 0])); px, py = pts[i]
    nd = len(str(n)); L = 4.0 + nd * TAB["dw"] + (nd - 1) * TAB["gap"]
    y0 = py - TAB["h"] / 2
    tab = box(px - L, px + 0.01, y0, y0 + TAB["h"], 0.0, TAB["t"])
    return (m + tab) - digits(n, px - L + 2.0, y0 + (TAB["h"] - TAB["dh"]) / 2)


def grow(bb, d):
    return [bb[0] - d[0], bb[1] - d[1], bb[2] - d[2], bb[3] + d[0], bb[4] + d[1], bb[5] + d[2]]


def cropbox(bb):
    return box(bb[0], bb[3], bb[1], bb[4], bb[2], bb[5])


def pieces():
    """[(number, name, manifold in its parent's print pose, card)]"""
    out = []; n = [0]
    pose_of = {}

    def add(name, m, down, card):
        n[0] += 1; out.append((n[0], name, posed(m, down), dict(card, pose=f"as its part: the {down} face of the part toward the bed")))

    def down_of(key, m):
        if key not in pose_of: pose_of[key] = mk.printability(m, near=30.0)["down"]
        return pose_of[key]

    BS = {pk: mk.build(pk) for pk in ("scout", "overseer")}
    for pk in ("scout", "overseer"):
        B = BS[pk]; g, r = B["g"], B["r"]; zt = g["Z_T"]; P = pk.capitalize()
        mb = B["male"].bounding_box()
        for nm, part in (("carrier", B["carrier"]), ("cap", B["cap"])):
            dn = down_of(f"{pk} {nm}", part)
            add(f"{P} plug {nm}: the XT60W-M pocket", part ^ cropbox(grow(mb, (4.0, 3.0, 3.0))), dn,
                dict(goes_in="the XT60W-M (male) in its collar (coupon %s), seated as on the drone" % ("collar"), good="the collar drops in by hand with no play you can feel, the plug's face flush with the pocket's mouth; "
                     "%s: the cap lies flat over it with no rocking" % ("carrier" if nm == "carrier" else "cap"),
                     tight_or_loose="latch5 battery_latch_v4.P_CLR (0.15 a side on the plug's pockets) and the XM_* plug numbers (Spark's measurement first)"))
        fb = B["female"].bounding_box(); dn = down_of(f"{pk} cart", B["cart"])
        add(f"{P} cartridge lead end: the XT60W-F pocket and its two set screws", B["cart"] ^ cropbox([fb[0] - 4.0, fb[1] - 3.0, g["Z_CW0"] - 1.0, fb[3] + 4.0, fb[4] + 1.0, g["L_C"] + 3.5]), dn,
            dict(goes_in="the pack's XT60W-F (female), its D-key to the chamfered corners; two M3 x 8 set screws from the end", good="the plug slides in with finger force and the key only goes one way; "
                 "the set screws cut their own thread in the o 2.5 holes and pinch the plug's back without cracking the boss",
                 tight_or_loose="latch5 battery_latch_v4.P_CLR and XF_W / XF_D / XF_KEY (the XT60W-F body); the set screw holes' o 2.5 (cyl r 1.25 in cartridge())"))
        zr = bl.REC_Z + bl.RIB_POST + 1.0
        crop = cropbox([-bl.RIB_HX - 2.0, -0.5, zt - zr, g["X_OUT"] + 0.5, mk.bl.Y_FL1 + 2.0, zt + zr])
        add(f"{P} cartridge latch half: the bolt's wall hole, channel, rib and stop bar notch", B["cart"] ^ crop, dn,
            dict(goes_in="the %s bolt (coupon %d) from outside through the wall hole; the stop bar (coupon %s) dropped across the rib into the bolt's top" % (P, n[0] + 1, "stop bar"),
                 good="the bolt slides its full 4.9 to the rib under its own weight when tilted, no catch; with the stop bar in, it stops at rest with 3.0 standing out of the wall",
                 tight_or_loose="make.py bl.CH_CLR (0.35, the wall hole round the bolt) and ST (the stop bar's 0.25 clearances in slider() and centre_rib())"))
        dnb = down_of(f"{pk} bolt", mk.slider(g, 0, 1))
        add(f"{P} bolt (the real one): its spring slots and its magnet pocket", mk.slider(g, 0, 1), dnb,
            dict(goes_in="two PATIKIL 0.3 x 3.0 x 30 springs, each on a printed o 2.0 x 7 guide pin (coupon 'pin'), in the two slots; a o 2 x 2 N52 magnet in the underside pocket",
                 good="a spring with its pin drops into its slot and lies below the bolt's top face; the magnet presses in with a thumb and stays when the bolt is shaken",
                 tight_or_loose="slots: make.py bl.SPR_R (1.6) and SPR_Y; magnet: bl.MAG_D (2.0) and bl.MAG_DEPTH (2.2)"))
        hw = B["hold_where"][0]; hb = B["hold_blocks"][0].bounding_box()
        hc = cropbox([min(hw["x"]) - 3.0, mk.HOLD["y"][0] - 3.0, min(hw["z"]) - 3.0, max(hw["x"]) + 0.5, mk.HOLD["y"][1] + 3.0, max(hw["z"]) + 3.0])
        add(f"{P} receiver hold-down notch", B["recv"] ^ hc, "+y",
            dict(goes_in="the 3 x 3 steel square key (the funnel's end-wall tongue), flats up and down, slid into the notch from its open end",
                 good="the key slides in by hand along the notch with no up-and-down play you can feel, and does not need pushing",
                 tight_or_loose="make.py HOLD (y 6.0..10.0 is the notch's 4.0 height round the 3.0 key; depth 2.5)"))
    B = BS["overseer"]; g, r = B["g"], B["r"]
    x_, z_ = B["drone_pos"][0]
    add("Overseer receiver deck boss: M3 x 10 from below into the base's insert", B["recv"] ^ cropbox([x_ - 8.0, r["Y_DK0"] - 4.0, z_ - 8.0, x_ + 8.0, r["Y_M"] + 0.01, z_ + 8.0]), "+y",
        dict(goes_in="an M3 x 10 socket head cap screw from below: through the o 3.4 hole, its head in the counterbore", good="the screw drops through the hole free; the head sits flat on its bearing face below the deck, not proud",
             tight_or_loose="make.py DRONE_HEAD (r 3.2 counterbore, h 2.8) and bl.BOLT_D (3.4)"))
    lead = [(bx, bz) for bx, bz in r["MOUNT"] if abs(bz - g["Z_X"]) < 1e-6][0]
    add("Overseer plug cap: an M3 x 5.7 heat-set insert hole", B["cap"] ^ cropbox([lead[0] - 7.0, r["Y_DK1"] - 2.0, lead[1] - 7.0, lead[0] + 7.0, r["Y_M"] + 0.01, lead[1] + 7.0]), down_of("overseer cap", B["cap"]),
        dict(goes_in="an M3 x 5.7 brass heat-set insert, pressed in with the iron at PCTG temperature; then an M3 screw from below", good="the insert goes in square and flush, the plastic rolls a small collar, the screw turns in without the insert spinning",
             tight_or_loose="make.py build(): the cap's o 4.0 hole (cyl r 2.0) over the lead-end bolts"))
    Bs = BS["scout"]; g, r = Bs["g"], Bs["r"]; zt = g["Z_T"]
    sa = [s_ for s_ in Bs["strips"].decompose()]; sa.sort(key=lambda m_: -m_.bounding_box()[0]); sb = sa[0].bounding_box()
    add("Scout receiver seat strip groove and its keys", Bs["recv"] ^ cropbox([sb[0] - 3.0, r["Y_DK0"] - 2.0, sb[2] - 4.0, sb[3] + 3.0, r["Y_DK1"] + 3.0, sb[5] + 4.0]), "+y",
        dict(goes_in="the TPU 95A seat strip (latch7_coupon_strip_tpu.stl, the real strip), pressed into the recess between its two keys", good="the strip presses in and stays when the coupon is turned over; it stands 1.5 proud of the deck",
             tight_or_loose="latch5 battery_latch_v4.STRIP_T (2.4), STRIP_REC (0.9) and make.py SEAT_HZ / SEAT_KEY (0.2 clear of the strip's ends)"))
    S = st.cartridge(Bs); zr = bl.REC_Z + bl.RIB_POST + 1.0
    add("Scout stand-in cartridge latch half: the spring's post, rod and slot (Spark's 5.0 x 0.5 x 25)", S ^ cropbox([-(st.seat_x() + st.END + 1.0), -0.5, zt - zr, g["X_OUT"] + 0.5, bl.Y_FL1 + 2.0, zt + zr]), down_of("scout cart", Bs["cart"]),
        dict(goes_in="one of Spark's springs over the rod to the post, then the stand-in bolt (coupon %d) from outside, its block's channel over the spring's free end" % (n[0] + 2),
             good="the spring slides on the rod free; pushed in by hand the bolt comes back out to the wall smartly and does not rub",
             tight_or_loose="standin.py ROD_R (1.75 for the spring's 4.0 ID), POCKET_R (2.7 for its 5.0 OD), TOP (6.4)"))
    add("Scout stand-in bolt: the spring block", st.bolt(g, 0, 1), down_of("standin bolt", st.bolt(g, 0, 1)),
        dict(goes_in="the spring's end into the block's channel", good="the spring's end sits square on the seat inside the channel", tight_or_loose="standin.py POCKET_R, DEPTH (3.3)"))
    add("stop bar (the real one, both packs)", Bs["stop"], down_of("stop", Bs["stop"]),
        dict(goes_in="across the rib's notch into both bolts' tops (coupons 'latch half')", good="drops in under its own weight; the bolts stop on its T ends", tight_or_loose="make.py ST"))
    pin = cyl("y", 0.0, 0.0, mk.GUIDE_PIN[0] / 2, 0.0, mk.GUIDE_PIN[1], 24)
    add("guide pin o 2.0 x 7 (the real one) for the PATIKIL spring", pin, "+y",
        dict(goes_in="inside a PATIKIL 0.3 x 3.0 x 30 spring (ID 2.4)", good="the spring slides over it free", tight_or_loose="make.py GUIDE_PIN"))
    add("XT60W-M plug collar (the real one, both packs)", Bs["collar"], down_of("collar", Bs["collar"]),
        dict(goes_in="the XT60W-M, glued after the fit is right", good="the plug pushes in with no side play; WAITING on Spark's measurement of the plug body", tight_or_loose="make.py plug_collar()"))
    return out, Bs


def main():
    sys.path.insert(0, os.path.join(ROOT, "tools")); import solid_check as sc, trimesh
    from topo.build import render
    out, Bs = pieces()
    placed = []; x = y = 2.0; row = 0.0; cards = []
    for nmb, name, m, card in sorted(out, key=lambda t: -t[2].bounding_box()[4]):
        t = tagged(m, nmb); bb = t.bounding_box(); w, h = bb[3] - bb[0], bb[4] - bb[1]
        if x + w > BED - 2.0: x = 2.0; y += row + 3.0; row = 0.0
        t = t.translate([x - bb[0], y - bb[1], 0.0]); x += w + 3.0; row = max(row, h)
        tm = trimesh.Trimesh(*[np.asarray(a) for a in (t.to_mesh().vert_properties[:, :3], t.to_mesh().tri_verts)])
        ok, info = sc.solid_check(tm)
        cards.append(dict(number=nmb, name=name, solid_check="PASS" if ok else "FAIL", why=None if ok else {k: info.get(k) for k in ("bodies_plain", "necks", "thin_walls", "sealed_voids")},
                          size_mm=[round(float(v), 1) for v in tm.extents], **card))
        placed.append(t)
    plate = U(*placed); pb = plate.bounding_box()
    fits = bool(pb[3] <= BED and pb[4] <= BED)
    pd = os.path.join(ROOT, "print"); f = os.path.join(pd, "latch7_coupons.stl")
    tm = trimesh.Trimesh(np.asarray(plate.to_mesh().vert_properties[:, :3]), np.asarray(plate.to_mesh().tri_verts)); tm.export(f)
    strip = sorted(Bs["strips"].decompose(), key=lambda m_: m_.bounding_box()[0])[0]; dn = mk.printability(strip, near=30.0)["down"]; ts = mk._on_bed(strip, dn)
    ts.export(os.path.join(pd, "latch7_coupon_strip_tpu.stl")); oks, _ = sc.solid_check(ts)
    render(tm, os.path.join(HERE, "kit", "latch7_coupons.png"), title="latch7_coupons.stl: one A1 mini plate, PCTG", info=f"{len(cards)} coupons | {pb[3]:.0f} x {pb[4]:.0f} mm of the 180 bed | numbers on the tabs")
    res = dict(note=__doc__.split("\n\n")[0], plate="print/latch7_coupons.stl", plate_mm=[round(pb[3], 1), round(pb[4], 1), round(pb[5], 1)], fits_bed=fits,
               tpu="print/latch7_coupon_strip_tpu.stl (TPU 95A, the real seat strip, %s face down), solid check %s" % (dn, "PASS" if oks else "FAIL"),
               grams=round(abs(tm.volume) / 1000 * 1.23, 1), coupons=sorted(cards, key=lambda c: c["number"]),
               ok=bool(fits and oks and all(c["solid_check"] == "PASS" for c in cards)))
    json.dump(res, open(os.path.join(HERE, "coupons.json"), "w"), indent=1)
    for c in res["coupons"]: print(c["number"], c["solid_check"], c["size_mm"], c["name"], c["why"] or "")
    print("plate", res["plate_mm"], "fits", fits, "tpu", oks, "grams", res["grams"], "ok", res["ok"])
    return res


if __name__ == "__main__":
    main()
