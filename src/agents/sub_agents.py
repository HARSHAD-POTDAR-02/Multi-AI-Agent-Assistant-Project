def handle_sub_agents(state):
    """
    Handles sub-agents for meetings and projects.
    """
    print("---HANDLE SUB-AGENTS---")
    user_query = state["user_query"]
    # In a real application, this agent would spawn and manage sub-agents.
    # For this MVP, we'll just return a simple message.
    return {"response": f"Sub-Agents: I have received your request to: {user_query}"}