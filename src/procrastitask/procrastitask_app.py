import cProfile
import pstats
from configparser import ConfigParser, NoSectionError
import json
import math
import os
import subprocess
import tempfile
from subprocess import call
from time import sleep
from datetime import datetime, timedelta
from typing import Callable, List, Optional, TypeVar, Union, Tuple
import ast
import logging

import croniter

from procrastitask.dynamics.base_dynamic import BaseDynamic
from procrastitask.task import Task, TaskStatus
from procrastitask.task_collection import TaskCollection
from procrastitask.dynamics.static_offset_dynamic import StaticOffsetDynamic
from procrastitask.dynamics.combined_dynamic import CombinedDynamic



EDITOR = os.environ.get("EDITOR", "vim")  # that easy!

log = logging.getLogger()
log.setLevel("DEBUG")
logging.basicConfig(filename="log.txt")


def rlinput(prefill: str = "", prompt="Edit:", multiprompt: Optional[dict] = None) -> List[str]:
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
        edited_message = str(tf.read().decode())

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
                formatted = first_part[:-1]
                formatted = None if formatted == "None" else formatted
                to_return.append(formatted)
        else:
            splitted = str(edited_message).split(prompt)
            if len(splitted) == 2:
                return [splitted[1][:-3]]
        return to_return


