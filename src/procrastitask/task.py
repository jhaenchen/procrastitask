import logging
from dataclasses import dataclass, field
import math
import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from typing import List, TypedDict, Optional
import uuid
import icalendar
import croniter
from .dynamics.base_dynamic import BaseDynamic

log = logging.getLogger()

class TaskStatus:
    INCOMPLETE = "INCOMPLETE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"

@dataclass
class CompletionRecord:
    completed_at: datetime
    stress_at_completion: int

    def to_dict(self):
        return {
            "completed_at": self.completed_at.isoformat(),
            "stress_at_completion": self.stress_at_completion
        }

    @classmethod
    def from_dict(cls, data):
        return cls(completed_at=datetime.fromisoformat(data["completed_at"]), stress_at_completion=data["stress_at_completion"])


@dataclass
class Task:
    _DEFAULT_REFRESHED = datetime(1970, 1, 1)

    title: str
    description: str
    difficulty: int
    duration: int
    stress: int
    _is_complete: bool = False
    due_date: Optional[datetime] = None
    due_date_cron: Optional[str] = None  # New: cron string for repeating due dates
    last_refreshed: datetime = field(default_factory=datetime.now)
    identifier: str = field(default_factory=lambda: str(uuid.uuid4()))
    dependent_on: List[int] = field(default_factory=lambda: [])
    stress_dynamic: Optional[BaseDynamic] = None
    creation_date: datetime = field(default_factory=datetime.now)
    list_name: str = "default"
    cool_down: Optional[str] = None
    periodicity: Optional[str] = None
    history: List[CompletionRecord] = field(default_factory=lambda: [])
    status: str = TaskStatus.INCOMPLETE

    def _format_num_as_int_if_possible(self, val):
        floated = float(val)
        if floated.is_integer():
            return int(floated)
        return round(floated, 1)

    @property
    def is_complete(self):
        log.debug(f"Evaluating is_complete for task named: {self.title}")

        # Wrap this in a function so matter what, the result it returns get assigned to the inner class property
        def render_logic():
            if not self._is_complete:
                log.debug("Task is incomplete, returning incomplete.")
                return self._is_complete
            if self.cool_down:
                log.debug("Cool down is configured. Let's evaluate.")
                if self.history:
                    time_since_last_completion = datetime.now() - self.history[-1].completed_at
                else:
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
                buffer = interval * 0.10
                reset_at = next_time_to_complete - buffer

                # Use the latest completion time from history, if available
                if self.history:
                    last_completion_time = self.history[-1].completed_at
                else:
                    last_completion_time = None

                if last_completion_time is None or last_completion_time < (previous_time_to_complete - buffer):
                    # We missed a chance, bump it to incomplete
                    return False

                if last_completion_time >= reset_at:
                    # Completed within the buffer period
                    return True

                if datetime.now() > reset_at:
                    return False
                return True
            elif self.due_date_cron: # If there's no periodicity, but a due date cron, then it's never complete
                return False
            return self._is_complete
        
        result = render_logic()
        self._is_complete = result
        if result:
            self.status = TaskStatus.COMPLETE
        elif self.status == TaskStatus.COMPLETE:
            self.status = TaskStatus.INCOMPLETE
        return self._is_complete

    @is_complete.setter
    def is_complete(self, val):
        if val is not None:
            log.info(f"Setting is_complete for task named: {self.title} to {val}")
            self._is_complete = val
            self.update_last_refreshed()
            if val == True:
                self.history.append(CompletionRecord(self.last_refreshed, int(self.get_rendered_stress())))
            self.status = TaskStatus.COMPLETE if val else TaskStatus.INCOMPLETE

    @staticmethod
    def convert_cool_down_str_to_delta(cool_down: str) -> timedelta:
        if "min" in cool_down:
            return timedelta(minutes=int(cool_down.split("min")[0]))
        if "hr" in cool_down:
            return timedelta(hours=int(cool_down.split("hr")[0]))
        if "d" in cool_down:
            return timedelta(days=int(cool_down.split("d")[0]))
        if "w" in cool_down:
            return timedelta(weeks=int(cool_down.split("w")[0]))
        if "m" in cool_down:
            return timedelta(weeks=int(cool_down.split("m")[0]) * 4.345)
        raise ValueError(f"The set cool down str is not parseable: {cool_down}")

    def get_dynamic_base_date(self):
        """
        Returns the correct base date for dynamic calculations, factoring in cool_down and periodicity.
        - For cool_down: returns the most recent moment when the task became incomplete again based on the cool down.
        - For periodicity: returns the most recent incomplete periodicity moment (cron boundary).
        - Otherwise, returns last_refreshed or creation_date.
        """
        now = datetime.now()
        # Handle periodicity (cron)
        if self.periodicity:
            cron = croniter.croniter(self.periodicity, now)
            prev_period = cron.get_prev(datetime)
            # If last completion is before the previous period, use prev_period
            if self.history:
                last_completion = self.history[-1].completed_at
                if last_completion < prev_period:
                    return prev_period
                else:
                    return last_completion
            else:
                return prev_period  # Use prev_period if no completions
        # Handle cool_down
        if self.cool_down:
            if self.history:
                last_completion = self.history[-1].completed_at
                cooldown_delta = self.convert_cool_down_str_to_delta(self.cool_down)
                cooldown_expiry = last_completion + cooldown_delta
                if now > cooldown_expiry:
                    return cooldown_expiry
                else:
                    return self.creation_date
            else:
                return self.creation_date
        # Default: use last_refreshed or creation_date
        return self.creation_date

    def get_rendered_stress(self):
        log.debug(f"Evaluating rendered stress for task {self.title}")
        base_stress = self.stress
        if not self.stress_dynamic:
            return round(base_stress, 1)
        base_stress_date = self.get_dynamic_base_date()
        return round(self.stress_dynamic.apply(base_stress_date, self.stress, self), 1)

    def update_last_refreshed(self):
        self.last_refreshed = datetime.now()
    
    def _key(self):
        return (self.title, self.description)

    def __hash__(self):
        return hash(self._key())

    def __eq__(self, other):
        if isinstance(other, Task):
            return self._key() == other._key()
        return NotImplemented
    
    @property
    def latest_history(self) -> Optional[CompletionRecord]:
        """
        Get the latest history record for this task, based on date.
        """
        if self.history:
            return max(self.history, key=lambda completion_rec: completion_rec.completed_at)
        return None

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

    @property
    def current_due_date(self) -> Optional[datetime]:
        """
        For cron-based due dates, returns the first due date (from creation_date forward) that does not have a corresponding completion record.
        Each completion record can satisfy any due date (past or future), one-to-one, in order.
        If all due dates are completed, returns the next due date.
        If only due_date is set, returns due_date.
        """
        if self.due_date_cron:
            completions = sorted(self.history, key=lambda c: c.completed_at)
            due_dates = []
            cron_iter = croniter.croniter(self.due_date_cron, self.creation_date)
            for _ in range(len(completions) + 1):
                due_dates.append(cron_iter.get_next(datetime))
            # Return the first due date without a corresponding completion
            if len(completions) < len(due_dates):
                return due_dates[len(completions)]
            # If all completions used, return the next due date
            return cron_iter.get_next(datetime)
        return self.due_date

    def is_due_soon(self):
        due = self.current_due_date
        if not due:
            return False
        due_in = due - datetime.now()
        if due_in < timedelta(0):
            # Already due
            return True
        # "Soon" is defined as +2 days for every hour of effort
        # Meaning a two hour task is due soon in < 4 days
        elif due_in < timedelta(days=math.ceil(self.duration / 60) * 2):
            return True
        return False

    def get_date_str(self, dt: datetime):
        delta = dt - datetime.now()
        if delta < timedelta(0):
            return f"-{abs(delta.days)} days"
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
            found = [t for t in all_tasks if t.identifier == task_id]
            if not found:
                log.warning(f"Dependent task with id {task_id} not found.")
                continue
            if not found[0]._is_complete:
                saw_incomplete = True
        return not saw_incomplete

    def headline(self):
        due = self.current_due_date
        return f"{self.title} ({self._format_num_as_int_if_possible(self.duration)}min, stress: {self._format_num_as_int_if_possible(self.get_rendered_stress())}, diff: {self._format_num_as_int_if_possible(self.difficulty)}{(', ' + self.get_date_str(due)) if due else ''})"

    def complete(self):
        self.update_last_refreshed()
        self.is_complete = True
        log.info(f"Completing task: {self.title}.")

    def set_in_progress(self):
        self.status = TaskStatus.IN_PROGRESS

    def set_incomplete(self):
        self.status = TaskStatus.INCOMPLETE

    @staticmethod
    def from_dict(incoming_dict):
        due_date = incoming_dict.get("due_date")
        due_date_cron = incoming_dict.get("due_date_cron")
        last_refreshed = incoming_dict.get("last_refreshed")
        stress_dynamic = incoming_dict.get("stress_dynamic")
        creation_date = incoming_dict.get("creation_date")
        status = incoming_dict.get("status", TaskStatus.INCOMPLETE)

        return Task(
            title=incoming_dict["title"],
            description=incoming_dict["description"],
            duration=incoming_dict["duration"],
            stress=incoming_dict["stress"],
            difficulty=incoming_dict["difficulty"],
            due_date=datetime.fromisoformat(due_date) if due_date else None,
            due_date_cron=due_date_cron,
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
            periodicity=incoming_dict.get("periodicity"),
            history=[CompletionRecord.from_dict(data) for data in incoming_dict.get("history", [])],
            status=status
        )

    def to_dict(self):
        return {
            "title": self.title,
            "description": self.description,
            "duration": self.duration,
            "stress": self.stress,
            "difficulty": self.difficulty,
            "is_complete": self.is_complete,
            "due_date": self.due_date.isoformat() if self.due_date else self.due_date,
            "due_date_cron": self.due_date_cron,
            "last_refreshed": self.last_refreshed.isoformat(),
            "identifier": self.identifier,
            "dependent_on": self.dependent_on,
            "stress_dynamic": self.stress_dynamic.to_text()
            if self.stress_dynamic
            else None,
            "creation_date": self.creation_date.isoformat(),
            "list_name": self.list_name,
            "cool_down": self.cool_down,
            "periodicity": self.periodicity,
            "history": [completion.to_dict() for completion in self.history],
            "status": self.status
        }
