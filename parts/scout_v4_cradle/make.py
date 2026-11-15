"""Scout v4 probe camera cradle, PROTOTYPE (15 Nov, drawn; was generated: Spark's bench print gave the camera no way in and would not go
on the head frame). Holds the Arducam 12MP AF camera in its metal case (36 square, 12..18 deep, bracket off) and nods on the SG90's
horn (+y) and the idler screw (-y). Interfaces and the assembly order: parts/scout_v4_head_lib.py.
Drawn: python parts/scout_v4_cradle/make.py writes part.stl (the drone's frame, parked), print/scout_v4_cradle.stl and preview.png.
  Sleeve: the case's four sides, 36.9 inside (0.45 a side), 12 long, top and bottom walls 2.2, side walls 3.35 (to WY 21.8, flat for the
    bed); a 3.0 lip on its front rim's top and upper sides (none along the bottom: the nod's clearance over the plate); the case slides in
    from behind until its front meets the lip (lens fixed for any depth), its own side screws (up to M3) clamp it through a 3.4 slot
    along each side wall, their heads in a recess. Open behind: the case and its plug pass the axis between the walls (insertion lane
    cut 36.9 square from the lip to 40 behind the axis).
  Side walls 3.35 thick, from the sleeve back past the axis (x -9..8, z -13..19): +y carries the horn's arm in a 1.0 x 7.6 channel open
    at the bottom edge (the cradle drops onto the horn), a 5.2 slot below the axis for the horn's centre screw head, and a 1.4 slot
    pilot at r 8.5..15.5 above it for two of the horn's small self-tappers (any of its arm's holes there); -y an O10 boss to 23.0 with
    the A1 3.3 bore the M3 idler turns in.
Hand calc (PCTG E: 45 MPa in-layer, ~20 across, topo/material.py; loads tools/scout_v4_shape, systems/scout_v4.head_load.json):
  - stall 1.8 kg cm (0.18 N m) through the horn: the arm bears on the channel's flanks (1.0 x ~16 a side) and two screws at r 10..14:
    0.18 / 0.012 = 15 N, 8 N a screw in a 3.35 wall; bearing 15 / 16 mm2 < 1 MPa. Margin > 20.
  - 35 g crash of the camera and LEDs (48.5 g): 16.6 N at the case's middle (10.5 ahead of the axis), half a wall: 8.3 N x 10.5 =
    87 N mm on a 3.35 x 32 section (z): 6 M / (t d^2) = 0.15 MPa. Margin > 100.
  - head-first crash 260 N: the cradle turns down (the SG90 slips) and the case's bottom front edge lands on the frame's plate through
    the sleeve's 2.2 bottom wall: 260 N over the edge's 36.9 x ~2 = 3.5 MPa compression in-layer. Margin ~13. The pivots carry 18 N.
  - handling: a 20 N finger push on the case's front: 20 x 20 = 400 N mm into the two walls at the axis: 200 / (3.35 x 32^2 / 6) =
    0.35 MPa. Margin > 50.
Print: on its +y face (the horn's side) flat on the bed: the walls' bending is in their layers; no supports (the channel and the
recesses bridge 7.6); 0.2 layers, 4 walls, 40 % infill (E ~1 h)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "parts"))
import numpy as np, trimesh                                                                     # noqa: E402
from parts.scout_v4_head_lib import (S, box, U, ycyl, to_tm, place, H, SI, SO, F0, D0, D1, LIP, XB, WY, CH, CHW, Y_BOSS,   # noqa: E402
                                     BORE, PCTG)


def cradle_local():
    """the cradle in its own frame (the axis at the origin), as a manifold"""
    sleeve = (box(XB, F0 + 2.0, -WY, WY, -SO, SO)
              - box(F0 - 1.0, F0 + 3.0, -SI + LIP, SI - LIP, -SI + LIP, SI - LIP)              # the lip's window
              - box(F0, F0 + 3.0, -WY - 1, WY + 1, -SO - 1, -SI + LIP))                        # no lip along the bottom
    walls = [box(-9.0, XB + 0.5, *((SI - 0.01, WY) if s > 0 else (-WY, -SI + 0.01)), -13.0, 19.0) for s in (1, -1)]
    boss = ycyl(0, 0, 5.0, -Y_BOSS, -WY + 0.5)
    solid = U([sleeve, boss] + walls)
    cuts = [box(-40.0, F0, -SI, SI, -SI, SI),                                                   # the case's lane: from 40 behind the axis to the lip
            box(F0, 80.0, -SI + LIP, SI - LIP, -SI + LIP, SI - LIP)]                            # the lens's view forward
    for s in (1, -1):
        cuts.append(box(XB + 1.5, F0 - 1.5, *((SI - 1, WY + 1) if s > 0 else (-WY - 1, -SI + 1)), -1.7, 1.7))   # the side screw's slot
        cuts.append(box(XB - 1.0, F0 + 0.5, *((SO, WY + 3) if s > 0 else (-WY - 3, -SO)), -3.5, 3.5))           # its head's recess
    for sz in (1, -1):                                                                          # the LED bars' windows and their light forward
        cuts.append(box(F0 - 8.6, 80.0, -13.0, 13.0, *((H - 0.5, SO + 1) if sz > 0 else (-SO - 1, -(H - 0.5)))))
    cuts += [box(-CHW / 2, CHW / 2, WY - CH, WY + 1, -14.0, 17.5),                              # the horn's channel, open at the bottom edge
             box(-2.6, 2.6, SI - 1, WY + 1, -14.0, 0.0), ycyl(0, 0, 2.6, SI - 1, WY + 1),       # its centre screw's head, in from the bottom edge
             box(-0.7, 0.7, SI - 1, WY + 1, 8.5, 15.5),                                         # the horn screws' slot pilot
             ycyl(0, 0, BORE / 2, -Y_BOSS - 1, -SI + 1)]                                        # the idler's bore
    return solid - U(cuts)


if __name__ == "__main__":
    c = cradle_local()
    drone = to_tm(place(c, np.degrees(S.TILT)))
    pr = to_tm(c); pr.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])); pr.apply_translation(-pr.bounds[0])   # +y face on the bed
    from scout_v4_probe_mech_lib import save                                                    # noqa: E402
    save("scout_v4_cradle", pr, drone, "+y face (the horn's side) down, no supports, ~1 h")
    from topo.build import render
    v = pr.volume / 1000
    render(pr, os.path.join(HERE, "preview.png"), title="scout_v4_cradle (drawn prototype)", info=f"{v * PCTG:.1f} g | as printed: +y face down")
