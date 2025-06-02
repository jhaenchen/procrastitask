import re
from typing import List
from .base_dynamic import BaseDynamic
from datetime import datetime


class CombinedDynamic(BaseDynamic):
    """
    CombinedDynamic composes multiple BaseDynamic instances using specified operators.

    This class allows combining several dynamic stress calculation strategies (subclasses of BaseDynamic)
    using a sequence of operators, enabling complex, composable dynamic behaviors for tasks.

    Args:
        dynamics (List[BaseDynamic]): List of dynamic instances to combine. The order matters and should
            correspond to the order in which operators are applied.
        operators (List[str]): List of operators as strings, each of which must be one of:
            '(+)'   - Add the next dynamic's difference to the running total.
            '(-)'   - Subtract the next dynamic's difference from the running total.
            '(|+)'  - Add the next dynamic's difference only if the previous difference is non-zero;
                      otherwise, stop applying further operators.

    Usage Example:
        combined = CombinedDynamic.from_text("dynamicA (+) dynamicB (|+) dynamicC")
    """
    def __init__(self, dynamics: List[BaseDynamic], operators: List[str]):
        self.dynamics = dynamics
        self.operators = operators

    def apply(self, creation_date: datetime, base_stress: int, task: "Task") -> float:
        prev_diff = self.dynamics[0].apply(creation_date, base_stress, task) - base_stress
        diff = prev_diff
        allow = True
        for i, operator in enumerate(self.operators):
            next_diff = self.dynamics[i + 1].apply(creation_date, base_stress, task) - base_stress
            if not allow:
                continue
            if operator == '(+)':
                diff += next_diff
            elif operator == '(-)':
                diff -= next_diff
            elif operator == '(|+)':
                if prev_diff != 0:
                    diff += next_diff
                else:
                    allow = False
            else:
                raise ValueError(f"Unsupported operator: {operator}")
            prev_diff = next_diff
        return base_stress + diff

    @staticmethod
    def from_text(text: str) -> "CombinedDynamic":
        # Split the text by operators surrounded with parentheses
        parts = re.split(r'(\(\|\+\)|\(\+\)|\(-\))', text)
        # Remove empty strings from split
        parts = [p for p in parts if p.strip() != '']
        if len(parts) == 1:
            return BaseDynamic.find_dynamic(parts[0])
        dynamics = []
        operators = []
        for part in parts:
            part = part.strip()
            if part in ['(+)', '(-)', '(|+)']:
                operators.append(part)
            else:
                dynamics.append(BaseDynamic.find_dynamic(part))
        if not dynamics or not operators:
            raise ValueError(f"Invalid dynamic string with operators: {text}")
        return CombinedDynamic(dynamics, operators)

    def to_text(self) -> str:
        result = self.dynamics[0].to_text()
        for i, operator in enumerate(self.operators):
            result += f" {operator} {self.dynamics[i + 1].to_text()}"
        return result

    prefixes = ["{dynamic} (+)/(-)/(|+) {dynamic}"]
