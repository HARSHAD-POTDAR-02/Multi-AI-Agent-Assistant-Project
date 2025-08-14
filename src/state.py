from typing import TypedDict, Optional, Any, List, Dict

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        user_query: The user's request.
        routed_agent: The agent that the router has selected.
        response: str
        conversation_history: List of conversation messages
        context: Additional context for the conversation
        session_id: Unique session identifier
        task_action: The action to be performed by the task manager.
        task_id: The ID of the task to be modified.
        task_description: The description of the task.
        supervisor: The supervisor instance.
        focus_session_active: Whether a focus session is currently active.
        focus_session_type: Type of focus session (pomodoro, deep work, etc.).
    """
    user_query: str
    routed_agent: str
    response: str
    conversation_history: List[Dict[str, Any]]
    context: Dict[str, Any]
    session_id: str
    task_action: Optional[str]
    task_id: Optional[str]
    task_description: Optional[str]
    supervisor: Optional[Any]
    focus_session_active: Optional[bool]
    focus_session_type: Optional[str]
