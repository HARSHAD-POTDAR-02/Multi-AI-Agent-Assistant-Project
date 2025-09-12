import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gmail_service import get_gmail_service, draft_email_with_ai, send_email

def triage_emails(state):
    """
    Triage emails based on the user's query - Web version
    """
    print("---TRIAGE EMAILS---")
    user_query = state["user_query"]
    conversation_history = state.get("conversation_history", [])
    context = state.get("context", {})
    
    # Check if this is a send confirmation
    if user_query.lower().strip() == 'send':
        if 'draft_email' in context:
            draft = context['draft_email']
            service, error = get_gmail_service()
            if error:
                return {"response": f"Gmail setup needed: {error}"}
            
            result = send_email(service, draft['to'], draft['subject'], draft['body'])
            return {"response": f"✅ Email sent successfully!\n\nTO: {draft['to']}\nSUBJECT: {draft['subject']}\n\nBODY:\n{draft['body']}\n\n{result}"}
        else:
            return {"response": "No draft found. Please compose an email first."}
    
    if user_query.lower().strip() == 'cancel':
        return {"response": "Email cancelled."}
    
    if user_query.lower().strip() == 'regenerate':
        if 'draft_email' in context:
            return draft_and_send_email_web(context['draft_email']['original_request'], conversation_history, context)
        else:
            return {"response": "No draft found. Please compose an email first."}
    
    # Check if this is a draft email request
    if any(keyword in user_query.lower() for keyword in ['draft', 'write', 'compose', 'email', 'send']):
        return draft_and_send_email_web(user_query, conversation_history, context)
    
    # Use memory to provide context-aware responses
    user_name = extract_user_name(conversation_history)
    response = f"Email Agent: I have received your request to: {user_query}"
    if user_name:
        response += f" I remember you're {user_name.title()} from our conversation."
    
    return {"response": response}

def draft_and_send_email_web(user_request, conversation_history=None, context=None):
    """Draft and send email automatically for web interface"""
    try:
        # Get Gmail service
        service, error = get_gmail_service()
        if error:
            return {"response": f"Gmail setup needed: {error}"}
        
        if not service:
            return {"response": "Gmail service unavailable. Please check your authentication."}
        
        # Direct parsing from user request
        import re
        
        # Extract email address
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, user_request)
        
        if not emails:
            return {"response": "Please specify a recipient email address. Example: 'send mail to user@example.com say hello'"}
        
        to_email = emails[0]
        
        # Use keyword detection to check if user wants to send chat content
        is_sending_chat = detect_chat_intent(user_request)
        
        # Generate intelligent subject line
        if 'subject' in user_request.lower():
            subject_match = re.search(r'subject[:\s]+([^\n]+)', user_request, re.IGNORECASE)
            if subject_match:
                subject = subject_match.group(1).strip()
                # Clean subject line
                subject = re.sub(r'[\n\r\t]', ' ', subject)
                subject = subject[:100]  # Limit length
        else:
            subject = generate_smart_subject(user_request, conversation_history, is_sending_chat)
        
        # Generate body based on request type
        if is_sending_chat and conversation_history:
            # Always send summary for chat content, not full conversation
            body = create_conversation_summary(conversation_history)
        else:
            body = generate_email_body(user_request, conversation_history)
        
        # Send email directly for web interface
        result = send_email(service, to_email, subject, body)
        
        response = f"""✅ Email sent successfully!

TO: {to_email}
SUBJECT: {subject}

BODY:
{body}

{result}"""
        
        return {"response": response}
        
    except Exception as e:
        print(f"Email processing error: {e}")
        if "invalid_grant" in str(e).lower():
            return {"response": "Gmail authentication expired. Please re-authenticate by running the application and following the OAuth flow."}
        return {"response": f"Error processing email: {str(e)}"}

def format_chat_for_email(conversation_history):
    """Format conversation history for email - always use summary for better readability"""
    if not conversation_history:
        return "No conversation history available."
    
    # Always return summary for better email readability
    return create_conversation_summary(conversation_history)

