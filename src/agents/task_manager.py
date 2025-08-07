from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
import uuid
import json
import os
import sqlite3
import threading
import re
import time
from collections import defaultdict, deque
from enum import Enum
import pickle
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Define database path relative to current file
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'task_manager.db')

# Ensure directory exists
Path(os.path.dirname(DB_PATH)).mkdir(parents=True, exist_ok=True)

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"
    REVIEW = "review"
    
    @classmethod
    def from_string(cls, status_str):
        try:
            return cls(status_str)
        except ValueError:
            return cls.PENDING

class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    
    @classmethod
    def from_int(cls, priority_int):
        for priority in cls:
            if priority.value == priority_int:
                return priority
        return cls.MEDIUM

class RecurrenceType(Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"

class Task:
    def __init__(self, 
                 title: str, 
                 description: str = "",
                 priority: Union[int, TaskPriority] = TaskPriority.MEDIUM,
                 status: Union[str, TaskStatus] = TaskStatus.PENDING,
                 parent_id: Optional[str] = None,
                 assigned_agent: Optional[str] = None,
                 dependencies: List[str] = None,
                 due_date: Optional[Union[str, datetime]] = None,
                 estimated_hours: float = 0.0,
                 tags: List[str] = None,
                 recurrence_type: Union[str, RecurrenceType] = RecurrenceType.NONE,
                 recurrence_interval: int = 1,
                 completion_criteria: List[str] = None):
        
        # Core attributes
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.parent_id = parent_id
        self.subtasks: List[str] = []  # List of task IDs
        
        # Handle priority conversion
        if isinstance(priority, int):
            self.priority = TaskPriority.from_int(priority)
        else:
            self.priority = priority
            
        # Handle status conversion
        if isinstance(status, str):
            self.status = TaskStatus.from_string(status)
        else:
            self.status = status
        
        # Assignment & dependencies
        self.assigned_agent = assigned_agent
        self.dependencies = dependencies or []
        
        # Tags
        self.tags = tags or []
        
        # Due date handling
        if isinstance(due_date, str) and due_date:
            try:
                self.due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            except ValueError:
                self.due_date = None
        else:
            self.due_date = due_date
            
        # Progress tracking
        self.progress = 0  # Progress as percentage (0-100)
        
        # Time tracking
        self.estimated_hours = estimated_hours
        self.actual_hours = 0.0
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
        """Calculate a dynamic priority score based on multiple factors"""
        # Handle both enum and string priority values
        priority_val = self.priority.value if hasattr(self.priority, 'value') else self.priority
        if isinstance(priority_val, str):
            # Convert string priority to int
            priority_map = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            priority_val = priority_map.get(priority_val.lower(), 2)
            
        base_score = 5 - priority_val  # Convert to ascending score (higher = more important)
        
        # Factor 1: Due date proximity
        if self.due_date:
            days_until_due = max(-10, (self.due_date - datetime.now(timezone.utc)).days)
            if days_until_due < 0:  # Overdue
                due_factor = 3  # High boost for overdue
            elif days_until_due == 0:  # Due today
                due_factor = 2
            elif days_until_due <= 2:  # Due in next 2 days
                due_factor = 1.5
            elif days_until_due <= 7:  # Due this week
                due_factor = 1
            else:
                due_factor = 0
            base_score += due_factor
            
        # Factor 2: Dependency chain length (how many tasks depend on this)
        dependency_factor = len(self.subtasks) * 0.2
        base_score += dependency_factor
        
        # Factor 3: Status adjustment
        # Handle both enum and string status values
        status_val = self.status.value if hasattr(self.status, 'value') else self.status
        if status_val == 'blocked':
            base_score -= 1  # Lower priority for blocked tasks
        elif status_val == 'in_progress':
            base_score += 0.5  # Slight boost for in-progress tasks
            
        return round(base_score, 2)
    
    def _calculate_next_occurrence(self) -> Optional[datetime]:
        """Calculate the next occurrence date based on recurrence settings"""
        if self.recurrence_type == RecurrenceType.NONE or not self.due_date:
            return None
            
        base_date = self.due_date
        
        if self.recurrence_type == RecurrenceType.DAILY:
            return base_date + timedelta(days=self.recurrence_interval)
        elif self.recurrence_type == RecurrenceType.WEEKLY:
            return base_date + timedelta(weeks=self.recurrence_interval)
        elif self.recurrence_type == RecurrenceType.MONTHLY:
            # Simple approximation of months
            return base_date + timedelta(days=30 * self.recurrence_interval)
        elif self.recurrence_type == RecurrenceType.YEARLY:
            # Simple approximation of years
            return base_date + timedelta(days=365 * self.recurrence_interval)
        else:
            return None
    
    def update_dynamic_priority(self) -> float:
        """Recalculate and update the dynamic priority score"""
        self.dynamic_priority_score = self._calculate_dynamic_priority()
        return self.dynamic_priority_score
    
    def is_overdue(self) -> bool:
        """Check if the task is overdue"""
        if not self.due_date:
            return False
        return datetime.now(timezone.utc) > self.due_date
    
    def days_until_due(self) -> Optional[int]:
        """Get the number of days until the due date"""
        if not self.due_date:
            return None
        return (self.due_date - datetime.now(timezone.utc)).days
    
    def add_milestone(self, title: str, description: str = "") -> str:
        """Add a milestone to the task"""
        milestone_id = str(uuid.uuid4())
        self.milestones.append({
            'id': milestone_id,
            'title': title,
            'description': description,
            'completed': False,
            'completed_at': None
        })
        return milestone_id
        
    def complete_milestone(self, milestone_id: str) -> bool:
        """Mark a milestone as completed"""
        for milestone in self.milestones:
            if milestone['id'] == milestone_id:
                milestone['completed'] = True
                milestone['completed_at'] = datetime.now(timezone.utc).isoformat()
                self._update_progress_from_milestones()
                return True
        return False
    
    def _update_progress_from_milestones(self):
        """Update overall progress based on milestone completion"""
        if not self.milestones:
            return
            
        completed = sum(1 for m in self.milestones if m['completed'])
        total = len(self.milestones)
        self.progress = int((completed / total) * 100)
        
        # If all milestones are complete, mark task as complete
        if self.progress == 100 and self.status != TaskStatus.COMPLETED:
            self.status = TaskStatus.COMPLETED
    
    def start_time_tracking(self):
        """Start time tracking for this task"""
        if not self.started_at:  # Only start if not already started
            self.started_at = datetime.now(timezone.utc)
    
    def stop_time_tracking(self):
        """Stop time tracking and record the time entry"""
        if self.started_at:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - self.started_at).total_seconds() / 3600  # in hours
            
            # Record the time entry
            self.time_entries.append({
                'start': self.started_at.isoformat(),
                'end': end_time.isoformat(),
                'duration': round(duration, 2)
            })
            
            # Update actual hours
            self.actual_hours += round(duration, 2)
            self.started_at = None
    
    def add_notification(self, message: str, notification_type: str = "info"):
        """Add a notification for this task"""
        self.notifications.append({
            'id': str(uuid.uuid4()),
            'message': message,
            'type': notification_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'read': False
        })
    
    def create_recurring_instance(self) -> 'Task':
        """Create a new instance of this task for recurring tasks"""
        if self.recurrence_type == RecurrenceType.NONE or not self.next_occurrence:
            return None
            
        # Create a new task with the same properties
        new_task = Task(
            title=self.title,
            description=self.description,
            priority=self.priority,
            assigned_agent=self.assigned_agent,
            dependencies=self.dependencies.copy(),
            due_date=self.next_occurrence,
            estimated_hours=self.estimated_hours,
            tags=self.tags.copy(),
            recurrence_type=self.recurrence_type,
            recurrence_interval=self.recurrence_interval,
            completion_criteria=self.completion_criteria.copy() if self.completion_criteria else None
        )
        
        # Copy milestones but reset completion
        for milestone in self.milestones:
            new_task.add_milestone(milestone['title'], milestone['description'])
            
        return new_task
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority.value if hasattr(self.priority, 'value') else self.priority,
            'status': self.status.value if hasattr(self.status, 'value') else self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'parent_id': self.parent_id,
            'assigned_agent': self.assigned_agent,
            'dependencies': self.dependencies,
            'subtasks': self.subtasks,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'progress': self.progress,
            'dynamic_priority_score': self.dynamic_priority_score,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'time_entries': self.time_entries,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'tags': self.tags,
            'recurrence_type': self.recurrence_type.value if hasattr(self.recurrence_type, 'value') else self.recurrence_type,
            'recurrence_interval': self.recurrence_interval,
            'next_occurrence': self.next_occurrence.isoformat() if self.next_occurrence else None,
            'completion_criteria': self.completion_criteria,
            'quality_score': self.quality_score,
            'milestones': self.milestones,
            'notifications': self.notifications,
            'view_count': self.view_count,
            'modification_count': self.modification_count
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create a Task instance from a dictionary"""
        # Initialize with required fields
        task = cls(title=data['title'])
        
        # Core attributes
        task.id = data['id']
        task.description = data.get('description', '')
        
        # Handle priority and status
        priority_val = data.get('priority', 2)
        if isinstance(priority_val, str):
            # Convert string priority to int
            priority_map = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            priority_val = priority_map.get(priority_val.lower(), 2)
        task.priority = TaskPriority.from_int(priority_val)
        
        status_val = data.get('status', 'pending')
        task.status = TaskStatus.from_string(status_val)
        
        # Timestamps
        task.created_at = datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(timezone.utc)
        task.updated_at = datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.now(timezone.utc)
        
        # Relationships
        task.parent_id = data.get('parent_id')
        task.assigned_agent = data.get('assigned_agent')
        task.dependencies = data.get('dependencies', [])
        task.subtasks = data.get('subtasks', [])
        
        # Due date
        if data.get('due_date'):
            try:
                task.due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                task.due_date = None
        else:
            task.due_date = None
            
        # Progress
        task.progress = data.get('progress', 0)
        task.dynamic_priority_score = data.get('dynamic_priority_score', 0)
        
        # Time tracking
        task.estimated_hours = data.get('estimated_hours', 0.0)
        task.actual_hours = data.get('actual_hours', 0.0)
        task.time_entries = data.get('time_entries', [])
        
        if data.get('started_at'):
            try:
                task.started_at = datetime.fromisoformat(data['started_at'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                task.started_at = None
        else:
            task.started_at = None
        
        # Tags
        task.tags = data.get('tags', [])
        
        # Recurrence
        rec_type = data.get('recurrence_type', 'none')
        if isinstance(rec_type, str):
            try:
                task.recurrence_type = RecurrenceType(rec_type)
            except ValueError:
                task.recurrence_type = RecurrenceType.NONE
        else:
            task.recurrence_type = rec_type if isinstance(rec_type, RecurrenceType) else RecurrenceType.NONE
            
        task.recurrence_interval = data.get('recurrence_interval', 1)
        
        if data.get('next_occurrence'):
            try:
                task.next_occurrence = datetime.fromisoformat(data['next_occurrence'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                task.next_occurrence = None
        else:
            task.next_occurrence = None
        
        # Quality and completion
        task.completion_criteria = data.get('completion_criteria', [])
        task.quality_score = data.get('quality_score', 0.0)
        
        # Analytics
        task.view_count = data.get('view_count', 0)
        task.modification_count = data.get('modification_count', 0)
        
        # Milestones and notifications
        task.milestones = data.get('milestones', [])
        task.notifications = data.get('notifications', [])
        
        return task

class DatabaseManager:
    """Handles SQLite database operations for task persistence"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority INTEGER,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    parent_id TEXT,
                    assigned_agent TEXT,
                    dependencies TEXT,  -- JSON array
                    subtasks TEXT,      -- JSON array
                    due_date TEXT,
                    progress INTEGER,
                    dynamic_priority_score REAL,
                    estimated_hours REAL,
                    actual_hours REAL,
                    time_entries TEXT,  -- JSON array
                    started_at TEXT,
                    tags TEXT,          -- JSON array
                    recurrence_type TEXT,
                    recurrence_interval INTEGER,
                    next_occurrence TEXT,
                    completion_criteria TEXT,  -- JSON array
                    quality_score REAL,
                    milestones TEXT,    -- JSON array
                    notifications TEXT, -- JSON array
                    view_count INTEGER,
                    modification_count INTEGER,
                    FOREIGN KEY (parent_id) REFERENCES tasks(id)
                )
            ''')
            
            # Create indexes for better query performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_priority ON tasks(priority)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_due_date ON tasks(due_date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_parent_id ON tasks(parent_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_assigned_agent ON tasks(assigned_agent)')
            
            # Create task templates table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS task_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    template_data TEXT,  -- JSON with task structure
                    created_at TEXT
                )
            ''')
            
            # Create performance metrics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id TEXT PRIMARY KEY,
                    metric_name TEXT,
                    metric_value REAL,
                    agent_name TEXT,
                    recorded_at TEXT
                )
            ''')
            
            conn.commit()
    
    def save_task(self, task: Task):
        """Save a task to the database"""
        with sqlite3.connect(self.db_path) as conn:
            task_dict = task.to_dict()
            
            # Convert arrays/objects to JSON strings for storage
            json_fields = ['dependencies', 'subtasks', 'time_entries', 'tags', 
                          'completion_criteria', 'milestones', 'notifications']
            
            for field in json_fields:
                task_dict[field] = json.dumps(task_dict.get(field, []))
            
            conn.execute('''
                INSERT OR REPLACE INTO tasks (
                    id, title, description, priority, status, created_at, updated_at,
                    parent_id, assigned_agent, dependencies, subtasks, due_date, 
                    progress, dynamic_priority_score, estimated_hours, actual_hours,
                    time_entries, started_at, tags, recurrence_type, recurrence_interval,
                    next_occurrence, completion_criteria, quality_score, milestones,
                    notifications, view_count, modification_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_dict['id'], task_dict['title'], task_dict['description'],
                task_dict['priority'], task_dict['status'], task_dict['created_at'],
                task_dict['updated_at'], task_dict['parent_id'], task_dict['assigned_agent'],
                task_dict['dependencies'], task_dict['subtasks'], task_dict['due_date'],
                task_dict['progress'], task_dict['dynamic_priority_score'],
                task_dict['estimated_hours'], task_dict['actual_hours'],
                task_dict['time_entries'], task_dict['started_at'], task_dict['tags'],
                task_dict['recurrence_type'], task_dict['recurrence_interval'],
                task_dict['next_occurrence'], task_dict['completion_criteria'],
                task_dict['quality_score'], task_dict['milestones'],
                task_dict['notifications'], task_dict['view_count'],
                task_dict['modification_count']
            ))
            conn.commit()
    
    def load_task(self, task_id: str) -> Optional[Task]:
        """Load a task from the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            # Convert row to dictionary
            columns = [desc[0] for desc in cursor.description]
            task_dict = dict(zip(columns, row))
            
            # Parse JSON fields
            json_fields = ['dependencies', 'subtasks', 'time_entries', 'tags',
                          'completion_criteria', 'milestones', 'notifications']
            
            for field in json_fields:
                if task_dict.get(field):
                    try:
                        task_dict[field] = json.loads(task_dict[field])
                    except json.JSONDecodeError:
                        task_dict[field] = []
                else:
                    task_dict[field] = []
            
            return Task.from_dict(task_dict)
    
    def load_all_tasks(self) -> Dict[str, Task]:
        """Load all tasks from the database"""
        tasks = {}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT * FROM tasks')
            columns = [desc[0] for desc in cursor.description]
            
            for row in cursor.fetchall():
                task_dict = dict(zip(columns, row))
                
                # Parse JSON fields
                json_fields = ['dependencies', 'subtasks', 'time_entries', 'tags',
                              'completion_criteria', 'milestones', 'notifications']
                
                for field in json_fields:
                    if task_dict.get(field):
                        try:
                            task_dict[field] = json.loads(task_dict[field])
                        except json.JSONDecodeError:
                            task_dict[field] = []
                    else:
                        task_dict[field] = []
                
                task = Task.from_dict(task_dict)
                tasks[task.id] = task
                
        return tasks
    
    def delete_task(self, task_id: str):
        """Delete a task from the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            conn.commit()
    
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

