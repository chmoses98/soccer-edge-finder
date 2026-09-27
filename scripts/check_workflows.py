"""Workflow hygiene lint (lessons from sibling repos):
* every workflow that pushes commits declares a concurrency group with cancel-in-progress: false
* no workflow triggers itself via workflow_run of itself
* schedules are not on the round :00/:15/:30/:45 minutes (GitHub starves those slots)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
problems: list[str] = []
for wf in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
    text = wf.read_text()
    pushes = "git push" in text
    if pushes and "concurrency:" not in text:
        problems.append(f"{wf.name}: pushes without a concurrency group")
    if pushes and "cancel-in-progress: true" in text:
        problems.append(f"{wf.name}: writer with cancel-in-progress: true")
    for m in re.finditer(r'cron:\s*"([^"]+)"', text):
        minute = m.group(1).split()[0]
        if minute in {"0", "15", "30", "45", "*/15", "*/30", "*/5", "*/10"}:
            problems.append(f"{wf.name}: cron minute {minute!r} sits on a congested slot")
    if re.search(r"workflow_run:\s*\n\s*workflows:\s*\[?\s*\"?" + re.escape(wf.stem), text):
        problems.append(f"{wf.name}: triggers on its own completion")
if problems:
    print("\n".join(problems))
    sys.exit(1)
print("workflows ok")
