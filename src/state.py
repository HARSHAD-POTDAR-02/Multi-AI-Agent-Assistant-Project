from typing import TypedDict, List, Dict, Any

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        user_query: The user's request.
        routed_agent: The agent that the router has selected.
        response: The final response from the agent.
        conversation_history: List of previous interactions.
        context: Additional context data for agents.
    """
    user_query: str
    routed_agent: str
    response: str
    conversation_history: List[Dict[str, Any]]
    context: Dict[str, Any]
