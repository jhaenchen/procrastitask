import json
import os
import random

class Task:
    def pretty_print(self):
        print(f"\n{self.title} ({self.duration}min, stress: {self.stress, diff: {self.difficulty}})\n")
        print(f"{self.description}\n")

    def headline(self):
        return f"{self.title} ({self.duration}min, stress: {self.stress}, diff: {self.difficulty})"

    def complete(self):
        self.is_complete = True

    def __init__(self, title, description, duration, stress, difficulty, is_complete = False):
        self.title = title
        self.description = description
        self.duration = duration
        self.stress = stress
        self.is_complete = is_complete
        self.difficulty = difficulty

    @staticmethod
    def from_dict(incoming_dict):
        return Task(
            incoming_dict["title"],
            incoming_dict["description"],
            incoming_dict["duration"],
            incoming_dict["stress"],
            incoming_dict["difficulty"],
            incoming_dict["is_complete"]
        )

    def to_dict(self):
        return {
            "title": self.title,
            "description": self.description,
            "duration": self.duration,
            "stress": self.stress,
            "difficulty": self.difficulty,
            "is_complete": self.is_complete
        }

class App:
    def __init__(self):
        self.all_tasks = []
        self.cached_listed_tasks = {}
        self.reset_screen()

    def load(self):
        with open("tasks.json", "r") as db:
            json_tasks = json.loads(db.read())
            self.all_tasks = [Task.from_dict(j_task) for j_task in json_tasks]

    def save(self):
        with open("tasks.json", "w") as db:
            task_json_dicts = [task.to_dict() for task in self.all_tasks]
            json_str = json.dumps(task_json_dicts)
            db.write(json_str)

    def delete_task(self, task_title):
        #print(f"Deleting title {task_title} from collection {self.all_tasks}")
        self.all_tasks = [task for task in self.all_tasks if task.title != task_title]    

    def get_numerical_prompt(self, prompt_text, also_accept=None):
        while True:
            try:
                result = input(prompt_text)
                return int(result)
            except ValueError:
                if result in also_accept:
                    return result
                print("\nBad input. Try again.\n")

    def create_new_task(self):
        task_title = input("Enter your task: ")
        task_description = input("Enter description: ")
        duration = self.get_numerical_prompt("Estimated duration (minutes): ")
        stress_level = self.get_numerical_prompt("Stress level: ")
        difficulty = self.get_numerical_prompt("Difficulty: ")
        created_task = Task(task_title, task_description, duration, stress_level, difficulty)
        return created_task

    def list_all_tasks(self, task_list_override = None, extend_cache = False):
        tasks = task_list_override or self.all_tasks
        if not extend_cache:
            self.cached_listed_tasks = {}
        incomplete_tasks = [task for task in tasks if task.is_complete == False]
        start_index = 0 if not extend_cache else (max(-1, *[key for key in self.cached_listed_tasks]) + 1)
        if len(incomplete_tasks) == 0:
            print("You have no available tasks.")
        incomplete_tasks.sort(key=lambda t: t.stress, reverse=True)
        for idx, task in enumerate(incomplete_tasks):
            true_idx = idx + start_index
            print(f"[{true_idx}] {task.headline()}")
            # print(f"\n* {task.title} ({task.duration}min)")
            self.cached_listed_tasks[true_idx] = task

    def _is_number(self, num_string):
        try:
            int(num_string)
            return True
        except ValueError:
            return False

    def _get_strictly_matching_tasks(self, available_time, available_energy):
        candidates = []
        for task in self.all_tasks:
            if (task.duration <= available_time) and (task.difficulty <= available_energy):
                candidates.append(task)
        candidates.sort(key=lambda t: t.stress)
        return candidates

    def _get_stretch_tasks(self, available_time, available_energy):
        candidates = []
        for task in self.all_tasks:
            if (task.duration < available_time) and ((task.difficulty <= (int(available_energy * 1.5)) and (task.difficulty > available_energy))):
                candidates.append(task)
        candidates.sort(key=lambda t: t.stress)
        return candidates

    def wizard(self):
        print("\nWelcome to the completion wizard.")
        available_time = self.get_numerical_prompt("\nHow much time do you have (minutes)? ")
        available_energy = self.get_numerical_prompt("\nHow much energy do you have? ")
        self.cached_listed_tasks = {}
        strict_candidates = self._get_strictly_matching_tasks(available_time, available_energy)
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
            remaining_tasks = [t for t in self.all_tasks if t.is_complete == False and t not in seen_tasks]
            if not remaining_tasks:
                return
            chosen_task = random.choice(remaining_tasks)
            if not chosen_task:
                return
            seen_tasks.add(chosen_task)
            self.list_all_tasks([chosen_task])
            new_stress = self.get_numerical_prompt("Enter new stress level for task: ", also_accept=["x", ""])
            if new_stress == "x":
                return
            found_task = self.find_task(chosen_task.title)
            if new_stress and found_task:
                found_task.stress = new_stress

    def reset_screen(self):
        os.system('clear')
        print("\nWelcome to Procrastinator's Companion\n")
        
    def display_home(self):
        print("\n")
        command = input("Enter your command (new = n, list = ls, digit = task, xdigit = complete, ddigit = delete, s = save, r = refresh): ")
        self.reset_screen()

        if len(command) == 0:
            return
        if command == 'n':
            self.all_tasks.append(self.create_new_task())
        if command == 'ls':
            self.list_all_tasks()
        if self._is_number(command):
            selected_task = self.cached_listed_tasks.get(int(command))
            selected_task.pretty_print()
        if command.startswith("x"):
            index_val = command.split("x")[1]
            selected_task = self.cached_listed_tasks.get(int(index_val))
            selected_task.complete()
            print("\nTask completed.")
        if command.startswith("d"):
            index_val = command.split("d")[1]
            selected_task = self.cached_listed_tasks.get(int(index_val))
            self.delete_task(selected_task.title)
            print("\nTask deleted.")
        if command == "s":
            self.save()
            print("Saved.")
        if command == "load":
            self.load()
            self.list_all_tasks()
        if command == "w":
            self.wizard()
        if command == "exit":
            exit()
        if command == "r":
            self.refresh_stress_levels()
        return


os.system('clear')
app = App()
app.load()
app.list_all_tasks()
while True:
    app.display_home()
