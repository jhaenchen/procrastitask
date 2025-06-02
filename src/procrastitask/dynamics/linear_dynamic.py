from dataclasses import dataclass
from datetime import datetime
import logging

from .base_dynamic import BaseDynamic

log = logging.getLogger()
log.setLevel("DEBUG")


@dataclass
class LinearDynamic(BaseDynamic):
    """
    In this dynamic, stress increases by 1 every X days. X can be a decimal.
    """

    # How often should the stress increase by one
    interval: float

    def apply(self, last_updated_date: datetime, base_stress: int, task) -> float:
        # Use total seconds for sub-day precision
        delta = (datetime.now() - last_updated_date)
        offset = (delta.total_seconds() / 86400) / self.interval
        log.debug(f"Linear dynamic applied a bonus: {base_stress} + {offset}")
        return base_stress + offset

    _full_prefix = "dynamic-linear-day.{increase_per_x_days}"

    @staticmethod
    def prefixes() -> list[str]:
        return [LinearDynamic._full_prefix, "linear-day.", "dynamic-linear-day-"]

    @staticmethod
    def from_text(text: str) -> "LinearDynamic":
        parts = None
        for prefix in LinearDynamic.prefixes():
            prefix = BaseDynamic.get_cleaned_prefix(prefix)
            if prefix in text:
                parts = text.split(prefix)
        if parts is None or len(parts) != 2 or parts[0] != "":
            # If the prefix is not found, or if the text doesn't split into exactly two parts
            # (the prefix and the interval), or if the first part is not empty
            raise ValueError(f"Invalid text repr: {text}")

        return LinearDynamic(interval=float(parts[1]))

    def to_text(self):
        return f"dynamic-linear-day-{self.interval}"
