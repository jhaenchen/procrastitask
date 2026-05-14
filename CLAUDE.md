# Procrastitask Development Instructions

## Running Tests

This project uses `pipenv` for dependency management. Always use pipenv to run tests:

```bash
pipenv run python -m pytest tests/ -v
```

To run specific tests:
```bash
pipenv run python -m pytest tests/test_file.py::TestClass::test_method -v
```

## Project Structure

- `src/procrastitask/` - Main source code
  - `task.py` - Task model with stress dynamics and completion tracking
  - `procrastitask_app.py` - CLI application with task editing interface
  - `task_collection.py` - Task collection management
  - `dynamics/` - Stress dynamic implementations
- `tests/` - Test suite
- `scripts/` - Helper scripts
  - `add_tasks.py` - Append tasks to `tasks.json` from a JSON array of partial task dicts (stdin or file). Auto-fills UUID, dates, etc.
  - `validate_tasks.py` - Round-trip every entry in a tasks JSON file through `Task.from_dict`/`to_dict`; `--strict` also flags unresolved `dependent_on` ids.
- `docs/conversational_task_generation.md` - Playbook for authoring tasks via a Claude chat: workflow, allowed fields, examples, and a `jq` migration recipe for moving a list's tasks to another procrastitask instance.
