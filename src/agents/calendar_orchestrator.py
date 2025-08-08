import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google_calendar_service import get_calendar_service, parse_meeting_request, create_google_meet_event

def orchestrate_calendar(state):
    """
    Orchestrates the calendar based on the user's query.
    """
    print("---ORCHESTRATE CALENDAR---")
    user_query = state["user_query"]
    
    # Check if this is a complex multi-step request (schedule + email)
    if (any(keyword in user_query.lower() for keyword in ['schedule', 'meeting', 'meet', 'appointment', 'call']) and 
        any(keyword in user_query.lower() for keyword in ['mail', 'email', 'send'])):
        # Redirect to sub_agents for complex coordination
        from agents.sub_agents import handle_meeting_and_email
        return handle_meeting_and_email(user_query)
    
    # Check if this is a simple meeting scheduling request
    elif any(keyword in user_query.lower() for keyword in ['schedule', 'meeting', 'meet', 'appointment', 'call']):
        try:
            # Get calendar service
            service, error = get_calendar_service()
            if error:
                return {"response": f"Calendar setup needed: {error}"}
            
            # Parse meeting details using AI
            meeting_details = parse_meeting_request(user_query)
            
            # Create the meeting with Google Meet link
            result = create_google_meet_event(service, meeting_details)
            
            if result['success']:
                response = f"""✅ Meeting scheduled successfully!

📅 **{result['title']}**
🕐 Time: {result['start_time']}
🔗 Google Meet: {result['meet_link']}
📋 Calendar: {result['event_link']}

Meeting created and invites sent!"""
            else:
                response = f"❌ Failed to schedule meeting: {result['error']}"
                
            return {"response": response}
            
        except Exception as e:
            return {"response": f"Error scheduling meeting: {str(e)}"}
    
    return {"response": f"Calendar Orchestrator: I have received your request to: {user_query}"}