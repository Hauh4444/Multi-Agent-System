"""
Memory & Context Agent - Manages session data, user preferences, and contextual information.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any
import sqlite3
import threading
from .base_agent import BaseAgent

class MemoryAgent(BaseAgent):
    """
    Specialized agent for managing memory, context, and session data.
    Handles user preferences, conversation history, and contextual information storage.
    """
    
    def __init__(self, agent_id: str = None, db_path: str = "memory.db"):
        super().__init__(agent_id, "MemoryAgent")
        self.db_path = db_path
        self.db_lock = threading.Lock()
        self._init_database()
        
        # In-memory cache for frequently accessed data
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.max_cache_size = 1000
    
    def _init_database(self):
        """Initialize SQLite database for persistent storage."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # User sessions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        session_data TEXT,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')
                
                # User preferences table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        user_id TEXT PRIMARY KEY,
                        preferences TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Context data table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS context_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        session_id TEXT,
                        context_key TEXT NOT NULL,
                        context_value TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                ''')
                
                # Conversation history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        session_id TEXT,
                        message TEXT NOT NULL,
                        response TEXT,
                        sentiment TEXT,
                        intent TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
    
    async def process(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process memory and context operations.
        
        Args:
            input_data: Contains operation type and data
            context: Additional context information
            
        Returns:
            Dict with retrieved or stored context data
        """
        start_time = datetime.now()
        self.set_status("processing")
        
        try:
            operation = input_data.get('operation', 'retrieve')
            user_id = input_data.get('user_id', 'unknown')
            session_id = input_data.get('session_id', 'unknown')
            
            if operation == 'store':
                result = await self._store_context(input_data, user_id, session_id)
            elif operation == 'retrieve':
                result = await self._retrieve_context(input_data, user_id, session_id)
            elif operation == 'update_preferences':
                result = await self._update_user_preferences(input_data, user_id)
            elif operation == 'get_preferences':
                result = await self._get_user_preferences(user_id)
            elif operation == 'store_conversation':
                result = await self._store_conversation(input_data, user_id, session_id)
            elif operation == 'get_conversation_history':
                result = await self._get_conversation_history(user_id, session_id)
            else:
                result = {"error": f"Unknown operation: {operation}"}
            
            response_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(response_time, True)
            self.set_status("idle")
            
            return {
                "operation": operation,
                "result": result,
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error in memory processing: {e}")
            response_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(response_time, False)
            self.set_status("error")
            
            return {
                "operation": input_data.get('operation', 'unknown'),
                "result": {"error": str(e)},
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _store_context(self, input_data: Dict[str, Any], user_id: str, session_id: str) -> Dict[str, Any]:
        """Store context data for a user session."""
        try:
            context_key = input_data.get('context_key')
            context_value = input_data.get('context_value')
            expires_at = input_data.get('expires_at')
            
            if not context_key or context_value is None:
                return {"error": "context_key and context_value are required"}
            
            # Parse expiration time
            expires_timestamp = None
            if expires_at:
                try:
                    expires_timestamp = datetime.fromisoformat(expires_at)
                except ValueError:
                    # If it's a number, treat as seconds from now
                    try:
                        expires_timestamp = datetime.now() + timedelta(seconds=int(expires_at))
                    except (ValueError, TypeError):
                        pass
            
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Store context data
                    cursor.execute('''
                        INSERT OR REPLACE INTO context_data 
                        (user_id, session_id, context_key, context_value, expires_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, session_id, context_key, json.dumps(context_value), expires_timestamp))
                    
                    # Update session activity
                    cursor.execute('''
                        UPDATE user_sessions 
                        SET last_activity = CURRENT_TIMESTAMP 
                        WHERE session_id = ?
                    ''', (session_id,))
                    
                    conn.commit()
            
            # Update cache
            cache_key = f"{user_id}:{session_id}:{context_key}"
            self.cache[cache_key] = {
                "value": context_value,
                "timestamp": datetime.now(),
                "expires_at": expires_timestamp
            }
            
            return {"success": True, "context_key": context_key}
            
        except Exception as e:
            self.logger.error(f"Error storing context: {e}")
            return {"error": str(e)}
    
    async def _retrieve_context(self, input_data: Dict[str, Any], user_id: str, session_id: str) -> Dict[str, Any]:
        """Retrieve context data for a user session."""
        try:
            context_key = input_data.get('context_key')
            include_expired = input_data.get('include_expired', False)
            
            if context_key:
                # Retrieve specific context key
                cache_key = f"{user_id}:{session_id}:{context_key}"
                
                # Check cache first
                if cache_key in self.cache:
                    cached_item = self.cache[cache_key]
                    if (not cached_item.get('expires_at') or 
                        cached_item['expires_at'] > datetime.now()):
                        return {"context_key": context_key, "context_value": cached_item['value']}
                
                # Retrieve from database
                with self.db_lock:
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        
                        if include_expired:
                            cursor.execute('''
                                SELECT context_value, expires_at FROM context_data
                                WHERE user_id = ? AND session_id = ? AND context_key = ?
                                ORDER BY created_at DESC LIMIT 1
                            ''', (user_id, session_id, context_key))
                        else:
                            cursor.execute('''
                                SELECT context_value, expires_at FROM context_data
                                WHERE user_id = ? AND session_id = ? AND context_key = ?
                                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                                ORDER BY created_at DESC LIMIT 1
                            ''', (user_id, session_id, context_key))
                        
                        result = cursor.fetchone()
                        
                        if result:
                            context_value = json.loads(result[0])
                            expires_at = result[1]
                            
                            # Update cache
                            self.cache[cache_key] = {
                                "value": context_value,
                                "timestamp": datetime.now(),
                                "expires_at": datetime.fromisoformat(expires_at) if expires_at else None
                            }
                            
                            return {"context_key": context_key, "context_value": context_value}
                        else:
                            return {"context_key": context_key, "context_value": None}
            else:
                # Retrieve all context for user/session
                with self.db_lock:
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        
                        cursor.execute('''
                            SELECT context_key, context_value, expires_at FROM context_data
                            WHERE user_id = ? AND session_id = ?
                            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                            ORDER BY created_at DESC
                        ''', (user_id, session_id))
                        
                        results = cursor.fetchall()
                        context_data = {}
                        
                        for context_key, context_value, expires_at in results:
                            context_data[context_key] = json.loads(context_value)
                        
                        return {"context_data": context_data}
            
        except Exception as e:
            self.logger.error(f"Error retrieving context: {e}")
            return {"error": str(e)}
    
    async def _update_user_preferences(self, input_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Update user preferences."""
        try:
            preferences = input_data.get('preferences', {})
            
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Get existing preferences
                    cursor.execute('SELECT preferences FROM user_preferences WHERE user_id = ?', (user_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        # Update existing preferences
                        existing_prefs = json.loads(result[0])
                        existing_prefs.update(preferences)
                        updated_prefs = existing_prefs
                    else:
                        # Create new preferences
                        updated_prefs = preferences
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_preferences 
                        (user_id, preferences, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    ''', (user_id, json.dumps(updated_prefs)))
                    
                    conn.commit()
            
            return {"success": True, "preferences": updated_prefs}
            
        except Exception as e:
            self.logger.error(f"Error updating preferences: {e}")
            return {"error": str(e)}
    
    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences."""
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('SELECT preferences FROM user_preferences WHERE user_id = ?', (user_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        preferences = json.loads(result[0])
                        return {"preferences": preferences}
                    else:
                        return {"preferences": {}}
            
        except Exception as e:
            self.logger.error(f"Error getting preferences: {e}")
            return {"error": str(e)}
    
    async def _store_conversation(self, input_data: Dict[str, Any], user_id: str, session_id: str) -> Dict[str, Any]:
        """Store conversation interaction."""
        try:
            message = input_data.get('message', '')
            response = input_data.get('response', '')
            sentiment = input_data.get('sentiment', 'neutral')
            intent = input_data.get('intent', 'general')
            
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT INTO conversation_history 
                        (user_id, session_id, message, response, sentiment, intent)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (user_id, session_id, message, response, sentiment, intent))
                    
                    conn.commit()
            
            return {"success": True}
            
        except Exception as e:
            self.logger.error(f"Error storing conversation: {e}")
            return {"error": str(e)}
    
    async def _get_conversation_history(self, user_id: str, session_id: str = None, limit: int = 50) -> Dict[str, Any]:
        """Get conversation history for a user."""
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    if session_id:
                        cursor.execute('''
                            SELECT message, response, sentiment, intent, created_at
                            FROM conversation_history
                            WHERE user_id = ? AND session_id = ?
                            ORDER BY created_at DESC
                            LIMIT ?
                        ''', (user_id, session_id, limit))
                    else:
                        cursor.execute('''
                            SELECT message, response, sentiment, intent, created_at
                            FROM conversation_history
                            WHERE user_id = ?
                            ORDER BY created_at DESC
                            LIMIT ?
                        ''', (user_id, limit))
                    
                    results = cursor.fetchall()
                    
                    conversations = []
                    for message, response, sentiment, intent, created_at in results:
                        conversations.append({
                            "message": message,
                            "response": response,
                            "sentiment": sentiment,
                            "intent": intent,
                            "created_at": created_at
                        })
                    
                    return {"conversations": conversations}
            
        except Exception as e:
            self.logger.error(f"Error getting conversation history: {e}")
            return {"error": str(e)}
    
    def cleanup_expired_data(self):
        """Clean up expired context data and old sessions."""
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Remove expired context data
                    cursor.execute('DELETE FROM context_data WHERE expires_at < CURRENT_TIMESTAMP')
                    
                    # Remove old inactive sessions (older than 24 hours)
                    cursor.execute('''
                        DELETE FROM user_sessions 
                        WHERE last_activity < datetime('now', '-24 hours')
                    ''')
                    
                    conn.commit()
            
            # Clean up cache
            current_time = datetime.now()
            expired_keys = []
            for key, value in self.cache.items():
                if (value.get('expires_at') and 
                    value['expires_at'] < current_time):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
            
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
