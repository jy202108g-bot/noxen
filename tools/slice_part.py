#!/usr/bin/env python3
"""Slice a print mesh for Spark's A1 mini printers (Gideon, Jarvis) with OrcaSlicer's CLI. Writes a .gcode.3mf; never sends or prints.

    python tools/slice_part.py <mesh.stl> [--out DIR] [--process 0.12|0.2] [--supports] [--setup]

Profiles in print/profiles/ (user presets: PCTG 3D-Fuel Pro @BBL A1M, 0.12mm PCTG @BBL A1M, machine = A1 mini 0.4 nozzle). They
inherit Orca's BBL system presets; the Orca CLI cannot resolve `inherits` for user files, so this flattens each chain first.
--setup downloads OrcaSlicer portable (v2.5.1) and the BBL profiles (sparse git clone) into $NOXY_SLICER (default ~/nox/data/slicer).
"""
import argparse, json, os, subprocess, sys, glob, shutil

BASE = os.environ.get("NOXY_SLICER") or os.path.join(os.path.expanduser("~"), "nox", "data", "slicer")
PROF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "print", "profiles")
EXE = os.path.join(BASE, "orca", "orca-slicer.exe")
DATA = os.path.join(BASE, "data2")


def index():
    ix = {}
    for f in glob.glob(os.path.join(DATA, "system", "BBL", "*", "*.json")):
        try:
            d = json.load(open(f, encoding="utf8"))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("name"):
            ix[d["name"]] = d
    return ix


def flat(d, ix):
    if d.get("inherits"):
        p = flat(ix[d["inherits"]], ix)
        p.update({k: v for k, v in d.items() if k not in ("inherits", "from", "instantiation")})
        d = p
    d = dict(d)
    # "include" lists the machine's own start / end / layer-change / time-lapse / filament-change g-code templates. The CLI does
    # not resolve them for a flattened file, so without this the generic 256 mm machine g-code (purge line to Y200, parking at
    # Y265) is used and the A1 mini's moves leave its 180 mm bed (jobs 815 and 823).
    for inc in d.pop("include", []) or []:
        d.update({k: v for k, v in ix[inc].items() if k not in ("type", "name", "from", "instantiation", "inherits", "setting_id")})
    return d


def slice_mesh(mesh, out, process="0.12", supports=False, support_angle=None):
    """Slice one mesh (already posed on the bed) into <out>/<mesh name>.gcode.3mf. Returns {ok, log}."""
    ix = index()
    out = os.path.abspath(out); os.makedirs(out, exist_ok=True)
    tmp = os.path.join(out, "_profiles"); os.makedirs(tmp, exist_ok=True)
    paths = {}
    for key, f in (("m", "a1mini_machine.json"), ("p", "pctg_process_0.12.json"), ("f", "pctg_filament.json")):
        d = flat(json.load(open(os.path.join(PROF, f), encoding="utf8")), ix)
        d["from"] = "User"
        if key == "p":
            if process != "0.12":
                d["layer_height"] = process; d["name"] = d["print_settings_id"] = "%smm PCTG @BBL A1M" % process
            if supports:
                d["enable_support"] = "1"
                if support_angle is not None: d["support_threshold_angle"] = str(int(support_angle))
        if key == "m": d["name"] = d["printer_settings_id"] = "Bambu Lab A1 mini 0.4 nozzle"
        paths[key] = os.path.join(tmp, f); json.dump(d, open(paths[key], "w", encoding="utf8"), indent=1)
    gname = os.path.splitext(os.path.basename(mesh))[0] + ".gcode.3mf"
    stale = os.path.join(out, gname)
    if os.path.exists(stale): os.remove(stale)
    cmd = [EXE, "--datadir", DATA, "--slice", "1", "--load-settings", paths["m"] + ";" + paths["p"],
           "--load-filaments", paths["f"], "--export-3mf", gname, "--outputdir", out, os.path.abspath(mesh)]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    return dict(ok=r.returncode == 0 and os.path.exists(stale), log=(r.stdout or "")[-1500:] + (r.stderr or "")[-1500:], returncode=r.returncode)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("mesh"); a.add_argument("--out", default="sliced")
    a.add_argument("--process", default="0.12"); a.add_argument("--supports", action="store_true")
    a = a.parse_args()
    r = slice_mesh(a.mesh, a.out, a.process, a.supports)
    print(r["log"])
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
