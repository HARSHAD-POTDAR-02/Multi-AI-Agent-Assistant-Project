import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from .models import Goal, GoalType, SmartGoal

class GoalMapper:
    def __init__(self, storage_path: str = "goals.json"):
        self.storage_path = storage_path
        self.goals: Dict[str, Goal] = {}
        self.smart_goals: Dict[str, SmartGoal] = {}
        self._load_goals()
    
    def create_goal(self, title: str, target_date: datetime = None, goal_type: GoalType = GoalType.PERSONAL, description: str = "") -> Goal:
        """Create a new SMART goal with validation"""
        goal = Goal(
            id=str(uuid.uuid4()),
            title=title.strip(),
            description=description.strip(),
            type=goal_type,
            target_date=target_date,
            created_at=datetime.now(timezone.utc),
            linked_tasks=[],
            progress=0.0,
            is_active=True,
            milestones=[]
        )
        
        self.goals[goal.id] = goal
        self._save_goals()
        return goal
    
    def create_smart_goal(self, specific: str, measurable: str, achievable: str, relevant: str, time_bound: datetime) -> SmartGoal:
        """Create a SMART (Specific, Measurable, Achievable, Relevant, Time-bound) goal"""
        smart_goal = SmartGoal(
            specific=specific,
            measurable=measurable,
            achievable=achievable,
            relevant=relevant,
            time_bound=time_bound,
            progress_metrics=[]
        )
        
        goal_id = str(uuid.uuid4())
        self.smart_goals[goal_id] = smart_goal
        
        # Also create a regular goal for tracking
        regular_goal = self.create_goal(
            title=specific,
            target_date=time_bound,
            description=f"Measurable: {measurable}\nAchievable: {achievable}\nRelevant: {relevant}"
        )
        
        self._save_goals()
        return smart_goal
    
    def link_task_to_goal(self, task_id: str, goal_id: str) -> bool:
        """Link a task to a goal for alignment tracking"""
        if goal_id not in self.goals:
            return False
        
        goal = self.goals[goal_id]
        if task_id not in goal.linked_tasks:
            goal.linked_tasks.append(task_id)
            self._save_goals()
        
        return True
    
    def unlink_task_from_goal(self, task_id: str, goal_id: str) -> bool:
        """Remove task-goal link"""
        if goal_id not in self.goals:
            return False
        
        goal = self.goals[goal_id]
        if task_id in goal.linked_tasks:
            goal.linked_tasks.remove(task_id)
            self._save_goals()
        
        return True
    
    def calculate_goal_progress(self, goal_id: str, tasks: List) -> float:
        """Calculate goal progress based on linked task completion"""
        if goal_id not in self.goals:
            return 0.0
        
        goal = self.goals[goal_id]
        if not goal.linked_tasks:
            return goal.progress
        
        completed_tasks = 0
        total_tasks = len(goal.linked_tasks)
        task_progress_sum = 0.0
        
        # Create task lookup for efficiency
        task_dict = {task.id: task for task in tasks if hasattr(task, 'id')}
        
        for task_id in goal.linked_tasks:
            if task_id in task_dict:
                task = task_dict[task_id]
                if hasattr(task, 'status'):
                    status_val = task.status.value if hasattr(task.status, 'value') else task.status
                    if status_val == 'completed':
                        completed_tasks += 1
                        task_progress_sum += 100.0
                    elif hasattr(task, 'progress'):
                        task_progress_sum += task.progress
        
        # Calculate weighted progress
        if total_tasks > 0:
            progress = task_progress_sum / total_tasks
        else:
            progress = goal.progress
        
        # Update goal progress
        goal.progress = round(progress, 1)
        self._save_goals()
        
        return goal.progress
    
    def get_goal_alignment_score(self, task, goals: List[Goal] = None) -> float:
        """Calculate how well a task aligns with active goals"""
        if not goals:
            goals = list(self.goals.values())
        
        alignment_score = 0.0
        aligned_goals = 0
        
        for goal in goals:
            if not goal.is_active:
                continue
            
            if hasattr(task, 'id') and task.id in goal.linked_tasks:
                aligned_goals += 1
                
                # Higher score for goals with approaching deadlines
                if goal.target_date:
                    days_to_target = (goal.target_date - datetime.now(timezone.utc)).days
                    if days_to_target < 7:
                        alignment_score += 3.0
                    elif days_to_target < 30:
                        alignment_score += 2.0
                    else:
                        alignment_score += 1.0
                else:
                    alignment_score += 1.5
                
                # Bonus for goals with low progress (need attention)
                if goal.progress < 25:
                    alignment_score += 1.0
                elif goal.progress < 50:
                    alignment_score += 0.5
        
        # Penalty for tasks not aligned to any goals
        if aligned_goals == 0:
            alignment_score = 0.5
        
        return min(alignment_score, 10.0)
    
    def get_tasks_for_goal(self, goal_id: str) -> List[str]:
        """Get all task IDs linked to a specific goal"""
        if goal_id not in self.goals:
            return []
        
        return self.goals[goal_id].linked_tasks.copy()
    
    def get_goals_by_type(self, goal_type: GoalType) -> List[Goal]:
        """Get all goals of a specific type"""
        return [goal for goal in self.goals.values() if goal.type == goal_type and goal.is_active]
    
    def get_overdue_goals(self) -> List[Goal]:
        """Get goals that are past their target date"""
        now = datetime.now(timezone.utc)
        overdue = []
        
        for goal in self.goals.values():
            if goal.is_active and goal.target_date and goal.target_date < now and goal.progress < 100:
                overdue.append(goal)
        
        return sorted(overdue, key=lambda g: g.target_date)
    
    def get_goals_needing_attention(self) -> List[Goal]:
        """Get goals that need attention (low progress, approaching deadline)"""
        now = datetime.now(timezone.utc)
        needs_attention = []
        
        for goal in self.goals.values():
            if not goal.is_active:
                continue
            
            # Goals with approaching deadlines and low progress
            if goal.target_date:
                days_remaining = (goal.target_date - now).days
                if days_remaining <= 14 and goal.progress < 50:
                    needs_attention.append(goal)
                elif days_remaining <= 7 and goal.progress < 80:
                    needs_attention.append(goal)
            
            # Goals with no recent progress
            elif goal.progress < 10:
                needs_attention.append(goal)
        
        return needs_attention
    
    def update_goal_progress(self, goal_id: str, progress: float) -> bool:
        """Manually update goal progress"""
        if goal_id not in self.goals:
            return False
        
        self.goals[goal_id].progress = max(0.0, min(100.0, progress))
        self._save_goals()
        return True
    
    def add_milestone_to_goal(self, goal_id: str, milestone: str) -> bool:
        """Add a milestone to a goal"""
        if goal_id not in self.goals:
            return False
        
        self.goals[goal_id].milestones.append(milestone)
        self._save_goals()
        return True
    
    def deactivate_goal(self, goal_id: str) -> bool:
        """Deactivate a goal (soft delete)"""
        if goal_id not in self.goals:
            return False
        
        self.goals[goal_id].is_active = False
        self._save_goals()
        return True
    
    def get_goal_hierarchy(self) -> Dict[str, List[Goal]]:
        """Get goals organized by type for hierarchical view"""
        hierarchy = {}
        for goal_type in GoalType:
            hierarchy[goal_type.value] = self.get_goals_by_type(goal_type)
        
        return hierarchy
    
    def calculate_overall_goal_progress(self) -> Dict[str, float]:
        """Calculate overall progress across all goal types"""
        progress_by_type = {}
        
        for goal_type in GoalType:
            goals = self.get_goals_by_type(goal_type)
            if goals:
                total_progress = sum(goal.progress for goal in goals)
                progress_by_type[goal_type.value] = total_progress / len(goals)
            else:
                progress_by_type[goal_type.value] = 0.0
        
        return progress_by_type
    
    def suggest_goal_based_tasks(self, goal_id: str) -> List[str]:
        """Suggest task ideas to help achieve a goal"""
        if goal_id not in self.goals:
            return []
        
        goal = self.goals[goal_id]
        suggestions = []
        
        # Basic suggestions based on goal type
        if goal.type == GoalType.LEARNING:
            suggestions = [
                f"Research resources for {goal.title}",
                f"Create study plan for {goal.title}",
                f"Practice exercises for {goal.title}",
                f"Find mentor or course for {goal.title}"
            ]
        elif goal.type == GoalType.PROFESSIONAL:
            suggestions = [
                f"Break down {goal.title} into phases",
                f"Identify stakeholders for {goal.title}",
                f"Create timeline for {goal.title}",
                f"Gather requirements for {goal.title}"
            ]
        elif goal.type == GoalType.HEALTH:
            suggestions = [
                f"Create weekly plan for {goal.title}",
                f"Track daily progress on {goal.title}",
                f"Research best practices for {goal.title}",
                f"Set up accountability system for {goal.title}"
            ]
        else:
            suggestions = [
                f"Define specific steps for {goal.title}",
                f"Set weekly milestones for {goal.title}",
                f"Identify resources needed for {goal.title}",
                f"Create accountability measures for {goal.title}"
            ]
        
        return suggestions
    
    def _load_goals(self):
        """Load goals from storage"""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                for goal_id, goal_data in data.get('goals', {}).items():
                    # Convert datetime strings back to datetime objects
                    if goal_data.get('created_at'):
                        goal_data['created_at'] = datetime.fromisoformat(goal_data['created_at'])
                    if goal_data.get('target_date'):
                        goal_data['target_date'] = datetime.fromisoformat(goal_data['target_date'])
                    
                    # Convert type string to enum
                    if goal_data.get('type'):
                        goal_data['type'] = GoalType(goal_data['type'])
                    
                    self.goals[goal_id] = Goal(**goal_data)
                
                # Load SMART goals
                for smart_id, smart_data in data.get('smart_goals', {}).items():
                    if smart_data.get('time_bound'):
                        smart_data['time_bound'] = datetime.fromisoformat(smart_data['time_bound'])
                    self.smart_goals[smart_id] = SmartGoal(**smart_data)
                    
        except FileNotFoundError:
            self.goals = {}
            self.smart_goals = {}
        except Exception as e:
            print(f"Error loading goals: {e}")
            self.goals = {}
            self.smart_goals = {}
    
    def _save_goals(self):
        """Save goals to storage"""
        try:
            data = {
                'goals': {},
                'smart_goals': {}
            }
            
            for goal_id, goal in self.goals.items():
                goal_dict = goal.dict()
                # Convert datetime objects to strings
                if goal_dict.get('created_at'):
                    goal_dict['created_at'] = goal_dict['created_at'].isoformat()
                if goal_dict.get('target_date'):
                    goal_dict['target_date'] = goal_dict['target_date'].isoformat()
                # Convert enum to string
                if goal_dict.get('type'):
                    goal_dict['type'] = goal_dict['type'].value
                
                data['goals'][goal_id] = goal_dict
            
            for smart_id, smart_goal in self.smart_goals.items():
                smart_dict = smart_goal.dict()
                if smart_dict.get('time_bound'):
                    smart_dict['time_bound'] = smart_dict['time_bound'].isoformat()
                data['smart_goals'][smart_id] = smart_dict
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving goals: {e}")