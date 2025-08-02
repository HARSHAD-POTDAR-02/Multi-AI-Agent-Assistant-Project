def manage_tasks(state):
    """
    Manages tasks based on the user's query.
    """
    print("---MANAGE TASKS---")
    user_query = state["user_query"]
    # In a real application, this agent would interact with a task management system.
    # For this MVP, we'll just return a simple message.
    return {"response": f"Task Manager: I have received your request to: {user_query}"}