import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from groq import Groq
from .enhanced_models import ContextState, ProactiveInsight

class NaturalLanguageInterface:
    def __init__(self):
        try:
            self.groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        except:
            self.groq_client = None
    
    def generate_conversational_response(self, 
                                       query: str, 
                                       prioritized_tasks: List, 
                                       context: ContextState,
                                       insights: List[ProactiveInsight] = None) -> str:
        """Generate natural, conversational responses"""
        
        if not self.groq_client:
            return self._generate_fallback_response(query, prioritized_tasks, context)
        
        try:
            # Prepare context for LLM
            context_info = self._prepare_context_info(context, insights or [])
            task_info = self._prepare_task_info(prioritized_tasks)
            
            # Create conversational prompt
            prompt = f"""You are Simi, a friendly and intelligent productivity assistant. You understand the user's work patterns, energy levels, and context to provide personalized advice.

Current Context:
{context_info}

User's Tasks (prioritized):
{task_info}

User Query: "{query}"

Respond as Simi in a natural, conversational way. Be:
- Friendly and encouraging
- Specific and actionable
- Context-aware and personalized
- Supportive but not overly enthusiastic
- Brief but helpful (2-3 sentences max)

Use emojis sparingly and naturally. Address the user directly and provide clear next steps."""

            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192",
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"LLM response error: {e}")
            return self._generate_fallback_response(query, prioritized_tasks, context)
    
    def _prepare_context_info(self, context: ContextState, insights: List[ProactiveInsight]) -> str:
        """Prepare context information for LLM"""
        info = []
        
        # Time and energy
        current_time = context.current_time.strftime("%I:%M %p")
        info.append(f"Time: {current_time}")
        info.append(f"Energy Level: {context.energy_level}/10")
        info.append(f"Available Time: {context.available_time_block} minutes")
        
        # Current state
        if context.focus_mode:
            info.append("Currently in focus mode")
        
        info.append(f"Current Momentum: {context.current_momentum}")
        
        if context.time_until_next_meeting:
            info.append(f"Next meeting in {context.time_until_next_meeting} minutes")
        
        # Recent activity
        if context.recent_completions:
            recent = ", ".join(context.recent_completions[-2:])
            info.append(f"Recently completed: {recent}")
        
        # Insights
        if insights:
            urgent_insights = [i for i in insights if i.priority >= 4]
            if urgent_insights:
                info.append(f"Important insights: {urgent_insights[0].message}")
        
        return "\n".join(info)
    
    def _prepare_task_info(self, prioritized_tasks: List) -> str:
        """Prepare task information for LLM"""
        if not prioritized_tasks:
            return "No active tasks found."
        
        task_info = []
        for i, (task, score) in enumerate(prioritized_tasks[:5], 1):
            title = task.get('title', 'Untitled')
            priority_score = getattr(score, 'final_score', score) if hasattr(score, 'final_score') else score
            reasoning = getattr(score, 'reasoning', '') if hasattr(score, 'reasoning') else ''
            
            due_info = ""
            if task.get('due_date'):
                try:
                    due_dt = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                    days_until = (due_dt - datetime.now()).days
                    if days_until < 0:
                        due_info = " (OVERDUE)"
                    elif days_until == 0:
                        due_info = " (due today)"
                    elif days_until <= 2:
                        due_info = f" (due in {days_until} days)"
                except:
                    pass
            
            task_line = f"{i}. {title}{due_info} - Score: {priority_score}/10"
            if reasoning:
                task_line += f" ({reasoning})"
            
            task_info.append(task_line)
        
        return "\n".join(task_info)
    
    def _generate_fallback_response(self, query: str, prioritized_tasks: List, context: ContextState) -> str:
        """Generate fallback response when LLM is unavailable"""
        query_lower = query.lower()
        
        # Handle common queries with personalized responses
        if any(word in query_lower for word in ['overwhelmed', 'too much', 'stressed']):
            return self._handle_overwhelmed_response(prioritized_tasks, context)
        
        elif any(word in query_lower for word in ['what should i', 'what to work', 'next task']):
            return self._handle_next_task_response(prioritized_tasks, context)
        
        elif any(word in query_lower for word in ['prioritize', 'priority', 'order']):
            return self._handle_prioritization_response(prioritized_tasks, context)
        
        elif any(word in query_lower for word in ['energy', 'tired', 'low energy']):
            return self._handle_energy_response(prioritized_tasks, context)
        
        elif any(word in query_lower for word in ['time', 'schedule', 'when']):
            return self._handle_timing_response(prioritized_tasks, context)
        
        else:
            return self._handle_general_response(prioritized_tasks, context)
    
    def _handle_overwhelmed_response(self, tasks: List, context: ContextState) -> str:
        """Handle overwhelmed user"""
        if not tasks:
            return "I understand you're feeling overwhelmed. Let's start by creating some tasks to organize your thoughts. What's the most pressing thing on your mind right now?"
        
        # Focus on just the top task
        top_task = tasks[0][0] if tasks else None
        if top_task:
            title = top_task.get('title', 'your top priority task')
            response = f"I hear you're feeling overwhelmed. Let's take it one step at a time. "
            response += f"Right now, just focus on '{title}' - that's your highest priority. "
            
            if context.energy_level <= 5.0:
                response += "Since your energy is a bit low, maybe break it into smaller pieces first?"
            else:
                response += "You've got this! 💪"
            
            return response
        
        return "When feeling overwhelmed, focus on just one task at a time. What's the most important thing you need to do today?"
    
    def _handle_next_task_response(self, tasks: List, context: ContextState) -> str:
        """Handle 'what should I work on next' queries"""
        if not tasks:
            return "You don't have any active tasks right now. Want to create some? Just tell me what you need to work on!"
        
        top_task = tasks[0][0]
        score = tasks[0][1]
        title = top_task.get('title', 'Untitled')
        
        response = f"I'd recommend working on '{title}' next. "
        
        # Add context-aware reasoning
        if hasattr(score, 'reasoning') and score.reasoning:
            response += f"It's a good fit because of {score.reasoning}. "
        
        # Add time-based advice
        estimated_hours = top_task.get('estimated_hours', 1.0)
        available_hours = context.available_time_block / 60.0
        
        if estimated_hours > available_hours:
            response += f"Though it might take {estimated_hours} hours and you have {available_hours:.1f} hours available, so consider breaking it down."
        elif estimated_hours <= 0.5:
            response += "It's a quick task, perfect for building momentum!"
        
        return response
    
    def _handle_prioritization_response(self, tasks: List, context: ContextState) -> str:
        """Handle prioritization requests"""
        if not tasks:
            return "No tasks to prioritize right now. Create some tasks first, then I can help you organize them by importance and urgency!"
        
        response = f"Here's your priority order based on deadlines, energy levels, and context:\n\n"
        
        for i, (task, score) in enumerate(tasks[:3], 1):
            title = task.get('title', 'Untitled')
            priority_score = getattr(score, 'final_score', score) if hasattr(score, 'final_score') else score
            
            response += f"{i}. {title} (Score: {priority_score}/10)\n"
        
        # Add personalized advice
        if context.energy_level >= 7.0:
            response += "\nYour energy is good - perfect time to tackle the top priority!"
        elif context.energy_level <= 4.0:
            response += "\nYour energy is low - consider starting with something easier to build momentum."
        
        return response
    
    def _handle_energy_response(self, tasks: List, context: ContextState) -> str:
        """Handle energy-related queries"""
        energy_level = context.energy_level
        
        if energy_level <= 3.0:
            return "Your energy is quite low right now. Consider taking a short break, having a snack, or doing some light tasks to build momentum. Maybe start with quick wins?"
        elif energy_level <= 5.0:
            return "Your energy is moderate. Good time for routine tasks or breaking down complex work into smaller pieces. Don't push too hard right now."
        elif energy_level >= 8.0:
            return "Your energy is high! Perfect time for deep work or tackling those complex tasks you've been putting off. Make the most of this peak time! 🚀"
        else:
            return "Your energy level is good. You can handle most tasks right now. Consider your priorities and available time."
    
    def _handle_timing_response(self, tasks: List, context: ContextState) -> str:
        """Handle timing and scheduling queries"""
        available_minutes = context.available_time_block
        
        if available_minutes < 30:
            return f"You have {available_minutes} minutes available - perfect for quick tasks like emails, calls, or small updates."
        elif available_minutes < 90:
            return f"You have {available_minutes} minutes - good for medium tasks or breaking down larger work into focused chunks."
        else:
            return f"You have {available_minutes} minutes - excellent for deep work or tackling complex tasks that need sustained focus."
    
    def _handle_general_response(self, tasks: List, context: ContextState) -> str:
        """Handle general queries"""
        if not tasks:
            return "I'm here to help you prioritize your work! Create some tasks first, then I can provide personalized recommendations based on your energy, time, and deadlines."
        
        task_count = len([t for t in tasks if t[0].get('status') != 'completed'])
        
        response = f"You have {task_count} active tasks. "
        
        if context.energy_level >= 7.0 and context.available_time_block >= 60:
            response += "Your energy is good and you have time - great moment to make progress!"
        elif context.energy_level <= 4.0:
            response += "Your energy is low - consider starting with something easy to build momentum."
        else:
            response += "Ready to tackle your priorities?"
        
        return response
    
    def generate_proactive_message(self, insights: List[ProactiveInsight], context: ContextState) -> Optional[str]:
        """Generate proactive messages based on insights"""
        if not insights:
            return None
        
        # Get highest priority insight
        top_insight = max(insights, key=lambda x: x.priority)
        
        if top_insight.type == "opportunity" and context.energy_level >= 7.0:
            return f"💡 {top_insight.message}"
        elif top_insight.type == "warning" and top_insight.action_required:
            return f"⚠️ {top_insight.message}"
        elif top_insight.type == "celebration":
            return f"🎉 {top_insight.message}"
        
        return None