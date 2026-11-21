"""Scout v4 probe bench, the 3D interactive artifact (21 Nov, Spark: "of the non-generated Scout probe prototype alone ... rotatable or explodable,
parts labelled, hover or click for each part's name and size").
    python tools/probe_bench_3d.py        -> artifacts/probe_bench_3d.html (one self-contained page: meshes, three.js and OrbitControls inlined)
Every drawn part is its own parts/<name>/part.stl (drone frame, mm, z up), so the assembly is the parts where the drone has them; the
bought N20 and the two blade stubs are the probe_* reference meshes; the M3 hardware is drawn from the sizes in systems/parts-list.md and
the bench base's make.py. The SG90 and the camera are not drawn (no mesh): the cradle and head frame show where they go.
Sizes on the page are the mesh bounding boxes (x, y, z in the drone frame) plus the dimensions each make.py states."""
import base64, json, os, sys
import numpy as np, trimesh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "parts")); sys.path.insert(0, os.path.join(ROOT, "tools"))
from parts.scout_v4_units_lib import TURRET_BOLTS, DZ1          # noqa: E402
import scout_v4_shape as S                                      # noqa: E402

PCTG = 1.23e-3
cz = S.SPOOL["c"][1]


def load(name):
    return trimesh.load(os.path.join(ROOT, "parts", name, "part.stl"), process=True)


def ycyl(r, y0, y1, x=0.0, z=0.0, n=40):
    c = trimesh.creation.cylinder(radius=r, height=y1 - y0, sections=n)
    c.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))   # local z -> y
    c.apply_translation([x, (y0 + y1) / 2, z]); return c


def zcyl(r, z0, z1, x, y, n=40):
    c = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=n); c.apply_translation([x, y, (z0 + z1) / 2]); return c


roller = load("scout_v4_probe_roller").split(only_watertight=False)
tubes = sorted([m for m in roller if m.extents[1] < 5], key=lambda m: m.bounds[0][1])
rod = [m for m in roller if m.extents[1] > 20][0]
saddle = [m for m in roller if 8 < m.extents[1] < 9][0]
bolts = [trimesh.util.concatenate([zcyl(1.5, DZ1 + 3 - 10, DZ1 + 3, x, y, 24), zcyl(2.75, DZ1 + 3, DZ1 + 5.4, x, y, 24)]) for x, y in TURRET_BOLTS]
inserts = [zcyl(2.0, DZ1 - 5.7, DZ1, x, y, 24) for x, y in TURRET_BOLTS]
axle = trimesh.util.concatenate([ycyl(1.5, -21.5, 18.5, 0, cz, 24), ycyl(2.75, 18.5, 21.5, 0, cz, 24)])
nyloc = ycyl(2.75, -25.5, -21.5, 0, cz, 6)
mastA, mastB = load("scout_v4_probe_mast_a"), load("scout_v4_probe_mast_b")

