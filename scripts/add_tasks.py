"""Append tasks to tasks.json from a JSON array of partial task dicts.

Reads JSON from a file path argument or stdin. Each entry is a dict with the
human-meaningful Task fields; UUID, creation_date, last_refreshed, etc. are
filled in by the Task dataclass defaults. The entry is then round-tripped
through to_dict() to produce canonical serialized form, validated by
re-parsing with Task.from_dict(), and appended to tasks.json.

Usage:
    pipenv run python scripts/add_tasks.py < /tmp/proposed_tasks.json
    pipenv run python scripts/add_tasks.py /tmp/proposed_tasks.json
    pipenv run python scripts/add_tasks.py --db /path/to/tasks.json < in.json

Default list_name (when omitted from an entry) is "move_with_emma_26".
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from procrastitask.task import Task  # noqa: E402
from procrastitask.dynamics.base_dynamic import BaseDynamic  # noqa: E402

DEFAULT_LIST = "move_with_emma_26"
DEFAULT_DB = REPO_ROOT / "tasks.json"

ALLOWED_FIELDS = {
    "title", "description", "duration", "stress", "difficulty",
    "due_date", "due_date_cron", "cool_down", "periodicity",
    "stress_dynamic", "dependent_on", "list_name",
}


def build_task(entry: dict) -> Task:
    unknown = set(entry) - ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"unknown fields: {sorted(unknown)}")

    kwargs = dict(entry)
    kwargs.setdefault("description", "")
    kwargs.setdefault("list_name", DEFAULT_LIST)

    dyn = kwargs.get("stress_dynamic")
    if isinstance(dyn, str):
        kwargs["stress_dynamic"] = BaseDynamic.find_dynamic(dyn)

    due = kwargs.get("due_date")
    if isinstance(due, str):
        from datetime import datetime
        kwargs["due_date"] = datetime.fromisoformat(due)

    task = Task(**kwargs)
    # Round-trip to surface any latent serialization issues now.
    Task.from_dict(task.to_dict())
    return task


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", nargs="?", help="JSON file (default: stdin)")
    ap.add_argument("--db", default=str(DEFAULT_DB), help="tasks.json path")
    ap.add_argument("--dry-run", action="store_true", help="don't write, just print")
    args = ap.parse_args()

    raw = Path(args.input).read_text() if args.input else sys.stdin.read()
    proposals = json.loads(raw)
    if not isinstance(proposals, list):
        sys.exit("input must be a JSON array of task dicts")

    new_tasks = []
    for i, entry in enumerate(proposals):
        try:
            new_tasks.append(build_task(entry))
        except Exception as e:
            sys.exit(f"entry #{i} ({entry.get('title', '?')!r}): {e}")

    db_path = Path(args.db)
    existing = json.loads(db_path.read_text()) if db_path.exists() else []
    merged = existing + [t.to_dict() for t in new_tasks]

    if args.dry_run:
        print(json.dumps([t.to_dict() for t in new_tasks], indent=2))
    else:
        db_path.write_text(json.dumps(merged))

    for t in new_tasks:
        print(f"+ {t.identifier}  [{t.list_name}]  {t.title}")
    print(f"{'would add' if args.dry_run else 'added'} {len(new_tasks)} task(s) to {db_path}")


if __name__ == "__main__":
    main()
