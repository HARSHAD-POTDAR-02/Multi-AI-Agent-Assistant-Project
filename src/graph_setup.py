from langgraph.graph import StateGraph, END
from typing import Dict, Any
from state import GraphState
from agents.supervisor import SupervisorAgent

# Import agents with error handling
# Import all agents with fallbacks
try:
    from agents.email_triage_web import triage_emails
    class EmailAgent:
        def process_request(self, state): 
            return triage_emails(state)
except ImportError:
    class EmailAgent:
        def process_request(self, state): return {"response": "Email agent not available"}

try:
    from agents.task_manager import manage_tasks
    class TaskAgent:
        def process_request(self, state): 
            return manage_tasks(state)
except ImportError:
    class TaskAgent:
        def process_request(self, state): return {"response": "Task agent not available"}

try:
    from agents.focus.focus_agent import support_focus
    class FocusAgent:
        def process_request(self, state): 
            return support_focus(state)
except ImportError:
    class FocusAgent:
        def process_request(self, state): return {"response": "Focus agent not available"}

try:
    from agents.general_chat import general_chat
    class GeneralAgent:
        def process_request(self, state): 
            result = general_chat(state)
            return result
except ImportError:
    class GeneralAgent:
        def process_request(self, state): return {"response": "General agent not available"}

# Additional agents with actual functions
try:
    from agents.calendar_orchestrator import orchestrate_calendar
    class CalendarAgent:
        def process_request(self, state): 
            return orchestrate_calendar(state)
except ImportError:
    class CalendarAgent:
        def process_request(self, state): return {"response": "Calendar agent not available"}

try:
    from agents.analytics_dashboard import show_analytics
    class AnalyticsAgent:
        def process_request(self, state): 
            return show_analytics(state)
except ImportError:
    class AnalyticsAgent:
        def process_request(self, state): return {"response": "Analytics agent not available"}

try:
    from agents.smart_reminders import send_reminders
    class ReminderAgent:
        def process_request(self, state): 
            return send_reminders(state)
except ImportError:
    class ReminderAgent:
        def process_request(self, state): return {"response": "Reminder agent not available"}


def build_graph():
    """Build the supervisor-based agent workflow graph"""
    
    # Initialize all agents
    supervisor = SupervisorAgent()
    email_agent = EmailAgent()
    task_agent = TaskAgent()
    focus_agent = FocusAgent()
    general_agent = GeneralAgent()
    calendar_agent = CalendarAgent()
    analytics_agent = AnalyticsAgent()
    reminder_agent = ReminderAgent()
    
    # Define supervisor node
    def supervisor_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Supervisor makes routing decisions"""
        result = supervisor.route_to_agents(state)
        if 'messages' not in result:
            result['messages'] = state.get('messages', []) + ['supervisor_routing']
        return result
    
    # Define all agent nodes
    def email_node(state: Dict[str, Any]) -> Dict[str, Any]:
        result = email_agent.process_request(state)
        result['messages'] = state.get('messages', []) + ['email_response']
        return result
    
    def task_node(state: Dict[str, Any]) -> Dict[str, Any]:
        result = task_agent.process_request(state)
        result['messages'] = state.get('messages', []) + ['task_response']
        return result
    
    def focus_node(state: Dict[str, Any]) -> Dict[str, Any]:
        result = focus_agent.process_request(state)
        result['messages'] = state.get('messages', []) + ['focus_response']
        return result
    
    def general_node(state: Dict[str, Any]) -> Dict[str, Any]:
        result = general_agent.process_request(state)
        result['messages'] = state.get('messages', []) + ['general_response']
        return result
    
    def calendar_node(state: Dict[str, Any]) -> Dict[str, Any]:
        result = calendar_agent.process_request(state)
        result['messages'] = state.get('messages', []) + ['calendar_response']
        return result
    
    def analytics_node(state: Dict[str, Any]) -> Dict[str, Any]:
        result = analytics_agent.process_request(state)
        result['messages'] = state.get('messages', []) + ['analytics_response']
        return result
    
    def reminder_node(state: Dict[str, Any]) -> Dict[str, Any]:
        result = reminder_agent.process_request(state)
        result['messages'] = state.get('messages', []) + ['reminder_response']
        return result
    

    
    # Create the graph
    workflow = StateGraph(GraphState)
    
    # Add all nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("email_support", email_node)
    workflow.add_node("task_management", task_node)
    workflow.add_node("focus_support", focus_node)
    workflow.add_node("general_assistant", general_node)
    workflow.add_node("calendar_support", calendar_node)
    workflow.add_node("analytics_support", analytics_node)
    workflow.add_node("reminder_support", reminder_node)
    
    # Set entry point to supervisor
    workflow.set_entry_point("supervisor")
    
    # Supervisor decides whether to route to agent or end
    def should_continue(state):
        messages = state.get('messages', [])
        if len(messages) > 1:  # If agent has responded, end
            return END
        return state.get('routed_agent', 'general_assistant')
    
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "email_support": "email_support",
            "task_management": "task_management",
            "focus_support": "focus_support", 
            "general_assistant": "general_assistant",
            "calendar_support": "calendar_support",
            "analytics_support": "analytics_support",
            "reminder_support": "reminder_support",
            END: END
        }
    )
    
    # All agents return to supervisor
    workflow.add_edge("email_support", "supervisor")
    workflow.add_edge("task_management", "supervisor")
    workflow.add_edge("focus_support", "supervisor")
    workflow.add_edge("general_assistant", "supervisor")
    workflow.add_edge("calendar_support", "supervisor")
    workflow.add_edge("analytics_support", "supervisor")
    workflow.add_edge("reminder_support", "supervisor")
    
    # Compile the graph
    return workflow.compile()
