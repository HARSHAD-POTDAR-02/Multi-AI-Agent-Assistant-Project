from typing import Dict, Any, List
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
import os

class SupervisorAgent:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0.1,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="openai/gpt-oss-120b"
        )
        
        self.available_agents = [
            "email_support",
            "task_management", 
            "focus_support",
            "general_assistant",
            "calendar_support",
            "analytics_support",
            "reminder_support"
        ]
    
    def route_to_agents(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Supervisor decides which agent(s) to use and coordinates the workflow"""
        
        user_query = state.get('user_query', '')
        conversation_history = state.get('conversation_history', [])
        session_id = state.get('session_id', 'unknown')
        
        # Analyze query complexity
        query_analysis = self._analyze_query(user_query)
        
        # Create context from conversation history
        context = ""
        if conversation_history:
            recent_messages = conversation_history[-3:]  # Last 3 messages for context
            context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])
        
        system_prompt = f"""You are a Supervisor Agent that coordinates multiple specialized agents.

Available agents:
- email_support: Handle email sending, reading, managing
- task_management: Create, update, delete tasks and projects (PRIORITY for any task operations with #ID)
- focus_support: Start/stop focus sessions, block distractions
- general_assistant: General questions, conversations, help
- calendar_support: Schedule meetings, manage calendar events
- analytics_support: Show analytics, reports, insights
- reminder_support: Set reminders, notifications, alerts

IMPORTANT ROUTING RULES:
- Analyze the user's request
- Decise which agent(s) to use
- Determine if multiple agents are needed for coordination
- Set the next action
- ANY query with "task #" or "#" followed by numbers goes to task_management
- ANY query with "update task", "complete task", "delete task" goes to task_management
- ANY query with "make task" or "change task" goes to task_management

Recent conversation context:
{context}

User query: {user_query}

Respond with ONLY the agent name that should handle this request. Choose ONE:
- email_support
- task_management  
- focus_support
- general_assistant
- calendar_support
- analytics_support
- reminder_support

If the request needs multiple agents, start with the most important one."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_query)
        ]
        
        response = self.llm.invoke(messages)
        selected_agent = response.content.strip().lower()
        
        # Validate agent selection
        if selected_agent not in self.available_agents:
            selected_agent = "general_assistant"
        
        # Update state with comprehensive supervisor decision
        coordination_needed = self._needs_coordination(user_query)
        confidence_score = self._calculate_confidence(user_query, selected_agent)
        
        state['routed_agent'] = selected_agent
        state['supervisor'] = {
            'session_id': session_id,
            'selected_agent': selected_agent,
            'confidence_score': confidence_score,
            'coordination_needed': coordination_needed,
            'query_analysis': query_analysis,
            'routing_reason': self._get_routing_reason(user_query, selected_agent),
            'alternative_agents': self._get_alternative_agents(user_query, selected_agent),
            'estimated_complexity': query_analysis['complexity'],
            'requires_followup': query_analysis['followup_likely'],
            'context_used': len(conversation_history) > 0,
            'next_steps': self._plan_next_steps(user_query, selected_agent),
            'routing_decision': f"🤖 Supervisor: Routing to {selected_agent} (confidence: {confidence_score}%)"
        }
        
        # Add supervisor routing info to response for visibility
        print(f"[SUPERVISOR] Query: '{user_query}'")
        print(f"[SUPERVISOR] Selected: {selected_agent} (confidence: {confidence_score}%)")
        print(f"[SUPERVISOR] Complexity: {query_analysis['complexity']}")
        print(f"[SUPERVISOR] Coordination needed: {coordination_needed}")
        
        return state
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Comprehensive query analysis"""
        query_lower = query.lower()
        
        # Complexity analysis
        complexity_indicators = {
            'simple': ['hi', 'hello', 'thanks', 'yes', 'no', 'ok'],
            'medium': ['create', 'send', 'start', 'stop', 'show', 'get'],
            'complex': ['schedule and', 'create task and', 'prepare for', 'setup', 'organize']
        }
        
        complexity = 'simple'
        if any(indicator in query_lower for indicator in complexity_indicators['complex']):
            complexity = 'complex'
        elif any(indicator in query_lower for indicator in complexity_indicators['medium']):
            complexity = 'medium'
        
        return {
            'complexity': complexity,
            'word_count': len(query.split()),
            'has_multiple_actions': ' and ' in query_lower or ' then ' in query_lower,
            'followup_likely': complexity == 'complex' or 'prepare' in query_lower,
            'urgency_indicators': any(word in query_lower for word in ['urgent', 'asap', 'immediately', 'now']),
            'question_type': 'question' if '?' in query else 'command'
        }
    
    def _needs_coordination(self, query: str) -> bool:
        """Determine if query needs multiple agents"""
        coordination_keywords = [
            "and then", "after that", "also", "schedule and send", 
            "create task and email", "focus session and", "morning routine",
            "prepare for", "setup", "organize"
        ]
        
        return any(keyword in query.lower() for keyword in coordination_keywords)
    
    def _calculate_confidence(self, query: str, selected_agent: str) -> int:
        """Calculate confidence score for agent selection"""
        query_lower = query.lower()
        
        # Agent-specific keywords with priority rules
        agent_keywords = {
            'email_support': ['email', 'send', 'mail', 'message', 'reply'],
            'task_management': ['task #', '#1', '#2', '#3', '#4', '#5', '#6', '#7', '#8', '#9', 'update task', 'complete task', 'delete task', 'make task', 'change task', 'task', 'todo', 'to-do', 'project', 'deadline', 'create', 'add', 'list', 'complete', 'finish', 'update', 'delete', 'manage'],
            'focus_support': ['focus', 'concentrate', 'distraction', 'session'],
            'general_assistant': ['help', 'what', 'how', 'explain', 'tell me']
        }
        
        keywords = agent_keywords.get(selected_agent, [])
        matches = sum(1 for keyword in keywords if keyword in query_lower)
        
        if matches >= 2:
            return 95
        elif matches == 1:
            return 80
        else:
            return 60
    
    def _get_routing_reason(self, query: str, selected_agent: str) -> str:
        """Explain why this agent was selected"""
        reasons = {
            'email_support': 'Query contains email-related keywords',
            'task_management': 'Query involves task or project management',
            'focus_support': 'Query relates to focus or productivity',
            'general_assistant': 'General query or fallback selection'
        }
        return reasons.get(selected_agent, 'Default routing')
    
    def _get_alternative_agents(self, query: str, selected_agent: str) -> List[str]:
        """Get alternative agents that could handle this query"""
        alternatives = [agent for agent in self.available_agents if agent != selected_agent]
        return alternatives[:2]  # Return top 2 alternatives
    
    def _plan_next_steps(self, query: str, selected_agent: str) -> List[str]:
        """Plan potential next steps based on query"""
        if self._needs_coordination(query):
            return [
                "Execute primary action",
                "Check for follow-up requirements", 
                "Coordinate with additional agents if needed"
            ]
        return ["Execute requested action"]
    
    def should_continue(self, state: Dict[str, Any]) -> str:
        """Determine if we should continue to agents or end"""
        # If there's already a response, we're done
        if state.get('response'):
            return "END"
        
        # Otherwise, route to the selected agent
        return state.get('routed_agent', 'general_assistant')
    
    def finalize_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Final processing before returning to user"""
        
        # Enhance response with supervisor info
        supervisor_info = state.get('supervisor', {})
        current_response = state.get('response', '')
        
        if supervisor_info.get('coordination_needed', False):
            # Add coordination context
            enhanced_response = f"{current_response}\n\n🤖 *Supervisor: This task may benefit from additional coordination. Let me know if you need help with related actions.*"
            state['response'] = enhanced_response
        else:
            # Add subtle supervisor acknowledgment
            enhanced_response = f"{current_response}\n\n*Handled by: {supervisor_info.get('selected_agent', 'unknown')} via Supervisor*"
            state['response'] = enhanced_response
        
        return state