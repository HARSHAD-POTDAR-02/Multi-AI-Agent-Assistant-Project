def support_focus(state):
    """
    Supports focus based on the user's query.
    """
    print("---SUPPORT FOCUS---")
    user_query = state["user_query"]
    
    # If this is not actually a focus-related request, redirect to general chat
    focus_keywords = ['focus', 'concentrate', 'deep work', 'distraction', 'block', 'productivity session']
    if not any(keyword in user_query.lower() for keyword in focus_keywords):
        from agents.general_chat import general_chat
        return general_chat(state)
    
    # In a real application, this agent would implement focus techniques.
    # For this MVP, we'll just return a simple message.
    return {"response": f"Focus Support: I have received your request to: {user_query}"}