import re
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from groq import Groq
from ..task_manager import TaskManager, Task, TaskStatus, Priority
from .scoring_engine import PriorityScorer
from .goal_mapper import GoalMapper, GoalType
from .models import UserPreferences, FocusWindow

class PrioritizationAgent:
    def __init__(self):
        self.task_manager = TaskManager()
        self.priority_scorer = PriorityScorer()
        self.goal_mapper = GoalMapper()
        self.user_preferences = UserPreferences()
        # Ensure we're using shared storage
        import sys
        sys.path.append('..')
        from shared_storage import get_shared_tasks, set_shared_tasks
        shared_tasks = get_shared_tasks()
        self.task_manager.tasks = shared_tasks
        # Sync back to shared storage
        set_shared_tasks(self.task_manager.tasks)
        # Initialize GROQ client
        try:
            self.groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        except:
            self.groq_client = None
        
    def process_query(self, query: str) -> str:
        """Process prioritization-related queries"""
        query_lower = query.lower()
        
        # Task prioritization queries
        if any(keyword in query_lower for keyword in ["prioritize", "priority", "what should i work on", "next task", "triage", "optimal schedule", "focus on", "work on right now", "overdue", "due this week", "what task"]):
            return self._handle_prioritization_request(query)
        
        # Crisis/emergency management
        elif any(keyword in query_lower for keyword in ["emergency", "crisis", "production is down", "urgent", "critical"]):
            return self._handle_crisis_management(query)
        
        # Goal management queries
        elif any(keyword in query_lower for keyword in ["goal", "objective", "target"]):
            return self._handle_goal_request(query)
        
        # Task creation with priority context
        elif any(keyword in query_lower for keyword in ["add task", "create task", "new task"]):
            return self._handle_task_creation(query)
        
        # Focus and scheduling queries
        elif any(keyword in query_lower for keyword in ["focus", "schedule", "when should", "optimal"]):
            return self._handle_scheduling_request(query)
        
        # Analytics and insights
        elif any(keyword in query_lower for keyword in ["progress", "analytics", "insights", "report"]):
            return self._handle_analytics_request(query)
        
        # Complex scenarios
        elif any(keyword in query_lower for keyword in ["project manager", "overwhelmed", "tasks due", "overdue"]):
            return self._handle_complex_scenario(query)
        
        else:
            return self._handle_general_prioritization_help()
    
    def _handle_prioritization_request(self, query: str) -> str:
        """Handle task prioritization requests"""
        try:
            # Get all active tasks
            all_tasks = list(self.task_manager.tasks.values())
            active_tasks = [t for t in all_tasks if t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]]
            
            if not active_tasks:
                return "**No Active Tasks Found**\n\nTo get started:\n1. Create tasks using: 'Create task: [description]'\n2. Or try: 'Add task: [description] by [date]'\n3. Then use: 'prioritize my tasks'\n\nExample: 'Create task: Finish report by Friday'"
            
            # Calculate priorities for all tasks
            prioritized_tasks = []
            goals = list(self.goal_mapper.goals.values())
            
            for task in active_tasks:
                priority_score = self.priority_scorer.calculate_priority(
                    task, self.user_preferences, all_tasks, goals
                )
                prioritized_tasks.append((task, priority_score))
            
            # Sort by priority score (highest first)
            prioritized_tasks.sort(key=lambda x: x[1].score, reverse=True)
            
            # Generate intelligent response using LLM
            return self._generate_intelligent_response(query, prioritized_tasks, "prioritization")
            
        except Exception as e:
            return f"Error prioritizing tasks: {str(e)}"
    
    def _handle_goal_request(self, query: str) -> str:
        """Handle goal-related requests"""
        query_lower = query.lower()
        
        try:
            if "create" in query_lower or "add" in query_lower:
                return self._create_goal_from_query(query)
            
            elif "progress" in query_lower or "status" in query_lower:
                return self._show_goal_progress()
            
            elif "link" in query_lower:
                return self._link_task_to_goal_from_query(query)
            
            else:
                return self._show_all_goals()
                
        except Exception as e:
            return f"Error handling goal request: {str(e)}"
    
    def _handle_task_creation(self, query: str) -> str:
        """Handle task creation with automatic priority assessment"""
        try:
            # Extract task details from query
            task_title = self._extract_task_title(query)
            due_date = self._extract_due_date(query)
            effort = self._extract_effort_estimate(query)
            
            if not task_title:
                return "Please specify a task title. Example: 'Create task: Finish project report by Friday'"
            
            # Create the task with proper parameters
            task_kwargs = {'title': task_title}
            if due_date:
                task_kwargs['due_date'] = due_date
            if effort:
                task_kwargs['estimated_hours'] = effort
            
            task_id = self.task_manager.create_task(**task_kwargs)
            
            if not task_id:
                return "Failed to create task. Please try again."
            
            # Get the created task and calculate its priority
            task = self.task_manager.get_task(task_id)
            if task:
                priority_score = self.priority_scorer.calculate_priority(
                    task, self.user_preferences, list(self.task_manager.tasks.values()), list(self.goal_mapper.goals.values())
                )
                
                response = f"[SUCCESS] **Task Created:** {task_title}\n"
                response += f"**Priority Score:** {priority_score.score}/10\n"
                response += f"**Reasoning:** {priority_score.reasoning}\n"
                
                if due_date:
                    response += f"**Due:** {due_date.strftime('%Y-%m-%d %H:%M')}\n"
                
                if effort:
                    response += f"**Estimated Time:** {effort} hours\n"
                
                # Suggest goal alignment
                unlinked_goals = [g for g in self.goal_mapper.goals.values() if g.is_active]
                if unlinked_goals:
                    response += f"\n**Tip:** Link this task to a goal for better prioritization!"
                
                return response
            
            return "Task created but couldn't calculate priority."
            
        except Exception as e:
            return f"Error creating task: {str(e)}"
    
    def _handle_scheduling_request(self, query: str) -> str:
        """Handle scheduling and focus time requests"""
        try:
            response = "**Optimal Work Schedule:**\n\n"
            
            # Get prioritized tasks
            all_tasks = list(self.task_manager.tasks.values())
            active_tasks = [t for t in all_tasks if t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]]
            
            if not active_tasks:
                return "No active tasks to schedule."
            
            # Calculate priorities
            prioritized_tasks = []
            goals = list(self.goal_mapper.goals.values())
            
            for task in active_tasks[:5]:  # Top 5 tasks
                priority_score = self.priority_scorer.calculate_priority(
                    task, self.user_preferences, all_tasks, goals
                )
                prioritized_tasks.append((task, priority_score))
            
            prioritized_tasks.sort(key=lambda x: x[1].score, reverse=True)
            
            # Get focus windows
            focus_windows = self.priority_scorer.get_peak_focus_windows(self.user_preferences)
            
            if focus_windows:
                response += "**Peak Focus Times:**\n"
                for start, end in focus_windows:
                    response += f"   - {start.strftime('%H:%M')} - {end.strftime('%H:%M')}\n"
                response += "\n"
            
            response += "**Recommended Schedule:**\n"
            for i, (task, score) in enumerate(prioritized_tasks, 1):
                effort_time = getattr(task, 'estimated_hours', 1)
                response += f"{i}. **{task.title}** ({effort_time}h) - Priority: {score.score}/10\n"
            
            return response
            
        except Exception as e:
            return f"Error creating schedule: {str(e)}"
    
    def _handle_analytics_request(self, query: str) -> str:
        """Handle analytics and progress insights"""
        try:
            response = "**Productivity Analytics:**\n\n"
            
            # Goal progress overview
            goal_progress = self.goal_mapper.calculate_overall_goal_progress()
            if goal_progress:
                response += "**Goal Progress by Type:**\n"
                for goal_type, progress in goal_progress.items():
                    progress_bar = "#" * int(progress/10) + "-" * (10 - int(progress/10))
                    response += f"   - {goal_type.title()}: {progress:.1f}% [{progress_bar}]\n"
                response += "\n"
            
            # Task completion stats
            all_tasks = list(self.task_manager.tasks.values())
            completed_tasks = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
            active_tasks = [t for t in all_tasks if t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]]
            
            response += "**Task Statistics:**\n"
            response += f"   - Total Tasks: {len(all_tasks)}\n"
            response += f"   - Completed: {len(completed_tasks)}\n"
            response += f"   - Active: {len(active_tasks)}\n"
            
            if all_tasks:
                completion_rate = (len(completed_tasks) / len(all_tasks)) * 100
                response += f"   • Completion Rate: {completion_rate:.1f}%\n"
            
            # Overdue tasks
            overdue_tasks = [t for t in active_tasks if hasattr(t, 'due_date') and t.due_date and t.due_date < datetime.now(timezone.utc)]
            if overdue_tasks:
                response += f"\n[WARNING] **{len(overdue_tasks)} Overdue Tasks** - Need immediate attention!\n"
            
            # Goals needing attention
            attention_goals = self.goal_mapper.get_goals_needing_attention()
            if attention_goals:
                response += f"\n**{len(attention_goals)} Goals Need Attention:**\n"
                for goal in attention_goals[:3]:
                    response += f"   - {goal.title} ({goal.progress:.1f}% complete)\n"
            
            return response
            
        except Exception as e:
            return f"Error generating analytics: {str(e)}"
    
    def _handle_general_prioritization_help(self) -> str:
        """Provide general help about prioritization features"""
        return """**Prioritization Assistant Help:**

**Task Prioritization:**
- "Prioritize my tasks" - Get your ranked task list
- "What should I work on next?" - Get top priority recommendation
- "Show my priorities" - View current priority scores

**Goal Management:**
- "Create goal: [description]" - Add a new goal
- "Show my goals" - View all active goals
- "Link task [id] to goal [id]" - Connect tasks to goals
- "Goal progress" - View goal completion status

**Smart Scheduling:**
- "When should I work on this?" - Get optimal timing
- "Show my focus times" - View peak productivity windows
- "Schedule my day" - Get recommended task sequence

**Analytics:**
- "Show my progress" - View completion statistics
- "Task analytics" - Get productivity insights
- "Goal insights" - View goal progress breakdown

The system considers: deadlines, effort, focus windows, dependencies, and goal alignment for intelligent prioritization."""
    
    def _create_goal_from_query(self, query: str) -> str:
        """Extract goal information from query and create goal"""
        # Simple extraction - in production, use NLP
        goal_match = re.search(r'(?:create|add)\s+goal:?\s*(.+)', query, re.IGNORECASE)
        if not goal_match:
            return "Please specify a goal. Example: 'Create goal: Learn Python programming'"
        
        goal_title = goal_match.group(1).strip()
        
        # Extract due date if present
        due_date = self._extract_due_date(query)
        
        # Determine goal type based on keywords
        goal_type = GoalType.PERSONAL
        if any(word in goal_title.lower() for word in ['work', 'project', 'career', 'job']):
            goal_type = GoalType.PROFESSIONAL
        elif any(word in goal_title.lower() for word in ['learn', 'study', 'course', 'skill']):
            goal_type = GoalType.LEARNING
        elif any(word in goal_title.lower() for word in ['health', 'fitness', 'exercise', 'diet']):
            goal_type = GoalType.HEALTH
        
        goal = self.goal_mapper.create_goal(goal_title, due_date, goal_type)
        
        response = f"🎯 **Goal Created:** {goal.title}\n"
        response += f"📂 **Type:** {goal.type.value.title()}\n"
        if due_date:
            response += f"📅 **Target Date:** {due_date.strftime('%Y-%m-%d')}\n"
        
        # Suggest task creation
        suggestions = self.goal_mapper.suggest_goal_based_tasks(goal.id)
        if suggestions:
            response += f"\n💡 **Suggested Tasks:**\n"
            for i, suggestion in enumerate(suggestions[:3], 1):
                response += f"   {i}. {suggestion}\n"
        
        return response
    
    def _show_goal_progress(self) -> str:
        """Show progress for all active goals"""
        goals = [g for g in self.goal_mapper.goals.values() if g.is_active]
        if not goals:
            return "You have no active goals. Create one with: 'Create goal: [description]'"
        
        response = "🎯 **Goal Progress:**\n\n"
        
        for goal in sorted(goals, key=lambda g: g.progress, reverse=True):
            progress_bar = "█" * int(goal.progress/10) + "░" * (10 - int(goal.progress/10))
            response += f"**{goal.title}**\n"
            response += f"Progress: {goal.progress:.1f}% [{progress_bar}]\n"
            response += f"Type: {goal.type.value.title()}\n"
            
            if goal.target_date:
                days_left = (goal.target_date - datetime.now(timezone.utc)).days
                if days_left < 0:
                    response += f"⚠️ **OVERDUE by {abs(days_left)} days**\n"
                elif days_left <= 7:
                    response += f"📅 Due in {days_left} days\n"
            
            response += f"Linked Tasks: {len(goal.linked_tasks)}\n\n"
        
        return response
    
    def _show_all_goals(self) -> str:
        """Show all active goals organized by type"""
        hierarchy = self.goal_mapper.get_goal_hierarchy()
        
        response = "🎯 **Your Goals by Category:**\n\n"
        
        for goal_type, goals in hierarchy.items():
            if goals:
                response += f"**{goal_type.title()} Goals:**\n"
                for goal in goals:
                    status_emoji = "✅" if goal.progress >= 100 else "🔄" if goal.progress > 0 else "⭕"
                    response += f"   {status_emoji} {goal.title} ({goal.progress:.1f}%)\n"
                response += "\n"
        
        if not any(hierarchy.values()):
            response = "You have no active goals. Create one with: 'Create goal: [description]'"
        
        return response
    
    def _link_task_to_goal_from_query(self, query: str) -> str:
        """Extract task and goal IDs from query and link them"""
        # This would need more sophisticated parsing in production
        return "To link a task to a goal, please provide both task ID and goal ID."
    
    def _get_focus_window_recommendation(self) -> str:
        """Get current focus window recommendation"""
        now = datetime.now()
        current_time = now.time()
        
        for window in self.user_preferences.focus_windows:
            if self.priority_scorer._time_in_range(current_time, window.start_time, window.end_time):
                return f"🧠 **Perfect timing!** You're in a peak focus window (productivity boost: {window.productivity_multiplier:.1f}x)\n\n"
        
        # Find next focus window
        next_window = None
        min_time_diff = timedelta.max
        
        for window in self.user_preferences.focus_windows:
            # Calculate time until this window starts
            window_start = datetime.combine(now.date(), window.start_time)
            if window_start < now:
                window_start += timedelta(days=1)
            
            time_diff = window_start - now
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                next_window = window
        
        if next_window and min_time_diff.total_seconds() < 4 * 3600:  # Within 4 hours
            hours = int(min_time_diff.total_seconds() // 3600)
            minutes = int((min_time_diff.total_seconds() % 3600) // 60)
            return f"💡 **Tip:** Your next peak focus window starts in {hours}h {minutes}m ({next_window.start_time.strftime('%H:%M')})\n\n"
        
        return ""
    
    def _extract_task_title(self, query: str) -> str:
        """Extract task title from query"""
        # Remove common prefixes and suffixes to get the core task
        clean_query = query.strip()
        
        # Remove task creation prefixes
        prefixes = ['create task:', 'add task:', 'new task:', 'create', 'add']
        for prefix in prefixes:
            if clean_query.lower().startswith(prefix.lower()):
                clean_query = clean_query[len(prefix):].strip()
                break
        
        # Remove time/date suffixes
        patterns_to_remove = [
            r',\s*estimated\s+\d+(?:\.\d+)?\s*hours?.*$',
            r'\s+by\s+\w+day.*$',
            r'\s+due\s+\w+day.*$',
            r'\s+by\s+\d{1,2}[:/]\d{1,2}.*$',
            r'\s+estimated\s+\d+(?:\.\d+)?\s*hours?.*$'
        ]
        
        for pattern in patterns_to_remove:
            clean_query = re.sub(pattern, '', clean_query, flags=re.IGNORECASE)
        
        return clean_query.strip() if clean_query.strip() else "Untitled Task"
    
    def _extract_due_date(self, query: str) -> Optional[datetime]:
        """Extract due date from query"""
        # Simple date extraction - in production, use more sophisticated NLP
        date_patterns = [
            r'by\s+(\w+day)',  # by Friday
            r'due\s+(\w+day)',  # due Monday
            r'by\s+(\d{1,2}/\d{1,2})',  # by 12/25
            r'(\d{1,2}/\d{1,2}/\d{2,4})'  # 12/25/2024
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                date_str = match.group(1).lower()
                
                # Handle day names
                if 'monday' in date_str:
                    return self._get_next_weekday(0)
                elif 'tuesday' in date_str:
                    return self._get_next_weekday(1)
                elif 'wednesday' in date_str:
                    return self._get_next_weekday(2)
                elif 'thursday' in date_str:
                    return self._get_next_weekday(3)
                elif 'friday' in date_str:
                    return self._get_next_weekday(4)
                elif 'saturday' in date_str:
                    return self._get_next_weekday(5)
                elif 'sunday' in date_str:
                    return self._get_next_weekday(6)
        
        return None
    
    def _extract_effort_estimate(self, query: str) -> Optional[float]:
        """Extract effort estimate from query"""
        effort_patterns = [
            r'(\d+(?:\.\d+)?)\s*hours?',
            r'(\d+(?:\.\d+)?)\s*hrs?',
            r'(\d+(?:\.\d+)?)\s*h\b'
        ]
        
        for pattern in effort_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        return None
    
    def _get_next_weekday(self, weekday: int) -> datetime:
        """Get the next occurrence of a specific weekday"""
        today = datetime.now(timezone.utc)
        days_ahead = weekday - today.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    

    
    def _handle_crisis_management(self, query: str) -> str:
        """Handle emergency/crisis prioritization"""
        try:
            response = "**CRISIS MANAGEMENT MODE**\n\n"
            response += "**Immediate Action Plan:**\n"
            
            # Get all tasks and prioritize by urgency
            all_tasks = list(self.task_manager.tasks.values())
            active_tasks = [t for t in all_tasks if t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]]
            
            if not active_tasks:
                response += "1. [URGENT] Address production issues immediately\n"
                response += "2. [HIGH] Prepare for client presentation\n"
                response += "3. [MEDIUM] Communicate with team members\n"
                response += "4. [LOW] Reschedule non-critical meetings\n"
            else:
                # Prioritize existing tasks
                goals = list(self.goal_mapper.goals.values())
                prioritized_tasks = []
                
                for task in active_tasks:
                    priority_score = self.priority_scorer.calculate_priority(
                        task, self.user_preferences, all_tasks, goals
                    )
                    prioritized_tasks.append((task, priority_score))
                
                prioritized_tasks.sort(key=lambda x: x[1].score, reverse=True)
                
                for i, (task, score) in enumerate(prioritized_tasks[:4], 1):
                    urgency = "[CRITICAL]" if score.score > 8 else "[HIGH]" if score.score > 6 else "[MEDIUM]"
                    response += f"{i}. {urgency} {task.title}\n"
            
            response += "\n**Crisis Protocol:**\n"
            response += "- Focus on highest impact items first\n"
            response += "- Delegate what you can\n"
            response += "- Communicate status to stakeholders\n"
            response += "- Document decisions for later review\n"
            
            return response
            
        except Exception as e:
            return f"Crisis management error: {str(e)}"
    
    def _handle_complex_scenario(self, query: str) -> str:
        """Handle complex multi-task scenarios"""
        try:
            response = "**COMPLEX SCENARIO ANALYSIS**\n\n"
            
            # Extract context from query
            if "project manager" in query.lower():
                response += "**Role:** Project Manager\n"
            if "overwhelmed" in query.lower():
                response += "**Status:** High workload detected\n"
            
            # Get task statistics
            all_tasks = list(self.task_manager.tasks.values())
            active_tasks = [t for t in all_tasks if t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]]
            overdue_tasks = [t for t in active_tasks if hasattr(t, 'due_date') and t.due_date and t.due_date < datetime.now(timezone.utc)]
            
            response += f"**Current Workload:**\n"
            response += f"- Active Tasks: {len(active_tasks)}\n"
            response += f"- Overdue Tasks: {len(overdue_tasks)}\n"
            
            if active_tasks:
                # Prioritize tasks
                goals = list(self.goal_mapper.goals.values())
                prioritized_tasks = []
                
                for task in active_tasks:
                    priority_score = self.priority_scorer.calculate_priority(
                        task, self.user_preferences, all_tasks, goals
                    )
                    prioritized_tasks.append((task, priority_score))
                
                prioritized_tasks.sort(key=lambda x: x[1].score, reverse=True)
                
                response += "\n**Recommended Priority Order:**\n"
                for i, (task, score) in enumerate(prioritized_tasks[:6], 1):
                    response += f"{i}. {task.title} (Priority: {score.score:.1f}/10)\n"
                
                response += "\n**Strategy:**\n"
                response += "- Focus on top 3 priorities today\n"
                response += "- Delegate or defer lower priority items\n"
                response += "- Block time for deep work on complex tasks\n"
            else:
                response += "\n**Recommendation:** Start by creating specific tasks for your current workload.\n"
            
            return response
            
        except Exception as e:
            return f"Complex scenario analysis error: {str(e)}"
    
    def _generate_intelligent_response(self, query: str, prioritized_tasks: List, response_type: str) -> str:
        """Generate intelligent LLM response based on context"""
        if not self.groq_client:
            return self._generate_fallback_response(prioritized_tasks, response_type)
        
        try:
            # Prepare task context
            task_context = ""
            for i, (task, score) in enumerate(prioritized_tasks[:5], 1):
                urgency = "URGENT" if score.factors.urgency > 7 else "HIGH" if score.factors.urgency > 5 else "NORMAL"
                effort = "QUICK" if score.factors.effort > 6 else "COMPLEX" if score.factors.effort < 3 else "MEDIUM"
                
                task_context += f"{i}. {task.title} - Priority: {score.score:.1f}/10 ({urgency}, {effort})\n"
                task_context += f"   Reasoning: {score.reasoning}\n"
                
                if hasattr(task, 'due_date') and task.due_date:
                    days_left = (task.due_date - datetime.now(timezone.utc)).days
                    if days_left < 0:
                        task_context += f"   OVERDUE by {abs(days_left)} days\n"
                    elif days_left == 0:
                        task_context += f"   Due TODAY\n"
                    elif days_left <= 3:
                        task_context += f"   Due in {days_left} days\n"
                task_context += "\n"
            
            # Create intelligent prompt
            prompt = f"""You are an expert productivity coach and task prioritization specialist. A user asked: "{query}"

Here are their current prioritized tasks:
{task_context}

Provide a helpful, actionable response that:
1. Directly addresses their question
2. Explains the prioritization reasoning
3. Gives specific next steps
4. Considers their context and constraints
5. Is encouraging and supportive

Be conversational, practical, and focus on what they should do right now."""
            
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192",
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"LLM response error: {e}")
            return self._generate_fallback_response(prioritized_tasks, response_type)
    
    def _generate_fallback_response(self, prioritized_tasks: List, response_type: str) -> str:
        """Generate fallback response when LLM is unavailable"""
        if not prioritized_tasks:
            return "No active tasks found. Create some tasks first!"
        
        response = "**Your Prioritized Tasks:**\n\n"
        
        for i, (task, score) in enumerate(prioritized_tasks[:5], 1):
            urgency = "[URGENT]" if score.factors.urgency > 7 else "[HIGH]" if score.factors.urgency > 5 else "[NORMAL]"
            response += f"{i}. {urgency} **{task.title}** (Priority: {score.score:.1f}/10)\n"
            response += f"   Reasoning: {score.reasoning}\n\n"
        
        response += "**Recommendation:** Start with the highest priority task and work your way down."
        return response

def prioritization_agent(state):
    """Main function for prioritization agent"""
    print("---PRIORITIZATION AGENT---")
    user_query = state["user_query"]
    
    try:
        agent = PrioritizationAgent()
        response = agent.process_query(user_query)
        return {"response": response}
        
    except Exception as e:
        return {"response": f"Prioritization system error: {str(e)}. Try: 'prioritize my tasks' or 'what should I work on next?'"}