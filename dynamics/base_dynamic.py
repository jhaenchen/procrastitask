from abc import ABC, abstractmethod
from typing import Optional


class BaseDynamic(ABC):
    @staticmethod
    @abstractmethod
    def from_text(text: str) -> "BaseDynamic":
        raise NotImplementedError()

    @abstractmethod
    def to_text(self: "BaseDynamic") -> str:
        raise NotImplementedError()

    @staticmethod
    def find_dynamic(text: str) -> Optional["BaseDynamic"]:
        for class_obj in BaseDynamic.__subclasses__():
            try:
                return class_obj.from_text(text)
            except:
                pass
        return None

    @staticmethod
    def get_implementers():
        return BaseDynamic.__subclasses__()
