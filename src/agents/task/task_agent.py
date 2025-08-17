from typing import Dict, Any, List, Optional
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from .task_storage import TaskStorage
from .task_utils import TaskUtils

class TaskAgent:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0.1,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="openai/gpt-oss-120b"
        )
        self.storage = TaskStorage()
        self.utils = TaskUtils()
    

    
    def process_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process task management requests"""
        user_query = state.get('user_query', '')
        
        # Use LLM to understand the intent
        intent_response = self._analyze_intent(user_query)
        
        if intent_response['action'] == 'create':
            return self._create_task(intent_response, user_query)
        elif intent_response['action'] == 'list':
            return self._list_tasks(intent_response)
        elif intent_response['action'] == 'update':
            return self._update_task(intent_response, user_query)
        elif intent_response['action'] == 'delete':
            return self._delete_task(intent_response, user_query)
        elif intent_response['action'] == 'complete':
            return self._complete_task(intent_response, user_query)
        elif intent_response['action'] == 'prioritize':
            return self._prioritize_tasks(user_query)
        else:
            return {"response": f"Task Manager: {intent_response.get('response', 'I can help you create, list, update, delete, or complete tasks.')}"}
    
    def _analyze_intent(self, query: str) -> Dict[str, Any]:
        """Use regex first, then LLM to analyze user intent"""
        # Extract task ID using regex (more reliable)
        task_id = None
        id_match = re.search(r'#?(\d+)', query)
        if id_match:
            task_id = int(id_match.group(1))
        
        # Check for prioritization/sequencing queries
        query_lower = query.lower()
        priority_keywords = ['priority', 'prioritize', 'sequence', 'order', 'focus', 'urgent', 'important']
        if any(keyword in query_lower for keyword in priority_keywords):
            return {"action": "prioritize", "task_id": task_id}
        
        system_prompt = f"""Analyze this task request: "{query}"

Task ID found: {task_id if task_id else "none"}

