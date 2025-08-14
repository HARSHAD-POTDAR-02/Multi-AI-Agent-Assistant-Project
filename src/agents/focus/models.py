from datetime import datetime
from typing import Optional, List

class FocusSession:
    def __init__(self, session_type="pomodoro", work_duration=25, break_duration=5):
        self.session_type = session_type
        self.work_duration = work_duration * 60  # Convert to seconds
        self.break_duration = break_duration * 60
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.is_active = False
        self.is_paused = False
        self.pause_time: Optional[datetime] = None
        self.total_paused_duration = 0  # seconds
        self.is_break = False
        self.interruptions = 0
        self.completed = False
        self.timer_thread = None
        self.blocked_notifications: List[str] = []

class FocusAnalyticsData:
    def __init__(self, success_rate: float, optimal_duration: int, recommendation: str):
        self.success_rate = success_rate
        self.optimal_duration = optimal_duration
        self.recommendation = recommendation