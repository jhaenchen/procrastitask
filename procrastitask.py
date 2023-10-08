from dataclasses import dataclass, field
import json
import math
import os
import subprocess
import tempfile
from subprocess import call
from time import sleep
from datetime import datetime, timedelta
from typing import Callable, List, Optional, TypeVar
import uuid
import ast

EDITOR = os.environ.get("EDITOR", "vim")  # that easy!


def rlinput(prefill: str = "", prompt="Edit:", multiprompt: dict = None) -> List[str]:
    if multiprompt:
        final_str = ""
        for key, val in multiprompt.items():
            final_str += f"{key}{val}\n"
        prompt = final_str[:-1]
    initial_message = bytes(
        str(prompt) + str(prefill), encoding="utf-8"
    )  # if you want to set up the file somehow

    with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
        tf.write(initial_message)
        tf.flush()
        call([EDITOR, "+set backupcopy=yes", tf.name])

        # do the parsing with `tf` using regular File operations.
        # for instance:
        tf.seek(0)
        edited_message = str(tf.read())

        to_return = []

        if multiprompt:
            multiprompt_items = list(multiprompt.items())
            for idx, (key, val) in enumerate(multiprompt_items):
                first_part = edited_message.split(key)[1]
                next_part_idx = idx + 1
                if len(multiprompt_items) >= next_part_idx + 1:
                    first_part = first_part.split(multiprompt_items[next_part_idx][0])[
                        0
                    ]
                formatted = first_part[:-2]
                formatted = None if formatted == "None" else formatted
                to_return.append(formatted)
        else:
            splitted = str(edited_message).split(prompt)
            if len(splitted) == 2:
                return [splitted[1][:-3]]
        return to_return


@dataclass
class Task:
    _DEFAULT_REFRESHED = datetime(1970, 1, 1)

    title: str
    description: str
    difficulty: int
    duration: int
    stress: int
    is_complete: bool = False
    due_date: datetime = None
    last_refreshed: datetime = field(default_factory=datetime.now)
    identifier: str = str(uuid.uuid4())
    dependent_on: List[int] = field(default_factory=lambda: [])

    def __key(self):
        return (self.title, self.description)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, Task):
            return self.__key() == other.__key()
        return NotImplemented

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
        elif due_in < timedelta(days=math.ceil(self.duration / 60) * 2):
            return True
        return False

    def get_date_str(self, datetime: datetime):
        delta = datetime - datetime.now()
        if delta < timedelta(0):
            return f"{delta.days} days"
        return f"+{delta.days} days"

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

    def headline(self):
        return f"{self.title} ({self.duration}min, stress: {self.stress}, diff: {self.difficulty}{(', ' + self.get_date_str(self.due_date)) if self.due_date else ''})"

    def complete(self):
        self.is_complete = True

    @staticmethod
    def from_dict(incoming_dict):
        due_date = incoming_dict.get("due_date")
        last_refreshed = incoming_dict.get("last_refreshed")
        return Task(
            title=incoming_dict["title"],
            description=incoming_dict["description"],
            duration=incoming_dict["duration"],
            stress=incoming_dict["stress"],
            difficulty=incoming_dict["difficulty"],
            due_date=datetime.fromisoformat(due_date) if due_date else None,
            is_complete=incoming_dict["is_complete"],
            last_refreshed=datetime.fromisoformat(last_refreshed)
            if last_refreshed
            else None or Task._DEFAULT_REFRESHED,
            identifier=incoming_dict.get("identifier", str(uuid.uuid4())),
            dependent_on=incoming_dict.get("dependent_on", []),
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
            "last_refreshed": self.last_refreshed.isoformat(),
            "identifier": self.identifier,
            "dependent_on": self.dependent_on,
        }


