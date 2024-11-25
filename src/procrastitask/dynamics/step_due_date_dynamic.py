from dataclasses import dataclass
from datetime import datetime
import logging

from ..task import Task

from .base_dynamic import BaseDynamic

log = logging.getLogger()
log.setLevel("DEBUG")


@dataclass
class StepDueDateDynamic(BaseDynamic):
    """
    In this dynamic, stress bumps up by a configured percentage Y when it's X days until a task is due.
    """

    # How much should the stress increase by
    increase_by_percentage: int
    # How many days before the due date should the stress increase
    increase_days_before: int

    def apply(self, _: datetime, base_stress: int, task: Task) -> float:
        if not task.due_date:
            raise ValueError("Due date is required on tasks utilizing the step due date dynamic")
        days_until_due = (task.due_date - datetime.now()).days
        if days_until_due <= self.increase_days_before:
            bonus = base_stress * (self.increase_by_percentage / 100)
            log.debug(f"Step due date dynamic applied a bonus: {base_stress} + {bonus}")
            return base_stress + bonus
        return base_stress

    _full_prefix = "dynamic-step-due.{days_before}.{percentage}"

    prefixes = [_full_prefix]

    @staticmethod
    def from_text(text: str) -> "StepDueDateDynamic":
        parts = None
        for prefix in StepDueDateDynamic.prefixes:
            prefix = BaseDynamic.get_cleaned_prefix(prefix)
            if text.startswith(prefix):
                parts = text[len(prefix):].split('.')
                break
        if parts is None or len(parts) != 2:
            raise ValueError(f"Invalid text repr: {text}")

        increase_days_before = int(parts[0])
        increase_by_percentage = int(parts[1])

        return StepDueDateDynamic(increase_by_percentage=increase_by_percentage, increase_days_before=increase_days_before)

    def to_text(self):
        return f"dynamic-step-due.{self.increase_days_before}.{self.increase_by_percentage}"
