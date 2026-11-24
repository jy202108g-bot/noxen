"""Overseer top plate plugs v1.1 (23 Nov): TPU 95A plugs that close the S500 top plate's open holes under the top cover
(cover v2.2 seals the sides with its window grommets; these close the floor). Drawn only, no topology run (no load path).
python parts/overseer_plate_plugs/make.py [out_dir] writes plugs.stl (all in place) and plugs.json (per plug: mass, how much
of its hole the membrane closes, its lip length).

Holes (sectioned from parts/top_plate/part.stl, z 45..46.6), every neighbour placed by systems/overseer.assembly.json:
* A, 4 corner cutouts on the diagonals (part of each sits on its arm root's top face);
* B + E, the centre cutout (x 8..22) and the small hole (x -1.3) inside the FC mount's open centre: one plug;
* C, 2 side slots at y +-43.2.
Not plugged: the FC stack slots' leftovers (3 wide strips beside the FC mount bolts) and the bolt clearances.
The motor leads leave through the cover's side windows (tools/overseer_wires.py), so no plug needs a wire slit; a plug
whose hole a wire still passes through gets a knife cross there.

Each plug (walls >= 2.0, the floor):
* a membrane MEM thick on the plate top, FLANGE past the hole edge where the plate top is free: KEEP_BOUGHT (5.0, Spark's
  clearance ask 23 Nov) off every bought part, KEEP off the printed parts (FC mount, cover, grommets) and the wires (no
  overlap: the schematic runs lie 0.5 over the plate), HEAD_R round every bolt axis;
* a ring RING wide down the hole's wall (press fit, 0 clearance): it seals the hole even where the flange steps back;
* no lip under the plate (23 Nov: a 1.0 lip failed the 2 mm floor, a 2.0 one is too stiff to squeeze through): the ring
  holds by its press fit, a printed outer face stands ~0.1 proud (systems/fit_table.json grow_mm; no TPU coupon yet, E);
  nothing loads the plugs under the cover.
Print flange down on the bed, no supports."""
import os, sys, json, numpy as np, trimesh, manifold3d as mf

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE
PB, PT = 45.0, 46.6
MEM, FLANGE, RING, LIP, LIP_T = 2.0, 2.0, 2.0, 0.7, 0.0   # LIP_T 0: no lip (a 1.0 lip was under the 2 mm floor, a 2.0 one will not squeeze through)
KEEP, KEEP_BOUGHT, HEAD_R = 0.3, 5.0, 4.0
BOLTS = [(sx * 34.1, sy * 55.3) for sx in (1, -1) for sy in (1, -1)] + [(sx * 55.3, sy * 34.1) for sx in (1, -1) for sy in (1, -1)] \
    + [(sx * 24.5, sy * 24.5) for sx in (1, -1) for sy in (1, -1)]           # arm bolts A (M3 x 50) and the arms' top screws
TPU = 1.21e-3
J = mf.JoinType.Round

ASM = json.load(open(os.path.join(ROOT, "systems", "overseer.assembly.json"), encoding="utf-8"))["parts"]


def pose(q):
    p = q.get("pose")
    if p is None:
        return np.eye(4)
    if isinstance(p, dict):
        T = np.eye(4); T[:3, 3] = p.get("t", [0, 0, 0]); return T
    return np.array(p, float)


def placed(q):
    m = trimesh.load(os.path.join(ROOT, q["mesh"])); m.apply_transform(pose(q)); return m


def ccw(p):
    p = np.asarray(p, float)
    return p if np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]) > 0 else p[::-1]


def area(q):
    return abs(np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1])) / 2


def footprint(meshes, z0, z1, n=6):
    """union of the meshes' sections at n heights between z0 and z1 (even-odd per section: a ring's open centre stays free)"""
    out = mf.CrossSection()
    for m in meshes:
        if m.bounds[1][2] < z0 or m.bounds[0][2] > z1:
            continue
        for z in np.linspace(z0, z1, n):
            s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            if s is None:
                continue
            ls = [d[:, :2] for d in s.discrete if len(d) >= 3]
            if ls:
                out = out + mf.CrossSection(ls, mf.FillRule.EvenOdd)
    return out


# ---------------- neighbours, by class
bought, other, wires = [], [], []
for q in ASM:
    if q["id"] in ("top_plate",) or not q.get("mesh") or not os.path.exists(os.path.join(ROOT, q["mesh"])):
        continue
    m = placed(q)
    if m.bounds[1][2] < PB - LIP_T - 6 or m.bounds[0][2] > PT + MEM + 6 or (np.abs(m.bounds[:, :2]) > 70).all():
        continue
    (wires if "wire" in q["id"] else bought if q.get("group") == "bought" else other).append(m)
