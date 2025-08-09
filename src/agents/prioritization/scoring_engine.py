import math
from datetime import datetime, timezone, time, timedelta
from typing import Dict, List, Optional, Tuple
from .models import PriorityScore, PriorityFactor, UserPreferences, FocusWindow

class PriorityScorer:
    def __init__(self):
        self.default_weights = {
            "urgency": 0.4,
            "effort": 0.2,
            "focus_window": 0.2,
            "dependency": 0.1,
            "goal_alignment": 0.1
        }
    
    def calculate_priority(self, task, user_prefs: UserPreferences = None, all_tasks: List = None, goals: List = None) -> PriorityScore:
        """Multi-factor priority scoring with real-time calculations"""
        if not user_prefs:
            user_prefs = UserPreferences()
        
        factors = PriorityFactor()
        
        # 1. Deadline urgency (exponential decay)
        factors.urgency = self._calculate_urgency_score(task)
        
        # 2. Effort estimation (inverse relationship)
        factors.effort = self._calculate_effort_score(task)
        
        # 3. Focus window optimization
        factors.focus_window = self._calculate_focus_score(user_prefs)
        
        # 4. Task dependencies
        factors.dependency = self._calculate_dependency_score(task, all_tasks or [])
        
        # 5. SMART goal alignment
        factors.goal_alignment = self._calculate_goal_alignment_score(task, goals or [])
        
        # Calculate weighted final score
        weights = user_prefs.priority_weights
        final_score = (
            factors.urgency * weights.get("urgency", 0.4) +
            factors.effort * weights.get("effort", 0.2) +
            factors.focus_window * weights.get("focus_window", 0.2) +
            factors.dependency * weights.get("dependency", 0.1) +
            factors.goal_alignment * weights.get("goal_alignment", 0.1)
        )
        
        reasoning = self._generate_reasoning(factors, weights)
        
        return PriorityScore(
            score=round(final_score, 2),
            factors=factors,
            timestamp=datetime.now(timezone.utc),
            reasoning=reasoning
        )
    
    def _calculate_urgency_score(self, task) -> float:
        """Exponential decay scoring based on deadline proximity and semantic importance"""
        # Check for semantic importance in task content
        semantic_urgency = self._analyze_task_importance(task)
        
        if not hasattr(task, 'due_date') or not task.due_date:
            return semantic_urgency  # Use semantic analysis for tasks without deadlines
        
        now = datetime.now(timezone.utc)
        if task.due_date.tzinfo is None:
            task_due = task.due_date.replace(tzinfo=timezone.utc)
        else:
            task_due = task.due_date
        
        days_remaining = (task_due - now).total_seconds() / 86400
        
        if days_remaining < 0:  # Overdue
            return 10.0
        elif days_remaining < 1:  # Due today
            return 8.0
        elif days_remaining < 3:  # Due in 2-3 days
            return 6.0
        elif days_remaining < 7:  # Due this week
            return 4.0
        elif days_remaining < 30:  # Due this month
            return 2.0
        else:  # Due later
            return 1.0
    
    def _calculate_effort_score(self, task) -> float:
        """Inverse relationship - lower effort gets higher priority for quick wins"""
        if not hasattr(task, 'estimated_hours') or not task.estimated_hours:
            return 3.0  # Default medium effort
        
        hours = task.estimated_hours
        if hours <= 0.5:  # 30 minutes or less
            return 8.0
        elif hours <= 2:  # 2 hours or less
            return 6.0
        elif hours <= 8:  # Full day
            return 4.0
        elif hours <= 24:  # 3 days
            return 2.0
        else:  # Long-term tasks
            return 1.0
    
    def _calculate_focus_score(self, user_prefs: UserPreferences) -> float:
        """Time-of-day multipliers based on user's peak performance windows"""
        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()
        
        max_multiplier = 1.0
        
        for window in user_prefs.focus_windows:
            if current_weekday in window.days_of_week:
                if self._time_in_range(current_time, window.start_time, window.end_time):
                    max_multiplier = max(max_multiplier, window.productivity_multiplier)
        
        # Check if within general work hours
        if self._time_in_range(current_time, user_prefs.work_hours_start, user_prefs.work_hours_end):
            max_multiplier = max(max_multiplier, 1.2)
        
        return min(max_multiplier * 5.0, 10.0)  # Scale to 0-10 range
    
    def _calculate_dependency_score(self, task, all_tasks: List) -> float:
        """Boost priority for blocking tasks, reduce for blocked tasks"""
        if not hasattr(task, 'dependencies') or not all_tasks:
            return 5.0  # Neutral score
        
        blocking_count = 0  # Tasks that depend on this task
        blocked_count = len(task.dependencies)  # Tasks this task depends on
        
        # Count how many tasks are blocked by this task
        for other_task in all_tasks:
            if hasattr(other_task, 'dependencies') and task.id in other_task.dependencies:
                blocking_count += 1
        
        # Calculate score
        score = 5.0  # Base score
        score += blocking_count * 2.0  # Boost for blocking others
        score -= blocked_count * 1.0   # Reduce for being blocked
        
        return max(0.0, min(10.0, score))
    
    def _calculate_goal_alignment_score(self, task, goals: List) -> float:
        """Boost priority for tasks that advance multiple goals"""
        if not goals:
            return 3.0  # Default score when no goals
        
        alignment_count = 0
        total_goal_progress_impact = 0.0
        
        for goal in goals:
            if hasattr(goal, 'linked_tasks') and task.id in goal.linked_tasks:
                alignment_count += 1
                # Higher impact for goals with lower progress (catch-up effect)
                progress_impact = (100 - goal.progress) / 100
                total_goal_progress_impact += progress_impact
        
        if alignment_count == 0:
            return 1.0  # Low priority for unaligned tasks
        
        # Scale based on number of goals and their progress needs
        base_score = min(alignment_count * 3.0, 8.0)
        progress_bonus = min(total_goal_progress_impact * 2.0, 2.0)
        
        return base_score + progress_bonus
    
    def _time_in_range(self, current: time, start: time, end: time) -> bool:
        """Check if current time is within the given range"""
        if start <= end:
            return start <= current <= end
        else:  # Range crosses midnight
            return current >= start or current <= end
    
    def _generate_reasoning(self, factors: PriorityFactor, weights: Dict[str, float]) -> str:
        """Generate human-readable reasoning for the priority score"""
        reasons = []
        
        if factors.urgency > 7:
            reasons.append("urgent deadline")
        elif factors.urgency > 5:
            reasons.append("approaching deadline")
        
        if factors.effort > 6:
            reasons.append("quick win")
        elif factors.effort < 3:
            reasons.append("complex task")
        
        if factors.focus_window > 6:
            reasons.append("peak focus time")
        
        if factors.dependency > 7:
            reasons.append("blocks other tasks")
        elif factors.dependency < 3:
            reasons.append("waiting on dependencies")
        
        if factors.goal_alignment > 6:
            reasons.append("advances multiple goals")
        
        return ", ".join(reasons) if reasons else "standard priority"
    
    def get_peak_focus_windows(self, user_prefs: UserPreferences) -> List[Tuple[time, time]]:
        """Get user's peak productivity windows for task scheduling"""
        windows = []
        for window in user_prefs.focus_windows:
            if window.productivity_multiplier > 1.2:
                windows.append((window.start_time, window.end_time))
        return windows
    
    def calculate_estimated_completion_time(self, task, user_prefs: UserPreferences) -> datetime:
        """Estimate when a task will be completed based on effort and focus windows"""
        if not hasattr(task, 'estimated_hours') or not task.estimated_hours:
            return datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Find next available focus window
        now = datetime.now()
        estimated_hours = task.estimated_hours
        
        # Simple estimation: add estimated hours to current time
        # In a real implementation, this would consider focus windows and breaks
        return now + timedelta(hours=estimated_hours)
    
    def _analyze_task_importance(self, task) -> float:
        """Analyze task importance using LLM for context understanding"""
        try:
            from groq import Groq
            import os
            
            client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
            
            text = f"{task.title} {getattr(task, 'description', '')}"
            
            prompt = f"""Rate the urgency/importance of this task on a scale of 1-10:

Task: {text}

Consider:
- Business impact (authentication, security, core features = high)
- Dependencies (blocking other work = high)
- Foundation work (setup, architecture = high)
- Personal tasks (gym, hobbies = low)
- Bug fixes and testing (medium-high)
- Documentation (medium-low)

Return only a number between 1-10."""
            
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="openai/gpt-oss-120b",
                temperature=0.1,
                max_tokens=10
            )
            
            score = float(response.choices[0].message.content.strip())
            return max(1.0, min(10.0, score))
            
        except Exception as e:
            print(f"LLM importance analysis failed: {e}")
            return 2.0  # Fallback to default