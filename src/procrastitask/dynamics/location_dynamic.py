from dataclasses import dataclass
from datetime import datetime
from .base_dynamic import BaseDynamic
from ..location import get_location
from geopy.distance import geodesic


@dataclass
class LocationDynamic(BaseDynamic):
    """
    In this dynamic, stress is adjusted based on the user's location.
    """

    latitude: float
    longitude: float
    radius: float

    def apply(self, creation_date: datetime, base_stress: int, task) -> float:
        location = get_location()
        if location is None:
            return base_stress  # Handle null location gracefully

        user_latitude, user_longitude = map(float, location.split(","))
        user_location = (user_latitude, user_longitude)
        task_location = (self.latitude, self.longitude)

        distance = geodesic(user_location, task_location).meters

        if distance <= self.radius:
            return base_stress * 2  # Increase stress by 100% if within the specified radius
        return base_stress

    _full_prefix = "dynamic-location.{latitude}.{longitude}.{radius}"

    prefixes = [_full_prefix, "location."]

    @staticmethod
    def from_text(text: str) -> "LocationDynamic":
        parts = None
        for prefix in LocationDynamic.prefixes:
            prefix = BaseDynamic.get_cleaned_prefix(prefix)
            if prefix in text:
                parts = text.split(prefix)
        if parts is None:
            raise ValueError(f"Invalid text repr: {text}")

        parts = parts[-1:][0].split(".")
        if "current" in parts[:2]:
            location = get_location()
            if location is None:
                raise RuntimeError("Unable to get current location")
            latitude, longitude = map(float, location.split(","))
            radius = float(parts[-1])
        else:
            latitude, longitude, radius = map(float, parts)

        return LocationDynamic(latitude=latitude, longitude=longitude, radius=radius)

    def to_text(self):
        return f"dynamic-location-{self.latitude}-{self.longitude}-{self.radius}"
