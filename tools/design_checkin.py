"""Check-in on the DESIGN AGENT chat (Spark, 22 Nov, final wish: no idle allowance). One line per run in
data/design_checkin.log. Run by the Windows scheduled task NoxyDesignCheckin (every minute, pythonw, no window).
Whenever no turn of the session runs and the week's usage is under 95 percent it wakes it at once through Noxy's own
wake route (designwake.wake, a message to the chat: it never types into or sends Spark's unsent input-box text),
with work waiting or an empty inbox alike. A turn running: logged, left alone. A wake is not repeated within
GAP seconds (the turn takes a moment to show). At 95 percent of the week or more: deletes its own scheduled task.
--dry only reports what it would do."""
import json
import subprocess
import sys
import time
from pathlib import Path

NOX = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(NOX))
import designwake  # noqa: E402

TASK = "NoxyDesignCheckin"
CAP = 95.0
GAP = 150      # seconds: no second wake before the first one's turn shows in the record
FRESH = 75     # the session record moved this recently: a turn runs (designwake.QUIET is 4 min, too slow for this)
STATE = NOX / "data" / "design_checkin.json"
TEXT = ("Check-in (every minute, from Noxy): no turn of yours was running. Spark's final rule: never end a turn while the "
        "week's usage is under 95 percent. Work the queue (data/design_queue.md), and when it is empty find and make the "
        "next Noxy improvement yourself, without pausing between tasks; re-arm your inbox watch.")


def log(line):
    with (NOX / "data" / "design_checkin.log").open("a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + line + "\n")
    print(line)


def turn_running():
    """A turn runs: the session record moved in the last FRESH s, or `claude agents` shows it busy/working."""
    try:
        if time.time() - designwake.RECORD.stat().st_mtime < FRESH:
            return True
    except OSError:
        pass
    try:
        return any(a.get("status") == "busy" or a.get("state") == "working" for a in designwake._entries(designwake.SESSION))
    except Exception:
        return False


def main():
    dry = "--dry" in sys.argv
    force = "--force" in sys.argv     # a test: wake even if a turn runs
    unread, open_, _ = designwake.queue()
    pct = designwake._usage()
    if pct >= CAP:
        r = "" if dry else subprocess.run(["schtasks", "/delete", "/tn", TASK, "/f"], capture_output=True, text=True).returncode
        log("week %.0f%% >= %.0f%%: check-ins stopped, task %s removed (rc %s)" % (pct, CAP, TASK, r))
        return
    busy = turn_running()
    try:
        last = float(json.loads(STATE.read_text(encoding="utf-8")).get("last") or 0)
    except (OSError, ValueError, TypeError, AttributeError):
        last = 0
    if busy and not force:
        act = "a turn is running, leave it"
    elif time.time() - last < GAP and not force:
        act = "woken %d s ago, turn starting, leave it" % (time.time() - last)
    elif dry:
        act = "no turn running: would wake"
    else:
        STATE.write_text(json.dumps({"last": time.time()}), encoding="utf-8")
        why = designwake.wake(unread, open_, text=TEXT)
        act = "no turn running: woke it" + ((" -> FAILED: " + why) if why else " (sent)")
    log("unread %d open %d busy %s week %.0f%% -> %s" % (unread, open_, busy, pct, act))


main()
