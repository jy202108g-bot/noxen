#!/usr/bin/env python3
"""Slice several queued parts as ONE plate for an A1 mini (Gideon / Jarvis), each part keeping its own queue settings. Never sends or prints.

    python tools/plate.py <plate.json> --out DIR

plate.json: {"name": "probe_plate1", "parts": [{"part": "scout_v4_probe_bench_base", "qty": 1, "layer": 0.16, "walls": 4, "infill": 100}, ...]}
Each part is posed like tools/prepare_part.py (least overhang), laid out on the bed with gaps for brim and supports, sliced with
print/profiles plus its own per-object layer height, walls, infill and supports (on only where it has overhang), and every part's
overhangs are checked against the g-code. Writes <out>/<name>.gcode.3mf and <out>/<name>.report.json.
"""
import argparse, json, os, re, sys, zipfile
import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prepare_part as pp
import slice_part

GAP = 12.0       # mm between footprints: 5 brim + support skirt + margin


def pose(spec, angle=40.0):
    path, name = pp.find_mesh(os.path.join(pp.ROOT, spec["mesh"]) if spec.get("mesh") else spec["part"])
    mesh = trimesh.load(path, force="mesh")
    best, _ = pp.orient(mesh, angle, keep=spec.get("keep_pose", False))
    m = best["mesh"]
    m.vertices -= [m.bounds[0][0], m.bounds[0][1], 0]          # corner at the origin
    oh, ohf = pp.overhang(m, angle)
    return m, oh, best


def layout(items):
    """Shelf-pack footprints on the 180 bed (tallest footprint first). Moves each item's mesh to its place."""
    order = sorted(range(len(items)), key=lambda i: -items[i]["mesh"].extents[1])
    x = y = row_h = 0.0
    M = 6.0
    x = y = M
    for i in order:
        m = items[i]["mesh"]; w, d = m.extents[0], m.extents[1]
        if x + w > pp.BED - M:
            x = M; y += row_h + GAP; row_h = 0.0
        if y + d > pp.BED - M:
            sys.exit("plate does not fit the bed")
        m.vertices += [x, y, 0]
        items[i]["xy"] = (x, y)
        x += w + GAP; row_h = max(row_h, d)


def write_3mf(items, path, name):
    """A Bambu-style 3mf: one object per instance, its mesh in bed coordinates, per-object settings in model_settings.config."""
    verts, objs = [], []
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    res, build, cfg = [], [], ['<?xml version="1.0" encoding="UTF-8"?>', "<config>"]
    for k, it in enumerate(items, 1):
        m = it["mesh"]
        v = "".join('<vertex x="%.5f" y="%.5f" z="%.5f"/>' % tuple(p) for p in m.vertices)
        t = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in m.faces)
        res.append('<object id="%d" type="model"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>' % (k, v, t))
        build.append('<item objectid="%d" transform="1 0 0 0 1 0 0 0 1 0 0 0" printable="1"/>' % k)
        cfg.append(' <object id="%d">' % k)
        cfg.append('  <metadata key="name" value="%s"/>' % it["label"])
        for key, val in it["opts"].items():
            cfg.append('  <metadata key="%s" value="%s"/>' % (key, val))
        cfg.append('  <part id="1" subtype="normal_part"><metadata key="name" value="%s"/></part>' % it["label"])
        cfg.append(" </object>")
    cfg.append("</config>")
    model = ('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<metadata name="Application">BambuStudio-01.10.00.00</metadata><resources>%s</resources><build>%s</build></model>' % ("".join(res), "".join(build)))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model); z.writestr("Metadata/model_settings.config", "\n".join(cfg))


def slice_3mf(f3, out, name):
    ix = slice_part.index()
    tmp = os.path.join(out, "_profiles"); os.makedirs(tmp, exist_ok=True)
    paths = {}
    for key, f in (("m", "a1mini_machine.json"), ("p", "pctg_process_0.12.json"), ("f", "pctg_filament.json")):
        d = slice_part.flat(json.load(open(os.path.join(slice_part.PROF, f), encoding="utf8")), ix)
        d["from"] = "User"
        if key == "m": d["name"] = d["printer_settings_id"] = "Bambu Lab A1 mini 0.4 nozzle"
        paths[key] = os.path.join(tmp, f); json.dump(d, open(paths[key], "w", encoding="utf8"), indent=1)
    gname = name + ".gcode.3mf"
    final = os.path.join(out, gname)
    if os.path.exists(final): os.remove(final)
    cmd = [slice_part.EXE, "--datadir", slice_part.DATA, "--slice", "1", "--load-settings", paths["m"] + ";" + paths["p"],
           "--load-filaments", paths["f"], "--export-3mf", gname, "--outputdir", out, f3]
    import subprocess
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    return dict(ok=r.returncode == 0 and os.path.exists(final), log=(r.stdout or "")[-1500:] + (r.stderr or "")[-1500:], path=final)


