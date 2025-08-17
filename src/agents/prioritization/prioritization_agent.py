import re
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from groq import Groq
from .enhanced_models import ContextState, UserBehavior, ProactiveInsight
from .smart_scorer import SmartPriorityScorer
from .natural_interface import NaturalLanguageInterface

class PrioritizationAgent:
    def __init__(self):
        # Use new task storage system
        from ..task.task_storage import TaskStorage
        self.task_storage = TaskStorage()
        
        # Initialize enhanced components
        self.smart_scorer = SmartPriorityScorer()
        self.natural_interface = NaturalLanguageInterface()
        
        # Initialize GROQ client (fallback)
        try:
            self.groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        except:
            self.groq_client = None
        
    def process_query(self, query: str, conversation_history: List = None) -> str:
        """Process prioritization-related queries with enhanced intelligence"""
        
        # Build current context
        context = self._build_current_context(conversation_history or [])
        
        # Get all active tasks
        all_tasks = self.task_storage.get_all_tasks()
        active_tasks = [t for t in all_tasks if t.get('status') != 'completed']
        
        # Generate proactive insights
        insights = self.smart_scorer.generate_proactive_insights(active_tasks, context)
        
        # Check for proactive opportunities first
        proactive_message = self.natural_interface.generate_proactive_message(insights, context)
        if proactive_message and not any(keyword in query.lower() for keyword in ['help', 'what', 'how']):
            return proactive_message + "\n\n" + self._handle_main_query(query, active_tasks, context, insights)
        
        return self._handle_main_query(query, active_tasks, context, insights)
    
    def _handle_main_query(self, query: str, active_tasks: List, context: ContextState, insights: List) -> str:
        """Handle the main query with context awareness"""
        query_lower = query.lower()
        
        # Enhanced prioritization with smart scoring
        if any(keyword in query_lower for keyword in ["prioritize", "priority", "what should i work on", "next task", "focus on", "work on right now", "what task", "overwhelmed", "too much"]):
            return self._handle_smart_prioritization(query, active_tasks, context, insights)
        
        # Crisis/emergency management
        elif any(keyword in query_lower for keyword in ["emergency", "crisis", "production is down", "urgent", "critical"]):
            return self._handle_crisis_management(query, active_tasks, context)
        
        # Energy and timing queries
        elif any(keyword in query_lower for keyword in ["energy", "tired", "when should", "timing", "schedule"]):
            return self._handle_energy_timing_query(query, active_tasks, context)
        
        # Task creation with smart assessment
        elif any(keyword in query_lower for keyword in ["add task", "create task", "new task"]):
            return self._handle_smart_task_creation(query, context)
        
        # Analytics and insights
        elif any(keyword in query_lower for keyword in ["progress", "analytics", "insights", "report", "how am i doing"]):
            return self._handle_analytics_request(active_tasks, context)
        
        else:
            return self._handle_general_query(query, active_tasks, context, insights)
    
    def _handle_smart_prioritization(self, query: str, active_tasks: List, context: ContextState, insights: List) -> str:
        """Handle prioritization with enhanced intelligence"""
        try:
            if not active_tasks:
                return self.natural_interface.generate_conversational_response(
                    "No tasks to prioritize", [], context, insights
                )
            
            # Calculate smart priorities
            prioritized_tasks = []
            for task in active_tasks:
                smart_score = self.smart_scorer.calculate_smart_priority(task, context, active_tasks)
                prioritized_tasks.append((task, smart_score))
            
            # Sort by final score
            prioritized_tasks.sort(key=lambda x: x[1].final_score, reverse=True)
            
            # Generate natural response
            return self.natural_interface.generate_conversational_response(
                query, prioritized_tasks, context, insights
            )
            
        except Exception as e:
            return f"I'm having trouble analyzing your tasks right now: {str(e)}. Let me try a simpler approach."
    
    def _build_current_context(self, conversation_history: List) -> ContextState:
        """Build current context from available information"""
        current_time = datetime.now()
        
        # Estimate energy level based on time of day
        hour = current_time.hour
        if 9 <= hour <= 11 or 14 <= hour <= 16:  # Peak hours
            energy_level = 8.0
        elif 7 <= hour <= 9 or 11 <= hour <= 14 or 16 <= hour <= 18:  # Good hours
            energy_level = 6.5
        elif hour < 7 or hour > 20:  # Low energy hours
            energy_level = 4.0
        else:
            energy_level = 5.5
        
        # Estimate available time (default 2 hours)
        available_time = 120
        
        # Determine momentum from recent activity
        momentum = "neutral"
        recent_completions = []
        
        if conversation_history:
            recent_messages = conversation_history[-5:]
            completed_mentions = sum(1 for msg in recent_messages if 'completed' in msg.get('content', '').lower())
            if completed_mentions >= 2:
                momentum = "high"
                recent_completions = [f"task_{i}" for i in range(completed_mentions)]
            elif any('stuck' in msg.get('content', '').lower() or 'difficult' in msg.get('content', '').lower() for msg in recent_messages):
                momentum = "low"
        
        return ContextState(
            current_time=current_time,
            energy_level=energy_level,
            available_time_block=available_time,
            current_momentum=momentum,
            recent_completions=recent_completions
        )
    
    def _handle_energy_timing_query(self, query: str, active_tasks: List, context: ContextState) -> str:
        """Handle energy and timing related queries"""
        return self.natural_interface.generate_conversational_response(
            query, [(task, self.smart_scorer.calculate_smart_priority(task, context)) for task in active_tasks[:3]], 
            context
        )
    
    def _handle_smart_task_creation(self, query: str, context: ContextState) -> str:
        """Handle task creation with smart assessment"""
        try:
            # Extract task details
            task_title = self._extract_task_title(query)
            due_date = self._extract_due_date(query)
            effort = self._extract_effort_estimate(query)
            
            if not task_title:
                return "I'd love to help you create a task! What would you like to work on? For example: 'Create task: Finish the quarterly report by Friday'"
            
            # Create task
            task_kwargs = {'title': task_title}
            if due_date:
                task_kwargs['due_date'] = due_date.isoformat()
            if effort:
                task_kwargs['estimated_hours'] = effort
            
            task_id = self.task_storage.add_task(task_kwargs)
            
            if task_id:
                task = self.task_storage.get_task_by_id(task_id)
                if task:
                    # Calculate smart priority for the new task
                    smart_score = self.smart_scorer.calculate_smart_priority(task, context)
                    
                    response = f"✅ Created '{task_title}' with priority score {smart_score.final_score}/10. "
                    
                    if smart_score.final_score >= 7.0:
                        response += "This looks important - consider working on it soon!"
                    elif smart_score.next_best_time:
                        next_time = smart_score.next_best_time.strftime("%I:%M %p")
                        response += f"Best time to work on this would be around {next_time}."
                    else:
                        response += "Good addition to your task list!"
                    
                    return response
            
            return "Task created successfully! Use 'prioritize my tasks' to see where it fits in your workflow."
            
        except Exception as e:
            return f"I had trouble creating that task: {str(e)}. Could you try rephrasing it?"
    
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
            
            # Use task storage instead of task_manager
            task_id = self.task_storage.add_task(task_kwargs)
            
            if not task_id:
                return "Failed to create task. Please try again."
            
            # Get the created task
            task = self.task_storage.get_task_by_id(task_id)
            if task:
                # Simple priority calculation since we don't have the complex scorer
                priority_level = task.get('priority', 'medium')
                priority_score_num = {'high': 8, 'medium': 5, 'low': 3}.get(priority_level, 5)
                
                response = f"[SUCCESS] **Task Created:** {task_title}\n"
                response += f"**Priority Score:** {priority_score_num}/10\n"
                response += f"**Priority Level:** {priority_level.title()}\n"
                
                if due_date:
                    response += f"**Due:** {due_date.strftime('%Y-%m-%d %H:%M')}\n"
                
                if effort:
                    response += f"**Estimated Time:** {effort} hours\n"
                
                response += f"\n**Tip:** Task created successfully!"
                
                return response
            
            return "Task created but couldn't calculate priority."
            
        except Exception as e:
            return f"Error creating task: {str(e)}"
    
    def _handle_scheduling_request(self, query: str) -> str:
        """Handle scheduling and focus time requests"""
        try:
            response = "**Optimal Work Schedule:**\n\n"
            
            # Get prioritized tasks
            all_tasks = self.task_storage.get_all_tasks()
            active_tasks = [t for t in all_tasks if t.get('status') != 'completed']
            
            if not active_tasks:
                return "No active tasks to schedule."
            
            # Calculate simple priorities
            prioritized_tasks = self._calculate_simple_priorities(active_tasks[:5])
            
            # Default focus windows
            response += "**Peak Focus Times:**\n"
            response += "   - 09:00 - 11:00 (Morning focus)\n"
            response += "   - 14:00 - 16:00 (Afternoon focus)\n\n"
            
            response += "**Recommended Schedule:**\n"
            for i, (task, score) in enumerate(prioritized_tasks, 1):
                effort_time = task.get('estimated_hours', 1)
                response += f"{i}. **{task.get('title')}** ({effort_time}h) - Priority: {score}/10\n"
            
            return response
            
        except Exception as e:
            return f"Error creating schedule: {str(e)}"
    
    def _handle_analytics_request(self, active_tasks: List, context: ContextState) -> str:
        """Handle analytics with enhanced insights"""
        try:
            all_tasks = self.task_storage.get_all_tasks()
            completed_tasks = [t for t in all_tasks if t.get('status') == 'completed']
            
            # Generate insights
            insights = self.smart_scorer.generate_proactive_insights(active_tasks, context)
            
            response = "📊 **Your Productivity Insights:**\n\n"
            
            # Basic stats
            if all_tasks:
                completion_rate = (len(completed_tasks) / len(all_tasks)) * 100
                response += f"**Completion Rate:** {completion_rate:.1f}% ({len(completed_tasks)}/{len(all_tasks)} tasks)\n"
            
            # Current context insights
            response += f"**Current State:** Energy {context.energy_level}/10, {context.available_time_block}min available\n"
            
            if context.current_momentum == "high":
                response += "**Momentum:** 🚀 You're on a roll! Great time to tackle priorities.\n"
            elif context.current_momentum == "low":
                response += "**Momentum:** 🐌 Consider starting with quick wins to build momentum.\n"
            
            # Priority insights
            if active_tasks:
                high_priority = sum(1 for task in active_tasks if task.get('priority') == 'high')
                overdue = sum(1 for task in active_tasks if self._is_overdue(task))
                
                if overdue > 0:
                    response += f"⚠️ **{overdue} overdue tasks** need immediate attention\n"
                if high_priority > 0:
                    response += f"🔴 **{high_priority} high-priority tasks** in your queue\n"
            
            # Proactive insights
            if insights:
                response += "\n**Smart Recommendations:**\n"
                for insight in insights[:2]:  # Top 2 insights
                    response += f"• {insight.message}\n"
            
            return response
            
        except Exception as e:
            return f"I'm having trouble analyzing your productivity: {str(e)}. But you're doing great by staying organized!"
    
    def _handle_general_query(self, query: str, active_tasks: List, context: ContextState, insights: List) -> str:
        """Handle general queries with natural conversation"""
        return self.natural_interface.generate_conversational_response(
            query, [(task, self.smart_scorer.calculate_smart_priority(task, context)) for task in active_tasks[:3]], 
            context, insights
        )
    
    def _is_overdue(self, task: Dict) -> bool:
        """Check if task is overdue"""
        due_date = task.get('due_date')
        if not due_date:
            return False
        try:
            due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            return due_dt < datetime.now()
        except:
            return False
    
    def complete_task_with_learning(self, task_id: str, satisfaction_rating: float = 7.0):
        """Complete task and learn from the experience"""
        try:
            task = self.task_storage.get_task_by_id(task_id)
            if task:
                # Calculate actual duration (placeholder - in real app, track start time)
                estimated = task.get('estimated_hours', 1.0)
                actual_duration = estimated * (0.8 + (satisfaction_rating / 10) * 0.4)  # Rough estimate
                
                # Learn from completion
                self.smart_scorer.learn_from_completion(task, actual_duration, satisfaction_rating)
                
                # Mark as completed
                self.task_storage.update_task(task_id, {'status': 'completed'})
                
                return f"✅ Task completed! Thanks for the feedback - I'm learning your patterns to give better recommendations."
        except Exception as e:
            return f"Error completing task: {str(e)}"
    
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
    

    
    def _handle_crisis_management(self, query: str, active_tasks: List, context: ContextState) -> str:
        """Handle emergency/crisis prioritization with smart assessment"""
        try:
            # Set crisis context
            crisis_context = ContextState(
                current_time=context.current_time,
                energy_level=9.0,  # Crisis energy
                stress_level=8.0,
                available_time_block=context.available_time_block,
                current_momentum="high"
            )
            
            if not active_tasks:
                return "🚨 I understand this is urgent. Let's create specific tasks for what needs immediate attention. What's the most critical issue right now?"
            
            # Calculate crisis priorities
            crisis_tasks = []
            for task in active_tasks:
                score = self.smart_scorer.calculate_smart_priority(task, crisis_context)
                # Boost urgency factor in crisis
                score.final_score += 2.0 if 'urgent' in task.get('title', '').lower() else 0
                crisis_tasks.append((task, score))
            
            crisis_tasks.sort(key=lambda x: x[1].final_score, reverse=True)
            
            response = "🚨 **Crisis Mode Activated**\n\n"
            response += "**Immediate priorities:**\n"
            
            for i, (task, score) in enumerate(crisis_tasks[:3], 1):
                title = task.get('title', 'Untitled')
                response += f"{i}. **{title}** (Critical Score: {score.final_score:.1f}/10)\n"
            
            response += "\n💡 **Crisis Strategy:** Focus on #1 first, delegate what you can, communicate progress to stakeholders."
            
            return response
            
        except Exception as e:
            return f"I'm having trouble with crisis analysis: {str(e)}. Focus on the most urgent task first and let me know what you need help with."
    

    
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
    """Enhanced prioritization agent with natural conversation"""
    print("---ENHANCED PRIORITIZATION AGENT---")
    user_query = state["user_query"]
    conversation_history = state.get("conversation_history", [])
    
    try:
        agent = PrioritizationAgent()
        response = agent.process_query(user_query, conversation_history)
        return {"response": response}
        
    except Exception as e:
        return {"response": f"I'm having some technical difficulties: {str(e)}. But I'm still here to help! Try asking 'what should I work on next?' or 'prioritize my tasks'."}