"""Scout v4 probe pressure roller tube and its leaf seats (10 Nov bench; tools/scout_v4_shape.ROLLER / LEAF, tools/probe_mast_sim.py blossom).
Drawn: python parts/scout_v4_probe_roller/make.py writes part.stl (drone frame, on the full coil: the tube, both saddles and carriers) and
print/scout_v4_probe_roller.stl, _saddle.stl, _carrier.stl.
  14 Nov (Spark: no bearings, the coupon's B dropped): an O8 x 19 tube (the blades' width) turning straight on its M3 x 60 axle in a
  plain bore sized like the spool's (the coupon's A1, 3.3: slides on free), 2.35 of wall; PCTG on steel, mu ~0.25 (E). A drop of light oil on the axle.
  14 Nov (Spark: no bought springs): each axle end, in the turret's pocket, carries a saddle (8.6 x 13 x 3.7, a half-round 3.4 groove on the
  axle, its flat face smooth for the leaf); behind it a Keystone-209-type leaf contact (ZCZQC B0C5D3XLBK) clipped on the 1.65 tab of a carrier
  (8.6 x 13 x 5.05: tab 1.65, a 0.9 slit 10 deep for the clip's back leg, a 2.5 back the M3 x 16 pushes).
  The tab is 1.65, under the 2 mm rule: the contact's clip sets it (1.52-1.78), like the camera's posts.
Print: the tube on end, no supports, 0.12 layers; the saddles groove up, the carriers on their side (the slit vertical), 0.12, 100 %."""
import math, os, sys
import numpy as np, trimesh
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scout_v4_probe_mech_lib import S, ROOT, cyl, minus, to_drone, save  # noqa: E402

R, W = S.ROLLER["r"], S.ROLLER["w"]
tube = minus(cyl(R, -W / 2, W / 2), [cyl(S.ROLLER["bore"] / 2, -W / 2 - 1, W / 2 + 1, n=48)])   # the coupon's A1
rr = S.SPOOL["hub"] + S.COIL + R; a = math.radians(S.ROLLER["ang"]); cx, cz = S.SPOOL["c"]
L = S.LEAF; VX, VY, ZS = 8.6, 13.0, 3.7                                          # the pocket is 9.0 x 13.4


def bx(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]])


def ycyl(r, y0, y1, n=48):
    c = cyl(r, y0, y1, n=n); c.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0])); return c   # local z -> -y... axis along y


saddle = minus(bx(-VX / 2, VX / 2, -VY / 2, VY / 2, 0.0, ZS), [ycyl(1.7, -VY, VY)])   # local: x tangential, y the axle, z radial out from the axle's centre


def carrier(tab, slit, back=2.5, depth=10.0):
    blk = bx(-VX / 2, VX / 2, -VY / 2, VY / 2, 0.0, tab + slit + back)
    return minus(blk, [bx(-VX, VX, VY / 2 - depth, VY, tab, tab + slit)])            # the slit open at +y: the contact clips over the tab's +y edge, its leaf toward -z


carrier1 = carrier(1.65, 0.9)
u = np.array([math.cos(a), 0, math.sin(a)]); v = np.array([-math.sin(a), 0, math.cos(a)])
yi = W / 2 + 0.5 + L["wall"]; yc = yi + L["pocket_y"] / 2


def pose(m, s, sy):
    """local (x tangential, y along the axle, z radial) at radial s from the spool's axis, the +y or -y pocket (its open slit end outward)"""
    d = m.copy(); M = np.eye(4); M[:3, 0] = -v; M[:3, 1] = [0, 1, 0]; M[:3, 2] = u
    if np.linalg.det(M[:3, :3]) < 0:
        M[:3, 0] = v
    if sy < 0:
        d.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [0, 0, 1]))
    d.apply_transform(M); d.apply_translation([cx, sy * yc, cz]); d.apply_translation(u * s); return d


view = [to_drone(tube, cx + rr * math.cos(a), cz + rr * math.sin(a))]
for sy in (1, -1):
    view += [pose(saddle, rr, sy), pose(carrier1, rr + ZS + 2.6, sy)]           # the leaf (4.6 free, E) pressed 2.0 on the full coil
pr = tube.copy(); pr.apply_translation([0, 0, W / 2])
save("scout_v4_probe_roller", pr, trimesh.util.concatenate(view), "on end, ~10 min")

import subprocess
for nm, m, rot in (("saddle", saddle, (math.pi, [1, 0, 0])), ("carrier", carrier1, (math.pi / 2, [0, 1, 0]))):
    p_ = m.copy(); p_.apply_transform(trimesh.transformations.rotation_matrix(rot[0], rot[1])); p_.apply_translation(-p_.bounds[0])
    if nm == "saddle":
        p_ = m.copy(); p_.apply_translation(-p_.bounds[0])                     # groove up: z 0 is the flat leaf face
        p_.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0])); p_.apply_translation(-p_.bounds[0])
    assert p_.is_watertight and p_.is_volume, nm
    f = os.path.join(ROOT, "print", f"scout_v4_probe_roller_{nm}.stl"); p_.export(f)
    sc = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "solid_check.py"), f], capture_output=True, text=True)
    print(f"scout_v4_probe_roller_{nm}: {p_.volume / 1000:.2f} cm3, {np.round(p_.extents, 1).tolist()} mm as printed, solid check {'PASS' if sc.returncode == 0 else 'FAIL ' + sc.stdout[-600:]}")
