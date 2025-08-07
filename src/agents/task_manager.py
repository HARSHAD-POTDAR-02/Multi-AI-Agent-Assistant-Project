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