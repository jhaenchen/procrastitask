# procrastitask_app.py

from configparser import ConfigParser, NoSectionError
import os
import json
import math
import subprocess
import tempfile
from subprocess import call
from time import sleep
from datetime import datetime, timedelta
from typing import Callable, List, Optional, TypeVar, Union, Dict
import ast
import logging

import croniter

from procrastitask.dynamics.base_dynamic import BaseDynamic
from procrastitask.task import Task, TaskState
from procrastitask.task_collection import TaskCollection

EDITOR = os.environ.get("EDITOR", "vim")  # Default editor

# Configure logging
log = logging.getLogger(__name__)
log.setLevel("DEBUG")
logging.basicConfig(filename="log.txt", level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')


def rlinput(prefill: str = "", prompt="Edit:", multiprompt: Optional[dict] = None) -> List[str]:
    if multiprompt:
        final_str = ""
        for key, val in multiprompt.items():
            final_str += f"{key}{val}\n"
        prompt = final_str[:-1]
    initial_message = bytes(
        str(prompt) + str(prefill), encoding="utf-8"
    )  # Initial content for the editor

    with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
        tf.write(initial_message)
        tf.flush()
        call([EDITOR, "+set backupcopy=yes", tf.name])

        # Read the edited content
        tf.seek(0)
        edited_message = tf.read().decode()

        to_return = []

        if multiprompt:
            multiprompt_items = list(multiprompt.items())
            for idx, (key, val) in enumerate(multiprompt_items):
                first_part = edited_message.split(key)[1]
                next_part_idx = idx + 1
                if len(multiprompt_items) > next_part_idx:
                    first_part = first_part.split(multiprompt_items[next_part_idx][0])[0]
                formatted = first_part.strip()
                formatted = None if formatted == "None" else formatted
                to_return.append(formatted)
        else:
            splitted = edited_message.split(prompt)
            if len(splitted) == 2:
                return [splitted[1].strip()]
        return to_return


class TaskManager:
    """
    Handles all task-related operations including loading, saving, adding, editing, deleting, and querying tasks.
    """

    def __init__(self, tasks_file: str, list_config_file: str):
        self.tasks_file = tasks_file
        self.list_config_file = list_config_file
        self.all_tasks: List[Task] = []
        self.filtered_tasks_to_resave: List[Task] = []
        self.selected_task_lists: List[str] = ["default"]
        self.task_lists: List[str] = []
        self.load_list_config()
        self.load_tasks()

    def load_list_config(self):
        try:
            with open(self.list_config_file, "r") as lists:
                task_lists = json.load(lists)["lists"]
                self.task_lists = [el["name"] for el in task_lists]
                log.info(f"Loaded task lists: {self.task_lists}")
        except Exception as e:
            log.error(f"Failed to load list config: {e}")
            print("Config error, check formatting of list_config.json")

    def load_tasks(self):
        try:
            with open(self.tasks_file, "r") as db:
                json_tasks = json.load(db)
                self.all_tasks = [Task.from_dict(j_task) for j_task in json_tasks]
                log.debug(f"Loaded {len(self.all_tasks)} tasks from {self.tasks_file}")
        except FileNotFoundError:
            log.warning(f"Tasks file not found at {self.tasks_file}. Starting with an empty task list.")
            self.all_tasks = []
        except json.JSONDecodeError as e:
            log.error(f"JSON decode error: {e}")
            print("Error: Corrupted tasks file. Unable to parse tasks.")
            self.all_tasks = []
        except Exception as e:
            log.error(f"Unexpected error while loading tasks: {e}")
            print(f"Error: {e}")
            self.all_tasks = []

    def save_tasks(self):
        try:
            with open(self.tasks_file, "w") as db:
                task_json_dicts = [task.to_dict() for task in self.all_tasks + self.filtered_tasks_to_resave]
                json.dump(task_json_dicts, db, indent=4)
                log.info(f"Saved {len(task_json_dicts)} tasks to {self.tasks_file}")
        except Exception as e:
            log.error(f"Failed to save tasks: {e}")
            print(f"Failed to save tasks: {e}")
            sleep(5)

    def add_task(self, task: Task):
        self.all_tasks.append(task)
        log.info(f"Added task: {task.title}")
        self.save_tasks()

    def edit_task(self, task_id: str, **kwargs):
        task = self.find_task_by_id(task_id)
        if not task:
            print("Task not found.")
            return
        for key, value in kwargs.items():
            setattr(task, key, value)
        log.info(f"Edited task: {task.title}")
        self.save_tasks()

    def delete_task(self, task_id: str):
        task = self.find_task_by_id(task_id)
        if task:
            self.all_tasks.remove(task)
            log.info(f"Deleted task: {task.title}")
            self.save_tasks()
        else:
            print("Task not found.")

    def find_task_by_id(self, task_id: str) -> Optional[Task]:
        return next((task for task in self.all_tasks if task.identifier == task_id), None)

    def filter_tasks(self, selected_lists: List[str]):
        self.selected_task_lists = selected_lists
        self.all_filtered_tasks = [
            task for task in self.all_tasks
            if task.list_name in self.selected_task_lists or "all" in self.selected_task_lists
        ]
        self.filtered_tasks_to_resave = [
            task for task in self.all_tasks
            if task.list_name not in self.selected_task_lists and "all" not in self.selected_task_lists
        ]
        log.debug(f"Filtered tasks based on selected lists: {selected_lists}")

    def should_do_refresh(self) -> bool:
        incomplete_tasks_dates = [
            task.last_refreshed for task in self.all_filtered_tasks if not task.is_complete
        ]
        if not incomplete_tasks_dates:
            return False
        min_refreshed = min(incomplete_tasks_dates)
        return datetime.now() - min_refreshed > timedelta(weeks=1)


class App:
    def __init__(self):
        self.config = self.config_loader()
        self.task_manager = TaskManager(
            tasks_file=self.get_db_location(),
            list_config_file=self.get_list_config_path()
        )
        self.cached_listed_tasks: Dict[int, Task] = {}
        self.reset_screen()

    CONFIG_FILE_NAME = "config.ini"

    def config_loader(self) -> dict:
        config = {}
        try:
            Config = ConfigParser()
            Config.read(self.get_config_path())
            config = dict(Config.items("task_config"))
            log.info("Configuration loaded successfully.")
        except NoSectionError:
            log.error("Config error, check formatting of config.ini")
            print("Config error, check formatting of config.ini")
        return config

    def get_current_dir(self):
        return os.path.dirname(os.path.realpath(__file__))

    def get_config_path(self):
        dir_path = self.get_current_dir() + "/../.."
        return os.path.join(dir_path, self.CONFIG_FILE_NAME)

    def get_list_config_path(self):
        dir_path = self.config.get("db_location", self.get_current_dir() + "/../..")
        return os.path.join(dir_path, "list_config.json")

    def get_db_location(self):
        dir_path = self.config.get("db_location", self.get_current_dir() + "/../..")
        return os.path.join(dir_path, "tasks.json")

    def prompt_for_task_list_selection(self) -> List[str]:
        self.reset_screen()
        task_lists_for_prompt = ["all"] + self.task_manager.task_lists
        print("Select your task lists (comma-separated indices):")
        for list_idx, list_name in enumerate(task_lists_for_prompt):
            print(f"[{list_idx}] {list_name}")
        chosen_indices = self.get_input_with_validation_mapper(
            prompt="Enter indices: ",
            validator_mapper=lambda s: [int(val.strip()) for val in s.split(",")],
        )
        selected_lists = [
            task_lists_for_prompt[idx] for idx in chosen_indices if 0 <= idx < len(task_lists_for_prompt)
        ]
        self.reset_screen()
        log.info(f"Selected task lists: {selected_lists}")
        return selected_lists

    def load(self, default_lists: Optional[List[str]] = None):
        if default_lists:
            self.task_manager.filter_tasks(default_lists)
        else:
            selected_lists = self.prompt_for_task_list_selection()
            self.task_manager.filter_tasks(selected_lists)
        log.info(f"Loaded tasks with selected lists: {self.task_manager.selected_task_lists}")

    def save(self):
        self.task_manager.save_tasks()
        print("Tasks saved successfully.")
        log.info("Tasks saved successfully.")

    def delete_task(self, task_id: str):
        self.task_manager.delete_task(task_id)
        print("Task deleted successfully.")
        log.info(f"Task with ID {task_id} deleted.")

    def should_do_refresh(self) -> bool:
        return self.task_manager.should_do_refresh()

    def get_date_prompt(self, prompt_text: str, input_func=None) -> Optional[datetime]:
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
                month += 1
            if now.month > month:
                year += 1
            return datetime(year=year, month=month, day=day, hour=9)
        if len(parts) == 2:
            year = now.year
            day = int(parts[0])
            month = int(parts[1])
            if now.month > month:
                year += 1
            return datetime(year=year, month=month, day=day, hour=9)
        if len(parts) == 3:
            return datetime(year=int(parts[2]), month=int(parts[1]), day=int(parts[0]), hour=9)
        return None

    def modify_cached_task_stress_by_offset(self, cached_idx: int, offset: int):
        found_task: Task = self.cached_listed_tasks.get(cached_idx)
        if not found_task:
            print("Invalid task index.")
            return
        existing_stress = found_task.get_rendered_stress()
        new_stress = existing_stress + offset
        found_task.stress = new_stress
        found_task.update_last_refreshed()
        log.info(f"Updated task stress for '{found_task.title}' from {existing_stress} to {new_stress}")
        print(f"Updated task stress for '{found_task.title}' from {existing_stress} to {new_stress}")

    def get_numerical_prompt(
        self, prompt_text: str, also_accept: Optional[List[Union[str, int]]] = None,
        input_func=None, raise_exception: bool = False
    ) -> Union[float, str]:
        while True:
            try:
                result = input_func(prompt_text) if input_func else input(prompt_text)
                return float(result)
            except ValueError:
                message = f"\nBad input for prompt '{prompt_text}': '{result}'. Try again.\n"
                if also_accept and result in also_accept:
                    return result
                if raise_exception:
                    raise ValueError(message)
                print(message)
                sleep(5)

    T = TypeVar("T")

    def get_input_with_validation_mapper(
        self,
        prompt: str,
        validator_mapper: Callable[[str], T] = lambda s: s,
        raise_exception: bool = False,
    ) -> T:
        while True:
            result = input(prompt)
            try:
                mapped = validator_mapper(result)
                return mapped
            except ValueError as e:
                message = f"\nBad input for prompt '{prompt}': '{result}'. {e}\n"
                if raise_exception:
                    raise ValueError(message)
                print(message)
                sleep(5)

    @property
    def dependence_validator(self):
        def to_return_validator(dependent_on: str) -> List[str]:
            dependence_pieces = [piece.strip() for piece in dependent_on.split(",") if piece.strip()]
            if not dependence_pieces:
                return []
            mapped_ids = []
            for potential_val in dependence_pieces:
                # Check if potential_val is a UUID
                if self.task_manager.find_task_by_id(potential_val):
                    mapped_ids.append(potential_val)
                else:
                    try:
                        target_idx = int(potential_val)
                        task = self.cached_listed_tasks.get(target_idx)
                        if task:
                            mapped_ids.append(task.identifier)
                        else:
                            raise ValueError
                    except ValueError:
                        raise ValueError(f"Did not find corresponding task for value: {potential_val}")
            return mapped_ids

        return to_return_validator

    def edit_or_create_task(
        self, task_to_edit: Optional[Task] = None, dependent_on: Optional[List[str]] = None
    ) -> Task:
        try:
            title = task_to_edit.title if task_to_edit else ""
            description = task_to_edit.description if task_to_edit else ""
            due_date = task_to_edit.due_date.isoformat() if task_to_edit and task_to_edit.due_date else ""
            difficulty = str(task_to_edit.difficulty) if task_to_edit else ""
            stress = str(task_to_edit.get_rendered_stress()) if task_to_edit else ""
            duration = str(task_to_edit.duration) if task_to_edit else ""
            dependent_on = dependent_on if dependent_on else task_to_edit.dependent_on if task_to_edit else []
            is_complete = "True" if task_to_edit.is_complete else "False" if task_to_edit else "False"
            dynamic = task_to_edit.stress_dynamic.to_text() if task_to_edit and task_to_edit.stress_dynamic else ""
            creation_date = task_to_edit.creation_date.isoformat() if task_to_edit else datetime.now().isoformat()
            cool_down = task_to_edit.cool_down if task_to_edit else ""
            periodicity = task_to_edit.periodicity if task_to_edit else ""
            task_list_name = task_to_edit.list_name if task_to_edit else (
                self.task_manager.selected_task_lists[0]
                if len(self.task_manager.selected_task_lists) == 1 and "all" not in self.task_manager.selected_task_lists
                else "default"
            )

            multiprompt = {
                "Title:": title,
                "Description:": description,
                "Due Date:": due_date,
                "Difficulty:": difficulty,
                "Stress:": stress,
                "Duration:": duration,
                "Dependent On (comma-separated IDs):": ", ".join(dependent_on),
                "Is Complete (True/False):": is_complete,
                "Stress dynamic:": dynamic,
                "Creation Date:": creation_date,
                "Cool down:": cool_down,
                "Periodicity:": periodicity,
                "Task List Name:": task_list_name,
            }

            (
                title,
                description,
                due_date,
                difficulty,
                stress,
                duration,
                dependent_on_str,
                is_complete_str,
                dynamic,
                creation_date,
                cool_down,
                periodicity,
                task_list_name,
            ) = rlinput(multiprompt=multiprompt)

            cool_down = self.interval_validator(cool_down)
            periodicity = self.cron_validator(periodicity)
            dynamic = BaseDynamic.find_dynamic(dynamic) if dynamic else None
            dependent_on = ast.literal_eval(dependent_on_str) if dependent_on_str else []
            dependent_on = [
                self.task_manager.find_task_by_id(el).identifier
                for el in dependent_on
                if self.task_manager.find_task_by_id(el)
            ]

            creation_date = self.get_date_prompt(
                "Creation Date (YYYY-MM-DDTHH:MM:SS): ",
                input_func=lambda *args, **kwargs: creation_date,
            ) if creation_date else None

            due_date = self.get_date_prompt(
                "Due Date (YYYY-MM-DDTHH:MM:SS): ",
                input_func=lambda *args, **kwargs: due_date,
            ) if due_date else None

            difficulty = self.get_numerical_prompt(
                "Difficulty: ",
                raise_exception=True,
            )

            stress = self.get_numerical_prompt(
                "Stress: ",
                raise_exception=True,
            )

            duration = self.get_numerical_prompt(
                "Duration (minutes): ",
                raise_exception=True,
            )

            is_complete = is_complete_str.lower() == "true"

            if task_to_edit:
                task_to_edit.title = title
                task_to_edit.description = description
                task_to_edit.due_date = due_date
                task_to_edit.difficulty = difficulty
                task_to_edit.stress = stress
                task_to_edit.duration = duration
                task_to_edit.dependent_on = dependent_on
                task_to_edit.is_complete = is_complete
                task_to_edit.stress_dynamic = dynamic
                task_to_edit.creation_date = creation_date
                task_to_edit.cool_down = cool_down
                task_to_edit.periodicity = periodicity
                task_to_edit.list_name = task_list_name
                log.info(f"Edited task: {task_to_edit.title}")
                return task_to_edit

            new_task = Task(
                title=title,
                description=description,
                duration=int(duration),
                stress=int(stress),
                difficulty=int(difficulty),
                due_date=due_date,
                dependent_on=dependent_on,
                stress_dynamic=dynamic,
                creation_date=creation_date or datetime.now(),
                cool_down=cool_down,
                periodicity=periodicity,
                list_name=task_list_name,
            )
            log.info(f"Created new task: {new_task.title}")
            return new_task
        except ValueError as e:
                print(e)
                sleep(5)

    def verbose_create_new_task(self):
        new_task = self.edit_or_create_task()
        self.task_manager.add_task(new_task)

    @property
    def cron_validator(self):
        def validator(val: str) -> Optional[str]:
            if not val:
                return None
            try:
                cron = croniter.croniter(val, datetime.now())
                cron.get_next(datetime)
                return val
            except Exception as e:
                log.error(f"Cron validation error: {e}")
                raise ValueError("Invalid cron expression.")
        return validator

    @property
    def interval_validator(self):
        def validator(val: str) -> Optional[str]:
            if not val:
                return None
            try:
                Task.convert_cool_down_str_to_delta(val)
                return val
            except Exception as e:
                log.error(f"Interval validation error: {e}")
                raise ValueError("Invalid interval format.")
        return validator

    def create_new_task(self):
        new_task = self.edit_or_create_task()
        self.task_manager.add_task(new_task)

    def task_sorter(self, task: Task) -> float:
        x_stress = task.get_rendered_stress()
        if task.is_due_soon():
            x_stress += max(x_stress * 0.33, 1)
        return x_stress

    def get_list_name_text(self) -> str:
        return f"(list: {self.task_manager.selected_task_lists})"

    def print_list_name(self):
        print(self.get_list_name_text(), end="")

    def list_all_tasks(
        self,
        task_list_override: Optional[List[Task]] = None,
        extend_cache: bool = False,
        also_print: bool = True,
        smart_filter: bool = True,
    ) -> List[str]:
        if not extend_cache:
            self.cached_listed_tasks = {}

        tasks = task_list_override or self.task_manager.all_filtered_tasks

        # Separate queued tasks and other incomplete tasks
        queued_tasks = [task for task in tasks if task.current_status == TaskState.QUEUED]
        other_tasks = [
            task for task in tasks
            if task.current_status != TaskState.QUEUED and
               (not smart_filter or (not task.is_complete and task.dependent_tasks_complete(tasks)))
        ]

        # Sort tasks
        queued_tasks_sorted = sorted(queued_tasks, key=self.task_sorter, reverse=True)
        other_tasks_sorted = sorted(other_tasks, key=self.task_sorter, reverse=True)

        # Combine tasks with headers
        combined_tasks = []
        if queued_tasks_sorted:
            combined_tasks.append(("Queued Tasks", queued_tasks_sorted))
        if other_tasks_sorted:
            combined_tasks.append(("Tasks", other_tasks_sorted))

        to_return = []
        display_idx = 0
        max_digit_length = math.ceil(math.log10(len(tasks) + 1)) if tasks else 1

        for header, task_group in combined_tasks:
            if also_print:
                print(f"\n{header}:")
            for task in task_group:
                if not extend_cache and display_idx >= self.get_available_rows():
                    break
                formatted_line = self.format_task_line(display_idx, task)
                to_return.append(formatted_line)
                if also_print:
                    print(formatted_line)
                self.cached_listed_tasks[display_idx] = task
                display_idx += 1

        if not to_return and also_print:
            print("You have no available tasks.")

        return to_return

    def format_task_line(self, idx: int, task: Task) -> str:
        dependent_count = task.get_dependent_count(self.task_manager.all_tasks)
        due_soon_indicator = "⏰ " if task.is_due_soon() else ""
        dependent_info = f"(+{dependent_count}) " if dependent_count else ""
        return f"[{idx}] {due_soon_indicator}{dependent_info}{task.headline()}"

    def get_available_rows(self) -> int:
        try:
            rows = int(subprocess.check_output(["tput", "lines"]).decode("utf-8"))
            return rows - 5  # Subtracting lines for headers and buffers
        except Exception as e:
            log.error(f"Failed to get terminal rows: {e}")
            return 20  # Default value

    def wizard(self):
        print("\nWelcome to the completion wizard.")
        available_time = self.get_numerical_prompt(
            "\nHow much time do you have (minutes)? "
        )
        available_energy = self.get_numerical_prompt("\nHow much energy do you have? ")
        strict_candidates = self._get_strictly_matching_tasks(
            available_time, available_energy
        )
        stretch_candidates = self._get_stretch_tasks(available_time, available_energy)
        self.reset_screen()
        if strict_candidates:
            print("I recommend the following tasks:")
            self.list_all_tasks(strict_candidates)
            if stretch_candidates:
                print("\nAnd this possible stretch task:")
                self.list_all_tasks([stretch_candidates[0]], extend_cache=True)
        else:
            if stretch_candidates:
                print("\nYou have no perfect fits, but try these stretch tasks:")
                self.list_all_tasks(stretch_candidates[:3])

    def _get_strictly_matching_tasks(self, available_time: float, available_energy: float) -> List[Task]:
        candidates = [
            task for task in self.task_manager.all_filtered_tasks
            if task.duration <= available_time and task.difficulty <= available_energy
        ]
        candidates.sort(key=lambda t: t.stress)
        return candidates

    def _get_stretch_tasks(self, available_time: float, available_energy: float) -> List[Task]:
        stretch_energy = available_energy * 1.5
        candidates = [
            task for task in self.task_manager.all_filtered_tasks
            if task.duration <= available_time and available_energy < task.difficulty <= stretch_energy
        ]
        candidates.sort(key=lambda t: t.stress)
        return candidates

    def find_task_by_any_id(self, input_str: str) -> Optional[Task]:
        # First, try to interpret as an index
        try:
            idx = int(input_str)
            return self.cached_listed_tasks.get(idx)
        except ValueError:
            pass

        # Then, try to find by UUID
        return self.task_manager.find_task_by_id(input_str)

    CORE_COMMAND_PROMPT = (
        "Enter your command (n = new task, ls = list, view <id> = view task, "
        "x <id> = complete task, d <id> = delete task, s = save, r = refresh, "
        "e <id> = edit task, cal <id> = calendar event, load = reload, "
        "n <id> = create next task after <id>, p <id> = create previous task before <id>, "
        "q <id> = queue task, exit = exit): "
    )

    def display_home(self):
        print("\n")
        command_input = input(self.CORE_COMMAND_PROMPT)
        self.reset_screen()

        if not command_input.strip():
            return

        parts = command_input.strip().split()
        command = parts[0].lower()
        args = parts[1:]

        if command == "n":
            new_task = self.edit_or_create_task()
            self.task_manager.add_task(new_task)
        elif command == "ls":
            self.paged_task_list()
        elif command == "view" and args:
            task = self.find_task_by_any_id(args[0])
            if task:
                task.pretty_print(self.task_manager.all_tasks)
            else:
                print("Task not found.")
        elif command == "x" and args:
            task = self.find_task_by_any_id(args[0])
            if task:
                task.complete()
                self.task_manager.save_tasks()
                print("\nTask completed.")
                log.info(f"Task completed: {task.title}")
            else:
                print("Task not found.")
        elif command == "d" and args:
            self.delete_task(args[0])
        elif command == "s":
            self.save()
        elif command == "r":
            self.refresh_stress_levels()
        elif command == "e" and args:
            task = self.find_task_by_any_id(args[0])
            if task:
                edited_task = self.edit_or_create_task(task)
                self.task_manager.save_tasks()
            else:
                print("Task not found.")
        elif command == "cal" and args:
            task = self.find_task_by_any_id(args[0])
            if task:
                task.create_and_launch_ical_event()
            else:
                print("Task not found.")
        elif command == "load":
            self.load()
            self.paged_task_list()
        elif command == "n" and args:
            found_task = self.find_task_by_any_id(args[0])
            if found_task:
                new_task = self.edit_or_create_task(dependent_on=[found_task.identifier])
                self.task_manager.add_task(new_task)
        elif command == "p" and args:
            found_task = self.find_task_by_any_id(args[0])
            if found_task:
                new_task = self.edit_or_create_task()
                self.task_manager.add_task(new_task)
                found_task.dependent_on.append(new_task.identifier)
                self.task_manager.save_tasks()
        elif command == "q" and args:
            task = self.find_task_by_any_id(args[0])
            if task:
                task.current_status = TaskState.QUEUED
                self.task_manager.save_tasks()
                print(f"Task '{task.title}' has been queued.")
                log.info(f"Task queued: {task.title}")
            else:
                print("Task not found.")
        elif command == "exit":
            print("Exiting Procrastinator's Companion. Goodbye!")
            exit()
        else:
            print("Unknown command.")

    def refresh_stress_levels(self):
        self.reset_screen()
        seen_tasks = set()
        while True:
            self.reset_screen()
            if not self.should_do_refresh():
                print("List sufficiently refreshed.")
                break
            remaining_tasks = [
                task for task in self.task_manager.all_filtered_tasks
                if not task.is_complete and task.identifier not in seen_tasks
            ]
            if not remaining_tasks:
                break
            remaining_tasks.sort(key=lambda t: t.last_refreshed)
            chosen_task = remaining_tasks[0]
            seen_tasks.add(chosen_task.identifier)
            self.list_all_tasks([chosen_task], smart_filter=False)
            new_stress = self.get_numerical_prompt(
                "Enter new stress level for task (or 'x' to exit): ",
                also_accept=["x", ""]
            )
            if isinstance(new_stress, str) and new_stress.lower() == "x":
                break
            if new_stress != "":
                chosen_task.stress = new_stress
                chosen_task.update_last_refreshed()
                log.info(f"Stress level for task '{chosen_task.title}' updated to {new_stress}")
                self.task_manager.save_tasks()
                print(f"Stress level for task '{chosen_task.title}' updated.")

    def reset_screen(self):
        os.system("clear")
        print(self.WELCOME_MESSAGE)

    WELCOME_MESSAGE = "\nWelcome to Procrastinator's Companion\n"

    def edit_task(self, task: Task):
        edited_task = self.edit_or_create_task(task)
        self.task_manager.save_tasks()

    def paged_task_list(self):
        self.reset_screen()
        velocity_percentage = self.task_manager.task_collection.get_velocity(interval=timedelta(weeks=1))
        velocity_percentage_str = "{:.2f}".format(velocity_percentage)
        list_and_velocity_string = self.get_list_name_text() + f" (velocity: {velocity_percentage_str}%/wk)"
        print(list_and_velocity_string)

        # Get terminal size
        rows = self.get_available_rows()
        columns = int(subprocess.check_output(["tput", "cols"]).decode("utf-8"))

        # Get all task lines without printing
        would_print_collection = self.list_all_tasks(also_print=False)
        if self.should_do_refresh():
            would_print_collection = ["* Please refresh your tasks"] + would_print_collection

        # Calculate how many lines can be printed
        available_rows = rows
        to_print = []
        for line in would_print_collection:
            if len(to_print) >= available_rows:
                break
            to_print.append(line)

        # Print the tasks
        for line in to_print:
            print(line)

    def find_task(self, task_title: str) -> Optional[Task]:
        return next((task for task in self.task_manager.all_tasks if task.title == task_title), None)

    def create_new_task(self):
        new_task = self.edit_or_create_task()
        self.task_manager.add_task(new_task)

    def run(self):
        self.reset_screen()
        self.paged_task_list()
        while True:
            self.display_home()


if __name__ == "__main__":
    app = App()
    app.load()
    app.run()
