# Task Manager - Compatibility Layer
# This file provides backward compatibility while using the new task agent system

from .task.task_agent import TaskAgent
from typing import Dict, Any

# Initialize the new task agent
task_agent = TaskAgent()

def manage_tasks(state: Dict[str, Any]) -> Dict[str, Any]:
    """Main function for task management - uses new TaskAgent"""
    print("---MANAGE TASKS---")
    return task_agent.process_request(state)