class App:
    def __init__(self):
        self.filtered_tasks_to_resave = []
        self.selected_task_list_name = ["default"]
        self.task_lists = []
        self.all_tasks = []
        self.cached_listed_tasks = {}
        self.config = self.config_loader()
        self.reset_screen()

    TASKS_FILE_NAME = "tasks.json"

    def config_loader(self) -> dict:
        config = {}
        try:
            Config = ConfigParser()
            Config.read(self.get_config_path())
            config = dict(Config.items("task_config"))
        except NoSectionError:
            print("Config error, check formatting")
        return config

    def load_list_config(self):
        dir = self.config.get("db_location", self.get_current_dir() + "/../..")
        with open(dir + "/list_config.json", "r") as lists:
            task_lists = json.loads(lists.read())["lists"]
            self.task_lists = [el["name"] for el in task_lists]
            return self.task_lists

    def get_db_location(self):
        dir = self.config.get("db_location", self.get_current_dir() + "/../..")
        return dir + "/" + self.TASKS_FILE_NAME

    def prompt_for_task_list_selection(self):
        self.reset_screen()
        task_lists_for_prompt = ["all"] + self.task_lists
        for list_idx, list_name in enumerate(task_lists_for_prompt):
            print(f"[{list_idx}] {list_name}")
        chosen_lists_idx = self.get_input_with_validation_mapper(
            prompt="Select your task list: ",
            validator_mapper=lambda s: [int(val) for val in s.split(",")],
        )
        self.reset_screen()
        return [
            task_lists_for_prompt[chosen_list_idx]
            for chosen_list_idx in chosen_lists_idx
        ]

    def get_raw_db_file(self):
        with open(self.get_db_location(), "r") as db:
            return db.read()

    def load(self, default_list: Optional[Union[List, str]] = None, task_list_override=None):
        if task_list_override:
            self.task_collection = TaskCollection(task_list_override, [])
            return
        self.load_list_config()
        if self.task_lists:
            if default_list:
                if type(default_list) is list:
                    self.selected_task_list_name = default_list
                else:
                    self.selected_task_list_name = [default_list]
            else:
                self.selected_task_list_name = self.prompt_for_task_list_selection()
            log.info(f"List set to: {self.selected_task_list_name}")
        try:
            json_tasks = json.loads(self.get_raw_db_file())
            log.debug(f"Loaded {len(json_tasks)} from file {self.get_db_location()}")
            actual_all_tasks = [Task.from_dict(j_task) for j_task in json_tasks]
            self.all_tasks = [
                t
                for t in actual_all_tasks
                if (t.list_name in self.selected_task_list_name)
                or "all" in self.selected_task_list_name
            ]
            self.filtered_tasks_to_resave = [
                t
                for t in actual_all_tasks
                if (t.list_name not in self.selected_task_list_name)
                and "all" not in self.selected_task_list_name
            ]
            
        except Exception as e:
            log.error(e)
            print(f"Error: {e}")
            self.all_tasks = []
        self.task_collection = TaskCollection(filtered_tasks=self.all_tasks, unfiltered_tasks=self.all_tasks + self.filtered_tasks_to_resave)

    def save(self):
        backed_up_content = []
        try:
            with open(self.get_db_location(), "r") as existing_db:
                backed_up_content = existing_db.read()
        except FileNotFoundError:
            log.debug(f"Couldn't find an existing DB at location {self.get_db_location()}. One will be created.")
        with open(self.get_db_location(), "w") as db:
            try:

                def sorter(t: Task):
                    return (t.is_complete, t.title)

                sorted_tasks = sorted(
                    self.all_tasks + self.filtered_tasks_to_resave, key=sorter
                )
                task_json_dicts = [task.to_dict() for task in sorted_tasks]
                json_str = json.dumps(task_json_dicts)
                db.write(json_str)
            except Exception as e:
                print(f"Failed to save:{e}")
                sleep(5)
                db.write(backed_up_content)

    CONFIG_FILE_NAME = "config.ini"

    def get_current_dir(self):
        return os.path.dirname(os.path.realpath(__file__))

    def get_config_path(self):
        dir_path = self.get_current_dir() + "/../.."
        return dir_path + "/" + self.CONFIG_FILE_NAME

    def does_local_config_file_exist(self):
        return os.path.isfile(self.get_config_path())

    def delete_task_by_identifier(self, task_identifier):
        len_before = len(self.all_tasks)
        specified_task = [task for task in self.all_tasks if task.identifier == task_identifier]
        if not specified_task:
            raise ValueError(f"I couldn't find the task with identifier: {task_identifier}")
        elif len(specified_task) > 1:
            raise ValueError(f"I found more than one task with identifier: {task_identifier}: {specified_task}")
        else:
            specified_task = specified_task[0]
        self.all_tasks = [task for task in self.all_tasks if task.identifier != task_identifier]
        if len_before == len(self.all_tasks):
            raise ValueError(f"I couldn't find the task with identifier: {task_identifier}")
        # Remove the deleted task's identifier from other tasks' dependent_on lists
        for task in self.all_tasks:
            task.dependent_on = [dep for dep in task.dependent_on if dep != specified_task.identifier]
        log.info(f"Task deleted: {specified_task.title}")

    def delete_task(self, task_title):
        specified_task = [task for task in self.all_tasks if task.title == task_title]
        if not specified_task:
            raise ValueError(f"I couldn't find the task with title: {task_title}")
        elif len(specified_task) > 1:
            raise ValueError(f"I found more than one task with title: {task_title}: {specified_task}")
        else:
            specified_task = specified_task[0]
        self.delete_task_by_identifier(specified_task.identifier)

    def delete_task_by_idx(self, task_idx: int):
        selected_task = self.cached_listed_tasks.get(int(task_idx))
        if not selected_task:
            raise ValueError(f"That's not a valid idx: {task_idx}")
        self.delete_task(selected_task.title)
        print(f"\nTask deleted: {selected_task.title}")

    def should_do_refresh(self):
        incomplete_tasks_dates = [
            task.last_refreshed for task in self.all_tasks if not task.is_complete
        ]
        if not incomplete_tasks_dates:
            return False
        min_refreshed = min(incomplete_tasks_dates)
        if datetime.now() - min_refreshed > timedelta(weeks=1):
            return True

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
            month = int(parts[1])
            if now.month > month:
                year = year + 1
            return datetime(day=day, month=month, year=year, hour=9)
        if len(parts) == 3:
            return datetime(day=int(parts[0]), month=int(parts[1]), year=int(parts[2]), hour=9)

    def modify_cached_task_stress_by_offset(self, cached_idx: int, offset: int):
        """
        Change the stress of a task by an offset. This should apply to the rendered
        task stress rather than the base in the case of dynamics.
        """
        found_task: Task = self.cached_listed_tasks[cached_idx]
        self.modify_task_stress_by_offset(found_task.identifier, offset)

    def modify_task_stress_by_offset(self, task_identifier: str, offset: int):
        """
        Change the stress of a task by an offset. This should apply to the rendered
        task stress rather than the base in the case of dynamics.
        Uses StaticOffsetDynamic, and combines if needed.
        """
        found_task = self.find_task_by_any_id(task_identifier)
        if not found_task:
            raise ValueError(f"Task with identifier {task_identifier} not found.")
        dynamic = found_task.stress_dynamic

        def update_offset_in_combined(combined, offset):
            for d in combined.dynamics:
                if isinstance(d, StaticOffsetDynamic):
                    d.offset += offset
                    return True
            return False

        if dynamic is None:
            found_task.stress_dynamic = StaticOffsetDynamic(offset)
        elif isinstance(dynamic, StaticOffsetDynamic):
            dynamic.offset += offset
        elif isinstance(dynamic, CombinedDynamic):
            if not update_offset_in_combined(dynamic, offset):
                # Not found, add new StaticOffsetDynamic and operator
                dynamic.dynamics.append(StaticOffsetDynamic(offset))
                # Default to addition operator
                dynamic.operators.append("(+)")
        else:
            # Some other dynamic: combine with StaticOffsetDynamic and operator
            found_task.stress_dynamic = CombinedDynamic([dynamic, StaticOffsetDynamic(offset)], operators=["(+)"])

        found_task.update_last_refreshed()
        print(
            f"Updated task stress dynamic for {found_task.title} (offset change: {offset})"
        )

    def get_numerical_prompt(
        self, prompt_text, also_accept=None, input_func=None, raise_exception=False
    ):
        while True:
            try:
                result = input_func(prompt_text) if input_func else input(prompt_text)
                return float(result)
            except ValueError:
                message = (
                    f"\nBad input for prompt {prompt_text}: {result}. Try again.\n"
                )
                if result in (also_accept or []):
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
        raise_exception=False,
    ) -> T:
        while True:
            result = input(prompt)
            try:
                mapped = validator_mapper(result)
                return mapped
            except ValueError as e:
                message = f"\nBad input for prompt {prompt}: {result}. {e}\n"
                if raise_exception:
                    raise ValueError(message)
                print(message)
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

    def edit_or_create_task(
        self, task_to_edit: Optional[Task] = None, dependent_on=None
    ) -> Task:
        while True:
            try:
                title = task_to_edit.title if task_to_edit else ""
                description = task_to_edit.description if task_to_edit else ""
                due_date = task_to_edit.due_date if task_to_edit else ""
                due_date_cron = task_to_edit.due_date_cron if task_to_edit else ""
                difficulty = task_to_edit.difficulty if task_to_edit else ""
                stress = task_to_edit.get_rendered_stress() if task_to_edit else ""
                duration = task_to_edit.duration if task_to_edit else ""
                dependent_on = (
                    dependent_on
                    if dependent_on
                    else task_to_edit.dependent_on if task_to_edit else []
                )
                is_complete = task_to_edit.is_complete if task_to_edit else False
                dynamic = (
                    task_to_edit.stress_dynamic.to_text()
                    if task_to_edit and task_to_edit.stress_dynamic
                    else ""
                )
                creation_date = (
                    task_to_edit.creation_date if task_to_edit else datetime.now()
                )
                cool_down = task_to_edit.cool_down if task_to_edit else ""
                periodicity = task_to_edit.periodicity if task_to_edit else ""
                task_list_name = (
                    task_to_edit.list_name
                    if task_to_edit
                    else (
                        self.selected_task_list_name[0]
                        if (
                            len(self.selected_task_list_name) == 1
                            and "all" not in self.selected_task_list_name
                        )
                        else "default"
                    )
                )
                (
                    title,
                    description,
                    due_date,
                    due_date_cron,
                    difficulty,
                    stress,
                    duration,
                    dependent_on,
                    is_complete,
                    dynamic,
                    creation_date,
                    cool_down,
                    periodicity,
                    task_list_name,
                ) = rlinput(
                    multiprompt={
                        "Title:": title,
                        "Description:": description,
                        "Due Date:": due_date,
                        "Due Date Cron:": due_date_cron,
                        "Difficulty:": difficulty,
                        "Stress:": stress,
                        "Duration:": duration,
                        "Dependent On:": dependent_on,
                        "Is Complete:": is_complete,
                        "Stress dynamic:": dynamic,
                        "Creation Date:": creation_date,
                        "Cool down:": cool_down,
                        "Periodicity": periodicity,
                        "Task List Name:": task_list_name,
                    }
                )

                cool_down = self.interval_validator(cool_down)
                periodicity = self.cron_validator(periodicity)
                due_date_cron = self.cron_validator(due_date_cron)
                dynamic = BaseDynamic.find_dynamic(dynamic) if dynamic else None
                dependent_on = [
                    self.find_task_by_any_id(el).identifier
                    for el in ast.literal_eval(dependent_on)
                ]

                creation_date = (
                    self.get_date_prompt(
                        "Creation Date",
                        input_func=lambda *args, **kwargs: creation_date,
                    )
                    if creation_date
                    else None
                )

                due_date = (
                    self.get_date_prompt(
                        "Due Date",
                        input_func=lambda *args, **kwargs: due_date,
                    )
                    if due_date
                    else None
                )
                difficulty = self.get_numerical_prompt(
                    "Difficulty",
                    input_func=lambda *args, **kwargs: difficulty,
                    raise_exception=True,
                )
                stress = self.get_numerical_prompt(
                    "Stress",
                    input_func=lambda *args, **kwargs: stress,
                    raise_exception=True,
                )
                duration = self.get_numerical_prompt(
                    "Duration",
                    input_func=lambda *args, **kwargs: duration,
                    raise_exception=True,
                )
                is_complete = is_complete != "False"
                if task_to_edit:
                    task_to_edit.title = title
                    task_to_edit.description = description
                    task_to_edit.dependent_on = dependent_on
                    task_to_edit.duration = duration
                    task_to_edit.difficulty = difficulty
                    if float(task_to_edit.get_rendered_stress()) != float(stress):
                        task_to_edit.last_refreshed = datetime.now()
                    task_to_edit.stress = stress
                    task_to_edit.is_complete = is_complete
                    task_to_edit.stress_dynamic = dynamic
                    task_to_edit.creation_date = creation_date
                    task_to_edit.due_date = due_date
                    task_to_edit.due_date_cron = due_date_cron
                    task_to_edit.cool_down = cool_down
                    task_to_edit.periodicity = periodicity
                    task_to_edit.list_name = task_list_name
                    return task_to_edit

                created_task = Task(
                    title=title,
                    description=description,
                    duration=duration,
                    stress=stress,
                    difficulty=difficulty,
                    due_date=due_date,
                    due_date_cron=due_date_cron,
                    dependent_on=dependent_on,
                    stress_dynamic=dynamic,
                    creation_date=creation_date,
                    cool_down=cool_down,
                    periodicity=periodicity,
                    list_name=task_list_name,
                )
                return created_task
            except ValueError as e:
                print(e)
                sleep(5)

    def verbose_create_new_task(self):
        task = self.edit_or_create_task()
        log.info(f"Task created: {task.title}")
        return task

    @property
    def cron_validator(self):
        def validator(val):
            if not val:
                return None
            try:
                cron = croniter.croniter(val, datetime.now())
                cron.get_next(datetime)
                return val
            except Exception as e:
                print(e)
                raise ValueError("Invalid cron")

        return validator

    @property
    def interval_validator(self):
        def validator(val):
            if not val:
                return None
            try:
                Task.convert_cool_down_str_to_delta(val)
                return val
            except Exception as e:
                print(e)
                raise ValueError("Invalid interval")

        return validator

    def create_new_task(self):
        task_title = input("Enter your task: ")
        task_description = input("Enter description: ")
        duration = self.get_numerical_prompt("Estimated duration (minutes): ")
        stress_level = self.get_numerical_prompt("Stress level: ")
        difficulty = self.get_numerical_prompt("Difficulty: ")
        date = self.get_date_prompt("Due date:")
        due_date_cron = self.get_input_with_validation_mapper(
            "Due date cron: ", self.cron_validator
        )
        dependent_on = self.get_input_with_validation_mapper(
            "Dependent on tasks: ", self.dependence_validator
        )
        dynamic = self.get_input_with_validation_mapper(
            "Stress dynamic: ", lambda s: BaseDynamic.find_dynamic(s) if s else None
        )
        cool_down = self.get_input_with_validation_mapper(
            "Cool down: ", self.interval_validator
        )
        periodicity = self.get_input_with_validation_mapper(
            "Periodic cron: ", self.cron_validator
        )

        created_task = Task(
            title=task_title,
            description=task_description,
            duration=duration,
            stress=stress_level,
            difficulty=difficulty,
            due_date=date,
            due_date_cron=due_date_cron,
            dependent_on=dependent_on,
            stress_dynamic=dynamic,
            cool_down=cool_down,
            periodicity=periodicity,
            list_name=(
                self.selected_task_list_name[0]
                if (
                    "all" not in self.selected_task_list_name
                    and len(self.selected_task_list_name) == 1
                )
                else "default"
            ),
        )
        log.info(f"Task created: {created_task.title}")
        return created_task

    def task_sorter(self, x: Task):
        x_stress = x.get_rendered_stress()
        if x.is_due_soon():
            x_stress += max(x_stress * 0.33, 1)
        return x_stress

    def get_list_name_text(self):
        return f"(list: {self.selected_task_list_name})"

    def print_list_name(self):
        print(self.get_list_name_text(), end="")

    def list_all_tasks(
        self,
        task_list_override=None,
        extend_cache=False,
        also_print=True,
        smart_filter=True,
    ) -> List[Tuple[str, str, Task]]:
        if also_print:
            self.reset_screen()
            velocity_percentage = self.task_collection.get_velocity(interval=timedelta(weeks=1))
            velicocity_percentage_str = "{:.2f}".format(velocity_percentage)
            list_and_velocity_string = self.get_list_name_text() + f" (velocity: {velicocity_percentage_str}%/wk)"
            print(list_and_velocity_string)
        tasks = task_list_override or self.all_tasks
        if not extend_cache:
            self.cached_listed_tasks = {}
        incomplete_tasks = [
            task
            for task in tasks
            if (not smart_filter)
            or not task.is_complete
            and task.dependent_tasks_complete(tasks)
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

        max_digit_length = len(str((len(incomplete_tasks) + start_index)))

        for idx, task in enumerate(incomplete_tasks):
            true_idx = idx + start_index
            space_padding = " " * (int(max_digit_length) - len(str(true_idx)))
            dependent_count = task.get_dependent_count(tasks)
            due_soon_indicator = "⏰ " if (task.is_due_soon() and not task.is_complete) else ""
            task_str = f"[{true_idx}]  {space_padding}{due_soon_indicator}{f'(+{dependent_count}) ' if dependent_count else ''}{task.headline()}"
            to_return.append((task_str, task.identifier, task))
            # print(f"\n* {task.title} ({task.duration}min)")
            self.cached_listed_tasks[true_idx] = task

        if also_print:
            [print(el[0]) for el in to_return]
        return to_return

    def list_in_progress_tasks(self):
        self.reset_screen()
        in_progress_tasks = [
            task for task in self.all_tasks if task.status == TaskStatus.IN_PROGRESS
        ]
        if not in_progress_tasks:
            print("No tasks are currently in progress.")
            return
        return self.list_all_tasks(task_list_override=in_progress_tasks, smart_filter=False)

    def _is_number(self, num_string):
        try:
            float(num_string)
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
            if not self.should_do_refresh():
                print("List sufficiently refreshed.")
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
            self.list_all_tasks([chosen_task], smart_filter=False)
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
        return self.edit_or_create_task(task)

    def paged_task_list(self):
        self.reset_screen()
        velocity_percentage = self.task_collection.get_velocity(interval=timedelta(weeks=1))
        velicocity_percentage_str = "{:.2f}".format(velocity_percentage)
        list_and_velocity_string = self.get_list_name_text() + f" (velocity: {velicocity_percentage_str}%/wk)"
        print(list_and_velocity_string)
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
        rows -= math.ceil(len(list_and_velocity_string) / columns) + 1
        would_print_collection = self.list_all_tasks(also_print=False)
        if self.should_do_refresh():
            would_print_collection = [
                ("* Please refresh your tasks", "refresh")
            ] + would_print_collection

        print_until = 0
        for idx, candidate in enumerate(would_print_collection):
            new_y = pos[1] + math.ceil(len(candidate[0]) / columns)
            if new_y < rows:
                pos[1] = new_y
                print_until += 1
        for to_print in would_print_collection[:print_until]:
            print(to_print[0])

    def find_task_by_any_id(self, input_str: str) -> Optional[Task]:
        if self._is_number(input_str):
            selected_task = self.cached_listed_tasks.get(int(input_str))
            if selected_task:
                return selected_task
        found_id_matches = [
            task for task in self.all_tasks if task.identifier == input_str
        ]
        if found_id_matches:
            return found_id_matches[0]
        return None

    CORE_COMMAND_PROMPT = "Enter your command (n = new task, ls = list, 4 = view 4, x4 = complete 4, d4 = delete 4, s = save, r = refresh, e4 = edit 4, cal4 = calendar 4, load = reload, n4 = create next task after 4, p4 = create previous task before 4, q = view inprogress queue, q4 = mark task as in-progress, dq4 = dequeue a task from inprogress): "

    def display_home(self, optional_start_command: Optional[str] = None):
        print("\n")
        command = optional_start_command or input(self.CORE_COMMAND_PROMPT)
        self.reset_screen()

        if len(command) == 0:
            return
        if command == "n":
            self.all_tasks.append(self.create_new_task())
        if command == "nn":
            self.all_tasks.append(self.edit_or_create_task())
        if command == "ls":
            self.paged_task_list()
            # self.list_all_tasks()
        if self.find_task_by_any_id(command):
            found_task = self.find_task_by_any_id(command)
            found_task.pretty_print(self.all_tasks)
        if command.startswith("x"):
            index_val = command.split("x")[1]
            selected_task = self.cached_listed_tasks.get(int(index_val))
            selected_task.complete()
            print("\nTask completed.")
        if command.startswith("d") and not command.startswith("dq"):
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
            self.paged_task_list()
            #self.list_all_tasks()
        if command == "w":
            self.wizard()
        if command == "r":
            self.refresh_stress_levels()
        if command.startswith("cal"):
            found = self.find_task_by_any_id(command[3:])
            found.create_and_launch_ical_event()
        if command.startswith("n") and command not in ["n", "nn"]:
            found = self.find_task_by_any_id(command[1:])
            self.all_tasks.append(
                self.edit_or_create_task(dependent_on=[found.identifier])
            )
        if command.startswith("p"):
            found = self.find_task_by_any_id(command[1:])
            new_task = self.edit_or_create_task()
            self.all_tasks.append(new_task)
            found.dependent_on = [*found.dependent_on, new_task.identifier]
        if command == "history":
            recents = self.task_collection.get_recently_completed_tasks()
            self.list_all_tasks(task_list_override=recents, smart_filter=False)
        if command == "q":
            self.list_in_progress_tasks()
        if command.startswith("q") and command != "q":
            index_val = command.split("q")[1]
            selected_task = self.cached_listed_tasks.get(int(index_val))
            selected_task.set_in_progress()
            print(f"\nTask marked as in-progress: {selected_task.title}")
        if command.startswith("dq"):
            index_val = command.split("dq")[1]
            selected_task = self.cached_listed_tasks.get(int(index_val))
            selected_task.set_incomplete()
            print(f"\nTask marked as incomplete: {selected_task.title}")
        if command == "created":
            recents = self.task_collection.get_recently_created_tasks()
            self.list_all_tasks(task_list_override=recents, smart_filter=False)

        return


if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    os.system("clear")
    app = App()
    app.load()
    app.paged_task_list()
    app.display_home()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    stats.sort_stats("cumulative")  # Options: 'time', 'cumulative', 'calls'
    stats.print_stats(20)  # Print top 20 slowest entries
