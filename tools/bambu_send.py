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
