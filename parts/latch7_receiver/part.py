"""Scout battery receiver (latch v7): the setup is parts/latch7_recv_lib.py, shared with the Overseer's.
h 1.2: the receiver's box (68 x 111 x 54, hollow) is 295k cells there (1.0: 484k, refused). 36 cm3 on 26 drawn: about 76 g: 36 cm3 on 26 drawn since 14 Nov (drawn whole it was 95 g; runs at 34 and 40, 65.9 and 74.1 g: both gates failed at the tail feet both times, see make.scout_feet: the feet's gussets are drawn now); 28 left the 118 N jammed-bolt case at ~0.93 thinned (room-full 0.39).
gate_member off, as on the Overseer's: the side walls' room is 5.0 thick (cartridge inside, the drone's cage outside), under the member the gate's erosion asks for
(with the feet's wider leg room the engine routed 5.3 and the audit's env_neck refused the walls); members are the engine's 3.2, the solid gate judges as always.
14 Nov, run on 4d3d93cf at 36: 73.5 g, solid check PASS, 0.64 across the layers at the lead notches' roots in the hold-down (0.77 before the final pass; the room filled solid
read 0.43). Two causes: the key's seat block had 3.5 of ligament behind its notch (make.HOLD sc_len: 12 now, as the Overseer's), and 36 cm3 was 52 % of the room,
too little to join that root to the leg. 46 cm3 (67 % of the room), about 86 g.
14 Nov, run on 6789f02a: PASS 0.47 / 87.3 g, but its print mesh stood on 163 mm2 (the tail bosses' ends) with 1,330 mm2 of generated deck 0.4-0.5 above the bed:
a drawn 4 x 2.5 flat round the mount plane's two room regions now (latch7_recv_lib.bed_rim, 1,310 mm2 on the bed, bed_min_mm2 1100, Scout only), 3.3 cm3 more drawn
(28 % of the part), 46 cm3 generated (70 % of the room), about 91 g.
14 Nov, run on ca860675: 92.5 g, solid check PASS, bed 1,310 mm2 drawn, but 0.502 as built (0.52 in the field) across the layers at the lead foot's hold-down
notch root in the every-swap hold-down, the spot that read 0.524 on 48814dfb and 0.47 on 6789f02a: the root joined to the leg on the budget's margin (room filled
solid 0.39, thinned 0.56). 50 cm3 (76 % of the room), about 97 g."""
from parts.latch7_recv_lib import setup_for, POSE_OF
SPEC = dict(h=1.2, gen_cm3=50.0, max_worst=0.5, settings=dict(near_sym=True, gate_member=False))
setup = setup_for("scout", "latch7_receiver")
POSE = POSE_OF("scout")       # part (print pose, mount plane on the bed) -> cartridge coords
