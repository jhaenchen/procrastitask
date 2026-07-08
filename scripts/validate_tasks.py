"""Validate a procrastitask JSON file by round-tripping every entry.

Loads the array, runs each entry through Task.from_dict and back through
to_dict, reports any entries that raise. With --strict, also flags
dependent_on ids that don't resolve to any task in the file.

Usage:
    pipenv run python scripts/validate_tasks.py            # validates tasks.json
    pipenv run python scripts/validate_tasks.py path.json
    pipenv run python scripts/validate_tasks.py --strict
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from procrastitask.task import Task  # noqa: E402

DEFAULT_DB = REPO_ROOT / "tasks.json"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", nargs="?", default=str(DEFAULT_DB))
    ap.add_argument("--strict", action="store_true",
                    help="also flag unresolved dependent_on ids")
    args = ap.parse_args()

    raw = Path(args.path).read_text()
    entries = json.loads(raw)
    if not isinstance(entries, list):
        sys.exit(f"{args.path}: top-level JSON must be an array")

    errors = []
    ids = set()
    for i, entry in enumerate(entries):
        title = entry.get("title", "<no title>") if isinstance(entry, dict) else "<not a dict>"
        try:
            task = Task.from_dict(entry)
            task.to_dict()
            ids.add(task.identifier)
        except Exception as e:
            errors.append(f"#{i} {title!r}: {type(e).__name__}: {e}")

    if args.strict:
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            title = entry.get("title", "<no title>")
            for dep in entry.get("dependent_on", []) or []:
                if dep not in ids:
                    errors.append(f"#{i} {title!r}: unresolved dep {dep!r}")

    if errors:
        for e in errors:
            print(e)
        sys.exit(f"{len(errors)} error(s) in {len(entries)} task(s)")
    print(f"ok: {len(entries)} task(s) round-tripped cleanly in {args.path}")


if __name__ == "__main__":
    main()
