from langgraph.graph import StateGraph, END
from typing import Dict, Any
from state import GraphState
from agents.supervisor import SupervisorAgent

# Import agents with error handling
# Import all agents with fallbacks
try:
    from agents.email.email_agent import EmailAgent
except ImportError:
    class EmailAgent:
        def process_request(self, state): return {"response": "Email agent not available"}

try:
    from agents.task.task_agent import TaskAgent
except ImportError:
    class TaskAgent:
        def process_request(self, state): return {"response": "Task agent not available"}

try:
    from agents.focus.focus_agent import FocusAgent
except ImportError:
    class FocusAgent:
        def process_request(self, state): return {"response": "Focus agent not available"}

try:
    from agents.general.general_agent import GeneralAgent
except ImportError:
    class GeneralAgent:
        def process_request(self, state): return {"response": "General agent not available"}

# Additional agents (placeholders)
class CalendarAgent:
    def process_request(self, state): return {"response": "Calendar agent not available"}

class AnalyticsAgent:
    def process_request(self, state): return {"response": "Analytics agent not available"}

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
        return supervisor.route_to_agents(state)
    
    # Define all agent nodes
    def email_node(state: Dict[str, Any]) -> Dict[str, Any]:
        return email_agent.process_request(state)
    
    def task_node(state: Dict[str, Any]) -> Dict[str, Any]:
        return task_agent.process_request(state)
    
    def focus_node(state: Dict[str, Any]) -> Dict[str, Any]:
        return focus_agent.process_request(state)
    
    def general_node(state: Dict[str, Any]) -> Dict[str, Any]:
        return general_agent.process_request(state)
    
    def calendar_node(state: Dict[str, Any]) -> Dict[str, Any]:
        return calendar_agent.process_request(state)
    
    def analytics_node(state: Dict[str, Any]) -> Dict[str, Any]:
        return analytics_agent.process_request(state)
    
    def reminder_node(state: Dict[str, Any]) -> Dict[str, Any]:
        return reminder_agent.process_request(state)
    
    # Define conditional routing function
    def route_to_agent(state: Dict[str, Any]) -> str:
        """Route from supervisor to appropriate agent"""
        return supervisor.should_continue(state)
    
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
    
    # Add conditional edges from supervisor to all agents
    workflow.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "email_support": "email_support",
            "task_management": "task_management", 
            "focus_support": "focus_support",
            "general_assistant": "general_assistant",
            "calendar_support": "calendar_support",
            "analytics_support": "analytics_support",
            "reminder_support": "reminder_support"
        }
    )
    
    # All agents return to supervisor with solid edges
    workflow.add_edge("email_support", "supervisor")
    workflow.add_edge("task_management", "supervisor")
    workflow.add_edge("focus_support", "supervisor")
    workflow.add_edge("general_assistant", "supervisor")
    workflow.add_edge("calendar_support", "supervisor")
    workflow.add_edge("analytics_support", "supervisor")
    workflow.add_edge("reminder_support", "supervisor")
    
    # Supervisor connects to END with solid edge
    workflow.add_edge("supervisor", END)
    
    # Compile the graph
    return workflow.compile()
