from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime, time
from enum import Enum

class GoalType(Enum):
    PERSONAL = "personal"
    PROFESSIONAL = "professional"
    LEARNING = "learning"
    HEALTH = "health"
    PROJECT = "project"

class PriorityFactor(BaseModel):
    urgency: float = 0.0
    effort: float = 0.0
    focus_window: float = 0.0
    dependency: float = 0.0
    goal_alignment: float = 0.0

class PriorityScore(BaseModel):
    score: float
    factors: PriorityFactor
    timestamp: datetime
    reasoning: str = ""

class Goal(BaseModel):
    id: str
    title: str
    description: str = ""
    type: GoalType
    target_date: Optional[datetime] = None
    progress: float = 0.0
    linked_tasks: List[str] = []
    created_at: datetime
    is_active: bool = True
    milestones: List[str] = []

class FocusWindow(BaseModel):
    start_time: time
    end_time: time
    productivity_multiplier: float = 1.0
    days_of_week: List[int] = [0, 1, 2, 3, 4, 5, 6]  # 0=Monday

class UserPreferences(BaseModel):
    focus_windows: List[FocusWindow] = []
    work_hours_start: time = time(9, 0)
    work_hours_end: time = time(17, 0)
    priority_weights: Dict[str, float] = {
        "urgency": 0.4,
        "effort": 0.2,
        "focus_window": 0.2,
        "dependency": 0.1,
        "goal_alignment": 0.1
    }
    break_duration: int = 15  # minutes
    max_daily_tasks: int = 8
    preferred_task_duration: int = 60  # minutes

class TaskDependency(BaseModel):
    task_id: str
    dependency_type: str  # "blocks", "blocked_by", "related"
    strength: float = 1.0  # 0.0 to 1.0

class SmartGoal(BaseModel):
    specific: str
    measurable: str
    achievable: str
    relevant: str
    time_bound: datetime
    progress_metrics: List[str] = []