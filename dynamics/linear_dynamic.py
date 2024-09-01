from dataclasses import dataclass
from datetime import datetime
import logging

from dynamics.base_dynamic import BaseDynamic

log = logging.getLogger()
log.setLevel("DEBUG")


@dataclass
class LinearDynamic(BaseDynamic):
    """
    In this dynamic, stress increases by 1 every X days. X can be a decimal.
    """

    # How often should the stress increase by one
    interval: float

    def apply(self, last_updated_date: datetime, base_stress: int) -> float:
        offset = (datetime.now() - last_updated_date).days / self.interval
        log.debug(f"Linear dynamic applied a bonus: {base_stress} + {offset}")
        return base_stress + offset

    _full_prefix = "dynamic-linear-day."

    prefixes = [_full_prefix, "linear-day.", "dynamic-linear-day-"]

    @staticmethod
    def from_text(text: str) -> "LinearDynamic":
        parts = None
        for prefix in LinearDynamic.prefixes:
            if prefix in text:
                parts = text.split(prefix)
        if parts is None:
            raise ValueError(f"Invalid text repr: {text}")

        return LinearDynamic(interval=float(parts[-1:][0]))

    def to_text(self):
        return f"dynamic-linear-day-{self.interval}"
