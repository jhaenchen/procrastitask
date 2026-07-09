from datetime import datetime
from typing import List, Tuple
import logging

from .base_dynamic import BaseDynamic

log = logging.getLogger()
log.setLevel("DEBUG")


class PiecewiseLinearDynamic(BaseDynamic):
    """
    Renders stress as a piecewise-linear function of days since the task's
    dynamic base date (creation date, unless a periodicity/cool_down reset
    has moved it forward). Parameters are the (day, stress) knots the user
    placed by drawing a curve.

    The rendered value is absolute — the drawn curve replaces base_stress
    rather than shifting it — because the drawing UX defines the desired
    stress directly. Before the first knot and after the last knot, the
    value holds constant at the nearest knot's stress (no extrapolation).
    """

    _full_prefix = "dynamic-piecewise.{d1}:{s1};{d2}:{s2};..."

    def __init__(self, knots: List[Tuple[float, float]]):
        if not knots:
            raise ValueError("PiecewiseLinearDynamic requires at least one knot")
        self.knots = sorted(knots, key=lambda k: k[0])

    @staticmethod
    def prefixes() -> list[str]:
        return [PiecewiseLinearDynamic._full_prefix]

    def apply(self, creation_date: datetime, base_stress: int, task) -> float:
        days = (datetime.now() - task.get_dynamic_base_date()).total_seconds() / 86400
        if days <= self.knots[0][0]:
            return max(self.knots[0][1], 0)
        if days >= self.knots[-1][0]:
            return max(self.knots[-1][1], 0)
        for (d0, s0), (d1, s1) in zip(self.knots, self.knots[1:]):
            if d0 <= days <= d1:
                if d1 == d0:
                    return max(s1, 0)
                t = (days - d0) / (d1 - d0)
                return max(s0 + t * (s1 - s0), 0)
        return max(self.knots[-1][1], 0)

    @staticmethod
    def from_text(text: str) -> "PiecewiseLinearDynamic":
        prefix = BaseDynamic.get_cleaned_prefix(PiecewiseLinearDynamic._full_prefix)
        if not text.startswith(prefix):
            raise ValueError(f"Invalid text repr: {text}")
        payload = text[len(prefix):]
        if not payload:
            raise ValueError(f"Invalid text repr: {text}")
        knots: List[Tuple[float, float]] = []
        for chunk in payload.split(";"):
            if ":" not in chunk:
                raise ValueError(f"Invalid knot in {text}: {chunk!r}")
            day_str, stress_str = chunk.split(":", 1)
            knots.append((float(day_str), float(stress_str)))
        return PiecewiseLinearDynamic(knots)

    def to_text(self) -> str:
        def fmt(x: float) -> str:
            return str(int(x)) if float(x).is_integer() else str(round(x, 4))
        body = ";".join(f"{fmt(d)}:{fmt(s)}" for d, s in self.knots)
        return f"dynamic-piecewise.{body}"
