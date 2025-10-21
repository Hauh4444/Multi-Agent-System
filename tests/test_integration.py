"""
Integration tests for the multi-agent system.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from flask import Flask
from flask_socketio import SocketIO
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
from orchestrator import AIOrchestrator
from agents import ConversationalAgent, MemoryAgent, MatchingAgent


class TestIntegration:
    """Integration tests for the multi-agent system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock all external dependencies
        with patch('app.Config') as mock_config, \
             patch('google.genai') as mock_genai, \
             patch('agents.conversational_agent.openai') as mock_openai:
            
            # Configure mock config
            mock_config.return_value.GOOGLE_API_KEY = "test_key"
            mock_config.return_value.OPENAI_API_KEY = "test_key"
            mock_config.return_value.SECRET_KEY = "test_secret"
            
            # Configure mock genai
            mock_genai.Client.return_value = Mock()
            
            # Configure mock openai
            mock_openai.OpenAI.return_value = Mock()
            
            self.app = app.app
            self.app.config['TESTING'] = True
            self.client = self.app.test_client()
            self.socketio = app.socketio
    
    def test_app_creation(self):
        """Test Flask app creation."""
        assert self.app is not None
        assert self.app.config['TESTING'] is True
    
    def test_orchestrator_integration(self):
        """Test orchestrator with real agents."""
        with patch('orchestrator.Config') as mock_config, \
             patch('google.genai') as mock_genai, \
             patch('agents.conversational_agent.openai') as mock_openai:
            
            mock_config.return_value.GOOGLE_API_KEY = "test_key"
            mock_config.return_value.OPENAI_API_KEY = "test_key"
            mock_genai.Client.return_value = Mock()
            mock_openai.OpenAI.return_value = Mock()
            
            orchestrator = AIOrchestrator()
            
            # Verify all agents are initialized
            assert "conversational" in orchestrator.agents
            assert "memory" in orchestrator.agents
            assert "matching" in orchestrator.agents
            
            # Verify agents are of correct types
            assert isinstance(orchestrator.agents["conversational"], ConversationalAgent)
            assert isinstance(orchestrator.agents["memory"], MemoryAgent)
            assert isinstance(orchestrator.agents["matching"], MatchingAgent)
    
    @pytest.mark.asyncio
    async def test_end_to_end_request_processing(self):
        """Test complete request processing flow."""
        with patch('orchestrator.Config') as mock_config, \
             patch('google.genai') as mock_genai, \
             patch('agents.conversational_agent.openai') as mock_openai:
            
            mock_config.return_value.GOOGLE_API_KEY = "test_key"
            mock_config.return_value.OPENAI_API_KEY = "test_key"
            mock_genai.Client.return_value = Mock()
            mock_openai.OpenAI.return_value = Mock()
            
            orchestrator = AIOrchestrator()
            
            # Mock all agent process methods
            orchestrator.agents["memory"].process = AsyncMock(return_value={
                "operation": "retrieve",
                "result": {"user_preferences": {}, "conversation_history": []},
                "agent_id": "memory_agent",
                "timestamp": "2023-01-01T00:00:00"
            })
            
            orchestrator.agents["matching"].process = AsyncMock(return_value={
                "intent": {"primary": "greeting"},
                "entities": [],
                "confidence": 0.8,
                "suggestions": []
            })
            
            orchestrator.agents["conversational"].process = AsyncMock(return_value={
                "response": "Hello! How can I help you?",
                "sentiment": "positive",
                "dialogue_state": "neutral"
            })
            
            # Process a request
            result = await orchestrator.handle_request("Hello!", "user1", "session1")
            
            # Verify the result
            assert "response" in result
            assert "metadata" in result
            assert "context" in result
            assert "suggestions" in result
            assert result["response"] == "Hello! How can I help you?"
            assert result["context"]["sentiment"] == "positive"
            assert result["context"]["intent"] == "greeting"
    
    @pytest.mark.asyncio
    async def test_memory_agent_integration(self):
        """Test memory agent integration with orchestrator."""
        with patch('orchestrator.Config') as mock_config, \
             patch('google.genai') as mock_genai, \
             patch('agents.conversational_agent.openai') as mock_openai:
            
            mock_config.return_value.GOOGLE_API_KEY = "test_key"
            mock_config.return_value.OPENAI_API_KEY = "test_key"
            mock_genai.Client.return_value = Mock()
            mock_openai.OpenAI.return_value = Mock()
            
            orchestrator = AIOrchestrator()
            
            # Test memory agent operations
            memory_agent = orchestrator.agents["memory"]
            
            # Test storing data
            store_result = await memory_agent.process({
                "operation": "store",
                "user_id": "test_user",
                "session_id": "test_session",
                "context_key": "session_data",
                "context_value": {"key": "value"}
            })
            
            assert store_result["operation"] == "store"
            assert "result" in store_result
            
            # Test retrieving data
            retrieve_result = await memory_agent.process({
                "operation": "retrieve",
                "user_id": "test_user",
                "session_id": "test_session"
            })
            
            assert retrieve_result["operation"] == "retrieve"
            assert "result" in retrieve_result
    
    @pytest.mark.asyncio
    async def test_matching_agent_integration(self):
        """Test matching agent integration with orchestrator."""
        with patch('orchestrator.Config') as mock_config, \
             patch('google.genai') as mock_genai, \
             patch('agents.conversational_agent.openai') as mock_openai:
            
            mock_config.return_value.GOOGLE_API_KEY = "test_key"
            mock_config.return_value.OPENAI_API_KEY = "test_key"
            mock_genai.Client.return_value = Mock()
            mock_openai.OpenAI.return_value = Mock()
            
            orchestrator = AIOrchestrator()
            
            # Test matching agent
            matching_agent = orchestrator.agents["matching"]
            
            result = await matching_agent.process({
                "message": "Hello there!",
                "user_id": "test_user",
                "session_id": "test_session"
            })
            
            assert "intent" in result
            assert "entities" in result
            assert "confidence" in result
            assert "action_route" in result
            assert "suggestions" in result
    
    def test_api_endpoints(self):
        """Test API endpoints."""
        # Test agents status endpoint
        response = self.client.get('/api/agents/status')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert "system_metrics" in data
        assert "agent_statuses" in data
        assert "active_sessions" in data
        assert "timestamp" in data
    
    def test_session_management(self):
        """Test session management endpoints."""
        # Test creating a new session with proper JSON headers
        response = self.client.post('/api/session/new', 
                                  content_type='application/json',
                                  data=json.dumps({}))
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert "user_id" in data
        assert "session_id" in data
        assert "timestamp" in data
        
        session_id = data["session_id"]
        
        # Test getting session info
        response = self.client.get(f'/api/session/{session_id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert "session_id" in data
        assert data["session_id"] == session_id
    
    @pytest.mark.asyncio
    async def test_conversation_flow(self):
        """Test complete conversation flow."""
        with patch('orchestrator.Config') as mock_config, \
             patch('google.genai') as mock_genai, \
             patch('agents.conversational_agent.openai') as mock_openai:
            
            mock_config.return_value.GOOGLE_API_KEY = "test_key"
            mock_config.return_value.OPENAI_API_KEY = "test_key"
            mock_genai.Client.return_value = Mock()
            mock_openai.OpenAI.return_value = Mock()
            
            orchestrator = AIOrchestrator()
            
            # Mock all agent process methods
            for agent in orchestrator.agents.values():
                agent.process = AsyncMock(return_value={"result": "success"})
            
            # First message
            result1 = await orchestrator.handle_request("Hello!", "user1", "session1")
            assert "response" in result1
            assert "metadata" in result1
            assert "context" in result1
            
            # Second message with context
            result2 = await orchestrator.handle_request("What can you do?", "user1", "session1")
            assert "response" in result2
            assert "metadata" in result2
            assert "context" in result2
    
    def test_error_handling(self):
        """Test error handling across the system."""
        with patch('orchestrator.Config') as mock_config, \
             patch('google.genai') as mock_genai, \
             patch('agents.conversational_agent.openai') as mock_openai:
            
            mock_config.return_value.GOOGLE_API_KEY = "test_key"
            mock_config.return_value.OPENAI_API_KEY = "test_key"
            mock_genai.Client.return_value = Mock()
            mock_openai.OpenAI.return_value = Mock()
            
            orchestrator = AIOrchestrator()
            
            # Test with invalid session
            result = orchestrator.get_session_info("invalid_session")
            assert "error" in result
            assert result["error"] == "Session not found"
    
    def test_system_metrics_accuracy(self):
        """Test system metrics are accurate."""
        with patch('orchestrator.Config') as mock_config, \
             patch('google.genai') as mock_genai, \
             patch('agents.conversational_agent.openai') as mock_openai:
            
            mock_config.return_value.GOOGLE_API_KEY = "test_key"
            mock_config.return_value.OPENAI_API_KEY = "test_key"
            mock_genai.Client.return_value = Mock()
            mock_openai.OpenAI.return_value = Mock()
            
            orchestrator = AIOrchestrator()
            
            # Add some sessions manually
            session1 = "session1"
            session2 = "session2"
            orchestrator.active_sessions[session1] = {"user_id": "user1", "created_at": "2023-01-01"}
            orchestrator.active_sessions[session2] = {"user_id": "user2", "created_at": "2023-01-01"}
            
            # Check metrics
            status = orchestrator.get_system_status()
            assert status["active_sessions"] == 2
            
            # Remove a session
            del orchestrator.active_sessions[session1]
            status = orchestrator.get_system_status()
            assert status["active_sessions"] == 1
    
    def test_agent_communication(self):
        """Test communication between agents."""
        with patch('orchestrator.Config') as mock_config, \
             patch('google.genai') as mock_genai, \
             patch('agents.conversational_agent.openai') as mock_openai:
            
            mock_config.return_value.GOOGLE_API_KEY = "test_key"
            mock_config.return_value.OPENAI_API_KEY = "test_key"
            mock_genai.Client.return_value = Mock()
            mock_openai.OpenAI.return_value = Mock()
            
            orchestrator = AIOrchestrator()
            
            # Test that agents can access each other's data
            session_id = "test_session"
            
            # Memory agent stores data
            memory_result = asyncio.run(orchestrator.agents["memory"].process({
                "operation": "store",
                "user_id": "test_user",
                "session_id": session_id,
                "context_key": "session_data",
                "context_value": {"key": "value"}
            }))
            
            assert memory_result["operation"] == "store"
            
            # Conversational agent should be able to access this data
            context_result = asyncio.run(orchestrator.agents["memory"].process({
                "operation": "retrieve",
                "user_id": "test_user",
                "session_id": session_id
            }))
            
            assert context_result["operation"] == "retrieve"
    
    def test_concurrent_sessions(self):
        """Test handling multiple concurrent sessions."""
        with patch('orchestrator.Config') as mock_config, \
             patch('google.genai') as mock_genai, \
             patch('agents.conversational_agent.openai') as mock_openai:
            
            mock_config.return_value.GOOGLE_API_KEY = "test_key"
            mock_config.return_value.OPENAI_API_KEY = "test_key"
            mock_genai.Client.return_value = Mock()
            mock_openai.OpenAI.return_value = Mock()
            
            orchestrator = AIOrchestrator()
            
            # Create multiple sessions
            sessions = []
            for i in range(5):
                session_id = f"session{i}"
                orchestrator.active_sessions[session_id] = {
                    "user_id": f"user{i}",
                    "created_at": "2023-01-01T00:00:00"
                }
                sessions.append(session_id)
            
            # Verify all sessions exist
            assert len(orchestrator.active_sessions) == 5
            
            # Verify each session is independent
            for i, session_id in enumerate(sessions):
                session_data = orchestrator.active_sessions[session_id]
                assert session_data["user_id"] == f"user{i}"
    
    def test_cleanup_functionality(self):
        """Test cleanup functionality."""
        with patch('orchestrator.Config') as mock_config, \
             patch('google.genai') as mock_genai, \
             patch('agents.conversational_agent.openai') as mock_openai:
            
            mock_config.return_value.GOOGLE_API_KEY = "test_key"
            mock_config.return_value.OPENAI_API_KEY = "test_key"
            mock_genai.Client.return_value = Mock()
            mock_openai.OpenAI.return_value = Mock()
            
            orchestrator = AIOrchestrator()
            
            # Create some sessions
            session1 = "session1"
            session2 = "session2"
            orchestrator.active_sessions[session1] = {"user_id": "user1", "created_at": "2023-01-01"}
            orchestrator.active_sessions[session2] = {"user_id": "user2", "created_at": "2023-01-01"}
            
            # Remove one session
            del orchestrator.active_sessions[session1]
            
            # Verify cleanup
            assert session1 not in orchestrator.active_sessions
            assert session2 in orchestrator.active_sessions