from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uuid
import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class Task:
    def __init__(self, 
                 title: str, 
                 description: str = "",
                 priority: int = 2,  # 1=high, 2=medium, 3=low
                 status: str = "pending",  # pending, in_progress, completed, blocked
                 parent_id: Optional[str] = None,
                 assigned_agent: Optional[str] = None,
                 dependencies: List[str] = None,
                 due_date: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.priority = priority
        self.status = status
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.parent_id = parent_id
        self.assigned_agent = assigned_agent
        self.dependencies = dependencies or []
        self.subtasks: List[str] = []  # List of task IDs
        self.due_date = due_date
        self.progress = 0  # Progress as percentage (0-100)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'parent_id': self.parent_id,
            'assigned_agent': self.assigned_agent,
            'dependencies': self.dependencies,
            'subtasks': self.subtasks,
            'due_date': self.due_date,
            'progress': self.progress
        }

class TaskManager:
    def __init__(self, supervisor=None):
        self.tasks: Dict[str, Task] = {}
        self.supervisor = supervisor
        
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
                
            # If we have a supervisor, add the task to its queue
            # Only add tasks to the queue if they don't have a parent (to prevent infinite loops)
            # or if they are explicitly marked for queuing
            if self.supervisor is not None and (not task.parent_id or add_to_queue):
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

def manage_tasks(state):
    """
    Manages tasks based on the user's query.
    This is kept for backward compatibility.
    """
    print("---MANAGE TASKS---")
    user_query = state["user_query"]
    return {"response": f"Task Manager: I have received your request to: {user_query}"}