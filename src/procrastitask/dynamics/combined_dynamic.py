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

    @staticmethod
    def prefixes() -> list[str]:
        return ["{dynamic} (+)/(-)/(|+) {dynamic}"]

    def apply(self, creation_date: datetime, base_stress: int, task: "Task") -> float:
        # Start with the initial stress
        current_stress = base_stress
        prev_diff = self.dynamics[0].apply(creation_date, current_stress, task) - current_stress
        current_stress += prev_diff
        allow = True
        for i, operator in enumerate(self.operators):
            # Each dynamic gets the updated stress
            next_diff = self.dynamics[i + 1].apply(creation_date, current_stress, task) - current_stress
            if not allow:
                continue
            if operator == '(+)':
                current_stress += next_diff
            elif operator == '(-)':
                current_stress -= next_diff
            elif operator == '(|+)':
                if prev_diff != 0:
                    current_stress += next_diff
                else:
                    allow = False
            else:
                raise ValueError(f"Unsupported operator: {operator}")
            prev_diff = next_diff
        return max(current_stress, 0)

    @staticmethod
    def from_text(text: str) -> "CombinedDynamic":
        # Split the text by operators surrounded with parentheses
        parts = re.split(r'(\(\|\+\)|\(\+\)|\(-\))', text)
        # Remove empty strings from split
        parts = [p for p in parts if p.strip() != '']
        if len(parts) == 1:
            return BaseDynamic.find_dynamic(parts[0], exclude=CombinedDynamic)
        dynamics = []
        operators = []
        for part in parts:
            part = part.strip()
            if part in ['(+)', '(-)', '(|+)']:
                operators.append(part)
            else:
                dynamics.append(BaseDynamic.find_dynamic(part, exclude=CombinedDynamic))
        if not dynamics or not operators:
            raise ValueError(f"Invalid dynamic string with operators: {text}")
        return CombinedDynamic(dynamics, operators)

    def to_text(self) -> str:
        result = self.dynamics[0].to_text()
        for i, operator in enumerate(self.operators):
            result += f" {operator} {self.dynamics[i + 1].to_text()}"
        return result
