from typing import List
from datetime import datetime
from procrastitask.task import Task
from .base_dynamic import BaseDynamic

class StaticOffsetDynamic(BaseDynamic):

    def __init__(self, offset: float):
        self.offset = offset

    @staticmethod
    def from_text(text: str) -> "StaticOffsetDynamic":
        # Expected format: "static-offset.{integer}", including negative numbers
        import re
        match = re.fullmatch(r"static-offset\.(-?\d+)", text)
        if not match:
            raise ValueError(f"Invalid static-offset dynamic format: {text}")
        offset = int(match.group(1))
        return StaticOffsetDynamic(offset)

    def to_text(self) -> str:
        return f"static-offset.{int(self.offset)}"

    def apply(self, creation_date: datetime, base_stress: int, task: "Task") -> float:
        return max(base_stress + self.offset, 0)

    @property
    def prefixes(self) -> List[str]:
        return ["static-offset."]