Respond with JSON:
{{
  "action": "create|list|update|delete|complete|prioritize|help",
  "task_id": {task_id if task_id else "null"},
  "title": "task title if creating",
  "priority": "high|medium|low if specified",
  "due_date": "date if specified"
}}"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ]
        
        try:
            response = self.llm.invoke(messages)
            result = json.loads(response.content)
            if task_id:
                result['task_id'] = task_id
            return result
        except:
            return {"action": "help", "task_id": task_id}
    
    def _create_task(self, intent: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Create a new task"""
        title = intent.get('title', '').strip()
        if not title:
            # Extract title from query if not provided by LLM
            title = re.sub(r'(create|add|new)\s+(task\s+)?', '', query, flags=re.IGNORECASE).strip()
        
        if not title:
            return {"response": "Task Manager: Please provide a task title. Example: 'create task Buy groceries'"}
        
        # Parse due date and priority from query
        due_date = self.utils.parse_due_date(query) or intent.get('due_date')
        priority = self.utils.extract_priority(query) if not intent.get('priority') else intent.get('priority', 'medium')
        
        task = {
            "title": title,
            "description": intent.get('description', ''),
            "priority": priority,
            "status": "pending",
            "due_date": due_date,
            "completed_at": None
        }
        
        task_id = self.storage.add_task(task)
        
        due_info = f" (Due: {due_date})" if due_date else ""
        return {"response": f"✅ Task Manager: Created task #{task_id}: '{title}' (Priority: {priority}){due_info}"}
    
    def _list_tasks(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """List tasks with optional filters"""
        tasks = self.storage.get_all_tasks()
        filters = intent.get('filters', {})
        
        # Apply filters
        if filters.get('status'):
            tasks = [t for t in tasks if t['status'] == filters['status']]
        if filters.get('priority'):
            tasks = [t for t in tasks if t['priority'] == filters['priority']]
        
        if not tasks:
            return {"response": "📋 Task Manager: No tasks found."}
        
        # Get task statistics
        stats = self.utils.get_task_stats(tasks)
        suggestions = self.utils.suggest_next_actions(tasks)
        
        response = self.utils.format_task_list(tasks)
        
        # Add statistics
        response += f"\n📊 **Stats:** {stats['completed']}/{stats['total']} completed ({stats['completion_rate']}%)"
        
        # Add suggestions
        if suggestions:
            response += "\n\n💡 **Suggestions:**\n"
            for suggestion in suggestions:
                response += f"  • {suggestion}\n"
        
        return {"response": response}
    
    def _update_task(self, intent: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Update an existing task"""
        task_id = intent.get('task_id')
        if not task_id:
            # Try to extract ID from query
            id_match = re.search(r'#?(\d+)', query)
            if id_match:
                task_id = int(id_match.group(1))
        
        if not task_id:
            return {"response": "Task Manager: Please specify a task ID. Example: 'update task #1 priority high'"}
        
        task = self.storage.get_task_by_id(task_id)
        if not task:
            return {"response": f"Task Manager: Task #{task_id} not found."}
        
        # Extract updates from query directly
        updates = {}
        query_lower = query.lower()
        
        # Extract priority
        if 'priority' in query_lower:
            if 'high' in query_lower or 'urgent' in query_lower:
                updates['priority'] = 'high'
            elif 'low' in query_lower:
                updates['priority'] = 'low'
            elif 'medium' in query_lower:
                updates['priority'] = 'medium'
            elif 'critical' in query_lower:
                updates['priority'] = 'critical'
        
        # Extract due date
        if 'due' in query_lower:
            due_date = self.utils.parse_due_date(query)
            if due_date:
                updates['due_date'] = due_date
        
        # Use intent data as fallback
        if intent.get('title'):
            updates['title'] = intent['title']
        if intent.get('description'):
            updates['description'] = intent['description']
        if not updates.get('priority') and intent.get('priority'):
            updates['priority'] = intent['priority']
        if not updates.get('due_date') and intent.get('due_date'):
            updates['due_date'] = intent['due_date']
        
        if updates:
            self.storage.update_task(task_id, updates)
            return {"response": f"✏️ Task Manager: Updated task #{task_id}: '{task['title']}'"}
        else:
            return {"response": f"Task Manager: No updates specified for task #{task_id}"}
    
    def _delete_task(self, intent: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Delete a task"""
        task_id = intent.get('task_id')
        if not task_id:
            id_match = re.search(r'#?(\d+)', query)
            if id_match:
                task_id = int(id_match.group(1))
        
        if not task_id:
            return {"response": "Task Manager: Please specify a task ID. Example: 'delete task #1'"}
        
        task = self.storage.get_task_by_id(task_id)
        if not task:
            return {"response": f"Task Manager: Task #{task_id} not found."}
        
        if self.storage.delete_task(task_id):
            return {"response": f"🗑️ Task Manager: Deleted task #{task_id}: '{task['title']}'"}
        else:
            return {"response": f"Task Manager: Failed to delete task #{task_id}"}
    
    def _complete_task(self, intent: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Mark a task as completed"""
        task_id = intent.get('task_id')
        if not task_id:
            id_match = re.search(r'#?(\d+)', query)
            if id_match:
                task_id = int(id_match.group(1))
        
        if not task_id:
            return {"response": "Task Manager: Please specify a task ID. Example: 'complete task #1'"}
        
        task = self.storage.get_task_by_id(task_id)
        if not task:
            return {"response": f"Task Manager: Task #{task_id} not found."}
        
        if task['status'] == 'completed':
            return {"response": f"Task Manager: Task #{task_id} is already completed."}
        
        updates = {
            'status': 'completed',
            'completed_at': datetime.now().isoformat()
        }
        
        if self.storage.update_task(task_id, updates):
            return {"response": f"🎉 Task Manager: Completed task #{task_id}: '{task['title']}'"}
        else:
            return {"response": f"Task Manager: Failed to complete task #{task_id}"}
    
    def _prioritize_tasks(self, query: str) -> Dict[str, Any]:
        """Provide task prioritization and sequencing"""
        tasks = self.storage.get_all_tasks()
        pending_tasks = [t for t in tasks if t['status'] == 'pending']
        
        if not pending_tasks:
            return {"response": "📋 No pending tasks to prioritize."}
        
        # Sort by priority and due date
        sorted_tasks = self.utils.sort_tasks_by_priority(pending_tasks)
        
        query_lower = query.lower()
        
        if 'sequence' in query_lower or 'order' in query_lower or 'efficient' in query_lower:
            # Provide task sequence
            response = "📋 **Optimal Task Sequence:**\n\n"
            for i, task in enumerate(sorted_tasks[:5], 1):
                due_info = f" (Due: {task['due_date']})" if task.get('due_date') else ""
                desc_info = f"\n     📝 {task['description']}" if task.get('description') else ""
                response += f"{i}. **#{task['id']}** {task['title']}{due_info}{desc_info}\n"
            
            response += "\n💡 **Why this order:**\n"
            response += "• Urgent tasks with deadlines first\n"
            response += "• High priority items next\n"
            response += "• Quick wins to build momentum\n"
            
        elif 'focus' in query_lower or 'right now' in query_lower:
            # Focus on immediate task
            top_task = sorted_tasks[0]
            due_info = f" (Due: {top_task['due_date']})" if top_task.get('due_date') else ""
            response = f"🎯 **Focus on:** #{top_task['id']} {top_task['title']}{due_info}\n\n"
            response += f"**Priority:** {top_task['priority'].title()}\n"
            if top_task.get('description'):
                response += f"**Details:** {top_task['description']}\n"
            
        else:
            # General prioritization
            response = "🎯 **Task Priorities:**\n\n"
            for task in sorted_tasks:
                priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(task['priority'], '🟡')
                due_info = f" (Due: {task['due_date']})" if task.get('due_date') else ""
                desc_info = f"\n     📝 {task['description']}" if task.get('description') else ""
                response += f"{priority_emoji} **#{task['id']}** {task['title']}{due_info}{desc_info}\n"
        
        return {"response": response}