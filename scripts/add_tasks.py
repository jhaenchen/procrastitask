"""Append or patch tasks in tasks.json from a JSON array of partial task dicts.

Reads JSON from a file path argument or stdin. Each entry is a dict with the
human-meaningful Task fields; UUID, creation_date, last_refreshed, etc. are
filled in by the Task dataclass defaults. The entry is then round-tripped
through to_dict() to produce canonical serialized form, validated by
re-parsing with Task.from_dict(), and appended to tasks.json.

If an entry contains an `identifier` field, it is treated as a patch: the
existing task with that identifier is looked up in tasks.json, the supplied
fields overwrite the corresponding fields on that task, and the result is
round-tripped for validation. All other fields (history, is_complete,
creation_date, etc.) are preserved. Entries without `identifier` are appended
as new tasks (existing behavior).

Usage:
    pipenv run python scripts/add_tasks.py < /tmp/proposed_tasks.json
    pipenv run python scripts/add_tasks.py /tmp/proposed_tasks.json
    pipenv run python scripts/add_tasks.py --db /path/to/tasks.json < in.json

Default list_name (when omitted from a new entry) is "move_with_emma_26".
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
NEW_TASK_EXTRA_FIELDS = {"identifier"}
PATCH_EXTRA_FIELDS = {"identifier"}


def _normalize_entry(entry: dict) -> dict:
    kwargs = dict(entry)
    dyn = kwargs.get("stress_dynamic")
    if isinstance(dyn, str):
        kwargs["stress_dynamic"] = BaseDynamic.find_dynamic(dyn)
    due = kwargs.get("due_date")
    if isinstance(due, str):
        from datetime import datetime
        kwargs["due_date"] = datetime.fromisoformat(due)
    return kwargs


def build_task(entry: dict) -> Task:
    unknown = set(entry) - ALLOWED_FIELDS - NEW_TASK_EXTRA_FIELDS
    if unknown:
        raise ValueError(f"unknown fields: {sorted(unknown)}")

    kwargs = _normalize_entry(entry)
    kwargs.setdefault("description", "")
    kwargs.setdefault("list_name", DEFAULT_LIST)

    task = Task(**kwargs)
    # Round-trip to surface any latent serialization issues now.
    Task.from_dict(task.to_dict())
    return task


def apply_patch(existing_dict: dict, entry: dict) -> dict:
    """Apply patch fields from entry onto existing_dict, round-trip validated."""
    unknown = set(entry) - ALLOWED_FIELDS - PATCH_EXTRA_FIELDS
    if unknown:
        raise ValueError(f"unknown fields: {sorted(unknown)}")

    kwargs = _normalize_entry({k: v for k, v in entry.items() if k != "identifier"})

    # Parse the existing task, mutate the allowed fields, re-serialize.
    task = Task.from_dict(existing_dict)
    for k, v in kwargs.items():
        setattr(task, k, v)
    new_dict = task.to_dict()
    # Round-trip to surface latent serialization issues.
    Task.from_dict(new_dict)
    return new_dict


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

    db_path = Path(args.db)
    existing = json.loads(db_path.read_text()) if db_path.exists() else []
    by_id = {t.get("identifier"): idx for idx, t in enumerate(existing)}

    new_tasks: list[Task] = []
    patched: list[tuple[str, str, dict, dict]] = []  # (identifier, title, before, after)

    for i, entry in enumerate(proposals):
        try:
            ident = entry.get("identifier")
            if ident is not None and ident in by_id:
                before = existing[by_id[ident]]
                after = apply_patch(before, entry)
                patched.append((ident, after.get("title", "?"), before, after))
            else:
                # No id, or id that doesn't collide with an existing task -> new task.
                # Caller-supplied identifier is honored (lets a single batch express
                # dependent_on relationships among its own new entries).
                new_tasks.append(build_task(entry))
        except Exception as e:
            sys.exit(f"entry #{i} ({entry.get('title', entry.get('identifier', '?'))!r}): {e}")

    merged = list(existing)
    for ident, _title, _before, after in patched:
        merged[by_id[ident]] = after
    merged.extend(t.to_dict() for t in new_tasks)

    if args.dry_run:
        print(json.dumps({
            "new": [t.to_dict() for t in new_tasks],
            "patched": [{"identifier": i, "title": t, "before": b, "after": a}
                        for i, t, b, a in patched],
        }, indent=2, default=str))
    else:
        db_path.write_text(json.dumps(merged))

    for ident, title, _b, _a in patched:
        print(f"~ {ident}  {title}")
    for t in new_tasks:
        print(f"+ {t.identifier}  [{t.list_name}]  {t.title}")
    verb = "would apply" if args.dry_run else "applied"
    print(f"{verb} {len(patched)} patch(es) and {len(new_tasks)} new task(s) to {db_path}")


if __name__ == "__main__":
    main()
