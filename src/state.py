from typing import TypedDict

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        user_query: The user's request.
        routed_agent: The agent that the router has selected.
        response: The final response from the agent.
    """
    user_query: str
    routed_agent: str
    response: str
