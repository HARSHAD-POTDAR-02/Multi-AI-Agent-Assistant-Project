import logging
import sqlite3
import uuid
import json
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from collections import defaultdict, deque
from threading import Lock
import os
from pathlib import Path
import html

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RecurrenceType(Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

# Constants
SECONDS_PER_HOUR = 3600

class Task:
    def __init__(self, title: str, description: str = "", priority: Priority = Priority.MEDIUM, 
                 assigned_agent: str = None, dependencies: List[str] = None, 
                 due_date: datetime = None, estimated_hours: float = 0.0, 
                 tags: List[str] = None, recurrence_type: RecurrenceType = RecurrenceType.NONE,
                 recurrence_interval: int = 1, completion_criteria: List[str] = None):
        self.id = str(uuid.uuid4())
        self.title = html.escape(title) if title else ""
        self.description = html.escape(description) if description else ""
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.parent_id = None
        self.assigned_agent = assigned_agent
        self.dependencies = dependencies or []
        self.subtasks = []
        self.due_date = due_date
        self.estimated_hours = estimated_hours
        self.actual_hours = 0.0
        self.progress = 0
        self.tags = tags or []
        
        # Time tracking
        self.time_entries = []
        self.started_at = None
        
        # Recurrence
        if isinstance(recurrence_type, str):
            try:
                self.recurrence_type = RecurrenceType(recurrence_type)
            except ValueError:
                self.recurrence_type = RecurrenceType.NONE
        else:
            self.recurrence_type = recurrence_type
            
        self.recurrence_interval = recurrence_interval
        self.next_occurrence = self._calculate_next_occurrence() if self.recurrence_type != RecurrenceType.NONE else None
        
        # Quality and completion
        self.completion_criteria = completion_criteria or []
        self.quality_score = 0.0
        
        # Analytics
        self.view_count = 0
        self.modification_count = 0
        
        # Milestones
        self.milestones = []
        
        # Notifications
        self.notifications = []
        
        # Calculate dynamic priority
        self.dynamic_priority_score = self._calculate_dynamic_priority()

    def _calculate_dynamic_priority(self) -> float:
        """Enhanced dynamic priority calculation with multi-factor scoring"""
        try:
            # Import here to avoid circular imports
            from agents.prioritization.scoring_engine import PriorityScorer
            from agents.prioritization.models import UserPreferences
            
            scorer = PriorityScorer()
            user_prefs = UserPreferences()
            
            # Use the advanced scoring engine
            priority_score = scorer.calculate_priority(self, user_prefs, [], [])
            return priority_score.score
            
        except ImportError:
            # Fallback to original calculation if prioritization module not available
            priority_val = self.priority.value if hasattr(self.priority, 'value') else self.priority
            if isinstance(priority_val, str):
                priority_map = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
                priority_val = priority_map.get(priority_val.lower(), 2)
                
            base_score = 5 - priority_val
            
            if self.due_date:
                days_until_due = max(-10, (self.due_date - datetime.now(timezone.utc)).days)
                if days_until_due < 0:
                    due_factor = 3
                elif days_until_due == 0:
                    due_factor = 2
                elif days_until_due <= 2:
                    due_factor = 1.5
                elif days_until_due <= 7:
                    due_factor = 1
                else:
                    due_factor = 0
                base_score += due_factor
                
            dependency_factor = len(self.subtasks) * 0.2
            base_score += dependency_factor
            
            status_val = self.status.value if hasattr(self.status, 'value') else self.status
            if status_val == 'blocked':
                base_score -= 1
            elif status_val == 'in_progress':
                base_score += 0.5
                
            return round(base_score, 2)
        except Exception as e:
            logger.error(f"Error calculating dynamic priority: {e}")
            return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'progress': self.progress,
            'tags': self.tags,
            'dependencies': self.dependencies,
            'subtasks': self.subtasks,
            'milestones': self.milestones,
            'time_entries': self.time_entries,
            'dynamic_priority_score': self.dynamic_priority_score
        }
    
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if not self.due_date:
            return False
        return datetime.now(timezone.utc) > self.due_date
    
    def add_notification(self, message: str, level: str = "info"):
        """Add a notification to the task"""
        notification = {
            'message': message,
            'level': level,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.notifications.append(notification)
    
    def _calculate_next_occurrence(self) -> Optional[datetime]:
        """Calculate next occurrence for recurring tasks"""
        if self.recurrence_type == RecurrenceType.NONE:
            return None
        
        base_date = self.due_date or self.created_at
        
        if self.recurrence_type == RecurrenceType.DAILY:
            return base_date + timedelta(days=self.recurrence_interval)
        elif self.recurrence_type == RecurrenceType.WEEKLY:
            return base_date + timedelta(weeks=self.recurrence_interval)
        elif self.recurrence_type == RecurrenceType.MONTHLY:
            return base_date + timedelta(days=30 * self.recurrence_interval)
        elif self.recurrence_type == RecurrenceType.YEARLY:
            return base_date + timedelta(days=365 * self.recurrence_interval)
        
        return None
    
    def create_recurring_instance(self):
        """Create a new instance of a recurring task"""
        if self.recurrence_type == RecurrenceType.NONE:
            return None
        
        new_task = Task(
            title=self.title,
            description=self.description,
            priority=self.priority,
            assigned_agent=self.assigned_agent,
            dependencies=self.dependencies.copy(),
            estimated_hours=self.estimated_hours,
            tags=self.tags.copy(),
            recurrence_type=self.recurrence_type,
            recurrence_interval=self.recurrence_interval,
            completion_criteria=self.completion_criteria.copy()
        )
        
        # Set new due date if original had one
        if self.due_date:
            new_task.due_date = self._calculate_next_occurrence()
        
        return new_task
    
    def update_dynamic_priority(self):
        """Update the dynamic priority score"""
        self.dynamic_priority_score = self._calculate_dynamic_priority()
        self.modification_count += 1

class TaskManager:
    def __init__(self, db_path: str = "tasks.db"):
        self.db_path = self._sanitize_path(db_path)
        # Use shared storage
        from shared_storage import get_shared_tasks, set_shared_tasks
        self.tasks = get_shared_tasks()
        # Ensure tasks are synced
        set_shared_tasks(self.tasks)
        self.lock = Lock()
        self._init_database()
        
    def _sanitize_path(self, path: str) -> str:
        """Sanitize file path to prevent path traversal"""
        safe_path = Path(path).resolve()
        base_dir = Path.cwd()
        try:
            safe_path.relative_to(base_dir)
            return str(safe_path)
        except ValueError:
            logger.warning(f"Path traversal attempt detected: {path}")
            return str(base_dir / "tasks.db")
    
    def _init_database(self):
        """Initialize the database with proper error handling"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        description TEXT,
                        priority TEXT,
                        status TEXT,
                        created_at TEXT,
                        updated_at TEXT,
                        data TEXT
                    )
                ''')
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def create_task(self, title: str, **kwargs) -> Optional[str]:
        """Create a new task with proper validation"""
        if not title or not title.strip():
            logger.error("Task title cannot be empty")
            return None
            
        try:
            with self.lock:
                # Filter out invalid parameters that Task constructor doesn't accept
                valid_params = {}
                valid_keys = ['description', 'priority', 'assigned_agent', 'dependencies', 
                             'due_date', 'estimated_hours', 'tags', 'recurrence_type', 
                             'recurrence_interval', 'completion_criteria']
                
                for key, value in kwargs.items():
                    if key in valid_keys and value is not None:
                        valid_params[key] = value
                
                task = Task(title=title.strip(), **valid_params)
                self.tasks[task.id] = task
                # Also update shared storage
                from shared_storage import add_shared_task, set_shared_tasks
                add_shared_task(task.id, task)
                set_shared_tasks(self.tasks)
                self._save_task(task)
                logger.info(f"Task created: {task.id}")
                return task.id
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None
    
    def _save_task(self, task: Task):
        """Save task to database with parameterized queries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO tasks 
                    (id, title, description, priority, status, created_at, updated_at, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.id,
                    task.title,
                    task.description,
                    task.priority.value,
                    task.status.value,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                    json.dumps(task.to_dict())
                ))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database save error: {e}")
            raise
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID with validation"""
        if not task_id:
            logger.error("Task ID cannot be empty")
            return None
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT data FROM tasks WHERE id = ?', (task_id,))
                row = cursor.fetchone()
                if row:
                    return Task.from_dict(json.loads(row[0]))
                return None
        except sqlite3.Error as e:
            logger.error(f"Database read error: {e}")
            return None
    
    def delete_task(self, task_id: str):
        """Delete a task from the database"""
        if not task_id:
            logger.error("Task ID cannot be empty")
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
                conn.commit()
                logger.info(f"Task deleted: {task_id}")
        except sqlite3.Error as e:
            logger.error(f"Database delete error: {e}")
            raise
    
    def backup_database(self, backup_path: str):
        """Create a backup of the database"""
        import shutil
        shutil.copy2(self.db_path, backup_path)
    
    def restore_database(self, backup_path: str):
        """Restore database from backup"""
        import shutil
        shutil.copy2(backup_path, self.db_path)

class TaskAnalytics:
    """Provides analytics and insights for tasks"""
    
    def __init__(self, task_manager):
        self.task_manager = task_manager
    
    def get_completion_velocity(self, days: int = 30) -> Dict[str, Any]:
        """Calculate task completion velocity over the last N days"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        completed_tasks = []
        
        for task in self.task_manager.tasks.values():
            if (task.status == TaskStatus.COMPLETED and 
                task.updated_at >= cutoff_date):
                completed_tasks.append(task)
        
        return {
            'period_days': days,
            'completed_count': len(completed_tasks),
            'velocity_per_day': len(completed_tasks) / days,
            'avg_completion_time': self._calculate_avg_completion_time(completed_tasks)
        }
    
    def get_agent_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for each agent"""
        agent_metrics = defaultdict(lambda: {
            'assigned_tasks': 0,
            'completed_tasks': 0,
            'average_completion_time': 0.0,
            'quality_score': 0.0
        })
        
        for task in self.task_manager.tasks.values():
            if task.assigned_agent:
                agent = task.assigned_agent
                agent_metrics[agent]['assigned_tasks'] += 1
                
                # Handle both enum and string status values
                task_status = task.status.value if hasattr(task.status, 'value') else task.status
                if task_status == 'completed':
                    agent_metrics[agent]['completed_tasks'] += 1
                    agent_metrics[agent]['quality_score'] += task.quality_score
        
        # Calculate averages
        for agent, metrics in agent_metrics.items():
            if metrics['completed_tasks'] > 0:
                metrics['completion_rate'] = metrics['completed_tasks'] / metrics['assigned_tasks']
                metrics['quality_score'] /= metrics['completed_tasks']
            else:
                metrics['completion_rate'] = 0
                
        return dict(agent_metrics)
    
    def get_overdue_tasks(self) -> List[Task]:
        """Get all overdue tasks"""
        overdue = []
        for task in self.task_manager.tasks.values():
            # Handle both enum and string status values
            task_status = task.status.value if hasattr(task.status, 'value') else task.status
            if task.is_overdue() and task_status not in ['completed', 'cancelled']:
                overdue.append(task)
        
        # Sort by how overdue they are
        return sorted(overdue, key=lambda t: t.due_date if t.due_date else datetime.max.replace(tzinfo=timezone.utc))
    
    def get_blocked_tasks(self) -> List[Task]:
        """Get all blocked tasks with their blocking reasons"""
        blocked = []
        for task in self.task_manager.tasks.values():
            # Handle both enum and string status values
            task_status = task.status.value if hasattr(task.status, 'value') else task.status
            if task_status == 'blocked':
                blocked.append(task)
        return blocked
    
    def _calculate_avg_completion_time(self, tasks: List[Task]) -> float:
        """Calculate average completion time for a list of tasks"""
        if not tasks:
            return 0.0
            
        total_time = sum(
            (task.updated_at - task.created_at).total_seconds() / 3600  # Convert to hours
            for task in tasks
        )
        return total_time / len(tasks)
    
    def generate_burndown_chart_data(self, project_tasks: List[Task]) -> Dict[str, List]:
        """Generate data for burndown chart visualization"""
        # This would be used with a plotting library like matplotlib
        dates = []
        remaining_tasks = []
        
        # Sort tasks by creation date
        sorted_tasks = sorted(project_tasks, key=lambda t: t.created_at)
        
        if not sorted_tasks:
            return {'dates': [], 'remaining': []}
            
        start_date = sorted_tasks[0].created_at.date()
        end_date = datetime.now(timezone.utc).date()
        
        current_date = start_date
        while current_date <= end_date:
            # Count tasks remaining on this date
            remaining = sum(
                1 for task in project_tasks 
                if (task.created_at.date() <= current_date and 
                    (task.status != TaskStatus.COMPLETED or 
                     task.updated_at.date() > current_date))
            )
            
            dates.append(current_date.isoformat())
            remaining_tasks.append(remaining)
            current_date += timedelta(days=1)
            
        return {'dates': dates, 'remaining': remaining_tasks}

# Remove duplicate TaskManager class - using the first one
    

    
    def list_tasks(self, status: str = None, parent_id: str = None) -> List[Dict[str, Any]]:
        """List tasks with optional filtering"""
        try:
            filtered_tasks = []
            for task in self.tasks.values():
                # Apply status filter
                if status and task.status.value != status:
                    continue
                
                # Apply parent_id filter
                if parent_id and task.parent_id != parent_id:
                    continue
                
                filtered_tasks.append(task.to_dict())
            
            return filtered_tasks
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            return []
    
    def get_prioritized_tasks(self, limit: int = 10) -> List[Task]:
        """Get tasks sorted by priority score (highest first)"""
        try:
            # Get active tasks only
            active_tasks = [t for t in self.tasks.values() 
                          if t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]]
            
            # Update priorities for all tasks
            for task in active_tasks:
                task.dynamic_priority_score = task._calculate_dynamic_priority()
            
            # Sort by priority score (highest first)
            prioritized = sorted(active_tasks, 
                               key=lambda t: t.dynamic_priority_score, 
                               reverse=True)
            
            return prioritized[:limit]
            
        except Exception as e:
            logger.error(f"Error getting prioritized tasks: {e}")
            return []

def manage_tasks(state):
    """Main function for task management agent"""
    print("---MANAGE TASKS---")
    user_query = state["user_query"]
    
    # If this is not actually a task-related request, redirect to general chat
    task_keywords = ['task', 'todo', 'to-do', 'create', 'add', 'list', 'manage', 'complete', 'finish']
    if not any(keyword in user_query.lower() for keyword in task_keywords):
        from agents.general_chat import general_chat
        return general_chat(state)
    
    try:
        task_manager = TaskManager()
        
        # Simple task creation for demo
        if "create" in user_query.lower() or "add" in user_query.lower():
            # Extract task title from query (simplified)
            title = user_query.replace("create task:", "").replace("add task:", "").replace("create", "").replace("add", "").strip()
            
            # Remove common prefixes
            if title.startswith("task:"):
                title = title[5:].strip()
            
            if title:
                task_id = task_manager.create_task(title)
                if task_id:
                    return {"response": f"Task created: '{title}' (ID: {task_id})"}
                else:
                    return {"response": "Failed to create task. Please try again."}
            else:
                return {"response": "Please provide a task title. Example: 'Create task: Finish report'"}
        
        return {"response": f"Task Manager: I have received your request to: {user_query}"}
        
    except Exception as e:
        logger.error(f"Error in manage_tasks: {e}")
        return {"response": "Task Manager: An error occurred while processing your request"}