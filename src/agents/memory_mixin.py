def get_conversation_context(conversation_history, max_messages=10):
    """Extract conversation context for any agent"""
    if not conversation_history:
        return ""
    
    # Get recent messages (including current)
    recent_messages = conversation_history[-max_messages:]
    
    # Build context string
    context_parts = []
    for msg in recent_messages:
        role = msg.get('role', '')
        content = msg.get('content', '')
        agent = msg.get('agent', '') if role == 'assistant' else ''
        
        if role == 'user':
            context_parts.append(f"User: {content}")
        elif role == 'assistant':
            agent_prefix = f"({agent})" if agent else ''
            context_parts.append(f"Assistant{agent_prefix}: {content}")
    
    if context_parts:
        context = "\n\nPrevious Conversation:\n" + "\n".join(context_parts)
        return context
    
    return ""

def add_memory_to_response(response, conversation_history):
    """Add memory demonstration to any agent response"""
    context = get_conversation_context(conversation_history)
    if context and len(conversation_history) > 1:
        # Don't append the context to the response - it's already used in the conversation
        return response
    return response
