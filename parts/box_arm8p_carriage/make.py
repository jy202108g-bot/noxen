"""Swap arm v8 PROTOTYPE carriage (15 Nov 2026), two per arm: drawn, the first print (the engine setup parts/box_arm8_carriage/part.py is kept for OPTIMISE).
Geometry: parts/box_arm8_lib.py carriage_proto(): the setup's room solid (the 9.85 wheel plate, the 13.7 x 23.6 spine with the MGN12 rail's seat, the rib
between the wheel pair (its ends run on round the wheels beside the spine), the 44 wide strap to the third wheel, the pick-up stop) with its interfaces.
MGN12 rail: four M3 x 25 through the rail and the spine to M3 nylocs on o 9 washers, slid into slots in the spine's screw side (the nyloc's slot 5.7 wide: it cannot
turn; 2.4 of spine behind it). They were M3 heat-set inserts: 0.84, over the project's 0.5. The rail's own hole pattern is as it was (25 apart from 12.5 in, E).
Wheel axles: each an M5 x 20 button head from behind the wheel, an o 10 x 1 washer on the inner ring, a washer sunk in the plate's back, the plate's 3.15 web, the
same washer and an M5 nut sunk in its front; the wheel pair's washers are o 20 x 1.2 fender washers (o 15 read 0.65), the third wheel's o 15, its bore and recesses
slots, +-1.0 across the rail: pushed home on the rail, then tightened.
Hand calc (index = stress / (PCTG allowable / SF); 0.5 is the limit; python parts/box_arm8p_carriage/make.py prints every row, make.json):
  spine and plate, every section 1 mm apart between a wheel's boss and the MGN block: 0.45 (dropped pack, u 27); at u 28 / u 64 as before: 0.41 / 0.35 (were 0.54 / 0.53)
  strap to the third wheel: 0.10        axle pried on the plate through its washers: 0.30 (third wheel; the pair 0.28), washers through the web: 0.16
  MGN rail's four M3 on o 9 washers: 0.35 (insert off square, 301 N a bolt); the screws themselves 0.33
Print: the rail seat's plane down (everything ends on it: 102.5 x 88.3 on the bed, 23.6 tall), no supports (the nut slots bridge 5.7); 0.2 layers, 4 walls, 40 % gyroid; 96 g, ~4 h (E).
Assembly path: wheels, axles and the MGN rail on at the bench, then rolled onto the V rail from its tip ("carriage A / B onto its rail")."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import box_arm8p_lib as P
P.save("box_arm8p_carriage", P.L.carriage_proto(), P.rot([1, 0, 0], -90), "rail seat's plane down, no supports", P.carriage_check)
