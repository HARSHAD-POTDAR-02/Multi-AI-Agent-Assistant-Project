import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict
from .models import FocusSession, FocusAnalyticsData

class FocusAnalytics:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), 'focus_analytics.db')
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY,
                session_type TEXT,
                start_time TEXT,
                end_time TEXT,
                duration_minutes INTEGER,
                interruptions INTEGER,
                completed BOOLEAN,
                created_at TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def record_session(self, session: FocusSession):
        if not session.start_time:
            return
        
        duration = 0
        if session.end_time:
            duration = (session.end_time - session.start_time).total_seconds() / 60

        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT INTO focus_sessions 
            (session_type, start_time, end_time, duration_minutes, interruptions, completed, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.session_type,
            session.start_time.isoformat(),
            session.end_time.isoformat() if session.end_time else None,
            duration,
            session.interruptions,
            session.completed,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def get_success_rate(self, days=7) -> float:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute('''
            SELECT COUNT(*) as total, SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed
            FROM focus_sessions WHERE created_at > ?
        ''', (since_date,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result[0] == 0:
            return 0.0
        return (result[1] / result[0]) * 100

    def suggest_optimal_duration(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT duration_minutes FROM focus_sessions 
            WHERE completed = 1 AND duration_minutes > 0
            ORDER BY created_at DESC LIMIT 10
        ''')
        
        durations = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not durations:
            return 25
        
        return int(sum(durations) / len(durations))

    def get_analytics_summary(self) -> Dict:
        success_rate = self.get_success_rate()
        optimal_duration = self.suggest_optimal_duration()
        
        return {
            "success_rate": success_rate,
            "optimal_duration": optimal_duration,
            "recommendation": f"Try {optimal_duration}-minute sessions for best results" if success_rate > 0 else "Start with 25-minute sessions"
        }