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
    
    return {"response": f"Email Triage: I have received your request to: {user_query}"}

def draft_and_send_email_web(user_request, conversation_history=None, context=None):
    """Draft and send email automatically for web interface"""
    try:
        # Get Gmail service
        service, error = get_gmail_service()
        if error:
            return {"response": f"Gmail setup needed: {error}"}
        
        # Direct parsing from user request
        import re
        
        # Extract email address
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, user_request)
        
        if not emails:
            return {"response": "Please specify a recipient email address. Example: 'send mail to user@example.com say hello'"}
        
        to_email = emails[0]
        
        # Extract subject
        subject = "Message from Simi.ai"
        if 'subject' in user_request.lower():
            subject_match = re.search(r'subject[:\s]+([^\n]+)', user_request, re.IGNORECASE)
            if subject_match:
                subject = subject_match.group(1).strip()
        elif 'about' in user_request.lower():
            about_match = re.search(r'about\s+([^\n]+)', user_request, re.IGNORECASE)
            if about_match:
                subject = about_match.group(1).strip()
        
        # Extract body
        body = "Hello! This is a message sent via Simi.ai assistant."
        if 'say' in user_request.lower():
            say_match = re.search(r'say\s+(.+)', user_request, re.IGNORECASE)
            if say_match:
                body = say_match.group(1).strip()
        elif 'message' in user_request.lower():
            msg_match = re.search(r'message[:\s]+(.+)', user_request, re.IGNORECASE)
            if msg_match:
                body = msg_match.group(1).strip()
        
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
        return {"response": f"Error processing email: {str(e)}"}