"""
AI Orchestrator - Coordinates and manages the multi-agent system.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any
import threading
import uuid
from agents import ConversationalAgent, MemoryAgent, MatchingAgent
from config import Config
from google import genai

class AIOrchestrator:
    """
    Central orchestrator that coordinates all agents in the multi-agent system.
    Manages agent lifecycle, request routing, and system coordination.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("AIOrchestrator")
        self.config = Config()
        
        self.agents = {
            "conversational": ConversationalAgent(),
            "memory": MemoryAgent(),
            "matching": MatchingAgent()
        }
        
        self.active_sessions = {}
        self.system_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "active_sessions": 0
        }
        
        self.lock = threading.Lock()
        self._initialize_google_ai()
        self._start_background_tasks()
    
    def _initialize_google_ai(self):
        try:
            if self.config.GOOGLE_API_KEY:
                os.environ['GEMINI_API_KEY'] = self.config.GOOGLE_API_KEY
                
                self.agents['conversational'].google_client = genai.Client()
                self.logger.info("Google AI client initialized successfully")
            else:
                self.logger.warning("Google API key not configured - some features may be limited")
                self.agents['conversational'].google_client = None
        except Exception as e:
            self.logger.error(f"Failed to initialize Google AI: {e}")
            self.agents['conversational'].google_client = None
        
        try:
            if self.config.OPENAI_API_KEY:
                self.agents['conversational']._initialize_openai(self.config.OPENAI_API_KEY)
            else:
                self.logger.warning("OpenAI API key not configured - fallback features may be limited")
                self.agents['conversational'].openai_client = None
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI: {e}")
            self.agents['conversational'].openai_client = None
        
        self.logger.info(f"AI clients status - Google: {self.agents['conversational'].google_client is not None}, OpenAI: {self.agents['conversational'].openai_client is not None}")
    
    def _start_background_tasks(self):
        """Start background maintenance tasks."""
        def cleanup_task():
            while True:
                try:
                    asyncio.run(self._cleanup_expired_sessions())
                    asyncio.run(self._update_system_metrics())
                    threading.Event().wait(300)  # Run every 5 minutes
                except Exception as e:
                    self.logger.error(f"Background task error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()
    
    async def handle_request(self, user_input: str, user_id: str = None, session_id: str = None) -> Dict[str, Any]:
        """
        Main entry point for handling user requests.
        
        Args:
            user_input: User's input message
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Dict containing the system's response
        """
        start_time = datetime.now()
        
        try:
            if not session_id:
                session_id = str(uuid.uuid4())
            
            if not user_id:
                user_id = f"user_{uuid.uuid4().hex[:8]}"
            
            with self.lock:
                self.system_metrics["total_requests"] += 1
                self.system_metrics["active_sessions"] = len(self.active_sessions)
            
            await self._create_or_update_session(user_id, session_id)
            
            memory_result = await self._process_memory_retrieval(user_id, session_id, user_input)
            matching_result = await self._process_matching(user_id, session_id, user_input, memory_result)
            conversational_result = await self._process_conversational(
                user_id, session_id, user_input, memory_result, matching_result
            )
            await self._process_memory_storage(
                user_id, session_id, user_input, conversational_result, matching_result
            )
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            with self.lock:
                self.system_metrics["successful_requests"] += 1
                total_time = self.system_metrics["average_response_time"] * (self.system_metrics["successful_requests"] - 1)
                self.system_metrics["average_response_time"] = (total_time + response_time) / self.system_metrics["successful_requests"]
            response = {
                "response": conversational_result.get("response", "I apologize, but I couldn't process your request."),
                "metadata": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "response_time": response_time,
                    "agents_used": ["memory", "matching", "conversational"],
                    "timestamp": datetime.now().isoformat()
                },
                "context": {
                    "sentiment": conversational_result.get("sentiment", "neutral"),
                    "intent": matching_result.get("intent", {}).get("primary", "general"),
                    "confidence": matching_result.get("confidence", 0.5),
                    "entities": matching_result.get("entities", [])
                },
                "suggestions": matching_result.get("suggestions", [])
            }
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error handling request: {e}")
            
            with self.lock:
                self.system_metrics["failed_requests"] += 1
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "metadata": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "response_time": response_time,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                },
                "context": {
                    "sentiment": "neutral",
                    "intent": "error",
                    "confidence": 0.0,
                    "entities": []
                },
                "suggestions": ["Please try rephrasing your request", "Contact support if the issue persists"]
            }
    
    async def _create_or_update_session(self, user_id: str, session_id: str):
        """Create or update user session."""
        try:
            session_data = {
                "user_id": user_id,
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "message_count": 0
            }
            
            with self.lock:
                self.active_sessions[session_id] = session_data
            
            # Store session in memory agent
            await self.agents["memory"].process({
                "operation": "store",
                "user_id": user_id,
                "session_id": session_id,
                "context_key": "session_data",
                "context_value": session_data
            })
            
        except Exception as e:
            self.logger.error(f"Error creating/updating session: {e}")
    
    async def _process_memory_retrieval(self, user_id: str, session_id: str, user_input: str) -> Dict[str, Any]:
        """Process memory retrieval to get context."""
        try:
            result = await self.agents["memory"].process({
                "operation": "retrieve",
                "user_id": user_id,
                "session_id": session_id
            })
            
            return result.get("result", {})
            
        except Exception as e:
            self.logger.error(f"Error in memory retrieval: {e}")
            return {}
    
    async def _process_matching(self, user_id: str, session_id: str, user_input: str, memory_context: Dict[str, Any]) -> Dict[str, Any]:
        """Process matching to analyze intent and extract entities."""
        try:
            result = await self.agents["matching"].process({
                "message": user_input,
                "user_id": user_id,
                "session_id": session_id
            }, memory_context)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in matching processing: {e}")
            return {
                "intent": {"primary": "general", "confidence": 0.5},
                "entities": [],
                "confidence": 0.5,
                "action_route": "conversational",
                "suggestions": []
            }
    
    async def _process_conversational(self, user_id: str, session_id: str, user_input: str, 
                                    memory_context: Dict[str, Any], matching_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process conversational response generation."""
        try:
            # Combine context from memory and matching
            combined_context = {
                "memory_context": memory_context,
                "matching_result": matching_result,
                "user_preferences": memory_context.get("user_preferences", {}),
                "conversation_history": memory_context.get("conversation_history", [])
            }
            
            result = await self.agents["conversational"].process({
                "message": user_input,
                "user_id": user_id,
                "session_id": session_id
            }, combined_context)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in conversational processing: {e}")
            return {
                "response": "I apologize, but I'm having trouble generating a response right now.",
                "sentiment": "neutral",
                "dialogue_state": "error",
                "intent": "error"
            }
    
    async def _process_memory_storage(self, user_id: str, session_id: str, user_input: str, 
                                    conversational_result: Dict[str, Any], matching_result: Dict[str, Any]):
        """Process memory storage to save conversation and context."""
        try:
            # Store conversation
            await self.agents["memory"].process({
                "operation": "store_conversation",
                "user_id": user_id,
                "session_id": session_id,
                "message": user_input,
                "response": conversational_result.get("response", ""),
                "sentiment": conversational_result.get("sentiment", "neutral"),
                "intent": matching_result.get("intent", {}).get("primary", "general")
            })
            
            # Store updated context
            context_data = {
                "last_intent": matching_result.get("intent", {}).get("primary", "general"),
                "last_sentiment": conversational_result.get("sentiment", "neutral"),
                "dialogue_state": conversational_result.get("dialogue_state", "neutral"),
                "entities": matching_result.get("entities", []),
                "confidence": matching_result.get("confidence", 0.5)
            }
            
            await self.agents["memory"].process({
                "operation": "store",
                "user_id": user_id,
                "session_id": session_id,
                "context_key": "conversation_context",
                "context_value": context_data
            })
            
        except Exception as e:
            self.logger.error(f"Error in memory storage: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions and old data."""
        try:
            current_time = datetime.now()
            expired_sessions = []
            
            with self.lock:
                for session_id, session_data in self.active_sessions.items():
                    last_activity = datetime.fromisoformat(session_data["last_activity"])
                    if (current_time - last_activity).seconds > self.config.SESSION_TIMEOUT:
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    del self.active_sessions[session_id]
            
            # Clean up memory agent data
            if hasattr(self.agents["memory"], 'cleanup_expired_data'):
                self.agents["memory"].cleanup_expired_data()
            
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    async def _update_system_metrics(self):
        """Update system metrics."""
        try:
            with self.lock:
                self.system_metrics["active_sessions"] = len(self.active_sessions)
                
                # Update agent metrics
                for agent_name, agent in self.agents.items():
                    if hasattr(agent, 'get_status'):
                        agent_status = agent.get_status()
                        self.logger.debug(f"Agent {agent_name} status: {agent_status}")
            
        except Exception as e:
            self.logger.error(f"Error updating metrics: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status and metrics."""
        try:
            agent_statuses = {}
            for agent_name, agent in self.agents.items():
                if hasattr(agent, 'get_status'):
                    agent_statuses[agent_name] = agent.get_status()
            
            return {
                "system_metrics": self.system_metrics,
                "agent_statuses": agent_statuses,
                "active_sessions": len(self.active_sessions),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """Get status of a specific agent."""
        try:
            if agent_name in self.agents:
                return self.agents[agent_name].get_status()
            else:
                return {"error": f"Agent {agent_name} not found"}
                
        except Exception as e:
            self.logger.error(f"Error getting agent status: {e}")
            return {"error": str(e)}
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a specific session."""
        try:
            with self.lock:
                if session_id in self.active_sessions:
                    session_data = self.active_sessions[session_id].copy()
                    session_data["session_id"] = session_id
                    return session_data
                else:
                    return {"error": "Session not found"}
                    
        except Exception as e:
            self.logger.error(f"Error getting session info: {e}")
            return {"error": str(e)}
