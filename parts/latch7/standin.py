"""Latch v7 stand-in springs (14 Nov, Spark: print and test the latch now with the springs he has, unlatching by hand, no arm).
The design stays on the PATIKIL 0.3 x 3.0 x 30 springs (make.py, two per bolt in slots along the bolt). This is a separate print set for
both packs; nothing here changes make.py, the receivers or their setups.

Spark's springs: uxcell 304 stainless compression, o 5.0 out, 0.5 wire, 25 free (ID 4.0); rate not listed, E 0.5..0.8 N/mm until he weighs one.
Where it goes: a 5.4 pocket does not fit in the 4.7 thick bolt, and beside the bolt there is 1.6 to the recess wall (the cross walls are 6 thick).
One spring a bolt, as the design's two are, but under the bolts: each bolt carries a block under its inner end with an open-bottomed o 5.4 channel
in a side lane (z_T +- 10, clear of the stop bar; the +x bolt's lane is +10, the same file turned half round puts the other's at -10), its seat 3.3 in.
The spring runs from that seat inward through a slot in the rib (open underneath; the rib stays whole over the middle and along its top) to a post
on the far side, 20.4 from the seat at rest: the post stands on two 2.0 rails tied to the rib's feet, all under the other bolt's path (top 6.4, the bolt's
underside 6.8), with a fixed o 3.5 guide rod 15 long that the spring threads on (printed with the cartridge, so nothing loose).
(First try, one spring between both bolts through a closed hole in the middle of the rib: the 2.0 bars round the hole under the stop bar's notch let the
rib's halves split off in the solid check's neck test.)
Seat to post 20.4 at rest, 15.5 with the bolt fully in: forces per bolt below; each bolt's spring is its own, as in the design.
In the cartridge: the wall hole's notch goes down to the underside over the block's lane so the block passes when the bolt goes in from outside, and the rib's
wedge feet are cut where the block sweeps (the grabber's hooks seat on them; no arm in this test). Travel (4.9 to the rib), the noses, the stop bar, the 1.5
snap window and every slant case are the design's: the bolt's outer part is the design's bolt; the design's spring slots in it are filled (unused).

python3 parts/latch7/standin.py   -> print/latch7*_standin_*.stl, parts/latch7/kit/*standin*.png, parts/latch7/standin.json
"""
import importlib.util, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
_s = importlib.util.spec_from_file_location("latch7_make", os.path.join(HERE, "make.py"))
mk = sys.modules.get("latch7_make")
if mk is None:
    mk = importlib.util.module_from_spec(_s); sys.modules["latch7_make"] = mk; _s.loader.exec_module(mk)
bl, box, cyl, U, vol = mk.bl, mk.box, mk.cyl, mk.U, mk.vol

SPRING = dict(od=5.0, d=0.5, free=25.0, id=4.0, k_range=(0.5, 0.8), k_mid=0.65, listing="uxcell 304 stainless compression springs, 5.0 OD x 0.5 wire x 25 free (Spark's, on hand)")
LANE = 10.0                                            # the +x bolt's spring lane, z_T + LANE (the other bolt's: z_T - LANE)
POCKET_R, AXIS_Y, DEPTH, END = 2.7, 3.9, 3.3, 2.0     # channel o 5.4 at y 3.9 (the spring's top 6.4, under the other bolt's 6.8), seat 3.3 in, 2.0 end wall
WALL, CLR = 2.0, 0.3                                   # the block's and the cradle's walls; the block's clearance in the cartridge
TOP = 6.4                                              # the cradle's top (rails and post), 0.4 under the bolts
ROD_R = 1.75                                           # the fixed guide rod o 3.5 (the spring's ID 4.0)


def seat_x():
    return bl.TAB_IN + DEPTH                           # the bolt's seat |x| at rest; the post's face is at the same |x| on the far side


def lengths():
    L0 = 2 * seat_x()
    return dict(rest=round(L0, 2), fully_in=round(L0 - bl.TRAVEL, 2))


def forces():
    L = lengths(); out = {}
    for k in SPRING["k_range"] + (SPRING["k_mid"],):
        out[f"{k:.2f} N/mm"] = {f"latched ({L['rest']} long)": round(k * (SPRING["free"] - L["rest"]), 2), f"fully in ({L['fully_in']} long)": round(k * (SPRING["free"] - L["fully_in"]), 2)}
    return out