def create_conversation_summary(conversation_history):
    """Create a concise summary of the conversation using AI"""
    from groq import Groq
    import os
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Warning: GROQ_API_KEY not set. Using fallback summary generation.")
        return create_fallback_summary(conversation_history)
    
    client = Groq(api_key=api_key)
    
    # Prepare conversation text for AI analysis
    conversation_text = ""
    for msg in conversation_history:
        role = msg.get('role', '')
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')
        agent = msg.get('agent', '')
        
        if role == 'user':
            conversation_text += f"User: {content}\n\n"
        elif role == 'assistant':
            agent_name = f" ({agent})" if agent else ""
            conversation_text += f"Assistant{agent_name}: {content}\n\n"
    
    prompt = f"""Please create a comprehensive summary of this conversation between a user and an AI assistant. Include:
1. Key topics discussed
2. Important information shared by the user
3. Main questions asked and answers provided
4. Any action items or follow-ups mentioned
5. Overall context and purpose of the conversation

Conversation:
{conversation_text}

Provide a well-structured, professional summary that captures the essence of the discussion:"""
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.3,
            max_tokens=500
        )
        
        ai_summary = response.choices[0].message.content.strip()
        
        # Add header and footer
        summary = "Conversation Summary\n" + "=" * 20 + "\n\n"
        summary += ai_summary
        summary += "\n\n" + "=" * 20
        summary += f"\nTotal messages: {len(conversation_history)}"
        summary += "\nGenerated by Simi.ai Assistant\n\nThis is a test email from Harshad Potdar testing the email feature."
        
        return summary
        
    except Exception as e:
        print(f"Error generating AI summary: {e}")
        return create_fallback_summary(conversation_history)

def create_fallback_summary(conversation_history):
    """Fallback summary generation when AI is not available"""
    summary = "Conversation Summary\n" + "=" * 20 + "\n\n"
    
    key_topics = []
    user_info = {}
    
    for msg in conversation_history:
        content = msg.get('content', '').lower()
        
        # Extract user information
        if msg.get('role') == 'user':
            if 'my name is' in content:
                name = content.split('my name is')[1].strip().split()[0]
                user_info['name'] = name
            if 'my email' in content or 'email is' in content:
                import re
                emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)
                if emails:
                    user_info['email'] = emails[0]
            if 'creator' in content or 'co founder' in content:
                key_topics.append('User identified as creator/co-founder of Simi.ai')
        
        # Extract key discussion points
        elif msg.get('role') == 'assistant':
            if 'openai' in content.lower() or 'chatgpt' in content.lower():
                key_topics.append('Discussion about AI technology and origins')
            if 'simi' in content.lower() and 'team' in content.lower():
                key_topics.append('Explanation of Simi.ai platform and team')
    
    # Build summary
    if user_info:
        summary += "User Information:\n"
        for key, value in user_info.items():
            summary += f"- {key.title()}: {value}\n"
        summary += "\n"
    
    if key_topics:
        summary += "Key Discussion Points:\n"
        for topic in key_topics:
            summary += f"• {topic}\n"
        summary += "\n"
    
    summary += "=" * 20
    summary += f"\nTotal messages: {len(conversation_history)}"
    summary += "\nGenerated by Simi.ai Assistant\n\nThis is a test email from Harshad Potdar testing the email feature."
    
    return summary

def create_full_conversation(conversation_history):
    """Create full conversation format"""
    formatted_chat = "Here's our conversation:\n\n"
    
    for msg in conversation_history:
        role = msg.get('role', '')
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')
        agent = msg.get('agent', '')
        
        if role == 'user':
            formatted_chat += f"👤 User ({timestamp}):\n{content}\n\n"
        elif role == 'assistant':
            agent_name = f" ({agent})" if agent else ""
            formatted_chat += f"🤖 Simi.ai{agent_name} ({timestamp}):\n{content}\n\n"
    
    formatted_chat += "\n---\nSent via Simi.ai Assistant"
    return formatted_chat

def extract_user_name(conversation_history):
    """Extract user name from conversation history"""
    for msg in conversation_history:
        if msg.get('role') == 'user':
            content = msg.get('content', '').lower()
            if 'my name is' in content:
                name_part = content.split('my name is')[1].strip()
                return name_part.split()[0] if name_part else None
            elif 'i am' in content and len(content.split()) < 10:  # Short intro
                name_part = content.split('i am')[1].strip()
                return name_part.split()[0] if name_part else None
    return None

