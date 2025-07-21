from typing import Dict, List, Any
from app.database.storage import tasks_db, task_id_counter

class DatabaseSession:
    """Mock database session for learning purposes"""
    def __init__(self):
        self.tasks = tasks_db
        self.task_counter = task_id_counter

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks from database"""
        return self.tasks

    def get_task_by_id(self, task_id: int) -> Dict[str, Any] | None:
        """Get a single task by ID"""
        for task in self.tasks:
            if task["id"] == task_id:
                return task
        return None

    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task"""
        global task_id_counter
        task_data["id"] = task_id_counter
        self.tasks.append(task_data)
        task_id_counter += 1
        return task_data

    def update_task(self, task_id: int, update_data: Dict[str, Any]) -> Dict[str, Any] | None:
        """Update an existing task"""
        for i, task in enumerate(self.tasks):
            if task["id"] == task_id:
                for key, value in update_data.items():
                    task[key] = value
                self.tasks[i] = task
                return task
        return None

    def delete_task(self, task_id: int) -> Dict[str, Any] | None:
        """Delete a task"""
        for i, task in enumerate(self.tasks):
            if task["id"] == task_id:
                return self.tasks.pop(i)
        return None

def get_database() -> DatabaseSession:
    """
    Database dependency - returns a database session
    In a real app, this would connect to PostgreSQL/MySQL
    """
    return DatabaseSession()