gp = os.path.join(ROOT, "parts", "overseer_top_cover", "grommets.stl")
if os.path.exists(gp):
    other.append(trimesh.load(gp))
plate = placed([q for q in ASM if q["id"] == "top_plate"][0])

# ---------------- holes
loops = [d[:, :2] for d in plate.section(plane_origin=[0, 0, 0.5 * (PB + PT)], plane_normal=[0, 0, 1]).discrete]
loops.sort(key=lambda q: -area(q))
outline = mf.CrossSection([ccw(loops[0])]).simplify(0.02)
holes = []
for q in loops[1:]:
    lo, hi = q.min(0), q.max(0); w = hi - lo; c = (lo + hi) / 2; a = area(q)
    k = "A" if a > 400 and w[0] > 25 else "B" if a > 390 else "C" if w[0] > 25 and w[1] < 8 else "D" if a > 30 and min(w) <= 3.2 else "E" if a > 30 else "F"
    holes.append(dict(kind=k, c=c, cs=mf.CrossSection([ccw(q)]).simplify(0.02)))
groups = [("A", [h]) for h in holes if h["kind"] == "A"] + [("C", [h]) for h in holes if h["kind"] == "C"] \
    + [("B+E", [h for h in holes if h["kind"] in ("B", "E")])]

# ---------------- where a plug may go: on the plate top (PT .. PT + MEM + its keep) and under it (PB - LIP_T .. PB)
taken_top = footprint(other + wires, PT + 0.15, PT + MEM + KEEP).offset(KEEP, J) \
    + footprint(bought, PT + 0.15, PT + MEM + KEEP_BOUGHT).offset(KEEP_BOUGHT, J) \
    + mf.CrossSection.batch_boolean([mf.CrossSection.circle(HEAD_R, 32).translate(b) for b in BOLTS], mf.OpType.Add)
free_top = (outline.offset(-0.6, J) - taken_top).simplify(0.02)
taken_under = footprint(other + wires, PB - LIP_T - KEEP, PB - 0.05).offset(KEEP, J) \
    + footprint(bought, PB - LIP_T - KEEP_BOUGHT, PB - 0.05).offset(KEEP_BOUGHT, J)
free_under = (mf.CrossSection.square((400, 400), True) - taken_under).simplify(0.02)
wire_plan = footprint(wires, PB - 1.0, PT + MEM + 1.0)                # where a wire still passes a hole: a knife cross there


def ext(cs, z0, z1):
    return cs.extrude(z1 - z0).translate((0, 0, z0))


plugs, rows = [], []
for kind, hs in groups:
    H = mf.CrossSection.batch_boolean([h["cs"] for h in hs], mf.OpType.Add)
    reach = H.offset(FLANGE, J)
    if len(hs) > 1:                                                      # one membrane over both holes
        reach = reach + mf.CrossSection.hull_points([tuple(p) for h in hs for poly in h["cs"].to_polygons() for p in poly]).offset(FLANGE, J)
    mem = (reach ^ free_top).offset(-1.0, J).offset(1.0, J)               # opened by 1.0: no strip under the 2 mm floor where a keep-out trims it
    ring = (H - H.offset(-RING, J)) ^ mem                                 # only under the membrane: a bare ring seals nothing and stands 1.6 (the plate), under the floor
    solid = ext(mem, PT, PT + MEM) + ext(ring, PB, PT + 0.01)
    if LIP_T > 0:
        solid = solid + ext((H.offset(LIP, J) ^ free_under) - H.offset(-RING, J), PB - LIP_T, PB)
    bodies = sorted(solid.decompose(), key=lambda b: -b.volume())          # manifold's own bodies; slivers dropped
    m = bodies[0].to_mesh()
    t = trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts), process=False)   # no vertex merge: it breaks the manifold
    t.update_faces(t.nondegenerate_faces()); t.remove_unreferenced_vertices()   # the boolean's zero-area slivers
    c = np.mean([h["c"] for h in hs], axis=0)
    rows.append(dict(kind=kind, at=np.round(c, 1).tolist(), g=round(float(abs(t.volume) * TPU), 2), hole_mm2=round(H.area()),
                     closed=round((H ^ mem).area() / H.area(), 2), lip_mm=round(((H.offset(LIP, J) ^ free_under) - H).area() / LIP) if LIP_T > 0 else 0,
                     wire_mm2=round((H ^ wire_plan).area()), dropped_mm3=round(sum(b.volume() for b in bodies[1:]), 2), watertight=bool(t.is_watertight)))
    plugs.append(t)

trimesh.util.concatenate(plugs).export(os.path.join(OUT, "plugs.stl"))
json.dump(rows, open(os.path.join(OUT, "plugs.json"), "w"), indent=1)
for r in rows:
    print(r)
print(f"total {sum(r['g'] for r in rows):.1f} g TPU, {len(rows)} plugs")
