import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

class TaskStorage:
    """Simple JSON-based task storage system"""
    
    def __init__(self, storage_path: str = "data/tasks.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(exist_ok=True)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Ensure the storage file exists with proper structure"""
        if not self.storage_path.exists():
            initial_data = {
                "tasks": [],
                "next_id": 1,
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0"
                }
            }
            self.save_data(initial_data)
    
    def load_data(self) -> Dict[str, Any]:
        """Load all task data from storage"""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"tasks": [], "next_id": 1, "metadata": {}}
    
    def save_data(self, data: Dict[str, Any]):
        """Save all task data to storage"""
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks"""
        data = self.load_data()
        return data.get("tasks", [])
    
    def get_task_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID"""
        tasks = self.get_all_tasks()
        return next((task for task in tasks if task.get("id") == task_id), None)
    
    def add_task(self, task: Dict[str, Any]) -> int:
        """Add a new task and return its ID"""
        data = self.load_data()
        task["id"] = data["next_id"]
        task["created_at"] = datetime.now().isoformat()
        
        data["tasks"].append(task)
        data["next_id"] += 1
        
        self.save_data(data)
        return task["id"]
    
    def update_task(self, task_id: int, updates: Dict[str, Any]) -> bool:
        """Update a task by ID"""
        data = self.load_data()
        task = next((t for t in data["tasks"] if t.get("id") == task_id), None)
        
        if not task:
            return False
        
        task.update(updates)
        task["updated_at"] = datetime.now().isoformat()
        
        self.save_data(data)
        return True
    
    def delete_task(self, task_id: int) -> bool:
        """Delete a task by ID"""
        data = self.load_data()
        original_count = len(data["tasks"])
        
        data["tasks"] = [t for t in data["tasks"] if t.get("id") != task_id]
        
        if len(data["tasks"]) < original_count:
            self.save_data(data)
            return True
        return False
    
    def get_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get tasks filtered by status"""
        tasks = self.get_all_tasks()
        return [task for task in tasks if task.get("status") == status]
    
    def get_tasks_by_priority(self, priority: str) -> List[Dict[str, Any]]:
        """Get tasks filtered by priority"""
        tasks = self.get_all_tasks()
        return [task for task in tasks if task.get("priority") == priority]
    
    def backup_data(self, backup_path: str = None) -> str:
        """Create a backup of the task data"""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"data/tasks_backup_{timestamp}.json"
        
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(exist_ok=True)
        
        data = self.load_data()
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        
        return str(backup_path)