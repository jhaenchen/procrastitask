from typing import List, Optional
from procrastitask.task import CompletionRecord, Task
from datetime import timedelta, datetime
from collections import defaultdict


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
    

    def get_velocities_by_list(self, interval: timedelta) -> dict:
        """
        Returns a dictionary mapping list name to velocity for tasks in that list.
        Assumes each Task has a 'list_name' attribute.
        """
        lists = defaultdict(list)
        for task in self.filtered_tasks:
            list_name = getattr(task, 'list_name', 'default')
            lists[list_name].append(task)

        velocities = {}
        for list_name, tasks in lists.items():
            accomplished_total = 0
            uncompleted_stress = 0
            for task in tasks:
                if getattr(task, 'is_complete', False):
                    for completion in getattr(task, 'history', []):
                        if datetime.now() - completion.completed_at < interval:
                            accomplished_total += completion.stress_at_completion
                else:
                    uncompleted_stress += task.get_rendered_stress()
            velocity = (accomplished_total / ((uncompleted_stress or 1) + accomplished_total)) * 100
            velocities[list_name] = velocity
        return velocities

    def find_task_by_identifier(self, identifier: str) -> Optional[Task]:
        for task in self.filtered_tasks:
            if task.identifier == identifier:
                return task
        return None

    def get_recently_created_tasks(self, limit: int = 10, non_complete_only = True) -> List[Task]:
        """
        Retrieve tasks based on their creation_date.
        """
        tasks = [t for t in self.filtered_tasks if not t.is_complete] if non_complete_only else self.filtered_tasks
        recently_created = sorted(tasks, key=lambda t: t.creation_date, reverse=True)
        return recently_created[:limit]
