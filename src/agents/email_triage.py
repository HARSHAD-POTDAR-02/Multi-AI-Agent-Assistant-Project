import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gmail_service import get_gmail_service, draft_email_with_ai, send_email

def triage_emails(state):
    """
    Triage emails based on the user's query.
    """
    print("---TRIAGE EMAILS---")
    user_query = state["user_query"]
    conversation_history = state.get("conversation_history", [])
    context = state.get("context", {})
    
    # Check if this is a draft email request
    if any(keyword in user_query.lower() for keyword in ['draft', 'write', 'compose', 'email', 'send']):
        return draft_and_send_email(user_query, conversation_history, context)
    
    return {"response": f"Email Triage: I have received your request to: {user_query}"}

def draft_and_send_email(user_request, conversation_history=None, context=None):
    """Draft email, show for approval, and send if approved"""
    try:
        # Get Gmail service
        service, error = get_gmail_service()
        if error:
            return {"response": f"Gmail setup needed: {error}"}
        
        # Generate email content using AI with context
        ai_response = draft_email_with_ai(user_request, conversation_history, context)
        
        # Parse AI response
        lines = ai_response.split('\n')
        to_email = None
        subject = None
        body_lines = []
        current_section = None
        
        for line in lines:
            if line.startswith('TO:'):
                to_email = line.replace('TO:', '').strip()
                current_section = 'to'
            elif line.startswith('SUBJECT:'):
                subject = line.replace('SUBJECT:', '').strip()
                current_section = 'subject'
            elif line.startswith('BODY:'):
                body_lines.append(line.replace('BODY:', '').strip())
                current_section = 'body'
            elif current_section == 'body' and line.strip():
                body_lines.append(line)
        
        body = '\n'.join(body_lines)
        
        if to_email == "RECIPIENT_NEEDED":
            return {"response": f"Please specify recipient email address."}
        
        # Show draft for approval
        print(f"\n=== EMAIL DRAFT ===")
        print(f"TO: {to_email}")
        print(f"SUBJECT: {subject}")
        print(f"BODY:\n{body}")
        print(f"==================\n")
        
        approval = input("Do you want to send this email? (yes/y to send, anything else to cancel): ").lower().strip()
        
        if approval in ['yes', 'y']:
            result = send_email(service, to_email, subject, body)
            return {"response": f"Email sent!\n\n{result}"}
        else:
            return {"response": "Email cancelled. Not sent."}
        
    except Exception as e:
        return {"response": f"Error processing email: {str(e)}"}