from dataclasses import dataclass
from datetime import datetime
from dynamics.base_dynamic import BaseDynamic


@dataclass
class LinearWithPeakDynamic(BaseDynamic):
    """
    In this dynamic, stress increases by 1 every X days, with a ceiling max.
    """

    interval: int
    peak: int

    def apply(self, creation_date: datetime, base_stress: int) -> float:
        offset = (datetime.now() - creation_date).days / self.interval
        return min(base_stress + offset, self.peak)

    _name_prefix = "dynamic-linear-day-peaked-"

    @staticmethod
    def from_text(text: str) -> "LinearWithPeakDynamic":
        interval, peak = text.split(LinearWithPeakDynamic._name_prefix)[1].split("-")

        return LinearWithPeakDynamic(interval=int(interval), peak=int(peak))

    def to_text(self):
        return f"{self._name_prefix}-{self.interval}-{self.peak}"