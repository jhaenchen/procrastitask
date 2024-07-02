from abc import ABC, abstractmethod
from typing import List, Optional


class BaseDynamic(ABC):
    @staticmethod
    @abstractmethod
    def from_text(text: str) -> "BaseDynamic":
        raise NotImplementedError()

    @abstractmethod
    def to_text(self: "BaseDynamic") -> str:
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def prefixes(self) -> List[str]:
        raise NotImplementedError()

    @staticmethod
    def find_dynamic(text: str) -> Optional["BaseDynamic"]:
        from .linear_dynamic import LinearDynamic
        from .linear_with_peak_dynamic import LinearWithPeakDynamic
        all_prefixes = []
        for class_obj in BaseDynamic.__subclasses__():
            try:
                all_prefixes.extend(class_obj.prefixes)
                return class_obj.from_text(text)
            except:
                pass
        if text:
            raise ValueError(f"Provided dynamic text {text} could not be matched to a dynamic. Available: {all_prefixes}")
        return None

    @staticmethod
    def get_implementers():
        return BaseDynamic.__subclasses__()
