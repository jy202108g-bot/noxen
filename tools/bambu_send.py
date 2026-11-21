#!/usr/bin/env python3
"""Check a Bambu A1 mini over LAN (developer mode), and send and start a sliced .gcode.3mf on it.

    python tools/bambu_send.py check  <Gideon|Jarvis> [--shot out.png]     # state, error code, HMS, temps, a camera picture
    python tools/bambu_send.py send   <Gideon|Jarvis> <file.gcode.3mf> [--start]
    python tools/bambu_send.py watch  <Gideon|Jarvis>                      # state, progress, remaining time

Printer addresses and access codes come from data/bambu_printers.json next to the Noxy server (never in the repo).
"""
import argparse, io, json, os, sys, time

CFG = os.environ.get("BAMBU_CFG") or os.path.join(os.path.expanduser("~"), "nox", "data", "bambu_printers.json")


def connect(name):
    import bambulabs_api as bl
    cfg = json.load(open(CFG, encoding="utf-8"))
    p = next(x for x in cfg["printers"] if x["name"].lower() == name.lower())
    pr = bl.Printer(p["ip"], p["access_code"], p["serial"])
    pr.mqtt_start()
    for _ in range(40):
        time.sleep(0.5)
        if pr.get_state() not in (None, "UNKNOWN") and pr.get_nozzle_temperature() is not None:
            break
    return pr


BED = 180.0


def fits(path):
    """(ok, why): a print is sent only when it was sliced for the A1 mini and every move lies on its 180 mm bed (Spark, 21 Nov
    12:24, inbox 613: plates "too big or oriented wrong" started printing outside the plate). The machine's own stock moves
    (the "safe pos" park at X-13 left of the bed, its wipe station) are allowed; a move past Y 180 never is."""
    import re, zipfile
    try:
        z = zipfile.ZipFile(path)
        names = [n for n in z.namelist() if n.endswith(".gcode")]
        g = z.read(names[0]).decode("utf8", "replace") if names else ""
    except Exception as e:
        return False, "not a sliced .gcode.3mf (%s)" % e
    if not g:
        return False, "no g-code inside: slice it first"
    head = dict(re.findall(r"^; (printer_model|printable_area|printable_height) = (.*)$", g, re.M))
    if "A1 mini" not in head.get("printer_model", ""):
        return False, "sliced for %r, not the A1 mini: slice with the A1 mini profile" % head.get("printer_model", "an unknown printer")
    area = re.findall(r"(-?[\d.]+)x(-?[\d.]+)", head.get("printable_area", ""))
    if area and max(max(float(a), float(b)) for a, b in area) > BED + 0.5:
        return False, "sliced with a %s bed, not 180 mm" % head.get("printable_area")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import plate_safe                    # the one safe-area gate (5 mm from every plate edge, supports and brim included), shared with plate.py
    ok, why, _ = plate_safe.safe_check(g)
    return ok, why


def status(pr):
    d = pr.mqtt_dump() or {}
    pj = d.get("print", {}) if isinstance(d, dict) else {}
    return dict(state=str(pr.get_state()), gcode=str(pr.get_current_state()), file=pr.get_file_name(), progress=pr.get_percentage(),
                layer=pr.current_layer_num(), layers=pr.total_layer_num(), remaining_min=pr.get_time(),
                nozzle=pr.get_nozzle_temperature(), bed=pr.get_bed_temperature(), print_error=pj.get("print_error"), hms=pj.get("hms"),
                gcode_state=pj.get("gcode_state"), mc_remaining_time=pj.get("mc_remaining_time"), subtask=pj.get("subtask_name"))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["check", "send", "watch"]); ap.add_argument("printer")
    ap.add_argument("file", nargs="?"); ap.add_argument("--start", action="store_true"); ap.add_argument("--shot")
    a = ap.parse_args()
    if a.cmd == "send":                 # checked before the printer is even touched; never overridden
        ok, why = fits(a.file)
        print("plate check:", why, flush=True)
        if not ok:
            sys.exit("NOT SENT: " + why)
    pr = connect(a.printer)
    try:
        if a.cmd in ("check", "watch"):
            print(json.dumps(status(pr), indent=1, default=str))
            if a.shot:
                pr.camera_start(); time.sleep(4)
                img = pr.get_camera_image()
                pr.camera_stop()
                if img is not None:
                    img.save(a.shot); print("camera picture", a.shot)
                else:
                    print("no camera picture")
        else:
            fn = os.path.basename(a.file)
            with open(a.file, "rb") as f:
                r = pr.upload_file(f, fn)
            print("uploaded:", r)
            if a.start:
                ok = pr.start_print(fn, 1, use_ams=False, flow_calibration=True)
                print("start sent:", ok)
                time.sleep(15)
                print(json.dumps(status(pr), indent=1, default=str))
    finally:
        pr.mqtt_stop()


if __name__ == "__main__":
    main()
