"""
Project a task's rendered stress forward in time by sampling it at future
timestamps. Used by the web UI to draw per-task curve thumbnails and a
timeline overlay of all incomplete tasks.

Time is advanced with freezegun so every existing dynamic (linear ramp,
piecewise, step-at-due-date, etc.) computes against the imagined future
without needing per-dynamic refactors.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from freezegun import freeze_time

from .task import Task


def project_rendered_stress(
    task: Task,
    all_tasks: Optional[List[Task]] = None,
    days_ahead: float = 30.0,
    samples: int = 30,
) -> List[Tuple[float, float]]:
    """
    Sample `task.get_rendered_stress(all_tasks)` at `samples` evenly-spaced
    points across the next `days_ahead` days. Returns a list of
    (day_offset_from_now, rendered_stress) tuples.
    """
    if samples < 2:
        raise ValueError("samples must be at least 2")
    if days_ahead <= 0:
        raise ValueError("days_ahead must be positive")
    now = datetime.now()
    step_days = days_ahead / (samples - 1)
    out: List[Tuple[float, float]] = []
    for i in range(samples):
        target = now + timedelta(days=i * step_days)
        with freeze_time(target):
            stress = task.get_rendered_stress(all_tasks)
        out.append((i * step_days, stress))
    return out
