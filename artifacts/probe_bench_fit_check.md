# Probe bench: collision and fit check (22 Nov 2026)

Checked: tools/assembly_check.py scout_v4_bench (PASS: 14 parts, 6 of 6 paths clear, 3 of 3 mates), the solid check on every print file (all PASS), and my own distance scan of every pair on the drone-frame meshes.

## Two fits that failed (FIXED 23 Nov 2026: screws changed to M3 x 50 + nyloc and 4 x M3 x 8; assembly check and solid check re-run, PASS)

1. **Spool axle M3 x 40 is too short.** The axle bore runs from the -y wall's outer face (y -25.95) to the +y wall's outer face (y +18.5): 44.45 mm. A 40 mm screw is 4.45 mm short of even coming out, and the nyloc nut needs about 4 more.
   Fix: M3 x 50 + nyloc (reaches 48.45 incl. the nut, head outside). Change the page's "1x M3 x 40" and the parts list row to M3 x 50. (The M3 kit does not hold x 40 or x 50 anyway: buy the search link.)
2. **Turret bolts M3 x 10 bottom out.** Turret floor at the bolts is 4.07 thick (z 24.5 to 28.57), the base's insert hole is 6.0 deep with a 5.7 insert: a 10 mm screw reaches 0.05 mm from the hole's floor, 0.23 past the insert. If an insert sits 0.3 shallow the screw stops on the post and the turret is not clamped.
   Fix: M3 x 8 (3.9 mm engaged in the 5.7 insert, about 8 threads) for the four turret bolts; keep M3 x 10 for the camera idler.

## Tight but passing (measured minimum gap between meshes)

| Pair | Gap mm | Note |
|---|---|---|
| turret / N20 motor | 0.10 | the thinnest. Motor body is a 300 rpm drawing (E); the real 100 rpm unit may be a hair bigger. Printed holes run 0.1-0.2 small. Check by hand on the first fit; file the pocket 0.2 if it grips. |
| turret / roller tubes | 0.15 | tubes turn free on the rod: check by hand |
| pinion / motor | 0.15 | intended press fit (D bore 3.3 / 2.8, coupon-measured) |
| turret / pinion | 0.20 | ok |
| spool / motor | 0.20 | ok |
| turret / spool | 0.50 | intended mate gap |
| head frame / cradle | 0.50 | intended mate gap |
| head frame / camera case | 0.51 | ok |
| servo / horn | 0.25 | ok |

Touching by design, not clashes: bench base / turret (seat), head frame / servo (tabs stop on the ring), cradle / horn, cradle / camera (case on the lip), LED bars on the case, head frame on the turret's throat top (z 73.0, 0.0 gap: the parked head rests on the throat; nods -20..+90 sweep clear).
Overlaps by design, inside the allowed volume: spool coil over the drum hub 303 mm3 (limit 320), blades on the coil tangent 11.4 (15), spool gear and pinion teeth 5.7 (8: arbitrary tooth phase).

## Assembly order and reach (assembly check, all pass)

1. Turret with spool, gears, N20, drum, roller, feed lowered 90 mm onto the base: clear, 0.2 gap.
2. Blades into the head frame's clip (16 mm): clear.
3. SG90 slid +y into the frame's ring (30 mm): clear.
4. Camera into the cradle in hand (32 mm): clear.
5. Cradle lowered onto the horn: clear.
6. Head nods -20 to +90: clear.
Screw reach: the PH1 driver (shaft 75 mm or longer) is only checked by the sheet's note, not by a swept tool path; the four turret bolts open upward and the axle's nut is on the +y outside face, both open.

## Components and where each dimension comes from

| Part | Source | Status |
|---|---|---|
| Bench base, bench turret, spool, pinion, roller tubes and saddles S1-S3, head frame, cradle | drawn make.py, bores from systems/fit_table.json (Spark's coupons) | real (M) for bores; G gear centre 20.9 not yet tried on the bench (E) |
| N20 6 V 100 rpm (B07MZH851L) | body drawn from a 300 rpm Augiimor sketch: gearbox 12 x 10 x 10, can 12 x 10 x 17, shaft 3.0 / 2.5 D (shaft = coupon M) | **GUESSED (E)**: body length and the 100 rpm gearbox not measured. Stall 2.2 kg cm is a listing figure (E) |
| SG90 (Miuzei B0FGQ432JP) | typical drawing 22.4 x 12.5 x 22.8, tabs 32.8 | **GUESSED (E)**: clone bodies vary by 0.3; ring slide gap is 0.25 |
| Arducam 12MP (B0FLX58WKZ) | listing gives no case depth; coupon C: fits 12 to 18 deep, drawn for 18; case 36 square (E) | **partly guessed**: depth by coupon (M), the rest E; measure on arrival |
| Clearhill LED bars | 25 x 8 mm (listing, E) | E |
| ZCZQC leaf contact | 7.9 x 12.1 x 0.30, free height 4.6, 1.5 to 4 N/mm | **GUESSED (E)**: Spark has 50, measure one with calipers. The leaf, the M3 idler and the 5 inserts are not drawn in the check |
| Tape blade (Topzone B00ZMHXV4I) | 19 mm wide (listing), thickness 0.13 | **GUESSED (E)**: patents give 0.11 to 0.15; blade cup radius is coupon T (M) |
| PTFE ribbon 30 AWG x 6 | ribbon thickness 0.81 (E) | E |
| Carbon rod O3 x 23.8, M3, M2, M1.6 screws, inserts | fit table and standard sizes | M3 x 40 wrong (above); M1.6 x 4 and M2 x 4 / x 6 are standard, "CHECK on hand" |

No missing Amazon listing except the M3 x 50 screw (search link only) and the generic items (epoxy, CA, oil, PH1 driver, M1.6 / M2 assortment: search links). The Amazon pages themselves were not opened (refused to workers).

## Not checked / limits

- The roller's viewing mesh (assembled on the coil) fails the solid check by design; the files that print (tube, S1, S2, S3) all pass.
- Real N20, SG90, camera and leaf were not measured; only drawn sizes are checked. Re-run the check when you have measured values.
- Fixes above are applied to the make.py notes, the 3D page text and systems/parts-list.md (23 Nov). artifacts/probe_bench_assembly.html has no screw sizes to change. The M3 x 50 and x 8 screws still need buying (not in the M3 kit).
