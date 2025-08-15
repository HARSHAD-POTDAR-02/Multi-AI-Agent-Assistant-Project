from typing import TypedDict, Optional, Any, List, Dict, Annotated
from operator import add

class GraphState(TypedDict):
    """
    Represents the state of our graph.
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
    messages: Annotated[List[str], add]
