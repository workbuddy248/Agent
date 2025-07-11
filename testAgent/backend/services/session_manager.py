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
    CREATED = "created"
    PARSING = "parsing"
    PARSED = "parsed"
    GENERATING = "generating"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    TERMINATED = "terminated"

@dataclass
class UserSession:
    """User session data with all required fields for main.py"""
    session_id: str
    user_id: Optional[str]
    status: str  # Use string instead of enum for flexibility
    created_at: datetime
    last_accessed: datetime
    expires_at: datetime
    
    # Additional fields needed by main.py
    instruction: str = ""
    workflows: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    cluster_config: Dict[str, Any] = field(default_factory=dict)
    current_workflow: Optional[str] = None
    progress: float = 0.0
    execution_steps: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Legacy fields for backward compatibility
    context: Dict[str, Any] = field(default_factory=dict)
    workflow_history: List[str] = field(default_factory=list)

class SessionManagerService:
    """Service for managing user sessions"""
    
    def __init__(self, session_timeout: int = 3600):
        self.sessions: Dict[str, UserSession] = {}
        self.session_timeout = session_timeout  # seconds
        
    async def create_session(self, session_id: str, instruction: str, 
                           workflows: List[str], parameters: Dict[str, Any],
                           cluster_config: Dict[str, Any], user_id: str = None) -> UserSession:
        """Create a new user session with all required fields"""
        now = datetime.now()
        expires_at = now + timedelta(seconds=self.session_timeout)
        
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            status=SessionStatus.CREATED.value,
            instruction=instruction,
            workflows=workflows,
            parameters=parameters,
            cluster_config=cluster_config,
            created_at=now,
            last_accessed=now,
            expires_at=expires_at,
            started_at=now,
            updated_at=now
        )
        
        self.sessions[session_id] = session
        logger.info(f"Created new session: {session_id}")
        
        return session
    
    def create_simple_session(self, user_id: str = None, session_id: str = None) -> str:
        """Create a simple session (backward compatibility)"""
        if not session_id:
            session_id = str(uuid.uuid4())
            
        now = datetime.now()
        expires_at = now + timedelta(seconds=self.session_timeout)
        
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            status=SessionStatus.CREATED.value,
            created_at=now,
            last_accessed=now,
            expires_at=expires_at,
            started_at=now,
            updated_at=now
        )
        
        self.sessions[session_id] = session
        logger.info(f"Created simple session: {session_id}")
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if session is expired
        if datetime.now() > session.expires_at:
            session.status = SessionStatus.EXPIRED.value
            logger.info(f"Session expired: {session_id}")
            return None
        
        # Update last accessed time
        session.last_accessed = datetime.now()
        session.updated_at = datetime.now()
        session.expires_at = datetime.now() + timedelta(seconds=self.session_timeout)
        
        return session
    
    async def update_session_status(self, session_id: str, status: str, error_message: str = None) -> bool:
        """Update session status"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        session.status = status
        session.updated_at = datetime.now()
        
        if error_message:
            session.error_message = error_message
        
        logger.info(f"Updated session {session_id} status to: {status}")
        return True
    
    async def store_execution_results(self, session_id: str, results: Dict[str, Any]) -> bool:
        """Store execution results in session"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        # Store results in context
        session.context["execution_results"] = results
        session.updated_at = datetime.now()
        
        logger.info(f"Stored execution results for session: {session_id}")
        return True
    
    def update_session_context(self, session_id: str, context: Dict[str, Any]) -> bool:
        """Update session context"""
        session = self.get_session_sync(session_id)
        if not session:
            return False
        
        session.context.update(context)
        session.updated_at = datetime.now()
        logger.debug(f"Updated context for session: {session_id}")
        
        return True
    
    def get_session_sync(self, session_id: str) -> Optional[UserSession]:
        """Synchronous version of get_session"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if session is expired
        if datetime.now() > session.expires_at:
            session.status = SessionStatus.EXPIRED.value
            return None
        
        return session
    
    def add_workflow_to_history(self, session_id: str, workflow_id: str) -> bool:
        """Add workflow to session history"""
        session = self.get_session_sync(session_id)
        if not session:
            return False
        
        session.workflow_history.append(workflow_id)
        session.updated_at = datetime.now()
        logger.debug(f"Added workflow {workflow_id} to session {session_id}")
        
        return True
    
    def set_current_workflow(self, session_id: str, workflow_id: str) -> bool:
        """Set current workflow for session"""
        session = self.get_session_sync(session_id)
        if not session:
            return False
        
        session.current_workflow = workflow_id
        session.updated_at = datetime.now()
        logger.debug(f"Set current workflow {workflow_id} for session {session_id}")
        
        return True
    
    def terminate_session(self, session_id: str) -> bool:
        """Terminate a session"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        session.status = SessionStatus.TERMINATED.value
        session.updated_at = datetime.now()
        
        logger.info(f"Terminated session: {session_id}")
        return True
    
    async def cleanup_expired_sessions(self) -> int:
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
    
    async def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions"""
        active_sessions = []
        
        for session in self.sessions.values():
            if session.status not in [SessionStatus.EXPIRED.value, SessionStatus.TERMINATED.value] and datetime.now() <= session.expires_at:
                active_sessions.append({
                    "session_id": session.session_id,
                    "status": session.status,
                    "instruction": session.instruction,
                    "workflows": session.workflows,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat() if session.updated_at else None
                })
        
        return active_sessions
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        now = datetime.now()
        total_sessions = len(self.sessions)
        active_sessions = 0
        expired_sessions = 0
        
        for session in self.sessions.values():
            if session.status not in [SessionStatus.EXPIRED.value, SessionStatus.TERMINATED.value] and now <= session.expires_at:
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