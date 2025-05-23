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

    _full_prefix = "dynamic-step-due.{days_before}.{percentage}"

    @staticmethod
    def prefixes() -> list[str]:
        return [StepDueDateDynamic._full_prefix]

    def apply(self, creation_date: datetime, base_stress: int, task: Task) -> float:
        # Use current_due_date instead of due_date
        due = task.current_due_date
        if not due:
            raise ValueError("Due date is required on tasks utilizing the step due date dynamic")
        days_until_due = (due - datetime.now()).total_seconds() / 86400
        if days_until_due <= self.increase_days_before:
            bonus = base_stress * (self.increase_by_percentage / 100)
            log.debug(f"Step due date dynamic applied a bonus: {base_stress} + {bonus}")
            return base_stress + bonus
        return base_stress

    @staticmethod
    def from_text(text: str) -> "StepDueDateDynamic":
        parts = None
        for prefix in StepDueDateDynamic.prefixes():
            prefix = BaseDynamic.get_cleaned_prefix(prefix)
            if prefix in text:
                parts = text.split(prefix)
        if parts is None or len(parts) != 2 or parts[0] != "":
            raise ValueError(f"Invalid text repr: {text}")
        # Expecting format: dynamic-step-due.{days_before}.{percentage}
        split = parts[1].split(".")
        if len(split) != 2:
            raise ValueError(f"Invalid text repr: {text}")
        days_before, percentage = split
        return StepDueDateDynamic(increase_days_before=int(days_before), increase_by_percentage=int(percentage))

    def to_text(self):
        return f"dynamic-step-due.{self.increase_days_before}.{self.increase_by_percentage}"
