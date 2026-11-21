#!/usr/bin/env python3
"""The safe-area gate for every sliced A1 mini file (Gideon / Jarvis): refuses a file whose toolpaths come closer than SAFE mm to the
180 mm plate edge. Spark 21 Nov: prints sat against the plate edge and their supports were cut off.

    python tools/plate_safe.py <file.gcode.3mf> [--safe 5]      # exit 1 and the reason when refused

Every printing AND travel move from the first layer to the end routine counts: walls, supports, brim, skirt, travels. Only the machine's
own stock moves (the "safe pos" park left of the bed, its wipe station) are skipped. Used by tools/plate.py (a plate is not ready
otherwise) and tools/bambu_send.py (a send is refused otherwise); the two never differ because both call safe_check().
"""
import re, sys, zipfile

BED = 180.0
SAFE = 5.0      # mm from every plate edge: nozzle, supports, brim and skirt all stay inside [SAFE, BED - SAFE]


def read_gcode(path):
    z = zipfile.ZipFile(path)
    names = [n for n in z.namelist() if n.endswith(".gcode")]
    return z.read(names[0]).decode("utf8", "replace") if names else ""


def extent(g):
    """(xmin, xmax, ymin, ymax, zmax, nmoves) of every non-stock move between the first layer and the end routine."""
    ax, ay, zmax, started, park = [], [], 0.0, False, False
    for ln in g.splitlines():
        if ln.startswith("; SKIPTYPE: timelapse"):      # the stock per-layer timelapse park (X0 / X-13) up to its M623
            park = True
        elif park and ln.startswith("M623"):
            park = False
        if park:
            continue
        if ln.startswith(";LAYER_CHANGE") or ln.startswith("; CHANGE_LAYER"):
            started = True
        if ln.startswith("; MACHINE_END_GCODE_START") or ln.startswith("; EXECUTABLE_BLOCK_END") or ln.startswith("M140 S0 ; turn off bed") or "pull back filament" in ln:
            started = False
        if not started or ln[:2] not in ("G0", "G1", "G2", "G3") or ln[2:3] != " ":
            continue
        code = ln.split(";")[0]
        mx = re.search(r" X(-?[\d.]+)", code); my = re.search(r" Y(-?[\d.]+)", code); mz = re.search(r" Z(-?[\d.]+)", code)
        if "safe pos" in ln or (mx and float(mx.group(1)) < -5):
            continue
        if mz:
            zmax = max(zmax, float(mz.group(1)))
        if mx: ax.append(float(mx.group(1)))
        if my: ay.append(float(my.group(1)))
    if not ax or not ay:
        return None
    return min(ax), max(ax), min(ay), max(ay), zmax, len(ax)


def safe_check(g, safe=SAFE):
    """(ok, why, (xmin, xmax, ymin, ymax) or None)."""
    if not g:
        return False, "no g-code inside: slice it first", None
    e = extent(g)
    if e is None:
        return False, "no printing moves found", None
    x0, x1, y0, y1, zmax, _ = e
    box = (x0, x1, y0, y1)
    lo, hi = safe, BED - safe
    if x0 < lo or y0 < lo or x1 > hi or y1 > hi:
        return False, ("toolpaths x %.1f..%.1f y %.1f..%.1f pass the safe area %.0f..%.0f mm (supports, brim, skirt and travels included): "
                       "re-lay the plate with tools/plate.py" % (x0, x1, y0, y1, lo, hi)), box
    if zmax > BED + 0.5:
        return False, "taller than the A1 mini's 180 mm (z %.1f)" % zmax, box
    return True, "inside the safe area: x %.1f..%.1f, y %.1f..%.1f mm (%.0f mm margin)" % (x0, x1, y0, y1, safe), box


def main():
    args = sys.argv[1:]
    safe = SAFE
    if "--safe" in args:
        i = args.index("--safe"); safe = float(args[i + 1]); del args[i:i + 2]
    bad = 0
    for p in args:
        ok, why, _ = safe_check(read_gcode(p), safe)
        print("%s  %s  %s" % ("ok  " if ok else "FAIL", p, why)); bad += not ok
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
