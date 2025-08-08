import os
import base64
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.compose', 'https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    """Get Gmail API service"""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(script_dir, 'token.json')
    credentials_path = os.path.join(script_dir, 'credentials.json')
    
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                return None, "Please add credentials.json file from Google Cloud Console"
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    service = build('gmail', 'v1', credentials=creds)
    return service, None

def draft_email_with_ai(user_request, conversation_history=None, context=None):
    """Use AI to draft email content based on user request with context"""
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    # Build context from conversation history
    context_info = ""
    if conversation_history:
        recent_history = conversation_history[-3:]  # Last 3 interactions
        context_info = "\n\nPrevious conversation context:\n"
        for item in recent_history:
            context_info += f"User: {item['user_query']}\nAssistant: {item['response'][:100]}...\n\n"
    
    # Add any stored context
    if context:
        context_info += "\nAdditional context:\n"
        for key, value in context.items():
            context_info += f"{key}: {value}\n"
    
    prompt = f"""
    Based on the user's request and conversation context, draft a professional email. Extract the recipient, subject, and body.
    
    User request: "{user_request}"
    {context_info}
    
    Please respond in this exact format:
    TO: [email address if mentioned, otherwise "RECIPIENT_NEEDED"]
    SUBJECT: [appropriate subject line]
    BODY: [professional email body]
    """
    
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama3-8b-8192",
        temperature=0.3,
    )
    
    return response.choices[0].message.content.strip()

def create_draft_email(service, to_email, subject, body):
    """Create a draft email in Gmail"""
    message = MIMEText(body)
    message['to'] = to_email
    message['subject'] = subject
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    draft = {
        'message': {
            'raw': raw_message
        }
    }
    
    try:
        draft = service.users().drafts().create(userId='me', body=draft).execute()
        return f"Draft created successfully! Draft ID: {draft['id']}"
    except Exception as error:
        return f"Error creating draft: {error}"

def send_email(service, to_email, subject, body):
    """Send an email directly"""
    message = MIMEText(body)
    message['to'] = to_email
    message['subject'] = subject
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    try:
        sent_message = service.users().messages().send(
            userId='me', 
            body={'raw': raw_message}
        ).execute()
        return f"Email sent successfully! Message ID: {sent_message['id']}"
    except Exception as error:
        return f"Error sending email: {error}"