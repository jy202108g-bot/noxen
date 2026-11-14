"""Scout v4 probe pressure roller: its two tubes and the leaf's saddle (14 Nov, probe stream; tools/scout_v4_shape.ROLLER / LEAF / leaf_force,
tools/probe_mast_sim.py blossom).
Drawn: python parts/scout_v4_probe_roller/make.py writes part.stl (drone frame, on the full coil: both tubes, the rod, the S2 saddle) and
print/scout_v4_probe_roller.stl (a tube: print 2), print/scout_v4_probe_roller_saddle_S1.stl, _S2.stl, _S3.stl.
  Tubes: O8 x 4.5 on the O3 carbon rod (23.8 long) in the coupon's A1 3.3 bore (2.35 wall), one each side of the saddle, |y| 4.75..9.25; PCTG on carbon mu ~0.25 (E).
  Saddle (13 tangential x 8.6 along the rod): a half-round O3.4 groove on the rod's middle, its body over the rod, a slit 10 deep open at one
  tangential end for the leaf clip's back leg, and the tab the Keystone-209-type contact (ZCZQC B0C5D3XLBK) clips on; the leaf presses the
  turret pocket's fixed end wall. No screw: the set sets the force (leaf_force(), 1.5..4 N/mm a leaf, E):
    S1 body 2.0, one leaf (tab 1.65): 1.5 mm of leaf travel on the empty coil, 3.1 on the full
    S2 body 2.5, one leaf (tab 1.65): 2.0 / 3.6 (the leaf is flat at ~4)
    S3 body 2.8, one leaf: 2.3 / 3.9, at the leaf's flat on the full coil: only if S2 lets the coil lift (two contacts nested need a 1.05 tab: the solid check refuses it, 1.0 wall)
  The tab is under the 2 mm rule: the contact's clip sets it (as the camera's posts and the old carrier's tab).
Print: tubes on end, no supports, 0.12 layers, 100 %; the saddles on their side (the slit vertical), 0.12, 100 %."""
import math, os, sys
import numpy as np, trimesh
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scout_v4_probe_mech_lib import S, ROOT, cyl, minus, save  # noqa: E402

R, MID, W2 = S.ROLLER["r"], S.ROLLER["mid"], S.ROLLER["w"] / 2
LT = W2 - MID                                                                    # 4.75
tube = minus(cyl(R, 0.0, LT), [cyl(S.ROLLER["bore"] / 2, -1, LT + 1, n=48)])
L = S.LEAF; SD = L["saddle"]; VT, VY = SD["t"], SD["y"]


def bx(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]])


def ycyl(r, y0, y1, n=48):
    c = cyl(r, y0, y1, n=n); c.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0])); return c   # along -y.. +y


def saddle(body, n):
    """local: x tangential, y along the rod, z radial out from the rod's centre (z 0); the tab's top face is where the leaf sits"""
    tab = SD["tab"] - 0.6 * (n - 1); slit = SD["slit"] + 0.3 * (n - 1)
    z1 = 1.5 + body; top = z1 + slit + tab
    blk = bx(-VT / 2, VT / 2, -VY / 2, VY / 2, 0.0, top)
    return minus(blk, [ycyl(1.7, -VY, VY), bx(VT / 2 - 10.0, VT, -VY, VY, z1, z1 + slit)]), top


a = math.radians(S.ROLLER["ang"]); cx, cz = S.SPOOL["c"]
u = np.array([math.cos(a), 0, math.sin(a)]); v = np.array([-math.sin(a), 0, math.cos(a)])
rr = S.SPOOL["hub"] + S.COIL + R                                                 # the rod's centre on the full coil


def pose(m, s):
    d = m.copy(); M = np.eye(4); M[:3, 0] = v; M[:3, 1] = [0, 1, 0]; M[:3, 2] = u
    if np.linalg.det(M[:3, :3]) < 0:
        M[:3, 0] = -v
    M[:3, 3] = [cx + u[0] * s, 0, cz + u[2] * s]; d.apply_transform(M); return d


view = []                                                                        # the tubes are built along local z (pose maps local z to u): laid along y first
for y0 in (MID, -W2):
    t_ = tube.copy(); t_.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0])); t_.apply_translation([0, y0, 0])   # local z -> y (0..LT), then from y0
    t_.apply_translation([0, -t_.bounds[0][1] + y0, 0])
    view.append(pose(t_, rr))
rod = ycyl(1.5, -L["slot_y"][1] + 0.2, L["slot_y"][1] - 0.2, n=24); rod.apply_translation([0, -rod.bounds[0][1] - (L["slot_y"][1] - 0.2), 0])
view.append(pose(rod, rr))
sd2, top2 = saddle(*SD["sets"]["S2"]); view.append(pose(sd2, rr))
pr = tube.copy()
save("scout_v4_probe_roller", pr, trimesh.util.concatenate(view), "on end, print 2, ~6 min each")

import subprocess
for nm, (body, n) in SD["sets"].items():
    m, top = saddle(body, n)
    p_ = m.copy(); p_.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])); p_.apply_translation(-p_.bounds[0])   # on its side: the slit vertical, its open end up... the y face down
    assert p_.is_watertight and p_.is_volume, nm
    f = os.path.join(ROOT, "print", f"scout_v4_probe_roller_saddle_{nm}.stl"); p_.export(f)
    sc = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "solid_check.py"), f], capture_output=True, text=True)
    print(f"scout_v4_probe_roller_saddle_{nm}: {p_.volume / 1000:.2f} cm3, {np.round(p_.extents, 1).tolist()} mm as printed, {top:.2f} from the rod's centre to the tab's face, "
          f"{n} leaf, solid check {'PASS' if sc.returncode == 0 else 'FAIL ' + sc.stdout[-600:]}")