def extract_user_email(conversation_history):
    """Extract user email from conversation history"""
    import re
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    for msg in conversation_history:
        if msg.get('role') == 'user':
            content = msg.get('content', '')
            if 'my email' in content.lower() or 'email is' in content.lower():
                emails = re.findall(email_pattern, content)
                if emails:
                    return emails[0]
    return None

def detect_chat_intent(user_request):
    """Detect if user wants to send chat/conversation content using keywords"""
    # Use keyword-based detection for reliability
    chat_keywords = [
        'conversation', 'chat', 'convo', 'discussion', 'talked about',
        'chat history', 'conversation history', 'our chat', 'this conversation',
        'what we discussed', 'summary', 'summarize', 'chat summary'
    ]
    
    user_request_lower = user_request.lower()
    
    # Check for explicit chat/conversation keywords
    for keyword in chat_keywords:
        if keyword in user_request_lower:
            return True
    
    # Additional patterns
    if ('send' in user_request_lower and any(word in user_request_lower for word in ['this', 'our', 'the']) and 
        any(word in user_request_lower for word in ['chat', 'conversation', 'discussion'])):
        return True
        
    return False

def generate_smart_subject(user_request, conversation_history, is_sending_chat):
    """Generate intelligent subject line based on content"""
    from groq import Groq
    import os
    import re
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Warning: GROQ_API_KEY not set. Using default subject line.")
        return "Chat Conversation from Simi.ai" if is_sending_chat else "Message from Simi.ai"
        
    client = Groq(api_key=api_key)
    
    if is_sending_chat and conversation_history:
        recent_topics = []
        for msg in conversation_history[-6:]:
            if msg.get('role') == 'user':
                content = msg.get('content', '')[:100]
                recent_topics.append(content)
        
        topics_text = " | ".join(recent_topics)
        
        prompt = f"""Generate ONLY a concise email subject line (max 8 words) based on this conversation:

Recent topics: {topics_text}

Respond with ONLY the subject line, no extra text or formatting:"""
    else:
        prompt = f"""Generate ONLY a concise email subject line (max 8 words) for this request:

"{user_request}"

Respond with ONLY the subject line, no extra text or formatting:"""
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.3,
            max_tokens=15
        )
        
        subject = response.choices[0].message.content.strip()
        # Clean subject line to prevent header issues
        subject = re.sub(r'[\n\r\t]', ' ', subject)  # Remove newlines/tabs
        subject = re.sub(r'^(Subject:|subject:)\s*', '', subject, flags=re.IGNORECASE)  # Remove "Subject:" prefix
        subject = subject.replace('"', '').strip()
        
        # Ensure it's not empty and not too long
        if not subject or len(subject) > 100:
            return "Chat Conversation from Simi.ai" if is_sending_chat else "Message from Simi.ai"
            
        return subject
        
    except Exception as e:
        print(f"Error generating subject: {e}")
        return "Chat Conversation from Simi.ai" if is_sending_chat else "Message from Simi.ai"

def generate_email_body(user_request, conversation_history):
    """Generate intelligent email body for regular emails"""
    from groq import Groq
    import os
    import re
    
    # Extract explicit content first
    if 'say' in user_request.lower():
        say_match = re.search(r'say\s+(.+)', user_request, re.IGNORECASE)
        if say_match:
            return say_match.group(1).strip()
    
    if 'message' in user_request.lower():
        msg_match = re.search(r'message[:\s]+(.+)', user_request, re.IGNORECASE)
        if msg_match:
            return msg_match.group(1).strip()
    
    # Use LLM to generate appropriate email body
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Warning: GROQ_API_KEY not set. Using default message.")
        return "Hello! This is a message sent via Simi.ai assistant."
        
    client = Groq(api_key=api_key)
    
    user_name = extract_user_name(conversation_history)
    user_context = f"From: {user_name}" if user_name else "From: Simi.ai user"
    
    prompt = f"""Write a professional email body for this request:

"{user_request}"
{user_context}

Write ONLY the email body content, no subject line or extra formatting:"""
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.5,
            max_tokens=150
        )
        
        body = response.choices[0].message.content.strip()
        # Clean body to prevent issues
        body = re.sub(r'^(Body:|body:|Email body:|email body:)\s*', '', body, flags=re.IGNORECASE)
        
        return body if body else "Hello! This is a message sent via Simi.ai assistant."
        
    except Exception as e:
        print(f"Error generating email body: {e}")
        return "Hello! This is a message sent via Simi.ai assistant."

