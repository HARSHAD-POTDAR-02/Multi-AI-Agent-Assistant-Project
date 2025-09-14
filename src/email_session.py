import json
import os
from datetime import datetime, timedelta

class EmailSession:
    def __init__(self):
        self.sessions = {}
        self.session_timeout = 300  # 5 minutes
    
    def create_session(self, user_id="default"):
        """Create a new email drafting session"""
        session_id = f"{user_id}_{int(datetime.now().timestamp())}"
        self.sessions[session_id] = {
            'created_at': datetime.now(),
            'draft': None,
            'status': 'drafting',
            'revision_count': 0,
            'original_request': None
        }
        return session_id
    
    def get_session(self, session_id):
        """Get session data"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            # Check if session expired
            if datetime.now() - session['created_at'] > timedelta(seconds=self.session_timeout):
                del self.sessions[session_id]
                return None
            return session
        return None
    
    def update_session(self, session_id, draft=None, status=None):
        """Update session data"""
        if session_id in self.sessions:
            if draft:
                self.sessions[session_id]['draft'] = draft
                self.sessions[session_id]['revision_count'] += 1
            if status:
                self.sessions[session_id]['status'] = status
            return True
        return False
    
    def delete_session(self, session_id):
        """Delete session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def get_active_session(self, user_id="default"):
        """Get the most recent active session for a user"""
        user_sessions = [
            (sid, session) for sid, session in self.sessions.items() 
            if sid.startswith(f"{user_id}_") and session['status'] == 'drafting'
        ]
        if user_sessions:
            # Return the most recent session
            return max(user_sessions, key=lambda x: x[1]['created_at'])
        return None, None

# Global session manager
email_session_manager = EmailSession()