"""
User Manager - Handles multi-user support and session management.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import uuid
import threading
from sqlite3 import connect
import hashlib
import secrets

class UserManager:
    """
    Manages users, sessions, and authentication for the multi-agent system.
    Provides user registration, session management, and access control.
    """
    
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self.logger = logging.getLogger("UserManager")
        self.lock = threading.Lock()
        self.active_sessions = {}
        self._init_database()
    
    def _init_database(self):
        """Initialize database for user management."""
        try:
            with connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE,
                        password_hash TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        preferences TEXT,
                        metadata TEXT
                    )
                ''')
                
                # Sessions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        session_data TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # User activity log
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_activity (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        session_id TEXT,
                        activity_type TEXT NOT NULL,
                        activity_data TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                conn.commit()
                self.logger.info("User database initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash."""
        try:
            salt, password_hash = stored_hash.split(':')
            return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
        except ValueError:
            return False
    
    async def register_user(self, username: str, email: str = None, password: str = None) -> Dict[str, Any]:
        """Register a new user."""
        try:
            user_id = str(uuid.uuid4())
            
            # Hash password if provided
            password_hash = None
            if password:
                password_hash = self.hash_password(password)
            
            with self.lock:
                with connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Check if username already exists
                    cursor.execute('SELECT user_id FROM users WHERE username = ?', (username,))
                    if cursor.fetchone():
                        return {"error": "Username already exists"}
                    
                    # Check if email already exists
                    if email:
                        cursor.execute('SELECT user_id FROM users WHERE email = ?', (email,))
                        if cursor.fetchone():
                            return {"error": "Email already exists"}
                    
                    # Insert new user
                    cursor.execute('''
                        INSERT INTO users (user_id, username, email, password_hash, preferences, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (user_id, username, email, password_hash, '{}', '{}'))
                    
                    conn.commit()
            
            # Log registration activity
            await self.log_activity(user_id, None, "registration", {"username": username})
            
            return {
                "success": True,
                "user_id": user_id,
                "username": username,
                "message": "User registered successfully"
            }
            
        except Exception as e:
            self.logger.error(f"User registration failed: {e}")
            return {"error": str(e)}
    
    async def authenticate_user(self, username: str, password: str = None) -> Dict[str, Any]:
        """Authenticate a user."""
        try:
            with self.lock:
                with connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Find user by username
                    cursor.execute('''
                        SELECT user_id, username, password_hash, is_active 
                        FROM users WHERE username = ?
                    ''', (username,))
                    
                    result = cursor.fetchone()
                    if not result:
                        return {"error": "User not found"}
                    
                    user_id, username, password_hash, is_active = result
                    
                    if not is_active:
                        return {"error": "User account is inactive"}
                    
                    # Verify password if provided
                    if password and password_hash:
                        if not self.verify_password(password, password_hash):
                            return {"error": "Invalid password"}
                    elif password and not password_hash:
                        return {"error": "Password not set for this user"}
                    
                    # Update last login
                    cursor.execute('''
                        UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?
                    ''', (user_id,))
                    
                    conn.commit()
            
            # Log authentication activity
            await self.log_activity(user_id, None, "authentication", {"username": username})
            
            return {
                "success": True,
                "user_id": user_id,
                "username": username,
                "message": "Authentication successful"
            }
            
        except Exception as e:
            self.logger.error(f"User authentication failed: {e}")
            return {"error": str(e)}
    
    async def create_session(self, user_id: str, ip_address: str = None, user_agent: str = None) -> Dict[str, Any]:
        """Create a new session for a user."""
        try:
            session_id = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(hours=24)  # 24 hour session
            
            session_data = {
                "created_at": datetime.now().isoformat(),
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
            
            with self.lock:
                with connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Insert session
                    cursor.execute('''
                        INSERT INTO user_sessions 
                        (session_id, user_id, expires_at, session_data, ip_address, user_agent)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (session_id, user_id, expires_at, json.dumps(session_data), ip_address, user_agent))
                    
                    conn.commit()
                
                # Store in active sessions
                self.active_sessions[session_id] = {
                    "user_id": user_id,
                    "created_at": datetime.now(),
                    "last_activity": datetime.now(),
                    "expires_at": expires_at,
                    "ip_address": ip_address,
                    "user_agent": user_agent
                }
            
            # Log session creation
            await self.log_activity(user_id, session_id, "session_created", {"session_id": session_id})
            
            return {
                "success": True,
                "session_id": session_id,
                "user_id": user_id,
                "expires_at": expires_at.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Session creation failed: {e}")
            return {"error": str(e)}
    
    async def validate_session(self, session_id: str) -> Dict[str, Any]:
        """Validate a session and return user information."""
        try:
            with self.lock:
                # Check active sessions first
                if session_id in self.active_sessions:
                    session_data = self.active_sessions[session_id]
                    
                    # Check if session is expired
                    if session_data["expires_at"] < datetime.now():
                        del self.active_sessions[session_id]
                        return {"error": "Session expired"}
                    
                    # Update last activity
                    session_data["last_activity"] = datetime.now()
                    
                    return {
                        "success": True,
                        "user_id": session_data["user_id"],
                        "session_id": session_id,
                        "created_at": session_data["created_at"].isoformat(),
                        "last_activity": session_data["last_activity"].isoformat()
                    }
                
                # Check database for session
                with connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT user_id, created_at, last_activity, expires_at, is_active
                        FROM user_sessions WHERE session_id = ?
                    ''', (session_id,))
                    
                    result = cursor.fetchone()
                    if not result:
                        return {"error": "Session not found"}
                    
                    user_id, created_at, last_activity, expires_at, is_active = result
                    
                    if not is_active:
                        return {"error": "Session is inactive"}
                    
                    # Check if session is expired
                    if datetime.fromisoformat(expires_at) < datetime.now():
                        return {"error": "Session expired"}
                    
                    # Update last activity
                    cursor.execute('''
                        UPDATE user_sessions SET last_activity = CURRENT_TIMESTAMP 
                        WHERE session_id = ?
                    ''', (session_id,))
                    
                    conn.commit()
                
                # Add to active sessions
                self.active_sessions[session_id] = {
                    "user_id": user_id,
                    "created_at": datetime.fromisoformat(created_at),
                    "last_activity": datetime.now(),
                    "expires_at": datetime.fromisoformat(expires_at)
                }
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "session_id": session_id,
                    "created_at": created_at,
                    "last_activity": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Session validation failed: {e}")
            return {"error": str(e)}
    
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a user session."""
        try:
            with self.lock:
                # Remove from active sessions
                if session_id in self.active_sessions:
                    user_id = self.active_sessions[session_id]["user_id"]
                    del self.active_sessions[session_id]
                else:
                    # Get user_id from database
                    with connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT user_id FROM user_sessions WHERE session_id = ?', (session_id,))
                        result = cursor.fetchone()
                        user_id = result[0] if result else None
                
                # Mark session as inactive in database
                with connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE user_sessions SET is_active = 0 WHERE session_id = ?
                    ''', (session_id,))
                    conn.commit()
                
                # Log session end
                if user_id:
                    await self.log_activity(user_id, session_id, "session_ended", {"session_id": session_id})
                
                return {
                    "success": True,
                    "message": "Session ended successfully"
                }
                
        except Exception as e:
            self.logger.error(f"Session end failed: {e}")
            return {"error": str(e)}
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information."""
        try:
            with self.lock:
                with connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT username, email, created_at, last_login, is_active, preferences, metadata
                        FROM users WHERE user_id = ?
                    ''', (user_id,))
                    
                    result = cursor.fetchone()
                    if not result:
                        return {"error": "User not found"}
                    
                    username, email, created_at, last_login, is_active, preferences, metadata = result
                    
                    return {
                        "user_id": user_id,
                        "username": username,
                        "email": email,
                        "created_at": created_at,
                        "last_login": last_login,
                        "is_active": bool(is_active),
                        "preferences": json.loads(preferences) if preferences else {},
                        "metadata": json.loads(metadata) if metadata else {}
                    }
                    
        except Exception as e:
            self.logger.error(f"Get user info failed: {e}")
            return {"error": str(e)}
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Update user preferences."""
        try:
            with self.lock:
                with connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Get existing preferences
                    cursor.execute('SELECT preferences FROM users WHERE user_id = ?', (user_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        existing_prefs = json.loads(result[0]) if result[0] else {}
                        existing_prefs.update(preferences)
                        updated_prefs = existing_prefs
                    else:
                        updated_prefs = preferences
                    
                    cursor.execute('''
                        UPDATE users SET preferences = ? WHERE user_id = ?
                    ''', (json.dumps(updated_prefs), user_id))
                    
                    conn.commit()
                
                # Log preference update
                await self.log_activity(user_id, None, "preferences_updated", {"preferences": preferences})
                
                return {
                    "success": True,
                    "preferences": updated_prefs,
                    "message": "Preferences updated successfully"
                }
                
        except Exception as e:
            self.logger.error(f"Update preferences failed: {e}")
            return {"error": str(e)}
    
    async def log_activity(self, user_id: str, session_id: str, activity_type: str, activity_data: Dict[str, Any]):
        """Log user activity."""
        try:
            with self.lock:
                with connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT INTO user_activity (user_id, session_id, activity_type, activity_data)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, session_id, activity_type, json.dumps(activity_data)))
                    
                    conn.commit()
                    
        except Exception as e:
            self.logger.error(f"Activity logging failed: {e}")
    
    async def get_user_activity(self, user_id: str, limit: int = 50) -> Dict[str, Any]:
        """Get user activity history."""
        try:
            with self.lock:
                with connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT activity_type, activity_data, timestamp
                        FROM user_activity WHERE user_id = ?
                        ORDER BY timestamp DESC LIMIT ?
                    ''', (user_id, limit))
                    
                    results = cursor.fetchall()
                    
                    activities = []
                    for activity_type, activity_data, timestamp in results:
                        activities.append({
                            "activity_type": activity_type,
                            "activity_data": json.loads(activity_data) if activity_data else {},
                            "timestamp": timestamp
                        })
                    
                    return {
                        "user_id": user_id,
                        "activities": activities,
                        "total": len(activities)
                    }
                    
        except Exception as e:
            self.logger.error(f"Get user activity failed: {e}")
            return {"error": str(e)}
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        try:
            current_time = datetime.now()
            expired_sessions = []
            
            with self.lock:
                # Clean up active sessions
                for session_id, session_data in self.active_sessions.items():
                    if session_data["expires_at"] < current_time:
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    del self.active_sessions[session_id]
                
                # Clean up database sessions
                with connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE user_sessions SET is_active = 0 
                        WHERE expires_at < CURRENT_TIMESTAMP
                    ''')
                    conn.commit()
            
            if expired_sessions:
                self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
        except Exception as e:
            self.logger.error(f"Session cleanup failed: {e}")
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        return len(self.active_sessions)
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get session information."""
        if session_id in self.active_sessions:
            session_data = self.active_sessions[session_id]
            return {
                "session_id": session_id,
                "user_id": session_data["user_id"],
                "created_at": session_data["created_at"].isoformat(),
                "last_activity": session_data["last_activity"].isoformat(),
                "expires_at": session_data["expires_at"].isoformat()
            }
        else:
            return {"error": "Session not found"}
