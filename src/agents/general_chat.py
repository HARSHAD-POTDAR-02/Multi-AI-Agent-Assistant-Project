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
    
    # Initialize Groq client
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY")
    )
    
    from .memory_mixin import get_conversation_context
    
    # Build conversation context
    messages = [
        {
            "role": "system", 
            "content": """You are Simi.ai, a helpful AI assistant. Be natural and conversational.
            Remember previous parts of our conversation when relevant, but don't force references to past messages.
            Respond appropriately to the current message - if it's a simple greeting, give a simple friendly response.
            Be helpful, friendly, and engaging."""
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
            messages.append({"role": "assistant", "content": content})
    
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
            model="openai/gpt-oss-120b",
            temperature=0.9,  # High temperature for creative responses
            max_tokens=1000
        )
        
        response_text = response.choices[0].message.content.strip()
        
        return {"response": response_text}
        
    except Exception as e:
        return {"response": f"I'm having trouble processing that right now. Error: {str(e)}"}