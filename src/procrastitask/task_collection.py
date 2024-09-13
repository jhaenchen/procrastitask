from procrastitask.task import CompletionRecord, Task
from datetime import timedelta, datetime


class TaskCollection:
    def __init__(self, filtered_tasks: list[Task], unfiltered_tasks: list[Task]):
        self.filtered_tasks = filtered_tasks
        self.unfiltered_tasks = unfiltered_tasks


    def get_velocity(self, interval: timedelta) -> float:
        completed_tasks = [task for task in self.filtered_tasks if task.is_complete == True]

        accomplished_total = 0
        for task in completed_tasks:
            for completion in task.history:
                if datetime.now() - completion.completed_at < interval:
                    accomplished_total += completion.stress_at_completion

        uncompleted_stress = 0
        for task in self.filtered_tasks:
            if not task.is_complete:
                uncompleted_stress += task.get_rendered_stress()

        return (accomplished_total / ((uncompleted_stress or 1) + accomplished_total)) * 100
