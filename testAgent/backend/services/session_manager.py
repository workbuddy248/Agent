"""
Session Manager Service - Manages user sessions and workflow state
File: backend/services/session_manager.py
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class SessionStatus(str, Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"

@dataclass
class UserSession:
    """User session data"""
    session_id: str
    user_id: Optional[str]
    status: SessionStatus
    created_at: datetime
    last_accessed: datetime
    expires_at: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    workflow_history: List[str] = field(default_factory=list)
    current_workflow: Optional[str] = None

class SessionManagerService:
    """Service for managing user sessions"""
    
    def __init__(self, session_timeout: int = 3600):
        self.sessions: Dict[str, UserSession] = {}
        self.session_timeout = session_timeout  # seconds
        
    def create_session(self, user_id: str = None) -> str:
        """Create a new user session"""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        expires_at = now + timedelta(seconds=self.session_timeout)
        
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            status=SessionStatus.ACTIVE,
            created_at=now,
            last_accessed=now,
            expires_at=expires_at
        )
        
        self.sessions[session_id] = session
        logger.info(f"Created new session: {session_id}")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if session is expired
        if datetime.now() > session.expires_at:
            session.status = SessionStatus.EXPIRED
            logger.info(f"Session expired: {session_id}")
            return None
        
        # Update last accessed time
        session.last_accessed = datetime.now()
        session.expires_at = datetime.now() + timedelta(seconds=self.session_timeout)
        
        return session
    
    def update_session_context(self, session_id: str, context: Dict[str, Any]) -> bool:
        """Update session context"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.context.update(context)
        logger.debug(f"Updated context for session: {session_id}")
        
        return True
    
    def add_workflow_to_history(self, session_id: str, workflow_id: str) -> bool:
        """Add workflow to session history"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.workflow_history.append(workflow_id)
        logger.debug(f"Added workflow {workflow_id} to session {session_id}")
        
        return True
    
    def set_current_workflow(self, session_id: str, workflow_id: str) -> bool:
        """Set current workflow for session"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.current_workflow = workflow_id
        logger.debug(f"Set current workflow {workflow_id} for session {session_id}")
        
        return True
    
    def terminate_session(self, session_id: str) -> bool:
        """Terminate a session"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        session.status = SessionStatus.TERMINATED
        
        logger.info(f"Terminated session: {session_id}")
        return True
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if now > session.expires_at:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")
        
        return len(expired_sessions)
    
    def list_active_sessions(self) -> List[UserSession]:
        """List all active sessions"""
        active_sessions = []
        
        for session in self.sessions.values():
            if session.status == SessionStatus.ACTIVE and datetime.now() <= session.expires_at:
                active_sessions.append(session)
        
        return active_sessions
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        now = datetime.now()
        total_sessions = len(self.sessions)
        active_sessions = 0
        expired_sessions = 0
        
        for session in self.sessions.values():
            if session.status == SessionStatus.ACTIVE and now <= session.expires_at:
                active_sessions += 1
            elif now > session.expires_at:
                expired_sessions += 1
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "expired_sessions": expired_sessions,
            "session_timeout": self.session_timeout
        }

# Global session manager instance
session_manager = SessionManagerService()
