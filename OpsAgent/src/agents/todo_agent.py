from typing import List
from pydantic import BaseModel, Field
from src.hooks.logging_hook import log_call
from src.skills.task_extraction_skill import ExtractedTask
from src.memory.store import create_task


class SavedTaskInfo(BaseModel):
    task_id: int
    description: str
    assignee: str = ""
    due_hint: str = ""
    status: str


class SaveTasksResult(BaseModel):
    saved_tasks: List[SavedTaskInfo]


@log_call
def save_extracted_tasks(tasks: List[ExtractedTask]) -> SaveTasksResult:
    """
    Saves a list of Pydantic ExtractedTask models into SQLite tasks table via store.py.
    """
    saved_list = []
    for task in tasks:
        db_task = create_task(
            description=task.description,
            assignee=task.assignee or "",
            due_hint=task.due_hint or "",
        )
        saved_list.append(
            SavedTaskInfo(
                task_id=db_task.id,
                description=db_task.description,
                assignee=db_task.assignee or "",
                due_hint=db_task.due_hint or "",
                status=db_task.status,
            )
        )
    return SaveTasksResult(saved_tasks=saved_list)
