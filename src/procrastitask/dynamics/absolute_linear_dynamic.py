from dataclasses import dataclass
from datetime import datetime
from .base_dynamic import BaseDynamic


@dataclass
class AbsoluteLinearDynamic(BaseDynamic):
    """
    In this dynamic, stress increases by `increase_by` every `every_x_days` days, with no ceiling.
    """

    increase_by: float
    every_x_days: float

    _full_prefix = "dynamic-linear.{increase_by}.{every_x_days}"
    _short_prefix = "linear.{increase_by}.{every_x_days}"

    def apply(self, creation_date: datetime, base_stress: int, task) -> float:
        delta = (datetime.now() - creation_date)
        days = delta.total_seconds() / 86400
        increments = days / self.every_x_days
        return base_stress + increments * self.increase_by

    @staticmethod
    def prefixes() -> list[str]:
        return [AbsoluteLinearDynamic._full_prefix, AbsoluteLinearDynamic._short_prefix]

    @staticmethod
    def from_text(text: str) -> "AbsoluteLinearDynamic":
        increase_by, every_x_days = None, None
        for prefix in AbsoluteLinearDynamic.prefixes():
            prefix_clean = BaseDynamic.get_cleaned_prefix(prefix)
            if prefix_clean in text:
                split = text.split(prefix_clean)
                if len(split) == 2:
                    values = split[1].split("-")
                    if len(values) == 2:
                        increase_by, every_x_days = values
        if increase_by is None or every_x_days is None:
            raise ValueError(f"Invalid text repr: {text}")
        return AbsoluteLinearDynamic(increase_by=float(increase_by), every_x_days=float(every_x_days))

    def to_text(self):
        return f"{BaseDynamic.get_cleaned_prefix(self._full_prefix)}{self.increase_by}-{self.every_x_days}"
