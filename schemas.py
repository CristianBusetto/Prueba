from typing import Optional
from pydantic import BaseModel


class CreateTaskRequest(BaseModel):
    title: str
    state: Optional[str] = None
    tipo: Optional[str] = None
    un: Optional[str] = None
    completed_work: Optional[float] = None
    assigned_to: Optional[str] = None
    iteration: Optional[str] = None


class UpdateWorkItemRequest(BaseModel):
    title: Optional[str] = None
    state: Optional[str] = None
    tipo: Optional[str] = None
    un: Optional[str] = None
    completed_work: Optional[float] = None
