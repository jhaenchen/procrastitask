from dataclasses import dataclass
from datetime import datetime
from .base_dynamic import BaseDynamic


@dataclass
class LinearWithPeakDynamic(BaseDynamic):
    """
    In this dynamic, stress increases by 1 every X days, with a ceiling max. X can be a decimal.
    """

    interval: float
    peak: int

    def apply(self, creation_date: datetime, base_stress: int, task) -> float:
        # Use total seconds for sub-day precision
        delta = (datetime.now() - task.get_dynamic_base_date())
        offset = (delta.total_seconds() / 86400) / self.interval
        return min(base_stress + offset, self.peak)

    _full_prefix = "dynamic-linear-day-peaked.{increase_per_x_days}.{max_stress}"

    @staticmethod
    def prefixes() -> list[str]:
        return [LinearWithPeakDynamic._full_prefix, "linear-day-peaked."]

    @staticmethod
    def from_text(text: str) -> "LinearWithPeakDynamic":
        interval, peak = None, None
        for prefix in LinearWithPeakDynamic.prefixes():
            prefix = BaseDynamic.get_cleaned_prefix(prefix)
            if prefix in text:
                split = text.split(prefix)
                if len(split) == 2:
                    values = split[1].split("-")
                    if len(values) == 2:
                        interval, peak = values
        if interval is None or peak is None:
            raise ValueError(f"Invalid text repr: {text}")
        return LinearWithPeakDynamic(interval=float(interval), peak=int(peak))

    def to_text(self):
        return f"dynamic-linear-day-peaked.{self.interval}-{self.peak}"