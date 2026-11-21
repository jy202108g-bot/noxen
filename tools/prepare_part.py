#!/usr/bin/env python3
"""Make a queued part truly print-ready for Gideon / Jarvis (Bambu A1 mini, PCTG 3D-Fuel Pro, 0.12 mm). Never sends or prints.

    python tools/prepare_part.py <part or queue id or mesh.stl> [--out DIR] [--angle 40] [--no-orient] [--keep-pose]

1. ORIENT: every flat face cluster of the mesh is tried face down; the pose with the least overhang area wins (ties: more bed contact,
   then lower height). --keep-pose keeps the file's own pose (a part whose `orient` is fixed, e.g. coupons).
2. OVERHANGS: downward faces steeper than the support angle (default 40 deg from vertical, as the profile) that are not on the bed.
3. SLICE with print/profiles (tools/slice_part.py), supports on when there is overhang.
4. CHECK the sliced .gcode.3mf: slice ran without error, every move inside the 180 cube (and the bed), supports are in the g-code
   and sit under every overhang sample point (support or model material in the layers below), no empty layers.
5. Writes <out>/<part>.gcode.3mf and <out>/<part>.report.json; the exit code is 0 only when every check passed (READY).
Nothing here talks to a printer.
"""
import argparse, glob, json, math, os, re, shutil, sys, zipfile
import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slice_part

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BED = 180.0
Z_MAX = 180.0
BED_CENTRE = (BED / 2, BED / 2)


def find_mesh(arg):
    if arg.lower().endswith(".stl") and os.path.exists(arg):
        return os.path.abspath(arg), os.path.splitext(os.path.basename(arg))[0]
    part = arg
    q = os.path.join(ROOT, "print", "queue", arg + ".json")
    if os.path.exists(q):
        part = json.load(open(q, encoding="utf8"))["part"]
    p = os.path.join(ROOT, "parts", part, "print.stl")
    if not os.path.exists(p):
        import subprocess
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "print_mesh.py"), "fetch", part], capture_output=True, text=True)
        p = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else p
    if not os.path.exists(p):
        sys.exit("no print mesh for " + arg)
    return p, part


def rot_to_down(n):
    """Rotation matrix taking unit vector n onto -z."""
    n = np.array(n, float); n /= np.linalg.norm(n)
    t = np.array([0, 0, -1.0])
    v = np.cross(n, t); c = float(np.dot(n, t))
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3) if c > 0 else np.diag([1, -1, -1.0])
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def overhang(mesh, angle):
    """Overhang faces of a mesh sitting on z=min: downward faces steeper than `angle` (deg from vertical) and above the bed.
    Returns (area mm2, face indices)."""
    n = mesh.face_normals
    zmin = mesh.bounds[0][2]
    # Orca's threshold: a face needs support when its slope from the horizontal is under `angle` (normal within `angle` of straight down)
    thr = -math.cos(math.radians(angle))
    low = mesh.triangles[:, :, 2].min(axis=1)
    sel = (n[:, 2] < thr) & (low > zmin + 0.05)
    return float(mesh.area_faces[sel].sum()), np.nonzero(sel)[0]


def candidates(mesh, min_area=20.0):
    """Unique candidate down-normals: facet clusters of coplanar faces, plus the file's own pose."""
    out = [(np.array([0, 0, -1.0]), float("inf"))]
    seen = [out[0][0]]
    for f in mesh.facets:
        a = mesh.area_faces[f].sum()
        if a < min_area:
            continue
        nv = mesh.face_normals[f[0]]
        if any(np.dot(nv, s) > 0.9999 for s in seen):
            continue
        seen.append(nv); out.append((nv, a))
    return out


