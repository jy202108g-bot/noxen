#!/usr/bin/env python3
"""The print queue (Spark 15 Nov): cloud sessions queue print-ready parts, the Claude desktop app on Spark's computer prints them.
One file per job in print/queue/ (no merge conflicts between sessions). A job moves
    ready -> approved -> printing -> printed -> done        (or failed / cancelled at any point)
- a subagent adds a job when a part is print-ready (status ready);
- Spark's "print <part>" in a design chat approves it, and means the plate is clear: approving also closes every printed job (done);
- the desktop scheduled task starts the first-approved job, one at a time, only when no job is printing or printed (a finished
  part is still on the plate until Spark's next approval), and records printing / printed / failed.

    python tools/print_queue.py add <part|print file> [--orient ...] [--supports ...] [--settings ...] [--time 1h20] [--qty 1] [--note ...]
    python tools/print_queue.py approve <id|part> ...        design chat, on Spark's "print <part>"
    python tools/print_queue.py cancel <id|part> ...
    python tools/print_queue.py list [--all]                 open jobs (--all: also done / failed / cancelled)
    python tools/print_queue.py next                         desktop task: the job to start now as JSON, or "none: <why>"
    python tools/print_queue.py refresh                     ready/approved jobs to their part's current print file (list marks STALE)
    python tools/print_queue.py set <id> printing|printed|failed [--note ...]   desktop task
The caller commits print/queue/ and pushes (git pull --rebase first). The file to print is a GitHub release URL (anyone can download it).

DESKTOP TASK (the Claude desktop app's scheduled task on Spark's computer; its prompt is one line: "In <noxen folder>, do the desktop
task in tools/print_queue.py"), each run:
 1. `git pull -q --rebase`. For a job marked printing, look at the printer (Bambu Studio, Device tab): finished -> `set <id> printed`,
    failed or cancelled on the printer -> `set <id> failed --note <what the screen says>`; still running -> stop here.
 2. `python tools/print_queue.py next`. "none: ..." -> commit and push any status change, then stop (a run with nothing to do ends here).
 3. `next` returns only a PREPARED job (python tools/print_queue.py prepare <part>: best flat pose, overhang found, supports on, sliced with print/profiles,
    the g-code checked: bed, supports under every overhang, no error; tools/prepare_part.py). Print its `prepared.gcode_3mf` as it is (already posed,
    never re-orient or re-arrange); the url/sha256 is only the source mesh. If a slice or check fails, the job is not returned: `set <id> failed --note ...`.
 4. Print to the A1 mini; once the printer shows it running, `set <id> printing`, commit "print: <part>", push. One job per run.
Never start a job while the printer is busy or a printed part is still on the plate; never print anything not returned by `next`.
"""
import argparse, datetime, glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Q = os.path.join(ROOT, "print", "queue")
OPEN = ("ready", "approved", "printing", "printed")
STATES = OPEN + ("done", "failed", "cancelled")


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def jobs(all_=True):
    out = []
    for f in sorted(glob.glob(os.path.join(Q, "*.json"))):
        j = json.load(open(f)); j["_file"] = f
        if all_ or j["status"] in OPEN:
            out.append(j)
    return sorted(out, key=lambda j: j["id"])


def save(j):
    os.makedirs(Q, exist_ok=True)
    f = j.pop("_file", None) or os.path.join(Q, j["id"] + ".json")
    json.dump(j, open(f, "w"), indent=1); open(f, "a").write("\n")


def resolve(name):
    """A part -> (url, sha256) of the file to print: the bed-pose print-<name>.stl a make.py wrote (print/index.json) first, else the
    part's release print mesh (a generated part's result.json; 16 Nov: the make.py parts' queue jobs pointed at <name>.stl, the
    drone-pose mesh, so 'as laid' and the orientation note did not hold)."""
    idx = json.load(open(os.path.join(ROOT, "print", "index.json")))
    for k in (name + ".stl", name):
        if k in idx:
            return idx[k]["url"], idx[k].get("sha256")
    for meta in (f"parts/{name}/result.json", f"parts/{name}/print.json"):
        p = os.path.join(ROOT, meta)
        if os.path.exists(p):
            d = json.load(open(p)); d = d.get("print_stl", d)
            if d.get("url"):
                return d["url"], d.get("sha256")
    sys.exit(f"print_queue: no print file for {name!r} (not in print/index.json, no parts/{name}/result.json or print.json with a url)")


def current(j):
    """(url, sha256) the job's part resolves to now, or None when the part's last make failed its solid or assembly check"""
    pj = os.path.join(ROOT, "parts", j["part"], "print.json")
    if os.path.exists(pj):
        d = json.load(open(pj))
        if not ((d.get("make") or {}).get("solid") or {}).get("ok", True) or not (d.get("assembly") or {}).get("ok", True):
            return None
    try:
        return resolve(j["part"])
    except SystemExit:
        return None



def find(key):
    hit = [j for j in jobs() if j["id"] == key] or [j for j in jobs(False) if j["part"] == key]
    if not hit:
        sys.exit(f"print_queue: no open job {key!r}")
    return hit


