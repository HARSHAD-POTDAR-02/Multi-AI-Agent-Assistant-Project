from datetime import datetime, timedelta
import json

class ConversationMemory:
    def __init__(self):
        self.conversations = {}
        self.session_timeout = 1800  # 30 minutes
    
    def get_session_id(self, user_id="default"):
        """Generate or get existing session ID"""
        # For now, use a simple session per user
        return f"session_{user_id}"
    
    def add_message(self, session_id, message, is_user=True, agent=None, context=None):
        """Add a message to conversation history"""
        if session_id not in self.conversations:
            self.conversations[session_id] = {
                'messages': [],
                'context': {},
                'last_activity': datetime.now(),
                'active_drafts': {}
            }
        
        message_data = {
            'timestamp': datetime.now().isoformat(),
            'content': message,
            'is_user': is_user,
            'agent': agent,
            'context': context or {}
        }
        
        self.conversations[session_id]['messages'].append(message_data)
        self.conversations[session_id]['last_activity'] = datetime.now()
        
        # Keep only last 50 messages to prevent memory bloat
        if len(self.conversations[session_id]['messages']) > 50:
            self.conversations[session_id]['messages'] = self.conversations[session_id]['messages'][-50:]
    
    def get_conversation_history(self, session_id, limit=10):
        """Get recent conversation history"""
        if session_id not in self.conversations:
            return []
        
        messages = self.conversations[session_id]['messages']
        return messages[-limit:] if limit else messages
    
    def update_context(self, session_id, context_updates):
        """Update session context"""
        if session_id not in self.conversations:
            self.conversations[session_id] = {
                'messages': [],
                'context': {},
                'last_activity': datetime.now(),
                'active_drafts': {}
            }
        
        self.conversations[session_id]['context'].update(context_updates)
        self.conversations[session_id]['last_activity'] = datetime.now()
    
    def get_context(self, session_id):
        """Get session context"""
        if session_id in self.conversations:
            return self.conversations[session_id]['context']
        return {}
    
    def set_active_draft(self, session_id, draft_type, draft_data):
        """Set active draft (email, meeting, etc.)"""
        if session_id not in self.conversations:
            self.conversations[session_id] = {
                'messages': [],
                'context': {},
                'last_activity': datetime.now(),
                'active_drafts': {}
            }
        
        self.conversations[session_id]['active_drafts'][draft_type] = draft_data
        self.conversations[session_id]['last_activity'] = datetime.now()
    
    def get_active_draft(self, session_id, draft_type):
        """Get active draft"""
        if session_id in self.conversations:
            return self.conversations[session_id]['active_drafts'].get(draft_type)
        return None
    
    def clear_active_draft(self, session_id, draft_type):
        """Clear active draft"""
        if session_id in self.conversations and draft_type in self.conversations[session_id]['active_drafts']:
            del self.conversations[session_id]['active_drafts'][draft_type]
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session_data in self.conversations.items():
            if current_time - session_data['last_activity'] > timedelta(seconds=self.session_timeout):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.conversations[session_id]
    
    def get_last_agent_response(self, session_id):
        """Get the last agent response for context"""
        history = self.get_conversation_history(session_id, limit=5)
        for message in reversed(history):
            if not message['is_user']:
                return message
        return None

# Global conversation memory instance
conversation_memory = ConversationMemory()