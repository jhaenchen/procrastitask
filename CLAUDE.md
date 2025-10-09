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