# kind: printed | bought | hardware ; step = build-sheet step it appears in ; ex = explode offset (mm) ; dims = what the design files state
P = [
    dict(id="base", name="Bench base", mesh=load("scout_v4_probe_bench_base"), kind="printed", step=1, ex=(0, 0, 0), q=1, src="parts/scout_v4_probe_bench_base/make.py",
         dims="4 mm plate 130 x 68 (x -65..65, y -35..33, z 12..16); four O10 posts to z 24.5 at the turret's floor bolts (x +-13, y -21 / +19); insert holes O4.0 x 6.0; two clamp tabs with 6 x 24 slots at x +-50; open under the N20"),
    dict(id="insert", name="M3 heat-set insert 5.7 (x4)", mesh=trimesh.util.concatenate(inserts), kind="hardware", step=1, ex=(0, 0, 14), q=4, src="systems/parts-list.md (bench)",
         dims="M3 x 5.7 long, one in each base post (hole O4.0 x 6.0); a fifth goes in the head frame's bracket"),
    dict(id="turret", name="Bench turret", mesh=load("scout_v4_probe_bench_turret"), kind="printed", step=1, ex=(0, 0, 32), q=1, src="parts/scout_v4_probe_bench_turret/make.py",
         dims="3 mm plates: two side walls (axle bosses, +y gear side, -y drum side), floor on the base's top (z 24.5), back wall and 32 mm throat (x 11.1..19.1, z 41..73); N20 face plate, roller rod slots and leaf pocket; prints on its -y wall"),
    dict(id="bolt", name="M3 x 10 bolt (x4, turret to base)", mesh=trimesh.util.concatenate(bolts), kind="hardware", step=1, ex=(0, 0, 60), q=4, src="systems/parts-list.md (bench)",
         dims="M3 x 10, pan head O5.5; into the base's inserts from above (PH1 screwdriver, shaft 75 mm or longer)"),
    dict(id="motor", name="N20 gearmotor 6 V 100 rpm", mesh=load("scout_v4_probe_motor"), kind="bought", step=5, ex=(0, 0, -45), q=1, src="Amazon B07MZH851L",
         dims="12 x 10 x 37 (gearbox 12 x 10 x 10, can 12 x 10 x 17, 3 mm D shaft 10 long, 2.5 across the flat); face screwed to the turret plate with 2 x M1.6 x 4; hangs through the base's opening"),
    dict(id="pinion", name="Pinion 12 T (print 2, one spare)", mesh=load("scout_v4_probe_pinion"), kind="printed", step=5, ex=(0, 40, -45), q=2, src="parts/scout_v4_probe_pinion/make.py",
         dims="12 T module 0.8 x +0.35, teeth y 11.7..14.7, hub O7 to y 15.4, D bore 3.3 / 2.8 across the flat on the N20's shaft (press on, a drop of CA)"),
    dict(id="spool", name="Spool with 40 T gear", mesh=load("scout_v4_probe_spool"), kind="printed", step=4, ex=(0, -55, 32), q=1, src="parts/scout_v4_probe_spool/make.py",
         dims="hub O28, two O31.4 flanges 1.9 thick, 19.6 apart (the 19 mm blades); 40 T module 0.8 gear 3 wide outside the +y flange; drum hub O8; 1.2 clamp slot at 45 deg for the blade stack; axle bore 3.3; gear down to print"),
    dict(id="axle", name="M3 x 40 spool axle", mesh=axle, kind="hardware", step=4, ex=(0, 75, 32), q=1, src="systems/parts-list.md (bench)",
         dims="M3 x 40 through both turret walls (y -21.5..18.5) and the spool; head on the +y side"),
    dict(id="nyloc", name="M3 nyloc nut", mesh=nyloc, kind="hardware", step=4, ex=(0, -85, 32), q=1, src="systems/parts-list.md (bench)",
         dims="M3 nyloc on the -y end of the axle, snug not tight (the spool must spin freely)"),
    dict(id="tube1", name="Roller tube (-y)", mesh=tubes[0], kind="printed", step=4, ex=(48, -22, 32), q=2, src="parts/scout_v4_probe_roller/make.py",
         dims="O8 x 4.5 long, bore 3.3 (coupon A1) on the O3 rod, 2.35 wall; |y| 4.75..9.25; print 2"),
    dict(id="tube2", name="Roller tube (+y)", mesh=tubes[1], kind="printed", step=4, ex=(48, 22, 32), q=2, src="parts/scout_v4_probe_roller/make.py",
         dims="O8 x 4.5 long, bore 3.3 on the O3 rod; the second print of the same file"),
    dict(id="rod", name="Carbon rod O3 x 23.8 (roller axle)", mesh=rod, kind="bought", step=4, ex=(48, 0, 32), q=1, src="Amazon B09N91J1FC, cut to 23.8",
         dims="3 mm carbon rod cut to 23.8, ends sanded square, a drop of light oil; its ends sit in the turret's two slots (|y| 9.55..12.1)"),
    dict(id="saddle", name="Roller saddle S2", mesh=saddle, kind="printed", step=4, ex=(48, 0, 52), q=1, src="parts/scout_v4_probe_roller/make.py",
         dims="13 tangential x 8.6 along the rod, half-round O3.4 groove, slit 10 deep for the leaf contact's back leg, 1.65 tab; S1 / S3 are the lighter and heavier sets; the ZCZQC leaf contact (B0C5D3XLBK) clips on and presses the pocket's far wall"),
    dict(id="blade_a", name="Blade A (tape strip 200 x 19)", mesh=mastA, kind="bought", step=2, ex=(34, 0, 20), q=1, src="Topzone tape measure B00ZMHXV4I",
         dims="19 wide x ~0.13 thick, 200 long cut from the tape (curve toward B); M2 x 4 fixed to the head sleeve; 150 mm stroke. Drawn as the stub leaving the throat, stretched by the slider"),
    dict(id="blade_b", name="Blade B (tape strip 200 x 19) + ribbon", mesh=mastB, kind="bought", step=2, ex=(-34, 0, 20), q=1, src="Topzone tape measure B00ZMHXV4I",
         dims="19 wide x ~0.13 thick, 200 long; M2 x 6 + nut through the sleeve slot so B slides 7.5..9.5; the 6 PTFE wires (30 AWG) ride on A"),
    dict(id="head", name="Head frame", mesh=load("scout_v4_head_frame"), kind="printed", step=8, ex=(0, 0, 85), q=1, src="parts/scout_v4_head_frame/make.py",
         dims="sleeve over the blade tips, SG90 ring (tab screws), idler-side bracket with one M3 insert; the servo is not drawn"),
    dict(id="cradle", name="Camera cradle", mesh=load("scout_v4_cradle"), kind="printed", step=11, ex=(0, 0, 150), q=1, src="parts/scout_v4_cradle/make.py",
         dims="holds the Arducam case (lens first, lip along the top and sides, its own 2 side screws through the wall slots); channel for the SG90 horn; lowered level between the bracket and the horn; M3 x 10 through the insert nods freely; the camera is not drawn"),
]
HEAD_IDS = ("head", "cradle")


