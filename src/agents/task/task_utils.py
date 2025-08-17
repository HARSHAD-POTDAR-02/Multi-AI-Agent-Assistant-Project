from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re

class TaskUtils:
    """Utility functions for task management"""
    
    @staticmethod
    def parse_due_date(date_str: str) -> Optional[str]:
        """Parse natural language due dates"""
        if not date_str:
            return None
        
        date_str = date_str.lower().strip()
        today = datetime.now()
        
        # Handle relative dates
        if 'today' in date_str:
            return today.strftime('%Y-%m-%d')
        elif 'tomorrow' in date_str:
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'next week' in date_str:
            return (today + timedelta(days=7)).strftime('%Y-%m-%d')
        elif 'next month' in date_str:
            return (today + timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Handle "in X days"
        days_match = re.search(r'in (\d+) days?', date_str)
        if days_match:
            days = int(days_match.group(1))
            return (today + timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Handle "in X weeks"
        weeks_match = re.search(r'in (\d+) weeks?', date_str)
        if weeks_match:
            weeks = int(weeks_match.group(1))
            return (today + timedelta(weeks=weeks)).strftime('%Y-%m-%d')
        
        return None
    
    @staticmethod
    def extract_priority(text: str) -> str:
        """Extract priority from text"""
        text = text.lower()
        if any(word in text for word in ['urgent', 'critical', 'asap', 'high']):
            return 'high'
        elif any(word in text for word in ['low', 'minor', 'later']):
            return 'low'
        else:
            return 'medium'
    
    @staticmethod
    def format_task_list(tasks: List[Dict[str, Any]], show_completed: bool = True) -> str:
        """Format tasks for display"""
        if not tasks:
            return "📋 No tasks found."
        
        # Filter completed tasks if needed
        if not show_completed:
            tasks = [t for t in tasks if t.get('status') != 'completed']
        
        # Group by status
        pending = [t for t in tasks if t.get('status') == 'pending']
        completed = [t for t in tasks if t.get('status') == 'completed']
        
        response = ""
        
        if pending:
            response += "⏳ **Pending Tasks:**\n"
            for task in pending:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.get('priority', 'medium'), "⚪")
                response += f"  {priority_icon} **#{task['id']}** {task['title']}\n"
                if task.get('description'):
                    response += f"     📝 {task['description']}\n"
                if task.get('due_date'):
                    response += f"     📅 Due: {task['due_date']}\n"
            response += "\n"
        
        if completed and show_completed:
            response += "✅ **Completed Tasks:**\n"
            for task in completed:
                response += f"  ✅ **#{task['id']}** {task['title']}\n"
            response += "\n"
        
        return response.strip()
    
    @staticmethod
    def get_task_stats(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get task statistics"""
        total = len(tasks)
        completed = len([t for t in tasks if t.get('status') == 'completed'])
        pending = len([t for t in tasks if t.get('status') == 'pending'])
        
        high_priority = len([t for t in tasks if t.get('priority') == 'high' and t.get('status') != 'completed'])
        
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'completed': completed,
            'pending': pending,
            'high_priority_pending': high_priority,
            'completion_rate': round(completion_rate, 1)
        }
    
    @staticmethod
    def suggest_next_actions(tasks: List[Dict[str, Any]]) -> List[str]:
        """Suggest next actions based on current tasks"""
        suggestions = []
        
        # Check for overdue tasks
        today = datetime.now().strftime('%Y-%m-%d')
        overdue = [t for t in tasks if t.get('due_date') and t['due_date'] < today and t.get('status') != 'completed']
        
        if overdue:
            suggestions.append(f"🚨 You have {len(overdue)} overdue task(s). Consider completing them first.")
        
        # Check for high priority tasks
        high_priority = [t for t in tasks if t.get('priority') == 'high' and t.get('status') != 'completed']
        if high_priority:
            suggestions.append(f"🔴 Focus on {len(high_priority)} high priority task(s).")
        
        # Check for tasks due soon
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        due_soon = [t for t in tasks if t.get('due_date') == tomorrow and t.get('status') != 'completed']
        if due_soon:
            suggestions.append(f"📅 {len(due_soon)} task(s) due tomorrow.")
        
        return suggestions
    
    @staticmethod
    def sort_tasks_by_priority(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort tasks by priority and due date"""
        def priority_score(task):
            # Priority weights
            priority_weights = {'high': 3, 'medium': 2, 'low': 1}
            score = priority_weights.get(task.get('priority', 'medium'), 2)
            
            # Due date urgency
            if task.get('due_date'):
                try:
                    due_date = datetime.strptime(task['due_date'], '%Y-%m-%d')
                    today = datetime.now()
                    days_until_due = (due_date - today).days
                    
                    if days_until_due < 0:  # Overdue
                        score += 10
                    elif days_until_due == 0:  # Due today
                        score += 5
                    elif days_until_due == 1:  # Due tomorrow
                        score += 3
                    elif days_until_due <= 7:  # Due this week
                        score += 1
                except:
                    pass
            
            return score
        
        return sorted(tasks, key=priority_score, reverse=True)