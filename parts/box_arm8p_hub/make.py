"""Swap arm v8 PROTOTYPE hub (15 Nov 2026): drawn, the first print (the engine setup parts/box_arm8_hub/part.py is kept for OPTIMISE, after Spark's tests).
Geometry: parts/box_arm8/make.py hub_proto(): the setup's interfaces exactly (two 6010-2RS pressed in the sleeve, o 80.3 from the fit table; the GT2 150T ring
and the detent's twelve notches on it; each rail's seat with four bolts (below); each head stepper's face plate; each screw's 4 mm thrust
wall between its two F8-16M), joined by solid sections: the ring to Y 33.25, a 45 deg cone from there to the plate's face (r 68, a 2 mm rim), a 40 x 14 keel
under each rail out to r 87.5, an 8 mm slab under each screw drive, a cradle either side of each thrust wall. Less every cut of the setup.
Detent roller (15 Nov, the assembly check: the 13 Nov run stood 5.3 mm3 in the 623ZZ): nothing of the hub stands outside the band's own surface (r 49.25, the
roller's track) from its stub end to Y 33.25, 0.95 (fit table "clear") past the detent arm; the setup's room and keep-out are cut the same way.
Rail bolts (15 Nov; two M5 into inserts a rail read 0.62, over the project's 0.5): four a rail, each head on an o 10 washer. u 36 and 52 (over the bearings and the
cone, nothing reachable behind): M5 x 12 into M5 heat-set inserts, o 6.4 x 8. u 64 and 77 (outside the cone): M5 x 25 through rail and keel to nylocs on o 15 washers
in o 15.6 pockets in the keel's back (seat at Y 43, 11 of keel over it; the screw tips end at Y 36, 2.8 over the detent arm's lane).
Hand calc (python parts/box_arm8p_hub/make.py prints it, make.json; index = stress / (PCTG allowable / SF 4 flight, 2.5 misuse); 0.5 is the limit; every case of box_arm8_lib.cases):
  sleeve under the cone, across the layers (A 2484 mm2, W 50737 mm3): 0.08 (insert off square)
  rail bolts: the M5 inserts at 1500 N (E) 0.38 (insert off square, 230 N); the through bolts' o 15 washers 0.05, through the keel 0.03; heads on the printed rail 0.27
  keel through the outer bolt's pocket (W 953 mm3): 0.43 (insert off square)
  thrust wall in its cradle: 0.35 (dropped pack, 150 N on the screw)        ring teeth at the axle's stall: 0.11
Print: stub end down (the ring's 2555 mm2 on the bed, bearing bore upright and round), tree supports from the bed under the keels' ends and bolt pockets, the slabs and the
stepper walls (the cone itself needs none); 0.2 layers, 4 walls, 25 % gyroid, PCTG at PETG + 10 C; 332 g solid, ~16 h (E). 160.4 x 175 x 70 on the 180 bed.
Assembly path: the bearings pressed in from the stub end, then the hub slid on the stub's spigot along the axle (systems/swap_arm.assembly.json "hub onto the stub")."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import box_arm8p_lib as P
P.save("box_arm8p_hub", P.M().hub_proto(), P.rot([1, 0, 0], 90), "stub end down, tree supports under keels, slabs and stepper walls", P.hub_check)
