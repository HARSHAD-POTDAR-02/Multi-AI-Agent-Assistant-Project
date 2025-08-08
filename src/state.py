from typing import TypedDict, Optional, Any

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        user_query: The user's request.
        routed_agent: The agent that the router has selected.
        response: The final response from the agent.
        task_action: The action to be performed by the task manager.
        task_id: The ID of the task to be modified.
        task_description: The description of the task.
        supervisor: The supervisor instance.
    """
    user_query: str
    routed_agent: str
    response: str
    task_action: Optional[str]
    task_id: Optional[str]
    task_description: Optional[str]
    supervisor: Optional[Any]
