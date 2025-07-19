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
        try:
            offset = float(text.split(StaticOffsetDynamic.prefixes()[0])[1])
            return StaticOffsetDynamic(offset)
        except (IndexError, ValueError):
            raise ValueError(f"Invalid static-offset dynamic format: {text}")

    def to_text(self) -> str:
        return f"static-offset.{float(self.offset)}"

    def apply(self, creation_date: datetime, base_stress: int, task: "Task") -> float:
        return max(base_stress + self.offset, 0)

    @staticmethod
    def prefixes() -> list[str]:
        return ["static-offset."]
