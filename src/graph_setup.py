from langgraph.graph import StateGraph, END
from typing import Dict, Any
from state import GraphState
from agents.supervisor import SupervisorAgent

# Import actual agents and create wrapper classes
from agents.task.task_agent import TaskAgent

class EmailAgent:
    def process_request(self, state):
        from agents.email_triage_web import triage_emails
        return triage_emails(state)

class FocusAgent:
    def process_request(self, state):
        from agents.focus.focus_agent import support_focus
        return support_focus(state)

class GeneralAgent:
    def process_request(self, state):
        from agents.general_chat import general_chat
        return general_chat(state)

class CalendarAgent:
    def process_request(self, state):
        from agents.calendar_orchestrator import orchestrate_calendar
        return orchestrate_calendar(state)

class AnalyticsAgent:
    def process_request(self, state):
        from agents.analytics_dashboard import show_analytics
        return show_analytics(state)

class ReminderAgent:
    def process_request(self, state):
        from agents.smart_reminders import send_reminders
        return send_reminders(state)




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
            "reminder_support": "reminder_support",
            "END": END
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
