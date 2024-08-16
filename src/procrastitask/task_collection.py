from procrastitask.task import CompletionRecord, Task
from datetime import timedelta, datetime


class TaskCollection:
    def __init__(self, all_tasks: list[Task]):
        self.all_tasks = all_tasks

    def get_velocity(self, interval: timedelta) -> int:
        completed_tasks = [task for task in self.all_tasks if task.is_complete == True]

        accomplished_total = 0
        for task in completed_tasks:
            for completion in task.history:
                if datetime.now() - completion["completed_at"] < interval:
                    accomplished_total += completion["stress_at_completion"]

        return accomplished_total