def quant(m):
    m = m.copy(); m.merge_vertices()
    lo, hi = m.bounds; span = np.maximum(hi - lo, 1e-6)
    q = np.round((m.vertices - lo) / span * 65535).astype(np.uint16)
    idx = m.faces.astype(np.uint16 if len(m.vertices) < 65536 else np.uint32)
    return dict(lo=lo.round(4).tolist(), span=span.round(4).tolist(), v=base64.b64encode(q.tobytes()).decode(),
                f=base64.b64encode(idx.tobytes()).decode(), w=("H" if idx.dtype == np.uint16 else "I"))


out = []
for p in P:
    m = p["mesh"]
    e = m.extents
    d = dict(id=p["id"], name=p["name"], kind=p["kind"], step=p["step"], ex=p["ex"], qty=p["q"], src=p["src"], dims=p["dims"],
             bbox=[round(float(v), 1) for v in e], at=[round(float(v), 1) for v in m.bounds[0]],
             mass=round(abs(float(m.volume)) * PCTG, 1) if p["kind"] == "printed" else None, mesh=quant(m))
    out.append(d)
tmpl = open(os.path.join(ROOT, "tools", "probe_bench_3d_template.html"), encoding="utf-8").read()
three = open(os.path.join(ROOT, "tools", "vendor", "three.min.js"), encoding="utf-8").read()
orbit = open(os.path.join(ROOT, "tools", "vendor", "OrbitControls.js"), encoding="utf-8").read()
pin = [p for p in P if p["id"] == "pinion"][0]["mesh"].bounds
meta = dict(reach=S.REACH, head=list(HEAD_IDS), mastz=S.THROAT["z1"],
            nod=dict(axis=[float(v) for v in S.AXIS], lo=S.HEAD["range"][0], hi=S.HEAD["range"][1], park=float(np.degrees(S.TILT))),   # the SG90's axis parked, its travel and the parked nod (deg)
            spool=dict(x=0.0, z=float(cz), r=float(S.SPOOL["hub"] + 0.7)),     # the drum's axis; r = hub radius + about half the coil's build
            pinion=dict(x=float((pin[0][0] + pin[1][0]) / 2), z=float((pin[0][2] + pin[1][2]) / 2), ratio=40 / 12))
page = (tmpl.replace("__DATA__", json.dumps(dict(parts=out, meta=meta), separators=(",", ":")))
        .replace("/*__THREE__*/", three.replace("</script", "<\\/script")).replace("/*__ORBIT__*/", orbit.replace("</script", "<\\/script")))
dst = os.path.join(ROOT, "artifacts", "probe_bench_3d.html")
open(dst, "w", encoding="utf-8").write(page)
print(dst, f"{len(page) / 1e6:.2f} MB", [(p['id'], p['bbox']) for p in out][:3])
