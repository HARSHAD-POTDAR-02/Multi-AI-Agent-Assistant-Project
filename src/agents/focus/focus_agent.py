from shared_storage import get_focus_manager
import re
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def support_focus(state):
    """
    Dynamic focus support with LLM-based intent detection.
    """
    print("---SUPPORT FOCUS---")
    user_query = state["user_query"]
    focus_manager = get_focus_manager()
    
    # Parse time duration from natural language
    def parse_duration(query):
        # Hours and minutes: "1 hour 30 minutes", "2h 45m"
        hour_min_match = re.search(r'(\d+)\s*(?:hours?|hrs?|h)\s*(?:and\s*)?(\d+)\s*(?:minutes?|mins?|m)', query.lower())
        if hour_min_match:
            hours = int(hour_min_match.group(1))
            minutes = int(hour_min_match.group(2))
            return hours * 60 + minutes
        
        # Hours: "4 hours", "2 hrs", "1 hour"
        hour_match = re.search(r'(\d+)\s*(?:hours?|hrs?|h)', query.lower())
        if hour_match:
            return int(hour_match.group(1)) * 60
        
        # Minutes: "30 minutes", "45 mins", "90 min"
        min_match = re.search(r'(\d+)\s*(?:minutes?|mins?|m)', query.lower())
        if min_match:
            return int(min_match.group(1))
        
        return 25  # Default pomodoro
    
    # LLM intent detection
    def detect_intent(query):
        prompt = f"""
        Analyze this user query and classify the intent. Return ONLY one of these exact words:
        
        START_SESSION - User wants to begin a new focus/work session
        END_SESSION - User wants to stop/end current session  
        CHECK_STATUS - User wants to know remaining time/status
        EXTEND_SESSION - User wants to add more time to current session
        PAUSE_SESSION - User wants to temporarily pause current session
        RESUME_SESSION - User wants to resume a paused session
        LOG_INTERRUPTION - User is reporting they got distracted/interrupted (past tense)
        ANALYTICS - User wants to see focus statistics/performance
        HELP - User needs help or general information
        
        Examples:
        "I want to focus for 2 hours" -> START_SESSION
        "How much time is left?" -> CHECK_STATUS
        "I got distracted" -> LOG_INTERRUPTION
        "Don't let me get distracted" -> START_SESSION
        "End my focus session" -> END_SESSION
        "Add 30 minutes" -> EXTEND_SESSION
        "Pause my session" -> PAUSE_SESSION
        "Resume focus" -> RESUME_SESSION
        
        User query: "{query}"
        
        Intent:"""
        
        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=10
            )
            return response.choices[0].message.content.strip()
        except:
            return "HELP"  # Fallback
    
    intent = detect_intent(user_query)
    
    if intent == "START_SESSION":
        duration = parse_duration(user_query)
        
        if 'pomodoro' in user_query.lower():
            session_type = 'pomodoro'
        elif any(word in user_query.lower() for word in ['deep work', 'deep', 'long']):
            session_type = 'deep work'
        elif duration > 60:
            session_type = 'extended focus'
        else:
            session_type = 'focus session'
        
        result = focus_manager.start_session(session_type, duration)
        return {"response": f"🎯 {result}"}
    
    elif intent == "END_SESSION":
        result = focus_manager.end_session()
        return {"response": f"✅ {result}"}
    
    elif intent == "CHECK_STATUS":
        status = focus_manager.get_status()
        block_status = focus_manager.blocker.get_blocked_status()
        blocking_info = f"\nBlocking: {block_status['blocked_apps_count']} apps monitored, {block_status['blocked_sites_count']} sites ready to block"
        return {"response": f"⏱️ {status}{blocking_info}"}
    
    elif intent == "EXTEND_SESSION":
        duration = parse_duration(user_query)
        if duration == 25:  # No specific time mentioned
            duration = 30
        result = focus_manager.extend_session(duration)
        return {"response": f"⏰ {result}"}
    
    elif intent == "PAUSE_SESSION":
        result = focus_manager.pause_session()
        return {"response": f"⏸️ {result}"}
    
    elif intent == "RESUME_SESSION":
        result = focus_manager.resume_session()
        return {"response": f"▶️ {result}"}
    
    elif intent == "LOG_INTERRUPTION":
        result = focus_manager.add_interruption()
        return {"response": f"📝 {result}"}
    
    elif intent == "ANALYTICS":
        analytics = focus_manager.get_analytics()
        response = f"📊 Focus Analytics:\n" \
                  f"• Success Rate: {analytics['success_rate']:.1f}%\n" \
                  f"• Optimal Duration: {analytics['optimal_duration']} minutes\n" \
                  f"• {analytics['recommendation']}"
        return {"response": response}
    
    else:  # HELP or unknown
        return {"response": "🧠 Focus Assistant - Natural Commands:\n" \
                           "• 'I want to focus for 4 hours' - Custom duration\n" \
                           "• 'Start pomodoro' - 25min work session\n" \
                           "• 'Deep work for 2 hours' - Extended session\n" \
                           "• 'Block distractions for 90 minutes'\n" \
                           "• 'Extend focus session by 1 hour' - Add time\n" \
                           "• 'Pause focus session' - Temporarily pause\n" \
                           "• 'Resume focus' - Continue paused session\n" \
                           "• 'End focus' - Stop current session\n" \
                           "• 'Focus status' - Check remaining time"}