import logging
import sqlite3
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from collections import defaultdict
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
        """Calculate a dynamic priority score based on multiple factors"""
        try:
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

class TaskManager:
    def __init__(self, db_path: str = "tasks.db"):
        self.db_path = self._sanitize_path(db_path)
        self.tasks = {}
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
                    if key in valid_keys:
                        valid_params[key] = value
                
                task = Task(title=title.strip(), **valid_params)
                self.tasks[task.id] = task
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
            return None
        
        with self.lock:
            return self.tasks.get(task_id)
    
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
            add_to_queue = kwargs.pop('add_to_queue', True)
            
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
            
        with self.lock:
            return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update task with validation"""
        if not task_id or not updates:
            return False
            
        try:
            with self.lock:
                task = self.tasks.get(task_id)
                if not task:
                    return False
                
                # Validate and sanitize updates
                for key, value in updates.items():
                    if hasattr(task, key):
                        if key in ['title', 'description'] and isinstance(value, str):
                            setattr(task, key, html.escape(value))
                        else:
                            setattr(task, key, value)
                
                task.updated_at = datetime.now(timezone.utc)
                self._save_task(task)
                return True
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            return False
    
    def delete_task(self, task_id: str) -> bool:
        """Delete task with proper error handling"""
        if not task_id:
            return False
            
        try:
            with self.lock:
                if task_id in self.tasks:
                    del self.tasks[task_id]
                    
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
                    conn.commit()
                    
                logger.info(f"Task deleted: {task_id}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return False

    def break_down_task(self, complex_goal: str) -> List[Task]:
        """Break down a complex goal into subtasks"""
        try:
            # Simple task breakdown for demo
            main_task = Task(title=complex_goal, description=f"Main task: {complex_goal}")
            self.tasks[main_task.id] = main_task
            self._save_task(main_task)
            
            # Create some example subtasks
            subtasks = [
                Task(title=f"Research for {complex_goal}", description="Gather information"),
                Task(title=f"Create outline for {complex_goal}", description="Structure the content"),
                Task(title=f"Develop content for {complex_goal}", description="Create the actual content")
            ]
            
            for subtask in subtasks:
                subtask.parent_id = main_task.id
                main_task.subtasks.append(subtask.id)
                self.tasks[subtask.id] = subtask
                self._save_task(subtask)
            
            return [main_task] + subtasks
        except Exception as e:
            logger.error(f"Error breaking down task: {e}")
            return []
    
    def assign_agent(self, task_id: str, agent_name: str) -> bool:
        """Assign an agent to a task"""
        try:
            task = self.get_task(task_id)
            if task:
                task.assigned_agent = agent_name
                self._save_task(task)
                return True
            return False
        except Exception as e:
            logger.error(f"Error assigning agent to task {task_id}: {e}")
            return False
    
    def update_task_status(self, task_id: str, status: str) -> bool:
        """Update task status"""
        try:
            task = self.get_task(task_id)
            if task:
                if hasattr(TaskStatus, status.upper()):
                    task.status = TaskStatus(status)
                    task.updated_at = datetime.now(timezone.utc)
                    self._save_task(task)
                    return True
            return False
        except Exception as e:
            logger.error(f"Error updating task status {task_id}: {e}")
            return False
    
    def update_task_progress(self, task_id: str, progress: int) -> bool:
        """Update task progress"""
        try:
            task = self.get_task(task_id)
            if task:
                task.progress = max(0, min(100, progress))
                task.updated_at = datetime.now(timezone.utc)
                self._save_task(task)
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating task progress {task_id}: {e}")
            return False
    
    def save_to_database(self, task: Task) -> bool:
        """Save task to database (alias for _save_task)"""
        try:
            self._save_task(task)
            return True
        except Exception as e:
            logger.error(f"Error saving task to database: {e}")
            return False
    
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
            title = user_query.replace("create", "").replace("add", "").strip()
            if title:
                task_id = task_manager.create_task(title)
                if task_id:
                    return {"response": f"Task Manager: Created task '{title}' with ID: {task_id}"}
                else:
                    return {"response": "Task Manager: Failed to create task"}
            else:
                return {"response": "Task Manager: Please provide a task title"}
        
        return {"response": f"Task Manager: I have received your request to: {user_query}"}
        
    except Exception as e:
        logger.error(f"Error in manage_tasks: {e}")
        return {"response": "Task Manager: An error occurred while processing your request"}