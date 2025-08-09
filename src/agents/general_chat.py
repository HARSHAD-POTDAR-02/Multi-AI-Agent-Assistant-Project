import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def general_chat(state):
    """
    Handle general conversations and questions like a normal AI assistant
    """
    print("---GENERAL CHAT---")
    user_query = state["user_query"]
    conversation_history = state["conversation_history"]
    
    print(f"Processing query with {len(conversation_history)} messages in history")
    if conversation_history:
        print("Last few messages:")
        for msg in conversation_history[-3:]:
            print(f"- {msg.get('role')}: {msg.get('content')[:50]}...")
    
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    from .memory_mixin import get_conversation_context
    
    # Build conversation context with stronger memory emphasis
    messages = [
        {
            "role": "system", 
            "content": """You are Simi.ai, a helpful AI assistant with perfect memory of our conversation.
            IMPORTANT: You must reference and acknowledge previous parts of the conversation. 
            When the user mentions something from earlier, explicitly acknowledge it.
            Show continuity in the conversation by connecting new responses to previous context.
            Be friendly, informative, and demonstrate that you remember our discussion."""
        }
    ]
    
    # Add conversation history with more context
    recent_history = conversation_history[-8:]  # Increased context window
    for msg in recent_history:
        role = msg.get('role')
        content = msg.get('content', '')
        if role == 'user':
            messages.append({"role": "user", "content": content})
        elif role == 'assistant':
            # Include agent identity in assistant messages
            agent_prefix = f"[{msg.get('agent', 'Assistant')}] " if msg.get('agent') else ''
            messages.append({"role": "assistant", "content": f"{agent_prefix}{content}"})
    
    # Add the current query
    
    # Add current query
    messages.append({"role": "user", "content": user_query})
    
    # Debug: Print what we're sending to LLM
    print(f"Sending {len(messages)} messages to LLM")
    print(f"Conversation history has {len(conversation_history)} items")
    print(f"Messages to LLM: {[(m['role'], m['content'][:50] + '...' if len(m['content']) > 50 else m['content']) for m in messages]}")
    
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="llama3-8b-8192",
            temperature=0.7,  # Higher temperature for more creative responses
            max_tokens=1000
        )
        
        response_text = response.choices[0].message.content.strip()
        
        return {"response": response_text}
        
    except Exception as e:
        return {"response": f"I'm having trouble processing that right now. Error: {str(e)}"}