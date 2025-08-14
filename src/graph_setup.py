from langgraph.graph import StateGraph, END
from state import GraphState

# Import agents with error handling
try:
    from agents.task_manager import manage_tasks
except ImportError as e:
    print(f"Warning: Could not import task_manager: {e}")
    def manage_tasks(state): return {"response": "Task manager not available"}

try:
    from agents.prioritization import prioritization_agent
except ImportError as e:
    print(f"Warning: Could not import prioritization: {e}")
    def prioritization_agent(state): return {"response": "Prioritization not available"}

try:
    from agents.general_chat import general_chat
except ImportError as e:
    print(f"Warning: Could not import general_chat: {e}")
    def general_chat(state): return {"response": "Hello! I'm having some technical difficulties."}

# Import other agents with fallbacks
try:
    from agents.calendar_orchestrator import orchestrate_calendar
except ImportError:
    def orchestrate_calendar(state): return {"response": "Calendar not available"}

try:
    from agents.email_triage_web import triage_emails
except ImportError:
    def triage_emails(state): return {"response": "Email not available"}

try:
    from agents.focus.focus_agent import support_focus
except ImportError:
    def support_focus(state): return {"response": "Focus support not available"}

try:
    from agents.smart_reminders import send_reminders
except ImportError:
    def send_reminders(state): return {"response": "Reminders not available"}

try:
    from agents.sub_agents import handle_sub_agents
except ImportError:
    def handle_sub_agents(state): return {"response": "Sub agents not available"}

try:
    from agents.analytics_dashboard import show_analytics
except ImportError:
    def show_analytics(state): return {"response": "Analytics not available"}


def build_graph():
    """
    Builds the graph.
    """
    workflow = StateGraph(GraphState)

    # Add the nodes
    workflow.add_node("task_manager", manage_tasks)
    workflow.add_node("prioritization", prioritization_agent)
    workflow.add_node("calendar_orchestrator", orchestrate_calendar)
    workflow.add_node("email_triage", triage_emails)
    workflow.add_node("focus_support", support_focus)
    workflow.add_node("smart_reminders", send_reminders)
    workflow.add_node("sub_agents", handle_sub_agents)
    workflow.add_node("analytics_dashboard", show_analytics)
    workflow.add_node("general_chat", general_chat)

    # Set the entry point to be conditional on the 'routed_agent'
    workflow.set_conditional_entry_point(
        lambda x: x["routed_agent"],
        {
            "task_manager": "task_manager",
            "prioritization": "prioritization",
            "calendar_orchestrator": "calendar_orchestrator",
            "email_triage": "email_triage",
            "focus_support": "focus_support",
            "smart_reminders": "smart_reminders",
            "sub_agents": "sub_agents",
            "analytics_dashboard": "analytics_dashboard",
            "general_chat": "general_chat",
        },
    )

    # Add the end points
    workflow.add_edge("task_manager", END)
    workflow.add_edge("prioritization", END)
    workflow.add_edge("calendar_orchestrator", END)
    workflow.add_edge("email_triage", END)
    workflow.add_edge("focus_support", END)
    workflow.add_edge("smart_reminders", END)
    workflow.add_edge("sub_agents", END)
    workflow.add_edge("analytics_dashboard", END)
    workflow.add_edge("general_chat", END)

    # Compile the graph
    graph = workflow.compile()
    return graph