class App:
    def __init__(self):
        self.all_tasks = []
        self.cached_listed_tasks: dict[int, Task] = {}
        self.reset_screen()

    def load(self):
        try:
            with open("/Users/haenchen/tasks.json", "r") as db:
                json_tasks = json.loads(db.read())
                self.all_tasks = [Task.from_dict(j_task) for j_task in json_tasks]
        except Exception as e:
            print(f"Error: {e}")
            self.all_tasks = []

    def save(self):
        with open("/Users/haenchen/tasks.json", "w") as db:
            task_json_dicts = [task.to_dict() for task in self.all_tasks]
            json_str = json.dumps(task_json_dicts)
            db.write(json_str)

    def delete_task(self, task_title):
        # print(f"Deleting title {task_title} from collection {self.all_tasks}")
        self.all_tasks = [task for task in self.all_tasks if task.title != task_title]

    def get_date_prompt(self, prompt_text: str, input_func=None):
        result = input_func(prompt_text) if input_func else input(prompt_text)
        try:
            return datetime.fromisoformat(result)
        except ValueError:
            pass
        if not result:
            return None
        parts = result.split(".")
        now = datetime.now()
        if len(parts) == 1:
            year = now.year
            day = int(parts[0])
            month = now.month
            if now.day > day:
                month = month + 1
            if now.month > month:
                year = year + 1
            return datetime(day=day, month=month, year=year, hour=9)
        if len(parts) == 2:
            year = now.year
            day = int(parts[0])
            month = int(parts[1]) - 1
            if now.day > day:
                month = month + 1
            if now.month > month:
                year = year + 1
            return datetime(day=day, month=month, year=year, hour=9)
        if len(parts) == 3:
            return datetime(day=parts[0], month=parts[1], year=parts[2], hour=9)

    def get_numerical_prompt(self, prompt_text, also_accept=None, input_func=None):
        while True:
            try:
                result = input_func(prompt_text) if input_func else input(prompt_text)
                return int(result)
            except ValueError:
                if result in (also_accept or []):
                    return result
                print(f"\nBad input: {result}. Try again.\n")
                sleep(5)

    T = TypeVar("T")

    def get_input_with_validation_mapper(
        self, prompt: str, validator_mapper: Callable[[str], T] = lambda s: s
    ) -> T:
        while True:
            result = input(prompt)
            try:
                mapped = validator_mapper(result)
                return mapped
            except ValueError:
                print(f"\nBad input: {result}. Try again.\n")
                sleep(5)

    @property
    def dependence_validator(self):
        def to_return_validator(dependent_on: str) -> List[str]:
            dependence_pieces = dependent_on.split(",")
            # Empty string yields ['']
            if dependence_pieces == [""]:
                return []
            mapped_ids = []
            for potential_val in dependence_pieces:
                mapped_to = None
                # Is the given val an ID?
                for task in self.all_tasks:
                    if task.identifier == potential_val:
                        mapped_to = potential_val
                # If we didn't find a perfect match, try index
                if mapped_to is None:
                    try:
                        target_idx = int(potential_val)
                        idx_looked_up_task = self.cached_listed_tasks.get(target_idx)
                        if idx_looked_up_task:
                            mapped_to = idx_looked_up_task.identifier
                    except ValueError:
                        pass

                if mapped_to is not None:
                    mapped_ids.append(mapped_to)
                else:
                    raise ValueError("Did not find corresponding task for that value")
            return mapped_ids

        return to_return_validator

    def create_new_task(self):
        task_title = input("Enter your task: ")
        task_description = input("Enter description: ")
        duration = self.get_numerical_prompt("Estimated duration (minutes): ")
        stress_level = self.get_numerical_prompt("Stress level: ")
        difficulty = self.get_numerical_prompt("Difficulty: ")
        date = self.get_date_prompt("Due date:")
        dependent_on = self.get_input_with_validation_mapper(
            "Dependent on tasks: ", self.dependence_validator
        )

        created_task = Task(
            title=task_title,
            description=task_description,
            duration=duration,
            stress=stress_level,
            difficulty=difficulty,
            due_date=date,
            dependent_on=dependent_on,
        )
        return created_task

    def task_sorter(self, x: Task):
        x_stress = x.stress
        if x.is_due_soon():
            x_stress += max(x_stress * 0.33, 1)
        return x_stress

    def list_all_tasks(
        self, task_list_override=None, extend_cache=False, also_print=True
    ):
        tasks = task_list_override or self.all_tasks
        if not extend_cache:
            self.cached_listed_tasks = {}
        incomplete_tasks = [
            task
            for task in tasks
            if task.is_complete == False and task.dependent_on == []
        ]
        start_index = (
            0
            if not extend_cache
            else (max(-1, *[key for key in self.cached_listed_tasks]) + 1)
        )
        if len(incomplete_tasks) == 0:
            if also_print:
                print("You have no available tasks.")
            return []

        incomplete_tasks = sorted(incomplete_tasks, key=self.task_sorter, reverse=True)
        to_return = []
        for idx, task in enumerate(incomplete_tasks):
            true_idx = idx + start_index
            dependent_count = task.get_dependent_count(tasks)
            to_return.append(
                f"[{true_idx}] {f'(+{dependent_count})' if dependent_count else ''} {task.headline()}"
            )
            # print(f"\n* {task.title} ({task.duration}min)")
            self.cached_listed_tasks[true_idx] = task

        if also_print:
            [print(el) for el in to_return]
        return to_return

    def _is_number(self, num_string):
        try:
            int(num_string)
            return True
        except ValueError:
            return False

    def _get_strictly_matching_tasks(self, available_time, available_energy):
        candidates = []
        for task in self.all_tasks:
            if (task.duration <= available_time) and (
                task.difficulty <= available_energy
            ):
                candidates.append(task)
        candidates.sort(key=lambda t: t.stress)
        return candidates

    def _get_stretch_tasks(self, available_time, available_energy):
        candidates = []
        for task in self.all_tasks:
            if (task.duration < available_time) and (
                (
                    task.difficulty <= (int(available_energy * 1.5))
                    and (task.difficulty > available_energy)
                )
            ):
                candidates.append(task)
        candidates.sort(key=lambda t: t.stress)
        return candidates

    def wizard(self):
        print("\nWelcome to the completion wizard.")
        available_time = self.get_numerical_prompt(
            "\nHow much time do you have (minutes)? "
        )
        available_energy = self.get_numerical_prompt("\nHow much energy do you have? ")
        self.cached_listed_tasks = {}
        strict_candidates = self._get_strictly_matching_tasks(
            available_time, available_energy
        )
        stretch_candidates = self._get_stretch_tasks(available_time, available_energy)
        self.reset_screen()
        if len(strict_candidates) > 0:
            print("I recommend the following tasks:")
            self.list_all_tasks(strict_candidates)
            if stretch_candidates:
                print("\nAnd this possible stretch task:")
                self.list_all_tasks([stretch_candidates[0]], extend_cache=True)
        else:
            if stretch_candidates:
                print("\nYou have no perfect fits, but try these stretch tasks:")
                self.list_all_tasks([stretch_candidates[:3]])

    def find_task(self, task_title):
        matches = [task for task in self.all_tasks if task.title == task_title]
        return matches[0] if matches else None

    def refresh_stress_levels(self):
        self.reset_screen()
        seen_tasks = set()
        while True:
            self.reset_screen()
            remaining_tasks = [
                t
                for t in self.all_tasks
                if t.is_complete == False and t not in seen_tasks
            ]
            if not remaining_tasks:
                return
            remaining_tasks.sort(key=lambda t: t.last_refreshed, reverse=False)
            chosen_task = remaining_tasks[0]
            if not chosen_task:
                return
            seen_tasks.add(chosen_task)
            self.list_all_tasks([chosen_task])
            new_stress = self.get_numerical_prompt(
                "Enter new stress level for task: ", also_accept=["x", ""]
            )
            if new_stress == "x":
                return
            found_task = self.find_task(chosen_task.title)
            if found_task:
                found_task.last_refreshed = datetime.now()
                if new_stress != "":
                    found_task.stress = new_stress

    def reset_screen(self):
        os.system("clear")
        print(self.WELCOME_MESSAGE)

    WELCOME_MESSAGE = "\nWelcome to Procrastinator's Companion\n"

    def edit_task(self, task: Task):
        (
            title,
            description,
            due_date,
            difficulty,
            stress,
            duration,
            dependent_on,
            is_complete,
        ) = rlinput(
            multiprompt={
                "Title:": task.title,
                "Description:": task.description,
                "Due Date:": task.due_date,
                "Difficulty:": task.difficulty,
                "Stress:": task.stress,
                "Duration:": task.duration,
                "Dependent On:": task.dependent_on,
                "Is Complete:": task.is_complete,
            }
        )
        task.dependent_on = ast.literal_eval(dependent_on)
        task.title = title

        task.description = description
        task.due_date = (
            self.get_date_prompt(
                "",
                input_func=lambda *args, **kwargs: due_date,
            )
            if due_date
            else None
        )
        task.difficulty = self.get_numerical_prompt(
            "",
            input_func=lambda *args, **kwargs: difficulty,
        )
        task.stress = self.get_numerical_prompt(
            "", input_func=lambda *args, **kwargs: stress
        )
        task.duration = self.get_numerical_prompt(
            "", input_func=lambda *args, **kwargs: duration
        )
        task.is_complete = bool(is_complete)

    def paged_task_list(self):
        self.reset_screen()
        rows = int(
            subprocess.run(["tput", "lines"], stdout=subprocess.PIPE).stdout.decode(
                "utf-8"
            )
        )
        columns = int(
            subprocess.run(["tput", "cols"], stdout=subprocess.PIPE).stdout.decode(
                "utf-8"
            )
        )
        pos = [0, 0]
        rows -= math.ceil(len(self.WELCOME_MESSAGE) / columns) + 1
        rows -= math.ceil(len(self.CORE_COMMAND_PROMPT) / columns) + 1
        would_print_collection = self.list_all_tasks(also_print=False)

        print_until = 0
        for idx, candidate in enumerate(would_print_collection):
            new_y = pos[1] + math.ceil(len(candidate) / columns)
            if new_y < rows:
                pos[1] = new_y
                print_until += 1
        for to_print in would_print_collection[:print_until]:
            print(to_print)

    def find_task_by_any_id(self, input_str: str) -> Optional[Task]:
        if self._is_number(input_str):
            selected_task = self.cached_listed_tasks.get(int(input_str))
            if selected_task:
                return selected_task
        found_id_matches = [task for task in self.all_tasks if task.identifier == input_str]
        if found_id_matches:
            return found_id_matches[0]

    CORE_COMMAND_PROMPT = "Enter your command (new = n, list = ls, digit = view, xdigit = complete, ddigit = delete, s = save, r = refresh): "

    def display_home(self):
        print("\n")
        command = input(self.CORE_COMMAND_PROMPT)
        self.reset_screen()

        if len(command) == 0:
            return
        if command == "n":
            self.all_tasks.append(self.create_new_task())
        if command == "ls":
            self.paged_task_list()
            # self.list_all_tasks()
        if self.find_task_by_any_id(command):
            found_task = self.find_task_by_any_id(command)
            found_task.pretty_print(self.all_tasks)
        if command.startswith("x"):
            index_val = command.split("x")[1]
            selected_task: Task = self.cached_listed_tasks.get(int(index_val))
            selected_task.complete()
            print("\nTask completed.")
        if command.startswith("d"):
            index_val = command.split("d")[1]
            selected_task = self.cached_listed_tasks.get(int(index_val))
            self.delete_task(selected_task.title)
            print("\nTask deleted.")
        if command == "exit":
            exit()
        if command.startswith("e"):
            index_val = command[1:]
            selected_task = self.find_task_by_any_id(index_val)
            self.edit_task(selected_task)
        if command == "s":
            self.save()
            print("Saved.")
        if command == "load":
            self.load()
            self.list_all_tasks()
        if command == "w":
            self.wizard()
        if command == "r":
            self.refresh_stress_levels()
        return


os.system("clear")
app = App()
app.load()
app.list_all_tasks()
while True:
    app.display_home()
