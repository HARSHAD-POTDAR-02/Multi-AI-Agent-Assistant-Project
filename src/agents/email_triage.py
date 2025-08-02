def triage_emails(state):
    """
    Triage emails based on the user's query.
    """
    print("---TRIAGE EMAILS---")
    user_query = state["user_query"]
    # In a real application, this agent would interact with an email API.
    # For this MVP, we'll just return a simple message.
    return {"response": f"Email Triage: I have received your request to: {user_query}"}