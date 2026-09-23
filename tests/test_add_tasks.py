import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "add_tasks.py"


def _seed_db(tmp_path: Path) -> Path:
    db = tmp_path / "tasks.json"
    seed = [{
        "title": "Existing",
        "description": "orig",
        "difficulty": 3,
        "duration": 10,
        "stress": 5,
        "identifier": "existing-id-1",
        "list_name": "ventana",
        "is_complete": True,
        "creation_date": "2024-01-01T00:00:00",
        "last_refreshed": "2024-06-01T00:00:00",
        "history": [{"completed_at": "2024-05-01T00:00:00", "stress_at_completion": 5}],
    }]
    db.write_text(json.dumps(seed))
    return db


def _run(input_json, db_path, extra=()):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--db", str(db_path), *extra],
        input=json.dumps(input_json),
        text=True,
        capture_output=True,
    )
    return proc


def test_patch_preserves_history_completion_and_creation_date(tmp_path):
    db = _seed_db(tmp_path)
    proc = _run(
        [{"identifier": "existing-id-1", "description": "new desc", "stress": 9}],
        db,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(db.read_text())
    assert len(result) == 1
    t = result[0]
    assert t["description"] == "new desc"
    assert t["stress"] == 9
    assert t["is_complete"] is True
    assert t["identifier"] == "existing-id-1"
    assert t["creation_date"].startswith("2024-01-01")
    assert len(t["history"]) == 1


def test_patch_unknown_identifier_treated_as_new_task(tmp_path):
    """Non-colliding identifier is a caller-supplied id for a new task."""
    db = _seed_db(tmp_path)
    proc = _run(
        [{
            "identifier": "brand-new-id",
            "title": "Brand new",
            "description": "d",
            "difficulty": 2,
            "duration": 5,
            "stress": 3,
        }],
        db,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(db.read_text())
    assert len(result) == 2
    assert result[1]["identifier"] == "brand-new-id"
    assert result[1]["title"] == "Brand new"


def test_mixed_batch_patch_and_append(tmp_path):
    db = _seed_db(tmp_path)
    proc = _run(
        [
            {"identifier": "existing-id-1", "stress": 1},
            {
                "title": "Appended",
                "description": "d",
                "difficulty": 2,
                "duration": 5,
                "stress": 3,
                "list_name": "ventana",
            },
        ],
        db,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(db.read_text())
    assert len(result) == 2
    assert result[0]["stress"] == 1
    assert result[0]["identifier"] == "existing-id-1"
    assert result[1]["title"] == "Appended"


def test_intra_batch_dependent_on_via_supplied_identifier(tmp_path):
    """A new entry can reference another new entry's supplied identifier."""
    db = _seed_db(tmp_path)
    proc = _run(
        [
            {
                "identifier": "prereq-id",
                "title": "Prereq",
                "description": "d",
                "difficulty": 2,
                "duration": 5,
                "stress": 3,
                "list_name": "ventana",
            },
            {
                "title": "Dependent",
                "description": "d",
                "difficulty": 2,
                "duration": 5,
                "stress": 3,
                "list_name": "ventana",
                "dependent_on": ["prereq-id"],
            },
        ],
        db,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(db.read_text())
    assert len(result) == 3
    assert result[1]["identifier"] == "prereq-id"
    assert result[2]["dependent_on"] == ["prereq-id"]


def test_dry_run_does_not_mutate_db(tmp_path):
    db = _seed_db(tmp_path)
    original = db.read_text()
    proc = _run(
        [{"identifier": "existing-id-1", "stress": 99}],
        db,
        extra=["--dry-run"],
    )
    assert proc.returncode == 0, proc.stderr
    assert db.read_text() == original
