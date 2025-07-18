from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
import re


class BaseDynamic(ABC):
    @staticmethod
    @abstractmethod
    def from_text(text: str) -> "BaseDynamic":
        raise NotImplementedError()

    @abstractmethod
    def to_text(self: "BaseDynamic") -> str:
        raise NotImplementedError()
    
    @staticmethod
    @abstractmethod
    def prefixes() -> List[str]:
        """
        Must be implemented by subclasses as a static method returning a list of prefixes.
        """
        raise NotImplementedError()
    
    @staticmethod
    def get_cleaned_prefix(prefix: str) -> str:
        return prefix.split("{")[0]
    
    @abstractmethod
    def apply(self, creation_date: datetime, base_stress: int, task: "Task") -> float:
        raise NotImplementedError()
    
    @staticmethod
    def get_all_dynamics() -> List[type["BaseDynamic"]]:
        from .linear_dynamic import LinearDynamic
        from .linear_with_peak_dynamic import LinearWithPeakDynamic
        from .step_due_date_dynamic import StepDueDateDynamic
        from .location_dynamic import LocationDynamic
        from .combined_dynamic import CombinedDynamic
        from .static_offset_dynamic import StaticOffsetDynamic
        from .absolute_linear_dynamic import AbsoluteLinearDynamic
        all_dynamics = []
        for class_obj in BaseDynamic.__subclasses__():
            all_dynamics.append(class_obj)
        return all_dynamics
    
    @staticmethod
    def get_all_prefixes() -> List[str]:
        all_prefixes: List[str] = []
        for class_obj in BaseDynamic.get_all_dynamics():
            all_prefixes.extend(class_obj.prefixes())
        return all_prefixes

    @staticmethod
    def find_dynamic(text: str, exclude: Optional[type["BaseDynamic"]] = None) -> Optional["BaseDynamic"]:
        all_dynamics = BaseDynamic.get_all_dynamics()

        for class_obj in all_dynamics:
            if class_obj == exclude:
                continue
            try:
                return class_obj.from_text(text)
            except (ValueError, TypeError, AttributeError):
                pass
        if text:
            raise ValueError(f"Provided dynamic text {text} could not be matched to a dynamic. Available: {BaseDynamic.get_all_prefixes()}")
        return None

    @staticmethod
    def get_implementers():
        return BaseDynamic.__subclasses__()
