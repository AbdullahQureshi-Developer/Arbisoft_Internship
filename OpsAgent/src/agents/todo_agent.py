from typing import List
from pydantic import BaseModel, Field
from src.hooks.logging_hook import log_call
from src.skills.task_extraction_skill import ExtractedTask
from src.memory.store import create_task


class SaveTasksRequest(BaseModel):
    tasks: List[ExtractedTask] = Field(
        ..., description="List of extracted task objects to save"
    )
    user_id: str = Field(..., description="User ID to scope task ownership")


class SavedTaskInfo(BaseModel):
    task_id: int
    description: str
    assignee: str = ""
    due_hint: str = ""
    status: str


class SaveTasksResult(BaseModel):
    saved_tasks: List[SavedTaskInfo]


@log_call
def save_extracted_tasks(request: SaveTasksRequest) -> SaveTasksResult:
    """
    Saves a list of Pydantic ExtractedTask models into SQLite tasks table via store.py scoped to user_id.
    """
    saved_list = []
    for task in request.tasks:
        db_task = create_task(
            user_id=request.user_id,
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
