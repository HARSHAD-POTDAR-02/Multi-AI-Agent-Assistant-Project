from langgraph.graph import StateGraph, END
from agents.router import route_request
from agents.task_manager import manage_tasks
from agents.prioritization_engine import prioritize_tasks
from agents.calendar_orchestrator import orchestrate_calendar
from agents.email_triage import triage_emails
from agents.focus_support import support_focus
from agents.smart_reminders import send_reminders
from agents.sub_agents import handle_sub_agents
from agents.analytics_dashboard import show_analytics
from state import GraphState


def router_node(state):
    """
    The main router node.
    """
    print("---ROUTER---")
    user_query = state["user_query"]
    routed_agent = route_request(user_query)
    return {"routed_agent": routed_agent}


def build_graph():
    """
    Builds the graph.
    """
    workflow = StateGraph(GraphState)

    # Add the nodes
    workflow.add_node("router", router_node)
    workflow.add_node("task_manager", manage_tasks)
    workflow.add_node("prioritization_engine", prioritize_tasks)
    workflow.add_node("calendar_orchestrator", orchestrate_calendar)
    workflow.add_node("email_triage", triage_emails)
    workflow.add_node("focus_support", support_focus)
    workflow.add_node("smart_reminders", send_reminders)
    workflow.add_node("sub_agents", handle_sub_agents)
    workflow.add_node("analytics_dashboard", show_analytics)

    # Set the entry point
    workflow.set_entry_point("router")

    # Add the conditional edges
    workflow.add_conditional_edges(
        "router",
        lambda x: x["routed_agent"],
        {
            "task_manager": "task_manager",
            "prioritization_engine": "prioritization_engine",
            "calendar_orchestrator": "calendar_orchestrator",
            "email_triage": "email_triage",
            "focus_support": "focus_support",
            "smart_reminders": "smart_reminders",
            "sub_agents": "sub_agents",
            "analytics_dashboard": "analytics_dashboard",
        },
    )

    # Add the end points
    workflow.add_edge("task_manager", END)
    workflow.add_edge("prioritization_engine", END)
    workflow.add_edge("calendar_orchestrator", END)
    workflow.add_edge("email_triage", END)
    workflow.add_edge("focus_support", END)
    workflow.add_edge("smart_reminders", END)
    workflow.add_edge("sub_agents", END)
    workflow.add_edge("analytics_dashboard", END)

    # Compile the graph
    graph = workflow.compile()
    return graph
