# Conversational task generation

Playbook for using a Claude chat to author procrastitask tasks. Optimized for
the `move_with_emma_26` list but generalizes to any list.

## Workflow

1. **User describes a task** in plain language (what, when, how often, prerequisites).
2. **I propose params** as a JSON entry — title, description, duration (min), stress, difficulty, plus any optional fields that fit.
3. **User confirms or edits**.
4. **I write the JSON** to a temp file (e.g. `$TMPDIR/proposed_tasks.json` as an array — even for a single task).
5. **I run** `pipenv run python scripts/add_tasks.py < $TMPDIR/proposed_tasks.json` and report back the identifier(s).

For larger batches the user can describe several tasks at once; I write them all into the array and one invocation appends them all.

## Re-read these files before generating

The schema drifts. Before producing JSON in a new session:

- `src/procrastitask/task.py` — the `Task` dataclass (fields & defaults), `from_dict`, `to_dict`. New optional fields appear here first.
- `src/procrastitask/dynamics/` — every file. Each dynamic class has a `from_text` / `to_text` pair defining its serialized signature. New dynamic types live here.
- `list_config.json` — confirm the target list still exists.

If `add_tasks.py` rejects something it didn't last time, the schema changed — re-read above.

## Allowed entry fields

Only these get passed to `Task(**kwargs)`; everything else is auto-defaulted (UUID, dates, history, status):

| Field | Required | Notes |
|---|---|---|
| `title` | yes | string |
| `description` | no | string; defaults to `""` |
| `duration` | yes | minutes; integer > 0 |
| `stress` | yes | integer/float > 0 (convention) |
| `difficulty` | yes | 1–10 convention |
| `due_date` | no | ISO 8601 string, e.g. `"2026-08-15T17:00:00"` |
| `due_date_cron` | no | 5-field cron string |
| `cool_down` | no | `"{n}{unit}"` with unit ∈ `min`, `hr`, `d`, `w`, `m` |
| `periodicity` | no | 5-field cron string |
| `stress_dynamic` | no | dynamic text signature; validated via `BaseDynamic.find_dynamic` |
| `dependent_on` | no | array of existing task identifiers |
| `list_name` | no | defaults to `move_with_emma_26` |

Soft constraints (not code-enforced; respect them anyway): difficulty 1–10, stress > 0, duration > 0 in minutes.

## Examples

Minimal:

```json
[
  {
    "title": "Inventory current furniture (what stays, sells, tosses)",
    "duration": 90,
    "stress": 25,
    "difficulty": 4
  }
]
```

Maximal — recurring task with stress that grows toward the due date:

```json
[
  {
    "title": "Re-confirm movers two weeks out",
    "description": "Email + phone confirmation, share unit numbers and elevator reservation.",
    "duration": 20,
    "stress": 30,
    "difficulty": 3,
    "due_date": "2026-08-01T10:00:00",
    "stress_dynamic": "dynamic-step-due.14.300",
    "list_name": "move_with_emma_26"
  }
]
```

## Migration to another procrastitask instance

Extract the list from this instance's `tasks.json`:

```bash
jq '[.[] | select(.list_name=="move_with_emma_26")]' tasks.json > move_export.json
```

Sanity-check it round-trips standalone:

```bash
pipenv run python scripts/validate_tasks.py move_export.json --strict
```

On the target instance, ensure `move_with_emma_26` exists in its `list_config.json`, then either paste the array entries into its `tasks.json` (top-level array) or write an import that does the same merge `add_tasks.py` does.

## Validating tasks.json at any time

```bash
pipenv run python scripts/validate_tasks.py            # validates tasks.json
pipenv run python scripts/validate_tasks.py --strict   # + unresolved-dep check
```

Catches bad cron strings, unknown stress dynamic signatures, malformed ISO dates, and missing required fields — i.e. everything `Task.from_dict` enforces.