def check_plate(items, res, out, name):
    """Whole-plate g-code checks plus, per object, that every overhang has support or model material under it."""
    checks = [("slice ran without error", res["ok"], "" if res["ok"] else res["log"][-200:])]
    stats = {}
    if not res["ok"]:
        return dict(part=name, checks=checks, stats=stats, ready=False)
    g = pp.read_gcode(res["path"])
    P = pp.parse_gcode(g)
    L = P["layers"]; b = P["bounds"]
    inside = b[0] >= 0 and b[1] >= 0 and b[2] <= pp.BED and b[3] <= pp.BED
    checks.append(("every move inside the 180 mm bed", inside, "x %.1f..%.1f y %.1f..%.1f z max %.1f" % (b[0], b[2], b[1], b[3], P["zmax"])))
    # every G0/G1/G2/G3 X/Y from the first printed feature on (travel included; the extrusion bounds above miss travels). The
    # machine's own start/end routine and its per-layer "safe pos" park (X-13, the A1 mini's purge and wipe station) are Bambu's
    # stock moves and lie off the bed by design: reported, not judged.
    ax, ay = [], []; started = False; stock = 0
    for ln in g.splitlines():
        if ln.startswith(";LAYER_CHANGE") or ln.startswith("; CHANGE_LAYER"): started = True
        if not started or ln[:2] not in ("G0", "G1", "G2", "G3") or ln[2:3] != " ": continue
        code = ln.split(";")[0]
        mx = re.search(r" X(-?[\d.]+)", code); my = re.search(r" Y(-?[\d.]+)", code)
        if "safe pos" in ln or (mx and float(mx.group(1)) < -5) or (my and float(my.group(1)) > 183):
            stock += 1; continue
        if mx: ax.append(float(mx.group(1)))
        if my: ay.append(float(my.group(1)))
    allin = bool(ax and ay) and min(ax) >= -1.0 and min(ay) >= -1.0 and max(ax) <= pp.BED + 1.0 and max(ay) <= pp.BED + 1.0
    checks.append(("every printing/travel move inside the A1 mini's 180 mm bed", allin,
                   "x %.1f..%.1f y %.1f..%.1f (+%d stock park moves left of the bed)" % (min(ax), max(ax), min(ay), max(ay), stock)))
    zs = sorted(L)
    gaps =[round(zs[i + 1] - zs[i], 3) for i in range(len(zs) - 1) if zs[i + 1] - zs[i] > 0.45]
    checks.append(("no empty layers", not gaps, "%d layers" % len(zs) if not gaps else "gaps %s" % gaps[:5]))
    # which settings did the slicer really use per object: layer heights seen in the g-code, per-object walls/infill from the 3mf
    heights = sorted(set(round(zs[i + 1] - zs[i], 3) for i in range(len(zs) - 1)))
    stats["layer_steps"] = heights
    # placement offset: every object's model points must fall in its footprint (+ brim); find the offset from the full set
    pts = np.array([p for z in zs for t in L[z] if not t.startswith("Support") and t not in ("Skirt", "Brim") for p in L[z][t]])
    mn = np.min([it["mesh"].bounds[0][:2] for it in items], axis=0); mx = np.max([it["mesh"].bounds[1][:2] for it in items], axis=0)
    off = (pts.min(axis=0) + pts.max(axis=0)) / 2 - (mn + mx) / 2
    stats["offset_xy"] = [round(float(v), 2) for v in off]
    checks.append(("objects stayed where laid out", float(np.abs(off).max()) < 1.0, "offset %s" % stats["offset_xy"]))
    grid = {}
    for z in zs:
        for t, ps in L[z].items():
            if t in ("Skirt", "Brim"): continue
            for (px, py) in ps:
                grid.setdefault((round(z, 2), int(px // 1), int(py // 1)), t)
    zl = np.array(zs)
    sup_total = 0
    for it in items:
        m = it["mesh"]; oh, ohf = pp.overhang(m, 40.0)
        if oh <= 1.0:
            continue
        cent = m.triangles[ohf].mean(axis=1); badf = []
        for fi, c in zip(ohf, cent):
            cx, cy, cz = c[0] + off[0], c[1] + off[1], c[2]
            below = zl[(zl < cz - 0.05) & (zl > cz - 1.5)]
            found = any(grid.get((round(z, 2), int(cx // 1) + dx, int(cy // 1) + dy)) for z in below[::-1] for dx in range(-3, 4) for dy in range(-3, 4) if (dx * dx + dy * dy) ** .5 <= 3)
            if not found: badf.append((fi, round(float(cz), 1)))
        bad = 0.0   # a ledge under 1.5 mm wide cannot carry a support (its walls span it, anchored on the part): not counted, as prepare_part
        for zr in sorted(set(z for _, z in badf)):
            idx = [f for f, z in badf if z == zr]
            v = m.triangles[idx].reshape(-1, 3)
            if (v[:, :2].max(axis=0) - v[:, :2].min(axis=0)).min() >= 1.5:
                bad += float(m.area_faces[idx].sum())
        sup_total += 1
        checks.append(("%s: overhang has material under it" % it["label"], bad <= max(2.0, 0.02 * oh), "%.0f of %.0f mm2 unsupported" % (bad, oh)))
    nsup = sum(len(L[z].get("Support", [])) + len(L[z].get("Support interface", [])) for z in zs)
    checks.append(("supports are in the g-code", nsup > 0 or sup_total == 0, "%d support moves" % nsup))
    mt = re.search(r"total estimated time:\s*(.+)", g); mg = re.search(r"filament used \[g\]\s*=\s*([\d.]+)", g)
    stats["time"] = mt.group(1).strip() if mt else ""; stats["grams"] = float(mg.group(1)) if mg else None
    return dict(part=name, checks=checks, stats=stats, ready=all(c[1] for c in checks), gcode_3mf=res["path"],
                objects=[dict(label=it["label"], opts=it["opts"], xy=it["xy"], normal=it["normal"]) for it in items])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("plate"); ap.add_argument("--out", required=True)
    ap.add_argument("--angle", type=float, default=40.0); ap.add_argument("--build-only", action="store_true")
    a = ap.parse_args()
    spec = json.load(open(a.plate, encoding="utf8"))
    out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
    items = []
    for p in spec["parts"]:
        m0, oh, best = pose(p, a.angle)
        for q in range(p.get("qty", 1)):
            label = p["part"] + ("_%d" % (q + 1) if p.get("qty", 1) > 1 else "")
            opts = {"layer_height": p.get("layer", 0.12), "wall_loops": p.get("walls", 3), "sparse_infill_density": "%d%%" % p.get("infill", 100),
                    "enable_support": 1 if oh > 1.0 else 0}
            items.append(dict(part=p["part"], label=label, mesh=m0.copy(), oh=oh, opts=opts, normal=best["normal"]))
    layout(items)
    f3 = os.path.join(out, spec["name"] + ".in.3mf")
    write_3mf(items, f3, spec["name"])
    print("laid out %d objects:" % len(items))
    for it in items:
        print("  %-42s at %5.1f,%5.1f size %s oh %.0f %s" % (it["label"], it["xy"][0], it["xy"][1], [round(float(e), 1) for e in it["mesh"].extents], it["oh"], it["opts"]))
    if a.build_only:
        return
    res = slice_3mf(f3, out, spec["name"])
    print("slice:", "ok" if res["ok"] else "FAILED", res["log"][-400:] if not res["ok"] else "")
    report = check_plate(items, res, out, spec["name"])
    json.dump(report, open(os.path.join(out, spec["name"] + ".report.json"), "w", encoding="utf8"), indent=1, default=str)
    for n, o, note in report["checks"]:
        print("  [%s] %s %s" % ("ok" if o else "FAIL", n, note))
    print("stats", report["stats"])
    sys.exit(0 if report["ready"] else 1)
    json.dump([{k: v for k, v in it.items() if k != "mesh"} | {"bounds": it["mesh"].bounds.tolist()} for it in items], open(os.path.join(out, "items.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