def bolt(g, retract=0.0, side=1):
    """the design's bolt (its spring slots filled) with the spring block under its inner end"""
    zt = g["Z_T"]; zl = zt + LANE; x0 = bl.TAB_IN; x1 = x0 + DEPTH + END; hz = POCKET_R + WALL
    keep = mk.SPRINGS_Z; mk.SPRINGS_Z = ()
    try: b = mk.slider(g, 0.0, 1)
    finally: mk.SPRINGS_Z = keep
    b = b + box(x0, x1, AXIS_Y - POCKET_R, bl.BOLT_Y0 + 0.01, zl - hz, zl + hz)
    b = b - cyl("x", AXIS_Y, zl, POCKET_R, x0 - 0.01, x0 + DEPTH, 48) - box(x0 - 0.01, x0 + DEPTH, AXIS_Y - POCKET_R - 1.0, AXIS_Y, zl - POCKET_R, zl + POCKET_R)
    b = b.translate([-retract, 0, 0])
    return b if side > 0 else mk.rot_y180(b, zt)


def cradle(g, sx):
    """the fixed end of the spring of the bolt on side sx: post, rails and rod on the far side (-sx), in that bolt's lane"""
    zt = g["Z_T"]; zl = zt + sx * LANE; X = lambda a, b: sorted((-sx * a, -sx * b)); hz = POCKET_R + WALL; s0 = seat_x()
    post = box(*X(s0, s0 + END), 0.0, TOP, zl - hz, zl + hz)
    rails = [box(*X(bl.RIB_HX - 0.5, s0 + 0.01), 0.0, TOP, *sorted((zl + e * POCKET_R, zl + e * hz))) for e in (-1, 1)]
    rod = cyl("x", AXIS_Y, zl, ROD_R, *sorted((-sx * (s0 + 0.01), sx * (s0 - bl.TRAVEL - 0.5))), 32)
    return U(post, *rails, rod)


def cartridge(B):
    """the design's cartridge, cut for the blocks and the springs, with the two cradles"""
    g = B["g"]; zt = g["Z_T"]; hz = POCKET_R + WALL + CLR
    c = B["cart"]
    for sx in (-1, 1):
        zl = zt + sx * LANE
        c = c - box(*sorted((sx * (bl.RIB_HX - 0.01), sx * (g["X_OUT"] + 1.5))), -1.0, bl.BOLT_Y0 + 0.01, zl - hz, zl + hz)      # the block's sweep and the wall hole's notch
        c = c - box(*sorted((sx * (bl.RIB_HX + 1.0), -sx * (seat_x() + 0.01))), -1.0, AXIS_Y + POCKET_R, zl - POCKET_R, zl + POCKET_R)   # its slot through the rib and the feet to the post
    return c + cradle(g, 1) + cradle(g, -1)


def spring_body(g, sx, retract=0.0):
    """the spring of the bolt on side sx as a tube (ID to OD), seat to post"""
    zt = g["Z_T"]; zl = zt + sx * LANE; a, b = sorted((sx * (seat_x() - retract), -sx * seat_x()))
    return cyl("x", AXIS_Y, zl, SPRING["od"] / 2, a, b, 32) - cyl("x", AXIS_Y, zl, SPRING["id"] / 2, a - 1, b + 1, 32)


def checks(B):
    """the stand-in against the design's own install and motion steps, in mm3 of overlap (0 = clear)"""
    g = B["g"]; C = cartridge(B); st = B["stop"]; R = B["recv"]
    steps = [0.0, 1.0, 2.0, 3.0, 4.0, bl.TRAVEL - 0.05]
    out = {}
    out["bolt in through its wall hole from outside (30 mm swept)"] = round(max(vol(bolt(g, -d, 1) ^ C) for d in [i * 0.5 for i in range(61)]), 3)
    out["bolts through their travel against the cartridge, the stop bar and each other"] = round(max(vol(bolt(g, a, 1) ^ (C + st)) + vol(bolt(g, a, 1) ^ bolt(g, b, -1)) + vol(bolt(g, b, -1) ^ (C + st)) for a in steps for b in steps), 3)
    out["springs seat to post, every travel, against the cartridge, the stop bar and the other bolt"] = round(max(vol(spring_body(g, sx, a) ^ (C + st + bolt(g, b, -sx)))
                                                                                                         for sx in (-1, 1) for a in steps for b in steps), 3)
    out["springs inside their own bolt's channel"] = round(max(vol(spring_body(g, sx, a) ^ bolt(g, a, sx)) for sx in (-1, 1) for a in steps), 3)
    out["latched in the receiver (bolts at rest, seated)"] = round(vol((bolt(g, 0, 1) + bolt(g, 0, -1)) ^ R) - vol((mk.slider(g, 0, 1) + mk.slider(g, 0, -1)) ^ R), 3)
    out["cartridge into the receiver, bolts held in (40 mm swept)"] = round(max(vol((C + bolt(g, bl.OVERLAP + 0.3, 1) + bolt(g, bl.OVERLAP + 0.3, -1)).translate([0, -d, 0]) ^ R) for d in [i * 0.5 for i in range(81)]), 3)
    out["ok"] = bool(all(v < 0.05 for k, v in out.items() if not isinstance(v, bool)))
    return out