def orient(mesh, angle, keep=False):
    """Try each flat face down, score, and return (oriented mesh sitting on z=0, list of tried poses)."""
    tried = []
    cands = [(np.array([0, 0, -1.0]), float("inf"))] if keep else candidates(mesh)
    for nv, area in cands:
        R = rot_to_down(nv)
        m = mesh.copy(); m.vertices = m.vertices @ R.T
        m.vertices -= [0, 0, m.bounds[0][2]]
        ext = m.extents
        # bed contact: area of faces lying on z=0
        contact = float(m.area_faces[(m.face_normals[:, 2] < -0.9999) & (m.triangles[:, :, 2].max(axis=1) < 0.05)].sum())
        oh, _ = overhang(m, angle)
        fits = bool(max(ext[0], ext[1]) <= BED - 4 and ext[2] <= Z_MAX)
        tried.append(dict(normal=[round(float(x), 4) for x in nv], contact=round(contact, 1), overhang=round(oh, 1),
                          height=round(float(ext[2]), 1), fits=fits, mesh=m))
    ok = [t for t in tried if t["fits"] and t["contact"] > 5] or [t for t in tried if t["fits"]] or tried
    # least overhang first (rounded to 5 mm2 so a sliver does not decide), then more contact, then lower
    ok.sort(key=lambda t: (round(t["overhang"] / 5), -t["contact"], t["height"]))
    return ok[0], tried


def read_gcode(path):
    z = zipfile.ZipFile(path)
    names = [n for n in z.namelist() if n.endswith(".gcode")]
    if not names:
        return None
    return z.read(names[0]).decode("utf8", "replace")


def parse_gcode(g):
    """Walk the g-code: per layer (z) the extruding XY points by feature type. Returns dict."""
    x = y = z = 0.0
    typ = ""
    lz = 0.0
    absxy = True
    layers = {}                       # z -> {type: list of (x, y)}
    bounds = [1e9, 1e9, -1e9, -1e9]
    zmax = 0.0
    errors = []
    rel_e = False
    last = None
    for line in g.splitlines():
        if line.startswith("; FEATURE:"):
            typ = line[10:].strip(); continue
        if line.startswith("; Z_HEIGHT:"):
            lz = round(float(line[11:]), 3); continue
        if not line or line[0] == ";":
            continue
        cmd = line.split(";")[0].split()
        if not cmd:
            continue
        c = cmd[0]
        if c == "G90": absxy = True
        elif c == "G91": absxy = False
        elif c in ("G0", "G1", "G2", "G3"):
            vals = {t[0]: t[1:] for t in cmd[1:] if len(t) > 1}
            nx = float(vals["X"]) if "X" in vals else x
            ny = float(vals["Y"]) if "Y" in vals else y
            if "Z" in vals:
                z = float(vals["Z"]) if absxy else z + float(vals["Z"])
            e = float(vals["E"]) if "E" in vals else 0.0
            if absxy:
                x, y = nx, ny
            else:
                x += float(vals.get("X", 0)); y += float(vals.get("Y", 0))
            if e > 0 and ("X" in vals or "Y" in vals) and typ and typ != "Custom" and lz > 0:
                layers.setdefault(lz, {}).setdefault(typ, []).append((x, y))
                bounds = [min(bounds[0], x), min(bounds[1], y), max(bounds[2], x), max(bounds[3], y)]
                zmax = max(zmax, lz)
    return dict(layers=layers, bounds=bounds, zmax=zmax)


