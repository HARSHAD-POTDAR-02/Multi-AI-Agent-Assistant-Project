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
    conversation_history = state.get("conversation_history", [])
    
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    # Build conversation context
    messages = [
        {
            "role": "system", 
            "content": "You are Simi.ai, a helpful AI assistant. You can have normal conversations, answer questions, provide explanations, and chat casually with users. Be friendly, informative, and engaging."
        }
    ]
    
    # Add recent conversation history for context
    for item in conversation_history[-5:]:  # Last 5 interactions
        messages.append({"role": "user", "content": item.get("user_query", "")})
        messages.append({"role": "assistant", "content": item.get("response", "")})
    
    # Add current query
    messages.append({"role": "user", "content": user_query})
    
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="llama3-8b-8192",
            temperature=0.7,  # Higher temperature for more creative responses
            max_tokens=1000
        )
        
        return {"response": response.choices[0].message.content.strip()}
        
    except Exception as e:
        return {"response": f"I'm having trouble processing that right now. Error: {str(e)}"}