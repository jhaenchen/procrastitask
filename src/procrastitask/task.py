import logging
from dataclasses import dataclass, field
import math
import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from typing import List
import uuid
import icalendar
import croniter

from procrastitask.dynamics.base_dynamic import BaseDynamic

log = logging.getLogger()


@dataclass
class Task:
    _DEFAULT_REFRESHED = datetime(1970, 1, 1)

    title: str
    description: str
    difficulty: int
    duration: int
    stress: int
    _is_complete: bool = False
    due_date: datetime = None
    last_refreshed: datetime = field(default_factory=datetime.now)
    identifier: str = field(default_factory=lambda: str(uuid.uuid4()))
    dependent_on: List[int] = field(default_factory=lambda: [])
    stress_dynamic: BaseDynamic = None
    creation_date: datetime = field(default_factory=datetime.now)
    list_name: str = "default"
    cool_down: str = None
    periodicity: str = None

    @property
    def is_complete(self):
        log.debug(f"Evaluating is_complete for task named: {self.title}")
        if not self._is_complete:
            log.debug("Task is incomplete, returning incomplete.")
            return self._is_complete
        if self.cool_down:
            log.debug("Cool down is configured. Let's evaluate.")
            time_since_last_completion = datetime.now() - self.last_refreshed
            expected_interval = self.convert_cool_down_str_to_delta(self.cool_down)
            log.debug(f"The specified interval is {expected_interval}, it's been {time_since_last_completion}")
            if time_since_last_completion > (expected_interval * .9):
                return False
            return True
        if self.periodicity:
            cron = croniter.croniter(self.periodicity, datetime.now())
            next_time_to_complete = cron.get_next(datetime)
            previous_time_to_complete = cron.get_prev(datetime)
            interval = next_time_to_complete - previous_time_to_complete
            buffer = interval * .10
            reset_at = next_time_to_complete - buffer

            if self.last_refreshed < previous_time_to_complete:
                # We missed a chance, bump it to incomplete
                return False

            if datetime.now() > reset_at:
                return False
            return True
        return self._is_complete

    @is_complete.setter
    def is_complete(self, val):
        if val is not None:
            self._is_complete = val
            self.update_last_refreshed()

    @staticmethod
    def convert_cool_down_str_to_delta(cool_down: str) -> timedelta:
        if "min" in cool_down:
            return timedelta(minutes=int(cool_down.split("min")[0]))
        if "d" in cool_down:
            return timedelta(days=int(cool_down.split("d")[0]))
        if "w" in cool_down:
            return timedelta(weeks=int(cool_down.split("w")[0]))
        if "m" in cool_down:
            return timedelta(weeks=int(cool_down.split("m")[0]) * 4)
        raise ValueError(f"The set cool down str is not parseable: {cool_down}")

    def get_rendered_stress(self):
        log.debug(f"Evaluating rendered stress for task {self.title}")
        base_stress = self.stress
        if not self.stress_dynamic:
            return base_stress
        return self.stress_dynamic.apply(self.last_refreshed, self.stress)

    def update_last_refreshed(self):
        self.last_refreshed = datetime.now()
    
    def __key(self):
        return (self.title, self.description)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, Task):
            return self.__key() == other.__key()
        return NotImplemented

    def create_and_launch_ical_event(self):
        cal = icalendar.Calendar()
        cal.add("prodid", "-//My calendar product//mxm.dk//")
        cal.add("version", "2.0")
        event = icalendar.Event()
        event.add("summary", self.title)
        event.add("description", self.description)

        def round_dt_up(dt, delta=timedelta(minutes=15)):
            return datetime.min + math.ceil((dt - datetime.min) / delta) * delta

        rounded_start = round_dt_up(datetime.now())
        event.add("dtstart", rounded_start)
        event.add("dtend", rounded_start + timedelta(minutes=self.duration))
        cal.add_component(event)
        directory = tempfile.mkdtemp()
        f = open(os.path.join(directory, "example.ics"), "wb")
        f.write(cal.to_ical())
        f.close()
        subprocess.call(("open", f.name))

    def get_dependent_count(self, all_tasks: List["Task"]) -> int:
        count = 0
        for task in all_tasks:
            if self.identifier in task.dependent_on:
                count += 1
        return count

    def is_due_soon(self):
        if not self.due_date:
            return False
        due_in = self.due_date - datetime.now()
        if due_in < timedelta(0):
            # Already due
            return True
        # "Soon" is defined as +2 days for every hour of effort
        # Meaning a two hour task is due soon in < 4 days
        elif due_in < timedelta(days=math.ceil(self.duration / 60) * 2):
            return True
        return False

    def get_date_str(self, datetime: datetime):
        delta = datetime - datetime.now()
        if delta < timedelta(0):
            return f"-{delta.days} days"
        return f"{round(delta / timedelta(days=1), 2)} days"

    def pretty_print(self, all_tasks: List["Task"]):
        print(self.headline())
        print(f"{self.description}\n")
        dependents = self.find_dependents(all_tasks)
        if dependents:
            print(f"Dependent Tasks: \n")
            for dependent in dependents:
                found = [
                    task
                    for task in all_tasks
                    if task.identifier == dependent.identifier
                ][0]
                print(f"* [{found.identifier}] {found.title}\n")

    def find_dependents(self, all_tasks: List["Task"]) -> List["Task"]:
        to_return = []
        for task in all_tasks:
            if self.identifier in task.dependent_on:
                to_return.append(task)
        return to_return

    def dependent_tasks_complete(self, all_tasks: List["Task"]) -> bool:
        saw_incomplete = False
        for task_id in self.dependent_on:
            found = [t for t in all_tasks if t.identifier == task_id][0]
            if not found._is_complete:
                saw_incomplete = True
        return not saw_incomplete

    def headline(self):
        return f"{self.title} ({self.duration}min, stress: {int(self.get_rendered_stress())}, diff: {self.difficulty}{(', ' + self.get_date_str(self.due_date)) if self.due_date else ''})"

    def complete(self):
        self.update_last_refreshed()
        self._is_complete = True

    @staticmethod
    def from_dict(incoming_dict):
        due_date = incoming_dict.get("due_date")
        last_refreshed = incoming_dict.get("last_refreshed")
        stress_dynamic = incoming_dict.get("stress_dynamic")
        creation_date = incoming_dict.get("creation_date")

        return Task(
            title=incoming_dict["title"],
            description=incoming_dict["description"],
            duration=incoming_dict["duration"],
            stress=incoming_dict["stress"],
            difficulty=incoming_dict["difficulty"],
            due_date=datetime.fromisoformat(due_date) if due_date else None,
            _is_complete=incoming_dict["is_complete"],
            last_refreshed=datetime.fromisoformat(last_refreshed)
            if last_refreshed
            else None or Task._DEFAULT_REFRESHED,
            identifier=incoming_dict.get("identifier", str(uuid.uuid4())),
            dependent_on=incoming_dict.get("dependent_on", []),
            stress_dynamic=BaseDynamic.find_dynamic(stress_dynamic)
            if stress_dynamic
            else None,
            creation_date=datetime.fromisoformat(creation_date)
            if creation_date
            else datetime.now(),
            list_name=incoming_dict.get("list_name", "default"),
            cool_down=incoming_dict.get("cool_down"),
            periodicity=incoming_dict.get("periodicity")
        )

    def to_dict(self):
        return {
            "title": self.title,
            "description": self.description,
            "duration": self.duration,
            "stress": self.stress,
            "difficulty": self.difficulty,
            "is_complete": self._is_complete,
            "due_date": self.due_date.isoformat() if self.due_date else self.due_date,
            "last_refreshed": self.last_refreshed.isoformat(),
            "identifier": self.identifier,
            "dependent_on": self.dependent_on,
            "stress_dynamic": self.stress_dynamic.to_text()
            if self.stress_dynamic
            else None,
            "creation_date": self.creation_date.isoformat(),
            "list_name": self.list_name,
            "cool_down": self.cool_down,
            "periodicity": self.periodicity
        }
