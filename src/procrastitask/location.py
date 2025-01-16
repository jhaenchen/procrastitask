import subprocess
import json
import requests
import logging
from datetime import datetime, timedelta

location_override = None
location_cache = None
location_cache_time = None

log = logging.getLogger()

def get_location(nocache=False):
    global location_cache, location_cache_time, location_override

    if location_override:
        return location_override

    if (not nocache) and location_cache and location_cache_time and datetime.now() - location_cache_time < timedelta(minutes=5):
        return location_cache

    try:
        result = subprocess.run(
            ["CoreLocationCLI", "-json"],
            capture_output=True,
            text=True,
            check=True
        )
        location_data = json.loads(result.stdout)
        location_cache = location_data.get("location")
        location_cache_time = datetime.now()
        return location_cache
    except Exception as e:
        log.debug(f"Error getting location from CoreLocationCLI: {e}")

    try:
        response = requests.get("https://ipinfo.io/json")
        location_data = response.json()
        location_cache = location_data.get("loc")
        location_cache_time = datetime.now()
        return location_cache
    except Exception as e:
        log.debug(f"Error getting location from IP: {e}")

    return None

def get_location_from_name(name):
    location_map = {
        "houston": (29.7601, 95.3701),
        "ingram": (30.0774, 99.2403),
        "nyc": (40.7128, 74.0060),
        "timbergrove": (29.7929,−95.4209),
        "tcjester": (29.824459,-95.453439)
        # Add more mappings as needed
    }
    return location_map.get(name)
