"""Registers the 10-minute Windows task NoxyDesignCheckin that runs tools/design_checkin.py (it removes itself at 95 percent)."""
import subprocess
import sys
from pathlib import Path

script = Path(__file__).resolve().with_name("design_checkin.py")
exe = Path(sys.executable)
exe = exe.with_name("pythonw.exe") if exe.with_name("pythonw.exe").exists() else exe
r = subprocess.run(["schtasks", "/create", "/tn", "NoxyDesignCheckin", "/sc", "minute", "/mo", "10", "/f",
                    "/tr", '"%s" "%s"' % (exe, script)], capture_output=True)
print(r.returncode, r.stdout.decode("gbk", "replace"), r.stderr.decode("gbk", "replace"))