class TaskManager:
    """Enhanced Task Manager with advanced features"""
    
    def __init__(self, supervisor=None):
        self.tasks: Dict[str, Task] = {}
        self.supervisor = supervisor
        self.db_manager = DatabaseManager()
        self.analytics = TaskAnalytics(self)
        self._lock = threading.Lock()
        
        # Load existing tasks from database
        self._load_tasks_from_db()
        
        # Task templates
        self.task_templates = {}
        
        # Notification system
        self.notification_queue = deque()
        
        # Start background processes
        self._start_background_processes()
    
    def _load_tasks_from_db(self):
        """Load all tasks from the database on startup"""
        try:
            self.tasks = self.db_manager.load_all_tasks()
            print(f"Loaded {len(self.tasks)} tasks from database")
        except Exception as e:
            print(f"Error loading tasks from database: {e}")
            self.tasks = {}
    
    def _start_background_processes(self):
        """Start background threads for maintenance tasks"""
        # Start notification checker
        notification_thread = threading.Thread(target=self._notification_checker, daemon=True)
        notification_thread.start()
        
        # Start recurring task scheduler
        scheduler_thread = threading.Thread(target=self._recurring_task_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Start priority updater
        priority_thread = threading.Thread(target=self._priority_updater, daemon=True)
        priority_thread.start()
    
    def _notification_checker(self):
        """Background process to check for notifications"""
        while True:
            try:
                self._check_deadline_notifications()
                self._check_stuck_tasks()
                time.sleep(300)  # Check every 5 minutes
            except Exception as e:
                print(f"Error in notification checker: {e}")
                time.sleep(60)
    
    def _recurring_task_scheduler(self):
        """Background process to handle recurring tasks"""
        while True:
            try:
                self._process_recurring_tasks()
                time.sleep(3600)  # Check every hour
            except Exception as e:
                print(f"Error in recurring task scheduler: {e}")
                time.sleep(300)
    
    def _priority_updater(self):
        """Background process to update dynamic priorities"""
        while True:
            try:
                self._update_all_priorities()
                time.sleep(1800)  # Update every 30 minutes
            except Exception as e:
                print(f"Error in priority updater: {e}")
                time.sleep(300)
    
    def _check_deadline_notifications(self):
        """Check for approaching deadlines and create notifications"""
        now = datetime.now(timezone.utc)
        
        for task in self.tasks.values():
            if not task.due_date or task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                continue
                
            days_until_due = (task.due_date - now).days
            
            # Create notifications for different time thresholds
            if days_until_due < 0:  # Overdue
                task.add_notification(
                    f"Task '{task.title}' is {abs(days_until_due)} days overdue!",
                    "error"
                )
            elif days_until_due == 0:  # Due today
                task.add_notification(
                    f"Task '{task.title}' is due today!",
                    "warning"
                )
            elif days_until_due == 1:  # Due tomorrow
                task.add_notification(
                    f"Task '{task.title}' is due tomorrow",
                    "info"
                )
    
    def _check_stuck_tasks(self):
        """Check for tasks that haven't been updated in a while"""
        now = datetime.now(timezone.utc)
        stuck_threshold = timedelta(days=3)
        
        for task in self.tasks.values():
            if (task.status == TaskStatus.IN_PROGRESS and 
                now - task.updated_at > stuck_threshold):
                task.add_notification(
                    f"Task '{task.title}' has been in progress for {(now - task.updated_at).days} days without updates",
                    "warning"
                )
    
    def _process_recurring_tasks(self):
        """Process recurring tasks and create new instances if needed"""
        now = datetime.now(timezone.utc)
        
        for task in list(self.tasks.values()):
            if (task.recurrence_type != RecurrenceType.NONE and 
                task.status == TaskStatus.COMPLETED and
                task.next_occurrence and
                now >= task.next_occurrence):
                
                # Create new recurring instance
                new_task = task.create_recurring_instance()
                if new_task:
                    self.tasks[new_task.id] = new_task
                    self.db_manager.save_task(new_task)
                    
                    # Update the original task's next occurrence
                    task.next_occurrence = task._calculate_next_occurrence()
                    self.db_manager.save_task(task)
    
    def _update_all_priorities(self):
        """Update dynamic priorities for all tasks"""
        with self._lock:
            for task in self.tasks.values():
                if task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                    task.update_dynamic_priority()
                    # Save to database periodically
                    if task.modification_count % 5 == 0:  # Save every 5 modifications
                        self.db_manager.save_task(task)
        
    def create_task(self, title: str, **kwargs) -> Optional[Task]:
        """
        Create a new task and add it to the supervisor's queue if available
        
        Args:
            title: The title of the task
            **kwargs: Additional task attributes
            
        Returns:
            The created task if successful, None otherwise
        """
        try:
            # Extract add_to_queue parameter before creating the Task object
            add_to_queue = kwargs.pop('add_to_queue', True) if 'add_to_queue' in kwargs else True
            
            task = Task(title, **kwargs)
            self.tasks[task.id] = task
            
            # If this is a subtask, add it to the parent's subtasks list
            if task.parent_id and task.parent_id in self.tasks:
                self.tasks[task.parent_id].subtasks.append(task.id)
                
            # Only add to supervisor queue if explicitly requested and not a subtask
            if self.supervisor is not None and add_to_queue and not task.parent_id:
                task_data = {
                    'id': task.id,
                    'query': task.title,
                    'description': task.description,
                    'priority': task.priority,
                    'parent_id': task.parent_id,
                    'dependencies': task.dependencies,
                    'status': task.status,
                    'type': 'task'  # Explicitly mark as a task type
                }
                self.supervisor.add_task(task_data)
                
            return task
            
        except Exception as e:
            print(f"Error creating task: {e}")
            return None
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        """
        Update a task with new attributes
        
        Args:
            task_id: The ID of the task to update
            **kwargs: New attribute values
            
        Returns:
            True if successful, False otherwise
        """
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        
        # Update task attributes
        for key, value in kwargs.items():
            if hasattr(task, key) and key != 'id':
                setattr(task, key, value)
                
        # Update the timestamp
        task.updated_at = datetime.now(timezone.utc)
        
        return True
        
    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task and its subtasks
        
        Args:
            task_id: The ID of the task to delete
            
        Returns:
            True if successful, False otherwise
        """
        if task_id not in self.tasks:
            return False
            
        # Get the task
        task = self.tasks[task_id]
        
        # Remove this task from its parent's subtasks list
        if task.parent_id and task.parent_id in self.tasks:
            if task_id in self.tasks[task.parent_id].subtasks:
                self.tasks[task.parent_id].subtasks.remove(task_id)
                
        # Delete all subtasks recursively
        for subtask_id in list(task.subtasks):  # Create a copy of the list to avoid modification during iteration
            self.delete_task(subtask_id)
            
        # Delete the task
        del self.tasks[task_id]
        
        return True
        
    def break_down_task(self, complex_goal: str) -> List[Task]:
        """
        Break down a complex goal into subtasks using LLM and add them to the task queue
        
        Args:
            complex_goal: The main goal to break down into subtasks
            
        Returns:
            List[Task]: A list containing the parent task and its subtasks
            
        Note:
            All created subtasks will be automatically added to the supervisor's queue
        """
        # Create the parent task
        parent_task = self.create_task(complex_goal, status="in_progress")
        
        try:
            # Generate subtasks using LLM
            prompt = f"""
            You are an expert at breaking down complex goals into actionable subtasks.
            Break down the following goal into 3-7 specific, actionable subtasks:
            
            GOAL: {complex_goal}
            
            Provide the subtasks in the following JSON format:
            {{
                "subtasks": [
                    {{"title": "Subtask 1", "description": "Detailed description of what needs to be done"}},
                    {{"title": "Subtask 2", "description": "Detailed description of what needs to be done"}}
                ]
            }}
            
            Make sure each subtask is:
            1. Specific and actionable
            2. Has a clear outcome
            3. Can be completed independently
            4. Is in logical order
            
            Only respond with the JSON, no other text.
            """
            
            # Call the LLM
            completion = client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that breaks down complex goals into actionable subtasks."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            try:
                response = json.loads(completion.choices[0].message.content)
                subtask_data = response.get("subtasks", [])
                
                if not subtask_data:
                    raise ValueError("No subtasks were generated")
                    
                subtasks = []
                for subtask in subtask_data:
                    title = subtask.get("title", "")
                    description = subtask.get("description", "")
                    if title:  # Only add if we have at least a title
                        subtask = self.create_task(
                            title=title,
                            description=description,
                            parent_id=parent_task.id,
                            status="pending",
                            add_to_queue=False  # Don't add subtasks to queue automatically
                        )
                        subtasks.append(subtask)
                
                if not subtasks:
                    raise ValueError("Failed to generate valid subtasks")
                    
                return [parent_task] + subtasks
                
            except json.JSONDecodeError as e:
                print(f"Error parsing LLM response: {e}")
                # Fallback to default behavior if JSON parsing fails
                
        except Exception as e:
            print(f"Error generating subtasks with LLM: {e}")
            # Fallback to default behavior if LLM call fails
        
        # Fallback to default behavior if LLM fails
        subtask_titles = [
            f"Research {complex_goal}",
            f"Plan {complex_goal}",
            f"Execute {complex_goal}"
        ]
        
        subtasks = []
        for title in subtask_titles:
            subtask = self.create_task(title, parent_id=parent_task.id, add_to_queue=False)
            subtasks.append(subtask)
            
        return [parent_task] + subtasks
        
    def assign_agent(self, task_id: str, agent_name: str) -> bool:
        """Assign a task to a specific agent"""
        if task_id in self.tasks and (self.supervisor is None or agent_name in self.supervisor.agents):
            self.tasks[task_id].assigned_agent = agent_name
            self.tasks[task_id].status = "assigned"
            self.tasks[task_id].updated_at = datetime.now(timezone.utc)
            return True
        return False
        
    def update_task_status(self, task_id: str, status: str) -> bool:
        """Update task status"""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            self.tasks[task_id].updated_at = datetime.now(timezone.utc)
            return True
        return False
    
    def update_task_progress(self, task_id: str, progress: int) -> bool:
        """Update task progress percentage (0-100)"""
        if task_id in self.tasks:
            # Ensure progress is between 0 and 100
            progress = max(0, min(100, progress))
            self.tasks[task_id].progress = progress
            
            # If progress is 100%, update status to completed
            if progress == 100:
                self.tasks[task_id].status = "completed"
                
            self.tasks[task_id].updated_at = datetime.now(timezone.utc)
            return True
        return False
        
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self.tasks.get(task_id)
        
    def list_tasks(self, status: str = None, parent_id: str = None) -> List[Dict[str, Any]]:
        """List all tasks, optionally filtered by status and/or parent_id"""
        tasks = self.tasks.values()
        
        # Apply filters
        if status:
            tasks = [t for t in tasks if t.status == status]
        if parent_id:
            tasks = [t for t in tasks if t.parent_id == parent_id]
        elif parent_id == "":
            # If parent_id is empty string, return only top-level tasks
            tasks = [t for t in tasks if t.parent_id is None]
            
        return [t.to_dict() for t in tasks]
    
    # ===== ENHANCED FEATURES =====
    
    def search_tasks(self, query: str, search_fields: List[str] = None) -> List[Task]:
        """Full-text search across tasks"""
        if not query.strip():
            return list(self.tasks.values())
            
        search_fields = search_fields or ['title', 'description', 'tags']
        query_lower = query.lower()
        matching_tasks = []
        
        for task in self.tasks.values():
            # Increment view count
            task.view_count += 1
            
            # Check each search field
            for field in search_fields:
                field_value = getattr(task, field, None)
                if field_value:
                    if isinstance(field_value, str) and query_lower in field_value.lower():
                        matching_tasks.append(task)
                        break
                    elif isinstance(field_value, list):
                        # For tags and other list fields
                        if any(query_lower in str(item).lower() for item in field_value):
                            matching_tasks.append(task)
                            break
                            
        return matching_tasks
    
    def get_tasks_by_priority(self, sort_by_dynamic: bool = True) -> List[Task]:
        """Get tasks sorted by priority (dynamic or static)"""
        tasks = list(self.tasks.values())
        
        if sort_by_dynamic:
            # Sort by dynamic priority score (higher = more important)
            return sorted(tasks, key=lambda t: t.dynamic_priority_score, reverse=True)
        else:
            # Sort by static priority (lower enum value = higher priority)
            return sorted(tasks, key=lambda t: t.priority.value)
    
    def get_tasks_by_deadline(self, include_completed: bool = False) -> List[Task]:
        """Get tasks sorted by deadline (earliest first)"""
        tasks = list(self.tasks.values())
        
        if not include_completed:
            tasks = [t for t in tasks if t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]]
            
        # Filter tasks with due dates and sort
        tasks_with_dates = [t for t in tasks if t.due_date]
        return sorted(tasks_with_dates, key=lambda t: t.due_date)
    
    def validate_dependencies(self, task_id: str) -> Tuple[bool, List[str]]:
        """Validate task dependencies and detect circular dependencies"""
        if task_id not in self.tasks:
            return False, ["Task not found"]
            
        errors = []
        visited = set()
        rec_stack = set()
        
        def has_cycle(task_id: str) -> bool:
            if task_id in rec_stack:
                return True
            if task_id in visited:
                return False
                
            visited.add(task_id)
            rec_stack.add(task_id)
            
            task = self.tasks.get(task_id)
            if task:
                for dep_id in task.dependencies:
                    if dep_id not in self.tasks:
                        errors.append(f"Dependency '{dep_id}' not found")
                    elif has_cycle(dep_id):
                        return True
                        
            rec_stack.remove(task_id)
            return False
            
        has_circular = has_cycle(task_id)
        if has_circular:
            errors.append("Circular dependency detected")
            
        return len(errors) == 0, errors
    
    def check_task_readiness(self, task_id: str) -> Tuple[bool, List[str]]:
        """Check if a task is ready to start based on dependencies"""
        if task_id not in self.tasks:
            return False, ["Task not found"]
            
        task = self.tasks[task_id]
        blocking_tasks = []
        
        for dep_id in task.dependencies:
            if dep_id in self.tasks:
                dep_task = self.tasks[dep_id]
                if dep_task.status != TaskStatus.COMPLETED:
                    blocking_tasks.append(f"'{dep_task.title}' (Status: {dep_task.status.value})")
            else:
                blocking_tasks.append(f"Missing dependency: {dep_id}")
                
        return len(blocking_tasks) == 0, blocking_tasks
    
    def auto_prioritize_tasks(self) -> int:
        """Automatically adjust task priorities based on AI analysis"""
        try:
            # Get current task summary
            task_summaries = []
            for task in self.tasks.values():
                if task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                    summary = {
                        'id': task.id,
                        'title': task.title,
                        'current_priority': task.priority.value,
                        'due_date': task.due_date.isoformat() if task.due_date else None,
                        'dependencies': len(task.dependencies),
                        'subtasks': len(task.subtasks),
                        'tags': task.tags
                    }
                    task_summaries.append(summary)
            
            if not task_summaries:
                return 0
                
            # Use AI to analyze and suggest priority changes
            prompt = f"""
            You are an expert task prioritization assistant. Analyze the following tasks and suggest priority levels (0=CRITICAL, 1=HIGH, 2=MEDIUM, 3=LOW) based on:
            1. Due date proximity
            2. Number of dependent tasks
            3. Task complexity and importance
            4. Tags that might indicate urgency
            
            Current tasks:
            {json.dumps(task_summaries, indent=2)}
            
            Respond with JSON in this format:
            {{
                "priority_changes": [
                    {{"task_id": "abc123", "new_priority": 1, "reason": "High importance due to dependencies"}}
                ]
            }}
            
            Only suggest changes where the new priority differs from current priority.
            """
            
            completion = client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=[
                    {"role": "system", "content": "You are an expert task management assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            response = json.loads(completion.choices[0].message.content)
            changes_made = 0
            
            for change in response.get('priority_changes', []):
                task_id = change.get('task_id')
                new_priority = change.get('new_priority')
                reason = change.get('reason', 'AI suggestion')
                
                if task_id in self.tasks and isinstance(new_priority, int) and 0 <= new_priority <= 3:
                    task = self.tasks[task_id]
                    old_priority = task.priority.value
                    
                    if old_priority != new_priority:
                        task.priority = TaskPriority.from_int(new_priority)
                        task.add_notification(f"Priority changed from {old_priority} to {new_priority}: {reason}", "info")
                        task.updated_at = datetime.now(timezone.utc)
                        changes_made += 1
                        
            return changes_made
            
        except Exception as e:
            print(f"Error in auto-prioritization: {e}")
            return 0
    
    def create_task_template(self, name: str, task_structure: Dict[str, Any]) -> str:
        """Create a reusable task template"""
        template_id = str(uuid.uuid4())
        template = {
            'id': template_id,
            'name': name,
            'description': task_structure.get('description', ''),
            'template_data': task_structure,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        self.task_templates[template_id] = template
        
        # Convert enums to serializable format for JSON storage
        serializable_structure = {}
        for key, value in task_structure.items():
            if isinstance(value, (TaskPriority, TaskStatus, RecurrenceType)):
                serializable_structure[key] = value.value
            else:
                serializable_structure[key] = value
        
        # Save to database
        with sqlite3.connect(self.db_manager.db_path) as conn:
            conn.execute(
                'INSERT INTO task_templates (id, name, description, template_data, created_at) VALUES (?, ?, ?, ?, ?)',
                (template_id, name, template['description'], json.dumps(serializable_structure), template['created_at'])
            )
            conn.commit()
            
        return template_id
    
    def create_task_from_template(self, template_id: str, overrides: Dict[str, Any] = None) -> Optional[Task]:
        """Create a new task from a template"""
        if template_id not in self.task_templates:
            return None
            
        template = self.task_templates[template_id]
        task_data = template['template_data'].copy()
        
        # Apply any overrides
        if overrides:
            task_data.update(overrides)
            
        return self.create_task(**task_data)
    
    def bulk_update_tasks(self, task_ids: List[str], updates: Dict[str, Any]) -> int:
        """Update multiple tasks at once"""
        updated_count = 0
        
        for task_id in task_ids:
            if self.update_task(task_id, **updates):
                # Save to database
                if task_id in self.tasks:
                    self.db_manager.save_task(self.tasks[task_id])
                updated_count += 1
                
        return updated_count
    
    def get_task_analytics_summary(self) -> Dict[str, Any]:
        """Get a comprehensive analytics summary"""
        total_tasks = len(self.tasks)
        status_counts = defaultdict(int)
        priority_counts = defaultdict(int)
        overdue_count = 0
        
        for task in self.tasks.values():
            # Handle both enum and string values
            status_val = task.status.value if hasattr(task.status, 'value') else task.status
            priority_val = task.priority.value if hasattr(task.priority, 'value') else task.priority
            
            status_counts[status_val] += 1
            priority_counts[priority_val] += 1
            if task.is_overdue():
                overdue_count += 1
                
        return {
            'total_tasks': total_tasks,
            'status_breakdown': dict(status_counts),
            'priority_breakdown': dict(priority_counts),
            'overdue_tasks': overdue_count,
            'completion_velocity': self.analytics.get_completion_velocity(),
            'agent_performance': self.analytics.get_agent_performance()
        }
    
    def export_tasks_to_json(self, file_path: str, include_completed: bool = True) -> bool:
        """Export tasks to JSON file"""
        try:
            tasks_to_export = []
            
            for task in self.tasks.values():
                # Handle both enum and string status values
                task_status = task.status.value if hasattr(task.status, 'value') else task.status
                if include_completed or task_status != 'completed':
                    tasks_to_export.append(task.to_dict())
                    
            export_data = {
                'exported_at': datetime.now(timezone.utc).isoformat(),
                'total_tasks': len(tasks_to_export),
                'tasks': tasks_to_export
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            print(f"Error exporting tasks: {e}")
            return False
    
    def import_tasks_from_json(self, file_path: str) -> Tuple[int, int]:
        """Import tasks from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            imported_count = 0
            error_count = 0
            
            for task_data in data.get('tasks', []):
                try:
                    # Check if task already exists
                    if task_data.get('id') not in self.tasks:
                        task = Task.from_dict(task_data)
                        self.tasks[task.id] = task
                        self.db_manager.save_task(task)
                        imported_count += 1
                except Exception as e:
                    print(f"Error importing task {task_data.get('id', 'unknown')}: {e}")
                    error_count += 1
                    
            return imported_count, error_count
            
        except Exception as e:
            print(f"Error importing tasks: {e}")
            return 0, 1
    
    def save_to_database(self, task: Task):
        """Save a single task to database"""
        self.db_manager.save_task(task)
    
    def backup_data(self, backup_path: str = None) -> bool:
        """Create a backup of all task data"""
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"task_backup_{timestamp}.db"
                
            self.db_manager.backup_database(backup_path)
            return True
            
        except Exception as e:
            print(f"Error creating backup: {e}")
            return False
    
    def get_natural_language_summary(self, task_ids: List[str] = None) -> str:
        """Generate a natural language summary of tasks using AI"""
        try:
            # Get tasks to summarize
            if task_ids:
                tasks_to_summarize = [self.tasks[tid] for tid in task_ids if tid in self.tasks]
            else:
                tasks_to_summarize = []
                for t in self.tasks.values():
                    # Handle both enum and string status values
                    task_status = t.status.value if hasattr(t.status, 'value') else t.status
                    if task_status not in ['completed', 'cancelled']:
                        tasks_to_summarize.append(t)
                                    
            if not tasks_to_summarize:
                return "No active tasks found."
                
            # Prepare task data for AI
            task_data = []
            for task in tasks_to_summarize[:20]:  # Limit to 20 tasks to avoid token limits
                # Handle both enum and string values safely
                status_val = task.status.value if hasattr(task.status, 'value') else task.status
                priority_val = task.priority.value if hasattr(task.priority, 'value') else task.priority
                
                task_info = {
                    'title': task.title,
                    'status': status_val,
                    'priority': priority_val,
                    'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else 'No deadline',
                    'progress': task.progress,
                    'assigned_agent': task.assigned_agent or 'Unassigned'
                }
                task_data.append(task_info)
                
            prompt = f"""
            Create a natural language summary of the current task situation. Focus on:
            1. Overall progress and workload
            2. High priority or overdue items
            3. Task distribution across agents
            4. Any concerning patterns or recommendations
            
            Current tasks:
            {json.dumps(task_data, indent=2)}
            
            Provide a concise, informative summary in 2-3 paragraphs.
            """
            
            completion = client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=[
                    {"role": "system", "content": "You are a helpful task management assistant that provides clear, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Get the raw response and clean it
            raw_response = completion.choices[0].message.content.strip()
            
            # Remove any <think>...</think> blocks that might appear in the response
            import re
            cleaned_response = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL)
            cleaned_response = re.sub(r'\*\*[^*]+\*\*\s*$', '', cleaned_response)  # Remove trailing bold formatting
            cleaned_response = cleaned_response.strip()
            
            return cleaned_response
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            # Count active tasks safely
            active_count = 0
            for t in self.tasks.values():
                task_status = t.status.value if hasattr(t.status, 'value') else t.status
                if task_status not in ['completed', 'cancelled']:
                    active_count += 1
            return f"Summary unavailable. Active tasks: {active_count}"
    
    def cleanup_old_notifications(self, days_old: int = 7):
        """Remove old read notifications"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        for task in self.tasks.values():
            original_count = len(task.notifications)
            task.notifications = [
                notif for notif in task.notifications 
                if not notif.get('read', False) or 
                   datetime.fromisoformat(notif['timestamp'].replace('Z', '+00:00')) >= cutoff_date
            ]
            
            # Save if notifications were removed
            if len(task.notifications) != original_count:
                self.db_manager.save_task(task)

def manage_tasks(state):
    """
    Manages tasks based on the user's query.
    This is kept for backward compatibility.
    """
    print("---MANAGE TASKS---")
    user_query = state["user_query"]
    return {"response": f"Task Manager: I have received your request to: {user_query}"}