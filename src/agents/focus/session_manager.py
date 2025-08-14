import threading
import time
from datetime import datetime
from typing import Optional
import subprocess
from .models import FocusSession
from .analytics import FocusAnalytics
from .focus_blocker import FocusBlocker

class FocusManager:
    def __init__(self):
        self.current_session: Optional[FocusSession] = None
        self.analytics = FocusAnalytics()
        self.blocker = FocusBlocker()

    def start_session(self, session_type="focus session", duration=25, break_duration=5):
        if self.current_session and self.current_session.is_active:
            return "A focus session is already active. End it first or add an interruption."
        
        self.current_session = FocusSession(session_type, duration, break_duration)
        return self._start_session()

    def _start_session(self):
        self.current_session.start_time = datetime.now()
        self.current_session.is_active = True
        self.current_session.is_break = False
        self._enable_focus_mode()
        
        # Only start timer thread for sessions under 8 hours (to prevent extremely long threads)
        if self.current_session.work_duration <= 8 * 60 * 60:
            self.current_session.timer_thread = threading.Thread(target=self._run_timer)
            self.current_session.timer_thread.daemon = True
            self.current_session.timer_thread.start()
        
        hours = self.current_session.work_duration // 3600
        minutes = (self.current_session.work_duration % 3600) // 60
        
        if hours > 0:
            time_str = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
        else:
            time_str = f"{minutes}m"
            
        block_result = self._enable_focus_mode()
        return f"Focus session started! {time_str} of uninterrupted work time ahead.\n{block_result}"

    def _enable_focus_mode(self):
        return self.blocker.enable_focus_mode_with_elevation()

    def _disable_focus_mode(self):
        return self.blocker.disable_focus_mode()

    def _run_timer(self):
        time.sleep(self.current_session.work_duration)
        if self.current_session and self.current_session.is_active:
            self._complete_session()

    def _complete_session(self):
        if self.current_session:
            self.current_session.completed = True
            self.current_session.is_break = True
            self._disable_focus_mode()

    def end_session(self):
        if not self.current_session or not self.current_session.is_active:
            return "No active focus session to end."
        
        self.current_session.end_time = datetime.now()
        self.current_session.is_active = False
        self._disable_focus_mode()
        self.analytics.record_session(self.current_session)
        
        duration = (self.current_session.end_time - self.current_session.start_time).total_seconds() / 60
        hours = int(duration // 60)
        minutes = int(duration % 60)
        
        if hours > 0:
            duration_str = f"{hours}h {minutes}m"
        else:
            duration_str = f"{minutes}m"
            
        return f"Focus session ended. Duration: {duration_str}. Great work!"

    def add_interruption(self):
        if self.current_session and self.current_session.is_active:
            self.current_session.interruptions += 1
            return "Interruption logged. Try to minimize distractions for better focus."
        return "No active session to record interruption."

    def get_status(self):
        if not self.current_session or not self.current_session.is_active:
            return "No active focus session."
        
        if self.current_session.is_paused:
            return "Focus session is paused. Use 'resume focus' to continue."
        
        elapsed = (datetime.now() - self.current_session.start_time).total_seconds() - self.current_session.total_paused_duration
        remaining = self.current_session.work_duration - elapsed
        
        if remaining > 0:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            
            if hours > 0:
                time_str = f"{hours}h {minutes}m"
            else:
                time_str = f"{minutes}m"
                
            return f"Focus session active: {time_str} remaining"
        else:
            return "Focus session completed! Time for a break."

    def extend_session(self, additional_minutes):
        if not self.current_session or not self.current_session.is_active:
            return "No active focus session to extend."
        
        # Add time to current session
        self.current_session.work_duration += additional_minutes * 60
        
        hours = additional_minutes // 60
        minutes = additional_minutes % 60
        
        if hours > 0:
            time_str = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
        else:
            time_str = f"{minutes}m"
            
        return f"Focus session extended by {time_str}. Keep up the great work!"
    
    def pause_session(self):
        if not self.current_session or not self.current_session.is_active:
            return "No active focus session to pause."
        
        if self.current_session.is_paused:
            return "Focus session is already paused."
        
        self.current_session.is_paused = True
        self.current_session.pause_time = datetime.now()
        self._disable_focus_mode()
        
        return "Focus session paused. Use 'resume focus' to continue."
    
    def resume_session(self):
        if not self.current_session or not self.current_session.is_active:
            return "No focus session to resume."
        
        if not self.current_session.is_paused:
            return "Focus session is not paused."
        
        # Calculate paused duration and add to total
        paused_duration = (datetime.now() - self.current_session.pause_time).total_seconds()
        self.current_session.total_paused_duration += paused_duration
        
        self.current_session.is_paused = False
        self.current_session.pause_time = None
        self._enable_focus_mode()
        
        return "Focus session resumed. Back to work!"
    
    def get_analytics(self):
        return self.analytics.get_analytics_summary()