def log(j, status, note=None):
    j["status"] = status
    j.setdefault("history", []).append(f"{now()} {status}" + (f": {note}" if note else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("add"); a.add_argument("name")
    for k in ("orient", "supports", "settings", "time", "note"):
        a.add_argument("--" + k, default="")
    a.add_argument("--qty", type=int, default=1)
    for c in ("approve", "cancel"):
        sp.add_parser(c).add_argument("keys", nargs="+")
    sp.add_parser("list").add_argument("--all", action="store_true")
    sp.add_parser("refresh")
    sp.add_parser("next")
    sp.add_parser("prepare").add_argument("keys", nargs="+")
    s = sp.add_parser("set"); s.add_argument("id"); s.add_argument("status", choices=("printing", "printed", "failed")); s.add_argument("--note")
    o = ap.parse_args()

    if o.cmd == "add":
        url, sha = resolve(o.name)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
        j = {"id": f"{stamp}-{o.name}", "part": o.name, "url": url, "sha256": sha, "qty": o.qty,
             "material": "PCTG" if "tpu" not in (o.settings + o.name).lower() else "TPU 95A",
             "orient": o.orient, "supports": o.supports, "settings": o.settings, "time": o.time, "note": o.note}
        log(j, "ready"); save(j); print(f"queued {j['id']} (ready: Spark approves it with \"print {o.name}\")")
    elif o.cmd in ("approve", "cancel"):
        if o.cmd == "approve":
            for j in jobs(False):
                if j["status"] == "printed":
                    log(j, "done", "plate cleared (next approval)"); save(j)
        for k in o.keys:
            for j in find(k):
                if o.cmd == "approve":
                    j["approved_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                log(j, "approved" if o.cmd == "approve" else "cancelled"); save(j); print(f"{j['status']}: {j['id']}")
    elif o.cmd == "list":
        js = jobs(o.all)
        for j in js:
            c = current(j) if j["status"] in ("ready", "approved") else (j["url"], j["sha256"])
            flag = "" if c == (j["url"], j["sha256"]) else ("  [STALE: its part fails a check now]" if c is None else "  [STALE: file changed, run refresh]")
            print(f"{j['status']:9} {j['id']}  x{j['qty']} {j['time']}  {j['orient']}  {j['note']}{flag}".rstrip())
        print(f"{len(js)} job(s)")
    elif o.cmd == "refresh":                                      # ready and approved jobs to their part's current print file
        for j in jobs(False):
            if j["status"] not in ("ready", "approved"):
                continue
            c = current(j)
            if c is None:
                print(f"left: {j['id']} (its part fails its solid or assembly check now)")
            elif c != (j["url"], j["sha256"]):
                j["url"], j["sha256"] = c; log(j, j["status"], "file refreshed"); save(j); print(f"refreshed: {j['id']} -> {c[0].rsplit('/', 1)[-1]} {c[1][:8]}")
    elif o.cmd == "prepare":                                      # orient, support, slice and check: a job is sent only once prepared
        import prepare_part
        for k in o.keys:
            for j in find(k):
                mesh, name = prepare_part.find_mesh(j["part"])
                r = prepare_part.prepare(mesh, name)
                if r["ready"]:
                    rel = os.path.relpath(r["gcode_3mf"], os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).replace(os.sep, "/")
                    j["prepared"] = {"for_sha256": j["sha256"], "gcode_3mf": rel, "supports": r["supports"], "orient": r["orient"],
                                     "time": r["stats"].get("time"), "grams": r["stats"].get("grams")}
                    j["orient"], j["supports"] = r["orient"], r["supports"]
                    log(j, j["status"], "prepared: sliced and checked, " + rel); save(j); print(f"prepared: {j['id']}")
                else:
                    j.pop("prepared", None); log(j, j["status"], "prepare FAILED: " + "; ".join(c[0] for c in r["checks"] if not c[1])); save(j)
                    print(f"NOT READY: {j['id']}")
    elif o.cmd == "next":
        js = jobs(False)
        busy = [j for j in js if j["status"] in ("printing", "printed")]
        ready = sorted((j for j in js if j["status"] == "approved"), key=lambda j: j.get("approved_at", ""))   # first approved, first printed
        if busy:
            print(f"none: {busy[0]['id']} is {busy[0]['status']} (a printed part stays on the plate until Spark approves the next job)")
        elif not ready:
            print("none: no approved job")
        elif not (ready[0].get("prepared") or {}).get("for_sha256") == ready[0]["sha256"] or not os.path.exists(os.path.join(ROOT, ready[0]["prepared"]["gcode_3mf"])):
            print(f"none: {ready[0]['id']} is approved but not print-ready; run: python tools/print_queue.py prepare {ready[0]['part']}")
        else:
            j = dict(ready[0]); j.pop("_file", None); print(json.dumps(j, indent=1))
    elif o.cmd == "set":
        j = find(o.id)[0]; log(j, o.status, o.note); save(j); print(f"{o.status}: {j['id']}")


if __name__ == "__main__":
    main()
