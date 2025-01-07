from typing import List, Optional
from procrastitask.task import CompletionRecord, Task
from datetime import timedelta, datetime


class TaskCollection:
    def __init__(self, filtered_tasks: list[Task], unfiltered_tasks: list[Task]):
        """
        Filtered tasks here usually applies to task list.
        Unfiltered tasks is literally the entire set of tasks in the db.
        """
        self.filtered_tasks = filtered_tasks
        self.unfiltered_tasks = unfiltered_tasks

    def get_n_last_completed_tasks(self, how_many_tasks: int) -> List[Task]:
        recently_completed: List[Task] = []
        for task in self.filtered_tasks:
            if task.history:
                recently_completed.append(task)
        recently_completed = sorted(recently_completed, key=lambda t: t.latest_history.completed_at, reverse=True)
        return recently_completed[:how_many_tasks] if recently_completed else []

    def get_recently_completed_tasks(self, recent_is=timedelta(weeks=1), how_many_results=10):
        """
        Get a collection of recently completed task according to the current filtered set.
        recent_is: How long to filter the list by. Default 1 week in the past.
        """
        recently_completed: List[Task] = []
        for task in self.filtered_tasks:
            if task.history:
                latest_history = task.latest_history
                if datetime.now() - latest_history.completed_at < recent_is:
                    recently_completed.append(task)

        recently_completed = sorted(recently_completed, key=lambda t: t.latest_history.completed_at, reverse=True)

        return recently_completed[:how_many_results] if recently_completed else []
        
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
    
    def find_task_by_identifier(self, identifier: str) -> Optional[Task]:
        for task in self.filtered_tasks:
            if task.identifier == identifier:
                return task
        return None

    def get_recently_created_tasks(self, limit: int = 10) -> List[Task]:
        """
        Retrieve tasks based on their creation_date.
        """
        recently_created = sorted(self.filtered_tasks, key=lambda t: t.creation_date, reverse=True)
        return recently_created[:limit]