def main():
    sys.path.insert(0, os.path.join(ROOT, "tools")); import solid_check as sc, trimesh
    from topo.build import render
    pd, kd = os.path.join(ROOT, "print"), os.path.join(HERE, "kit"); os.makedirs(pd, exist_ok=True)
    res = dict(note=__doc__.split("\n\n")[0], spring=SPRING, lengths_mm=lengths(), forces_N_per_bolt=forces(),
               design_per_bolt_N=dict(latched=round(2 * mk._spring_state(0.0)["each_N"], 2), fully_in=round(2 * mk._spring_state(bl.TRAVEL)["each_N"], 2)),
               scale_check="Stand one spring on a kitchen scale and press it down to 20 mm long (5 mm in): 255..410 g is 0.5..0.8 N/mm, the range these numbers cover "
                           "(latched 2.3..3.7 N, fully in 4.8..7.6 N a bolt; the design is 3.9 and 5.2). Under 255 g the bolts may not snap out cleanly: say so before printing.",
               assembly=["1 a magnet into each bolt's underside (as the design)", "2 one bolt in through its wall hole from outside",
                         "3 one spring onto each guide rod from underneath (the recess is open): over the rod's free end, through the rib's slot, to its post",
                         "4 each bolt in from outside (the same file, the second turned half round), its block's channel over the spring's free end; hold both in",
                         "5 the stop bar down across the rib into both bolts; let go: they spring out to the stop; the pack in (as the design)"],
               packs={}, files=[])
    done = {}
    for pack in ("scout", "overseer"):
        B = mk.build(pack); g = B["g"]; pre = "latch7_" if pack == "scout" else "latch7_ov_"
        ck = checks(B); res["packs"][pack] = dict(checks=ck)
        print(pack, ck)
        for nm, m, fn, n in (("cartridge", cartridge(B), pre + "standin_cartridge", 1), ("bolt", bolt(g, 0, 1), pre + "standin_bolt", 2)):
            if fn not in done:
                pr = mk.printability(m, near=30.0); t = mk._on_bed(m, pr["down"]); f = os.path.join(pd, fn + ".stl"); t.export(f)
                ok, info = sc.solid_check(trimesh.load(f, force="mesh"))
                png = os.path.join(kd, fn + ".png"); ext = [round(float(v), 1) for v in t.extents]
                render(t, png, title=f"{fn}.stl on its bed ({pr['down']} face down)", info=f"PCTG | {ext[0]} x {ext[1]} x {ext[2]} mm | solid check {'PASS' if ok else 'FAIL'}")
                done[fn] = dict(file=f"print/{fn}.stl", release=f"https://github.com/sparkiscool/noxen/releases/download/meshes/print-{fn}.stl", picture=os.path.relpath(png, ROOT),
                                solid_check="PASS" if ok else "FAIL", thin_walls=len(info.get("thin_walls", [])), pose=f"the part's {pr['down']} face on the bed", size_on_bed_mm=ext,
                                supports=("none" if pr["support_mm2"] < 5.0 else "yes: %d mm2 overhangs past 45 deg (tree supports)" % pr["support_mm2"]),
                                material="PCTG", grams_each=round(abs(t.volume) / 1000 * 1.23, 2), used_by={})
            done[fn]["used_by"][pack] = n
    res["files"] = list(done.values())
    res["ok"] = bool(all(p["checks"]["ok"] for p in res["packs"].values()) and all(f["solid_check"] == "PASS" for f in res["files"]))
    json.dump(res, open(os.path.join(HERE, "standin.json"), "w"), indent=1)
    for f in res["files"]: print(f["file"], f["solid_check"], f["pose"], f["size_on_bed_mm"], f["supports"][:30], f["grams_each"], f["used_by"], "thin", f["thin_walls"])
    print(json.dumps(res["forces_N_per_bolt"]), res["design_per_bolt_N"], "ok", res["ok"])
    return res


if __name__ == "__main__":
    main()
