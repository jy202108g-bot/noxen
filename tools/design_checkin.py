"""30-minute check-in on the DESIGN AGENT chat (Spark, 22 Nov). One line per run in data/design_checkin.log.
Run by the Windows scheduled task NoxyDesignCheckin (every 30 min). It reads the inbox line count against
design_status.json "read", whether a turn of the session runs (designwake.running), and the week's usage.
Busy: logs and leaves it. Idle with unread lines or open items: wakes it through Noxy's own wake route
(designwake.wake) with the carry-on message. At 95 percent of the week or more: deletes its own scheduled task and logs it.
--dry only reports what it would do."""
import subprocess
import sys
import time
from pathlib import Path

NOX = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(NOX))
import designwake  # noqa: E402

TASK = "NoxyDesignCheckin"
CAP = 95.0
TEXT = ("Check-in (every 30 min, from Noxy): requests wait past your read mark. Carry on working the whole queue by your "
        "own rules (data/design_queue.md), re-arm your inbox watch so the next request wakes you, and do not stop "
        "until the week's usage nears 95 percent.")


def log(line):
    with (NOX / "data" / "design_checkin.log").open("a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + line + "\n")
    print(line)


def main():
    dry = "--dry" in sys.argv
    unread, open_, _ = designwake.queue()
    busy = designwake.running()
    pct = designwake._usage()
    if pct >= CAP:
        r = "" if dry else subprocess.run(["schtasks", "/delete", "/tn", TASK, "/f"], capture_output=True, text=True).returncode
        log("week %.0f%% >= %.0f%%: check-ins stopped, task %s removed (rc %s)" % (pct, CAP, TASK, r))
        return
    if not unread and not open_:
        act = "idle, nothing waits" if not busy else "busy, nothing waits"
    elif busy:
        act = "busy, leave it"
    elif dry:
        act = "idle with work waiting: would wake"
    else:
        why = designwake.wake(unread, open_, text=TEXT)
        act = "idle with work waiting: woke" + ((" -> " + why) if why else " (sent)")
    log("unread %d open %d busy %s week %.0f%% -> %s" % (unread, open_, busy, pct, act))


main()
