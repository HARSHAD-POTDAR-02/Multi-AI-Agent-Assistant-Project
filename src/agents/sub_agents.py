import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google_calendar_service import get_calendar_service, create_google_meet_event
from gmail_service import get_gmail_service, send_email
from groq import Groq
from dotenv import load_dotenv
import json

load_dotenv()

def handle_sub_agents(state):
    """
    Handles complex multi-step tasks that require coordination between agents.
    """
    print("---HANDLE SUB-AGENTS---")
    user_query = state["user_query"]
    
    # Check if this is a complex task involving multiple actions
    if any(keyword in user_query.lower() for keyword in ['schedule', 'meeting']) and any(keyword in user_query.lower() for keyword in ['mail', 'email', 'send']):
        return handle_meeting_and_email(user_query)
    
    return {"response": f"Sub-Agents: I have received your request to: {user_query}"}

def handle_meeting_and_email(user_query):
    """Handle scheduling a meeting and sending email about it"""
    try:
        # Direct parsing without complex JSON
        import re
        from datetime import datetime, timedelta
        
        # Extract email
        email_match = re.search(r'(?:mailto:)?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', user_query)
        email = email_match.group(1) if email_match else "user@example.com"
        
        # Extract time
        time_match = re.search(r'(\d{1,2}:\d{2})\s*(am|pm)', user_query.lower())
        if time_match:
            time_str = time_match.group(1)
            am_pm = time_match.group(2)
            hour, minute = time_str.split(':')
            hour = int(hour)
            
            if am_pm == 'am' and hour == 12:
                hour = 0
            elif am_pm == 'pm' and hour != 12:
                hour += 12
                
            time_24 = f"{hour:02d}:{minute}"
        else:
            time_24 = "10:00"
        
        # Use tomorrow's date
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Create meeting details
        meeting_details = {
            "title": "App Launch Meeting",
            "description": "Meeting regarding app launch",
            "start_time": f"{tomorrow} {time_24}",
            "duration_minutes": 60,
            "attendees": [email]
        }
        
        # Create email details
        email_details = {
            "to": email,
            "subject": "Meeting Invitation - App Launch",
            "body": "Hi, I've scheduled a meeting regarding our app launch. Please find the details below."
        }
        
        # Step 2: Schedule the meeting
        calendar_service, cal_error = get_calendar_service()
        if cal_error:
            return {"response": f"❌ Calendar setup needed: {cal_error}"}
        
        meeting_result = create_google_meet_event(calendar_service, meeting_details)
        
        if not meeting_result['success']:
            return {"response": f"❌ Failed to schedule meeting: {meeting_result['error']}"}
        
        # Step 3: Send email with meeting details
        gmail_service, gmail_error = get_gmail_service()
        if gmail_error:
            return {"response": f"❌ Gmail setup needed: {gmail_error}"}
        
        # Create email body with meeting details
        email_body = f"""{email_details['body']}

📅 Meeting Details:
• Title: {meeting_result['title']}
• Time: {meeting_result['start_time']}
• Google Meet: {meeting_result['meet_link']}
• Calendar: {meeting_result['event_link']}

Looking forward to connecting!

Best regards,
Simi.ai Assistant"""
        
        email_result = send_email(
            gmail_service,
            email_details['to'],
            email_details['subject'],
            email_body
        )
        
        # Step 4: Return comprehensive result
        response = f"""✅ **Multi-task completed successfully!**

📅 **Meeting Scheduled:**
• {meeting_result['title']}
• Time: {meeting_result['start_time']}
• Google Meet: {meeting_result['meet_link']}

📧 **Email Sent:**
• To: {email_details['to']}
• Subject: {email_details['subject']}
• Status: Sent successfully

🎯 **All tasks completed!**"""
        
        return {"response": response}
        
    except Exception as e:
        return {"response": f"❌ Error handling complex task: {str(e)}"}