from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime, time
from enum import Enum

class UserBehavior(BaseModel):
    """Track user behavior patterns for learning"""
    user_id: str = "default"
    productivity_peaks: List[int] = [9, 10, 14, 15]  # Hours of day
    energy_patterns: Dict[int, float] = {}  # Hour -> energy level (0-10)
    task_completion_velocity: Dict[str, float] = {}  # Task type -> avg hours
    procrastination_triggers: List[str] = []
    preferred_task_duration: int = 60  # minutes
    context_switching_penalty: float = 0.3
    last_updated: datetime = datetime.now()

class ContextState(BaseModel):
    """Current user context for smart recommendations"""
    current_time: datetime = datetime.now()
    energy_level: float = 7.0  # 0-10 scale
    focus_mode: bool = False
    recent_completions: List[str] = []
    time_until_next_meeting: Optional[int] = None  # minutes
    current_momentum: str = "neutral"  # "high", "low", "neutral"
    stress_level: float = 5.0  # 0-10 scale
    available_time_block: int = 120  # minutes

class SmartPriorityScore(BaseModel):
    """Enhanced priority score with learning"""
    base_score: float
    context_multiplier: float
    energy_match: float
    momentum_bonus: float
    urgency_factor: float
    final_score: float
    confidence: float
    reasoning: str
    next_best_time: Optional[datetime] = None

class TaskPattern(BaseModel):
    """Learning patterns for specific tasks"""
    task_id: str
    actual_duration: List[float] = []
    completion_times: List[int] = []  # Hours when completed
    procrastination_count: int = 0
    energy_required: float = 5.0
    complexity_rating: float = 5.0
    user_satisfaction: float = 7.0

class ProactiveInsight(BaseModel):
    """Proactive suggestions and insights"""
    type: str  # "warning", "opportunity", "suggestion", "celebration"
    message: str
    priority: int  # 1-5
    action_required: bool = False
    expires_at: Optional[datetime] = None
    context: Dict[str, Any] = {}