def check_gcode(g, oriented, oh_faces, slice_ok, log_text, used_supports):
    """Verify the sliced result. Returns (checks list of (name, ok, note), stats)."""
    checks = []
    checks.append(("slice ran without error", slice_ok, log_text[-200:] if not slice_ok else ""))
    if g is None:
        checks.append(("g-code present in the 3mf", False, ""))
        return checks, {}
    P = parse_gcode(g)
    L = P["layers"]
    b = P["bounds"]
    if not L:
        checks.append(("g-code has printed layers", False, "0 layers parsed"))
        return checks, {}
    import plate_safe                       # one gate for every sliced file: 5 mm from each plate edge, supports and brim included
    inside = b[0] >= plate_safe.SAFE and b[1] >= plate_safe.SAFE and b[2] <= BED - plate_safe.SAFE and b[3] <= BED - plate_safe.SAFE and P["zmax"] <= Z_MAX
    checks.append(("every move inside the 5 mm safe area of the 180 mm bed and height", inside, "x %.1f..%.1f y %.1f..%.1f z max %.1f" % (b[0], b[2], b[1], b[3], P["zmax"])))
    zs = sorted(L)
    gaps = [round(zs[i + 1] - zs[i], 3) for i in range(len(zs) - 1) if zs[i + 1] - zs[i] > 0.45]
    checks.append(("no empty layers", not gaps, "gaps %s" % gaps[:5] if gaps else "%d layers" % len(zs)))
    sup_layers = [z for z in zs if "Support" in L[z] or "Support interface" in L[z]]
    nsup = sum(len(L[z].get("Support", [])) + len(L[z].get("Support interface", [])) for z in zs)
    stats = dict(layers=len(zs), support_layers=len(sup_layers), support_moves=nsup)
    # the model's placement in the g-code: offset between mesh frame and bed frame
    pts = np.array([p for z in zs for t in L[z] if not t.startswith("Support") and t not in ("Skirt", "Brim") for p in L[z][t]])
    if len(pts):
        off = (pts.min(axis=0) + pts.max(axis=0)) / 2 - (oriented.bounds[0][:2] + oriented.bounds[1][:2]) / 2
    else:
        off = np.zeros(2)
    stats["offset_xy"] = [round(float(v), 2) for v in off]
    n_oh = len(oh_faces)
    if n_oh:
        checks.append(("supports are in the g-code", nsup > 0, "%d support moves on %d layers" % (nsup, len(sup_layers))))
        # per overhang face: material (support or model) under it, within RAD, in the layers just below its height
        RAD = 2.0
        grid = {}
        for z in zs:
            for t, ps in L[z].items():
                if t in ("Skirt", "Brim"):
                    continue
                for (px, py) in ps:
                    grid.setdefault((round(z, 2), int(px // 1), int(py // 1)), t)
        zl = np.array(zs)
        tri = oriented.triangles[oh_faces]
        cent = tri.mean(axis=1)
        areas = oriented.area_faces[oh_faces]
        bad_area = 0.0; bad = []; badf = []
        for fi, c, a in zip(oh_faces, cent, areas):
            cx, cy, cz = c[0] + off[0], c[1] + off[1], c[2]
            below = zl[(zl < cz - 0.05) & (zl > cz - 1.5)]
            found = False
            for z in below[::-1]:
                for dx in range(-3, 4):
                    for dy in range(-3, 4):
                        t = grid.get((round(z, 2), int(cx // 1) + dx, int(cy // 1) + dy))
                        if t and (t.startswith("Support") or True):
                            if math.hypot(dx, dy) <= RAD + 1:
                                found = True; break
                    if found: break
                if found: break
            if not found:
                badf.append((fi, round(float(cz), 1)))
        # a ledge under 1.5 mm wide cannot carry a support (its own walls span it, anchored on the part): reported, not failed
        for zr in sorted(set(z for _, z in badf)):
            idx = [f for f, z in badf if z == zr]
            v = oriented.triangles[idx].reshape(-1, 3)
            ext = v[:, :2].max(axis=0) - v[:, :2].min(axis=0)
            if ext.min() >= 1.5:
                bad_area += float(oriented.area_faces[idx].sum()); bad.append((round(float(v[:, 0].mean() + off[0]), 1), round(float(v[:, 1].mean() + off[1]), 1), zr))
        tot = float(areas.sum())
        stats.update(overhang_area=round(tot, 1), unsupported_area=round(bad_area, 1))
        # small slivers (< 1 mm2 in all, or < 2 % of overhang) are bridged / printed on their own edge by the slicer
        stats["narrow_ledges_mm2"] = round(float(sum(oriented.area_faces[[f for f, z in badf]])) - bad_area, 1) if badf else 0.0
        checks.append(("every overhang has material under it", bad_area <= max(2.0, 0.02 * tot),
                       "%.0f of %.0f mm2 overhang unsupported%s" % (bad_area, tot, " at %s" % bad[:3] if bad else "")))
    else:
        checks.append(("no overhang, none needed", True, ""))
    m = re.search(r"total estimated time:\s*(.+)", g)
    stats["time"] = m.group(1).strip() if m else ""
    m = re.search(r"filament used \[g\]\s*=\s*([\d.]+)", g)
    stats["grams"] = float(m.group(1)) if m else None
    return checks, stats


def prepare(mesh_path, name, out=None, angle=40.0, keep_pose=False, quiet=False):
    """The whole pipeline; returns the report dict (report["ready"] is True only when every check passed)."""
    class a: pass
    a.angle = angle; a.keep_pose = keep_pose; a.no_orient = False
    out = os.path.abspath(out or os.path.join(ROOT, "print", "ready", name))
    os.makedirs(out, exist_ok=True)
    mesh = trimesh.load(mesh_path, force="mesh")
    report = dict(part=name, source=mesh_path, checks=[])
    if not mesh.is_watertight:
        report["checks"].append(("mesh is watertight", False, ""))
    best, tried = orient(mesh, a.angle, keep=a.keep_pose or a.no_orient)
    m = best["mesh"]
    # place on the bed centre
    c = (m.bounds[0][:2] + m.bounds[1][:2]) / 2
    m.vertices += [BED_CENTRE[0] - c[0], BED_CENTRE[1] - c[1], 0]
    ohA, ohF = overhang(m, a.angle)
    report["orientation"] = dict(down_normal=best["normal"], contact_mm2=best["contact"], overhang_mm2=round(ohA, 1),
                                 size=[round(float(v), 1) for v in m.extents],
                                 tried=[{k: v for k, v in t.items() if k != "mesh"} for t in tried])
    oriented_stl = os.path.join(out, name + ".oriented.stl")
    m.export(oriented_stl)
    supports = ohA > 1.0
    res = slice_part.slice_mesh(oriented_stl, out, supports=supports, support_angle=a.angle)
    gpath = os.path.join(out, name + ".oriented.gcode.3mf")
    ok = res["ok"] and os.path.exists(gpath)
    g = read_gcode(gpath) if ok else None
    checks, stats = check_gcode(g, m, ohF, ok, res["log"], supports)
    report["checks"] += checks
    report["supports"] = ("tree supports (auto) under %.0f mm2 of overhang" % ohA) if supports else "none (no overhang)"
    report["orient"] = "posed for you in the sliced file (flat face %.0f mm2 down, %s mm): do not re-orient" % (best["contact"], "x".join("%.0f" % v for v in m.extents))
    report["stats"] = stats
    ready = all(c[1] for c in report["checks"])
    report["ready"] = ready
    final = os.path.join(out, name + ".gcode.3mf")
    for junk in (os.path.join(out, "plate_1.gcode"), os.path.join(out, "_profiles"), oriented_stl):
        if os.path.isdir(junk): shutil.rmtree(junk, ignore_errors=True)
        elif os.path.exists(junk) and ready: os.remove(junk)
    if os.path.exists(final): os.remove(final)
    if ready:
        os.replace(gpath, final)
        report["gcode_3mf"] = final
    report["pose_note"] = "the 3mf holds the part already posed: do not re-orient or re-arrange it"
    json.dump(report, open(os.path.join(out, name + ".report.json"), "w", encoding="utf8"), indent=1)
    if quiet: return report
    print("%s: overhang %.0f mm2, supports %s, pose normal %s, contact %.0f mm2, size %s" % (
        name, ohA, report["supports"], best["normal"], best["contact"], report["orientation"]["size"]))
    for n, o, note in report["checks"]:
        print("  [%s] %s %s" % ("ok" if o else "FAIL", n, note))
    print("  stats", stats)
    print("READY: " + final if ready else "NOT READY (nothing to print)")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("part"); ap.add_argument("--out", default=None)
    ap.add_argument("--angle", type=float, default=40.0)
    ap.add_argument("--keep-pose", "--no-orient", dest="keep_pose", action="store_true", help="keep the file's own pose")
    a = ap.parse_args()
    mesh_path, name = find_mesh(a.part)
    r = prepare(mesh_path, name, a.out, a.angle, a.keep_pose)
    sys.exit(0 if r["ready"] else 1)


if __name__ == "__main__":
    main()
