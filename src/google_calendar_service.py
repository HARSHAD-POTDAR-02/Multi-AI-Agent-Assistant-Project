import os
import json
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Get Google Calendar API service"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    credentials_path = os.path.join(script_dir, 'calendar_credentials.json')
    token_path = os.path.join(script_dir, 'calendar_token.json')
    
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                return None, "Please add calendar_credentials.json file from Google Cloud Console"
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    service = build('calendar', 'v3', credentials=creds)
    return service, None

def parse_meeting_request(user_request):
    """Use AI to parse meeting details from user request"""
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    prompt = f"""
    Parse the following meeting request and extract the details. Pay close attention to the exact time mentioned.
    
    User request: "{user_request}"
    
    Please respond in this exact JSON format:
    {{
        "title": "Meeting title",
        "description": "Meeting description",
        "start_time": "YYYY-MM-DD HH:MM",
        "duration_minutes": 60,
        "attendees": ["email1@example.com", "email2@example.com"]
    }}
    
    Rules:
    - IMPORTANT: Use the EXACT time mentioned by the user (e.g., if they say "1:30 am", use "01:30")
    - Convert AM/PM to 24-hour format (1:30 AM = 01:30, 1:30 PM = 13:30)
    - If no date specified, use today's date if time hasn't passed, otherwise tomorrow
    - If no duration mentioned, default to 60 minutes
    - Extract all email addresses mentioned
    """
    
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama3-8b-8192",
        temperature=0.1,
    )
    
    try:
        return json.loads(response.choices[0].message.content.strip())
    except:
        # Fallback if JSON parsing fails
        return {
            "title": "Meeting",
            "description": user_request,
            "start_time": (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"),
            "duration_minutes": 60,
            "attendees": []
        }

def create_google_meet_event(service, meeting_details):
    """Create a calendar event with Google Meet link"""
    start_time = datetime.strptime(meeting_details['start_time'], "%Y-%m-%d %H:%M")
    end_time = start_time + timedelta(minutes=meeting_details['duration_minutes'])
    
    event = {
        'summary': meeting_details['title'],
        'description': meeting_details['description'],
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Asia/Kolkata',
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'Asia/Kolkata',
        },
        'attendees': [{'email': email} for email in meeting_details['attendees']],
        'conferenceData': {
            'createRequest': {
                'requestId': f"meet-{int(datetime.now().timestamp())}",
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    
    try:
        event = service.events().insert(
            calendarId='primary', 
            body=event,
            conferenceDataVersion=1
        ).execute()
        
        meet_link = event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri', 'No Meet link generated')
        
        return {
            'success': True,
            'event_id': event['id'],
            'event_link': event.get('htmlLink'),
            'meet_link': meet_link,
            'start_time': meeting_details['start_time'],
            'title': meeting_details['title']
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }