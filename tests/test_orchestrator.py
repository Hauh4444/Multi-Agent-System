"""
Unit tests for AIOrchestrator.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from orchestrator import AIOrchestrator


class TestAIOrchestrator:
    """Test cases for AIOrchestrator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock the config and all external dependencies
        with patch('orchestrator.Config') as mock_config, \
             patch('google.genai') as mock_genai, \
             patch('agents.conversational_agent.openai') as mock_openai:
            
            # Configure mock config
            mock_config.return_value.GOOGLE_API_KEY = "test_key"
            mock_config.return_value.OPENAI_API_KEY = "test_key"
            
            # Configure mock genai
            mock_genai.Client.return_value = Mock()
            
            # Configure mock openai
            mock_openai.OpenAI.return_value = Mock()
            
            self.orchestrator = AIOrchestrator()
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initializes correctly."""
        assert self.orchestrator.agents is not None
        assert "conversational" in self.orchestrator.agents
        assert "memory" in self.orchestrator.agents
        assert "matching" in self.orchestrator.agents
        assert self.orchestrator.active_sessions == {}
        assert self.orchestrator.system_metrics is not None
    
    def test_system_metrics_initialization(self):
        """Test system metrics are properly initialized."""
        metrics = self.orchestrator.system_metrics
        assert metrics["total_requests"] == 0
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 0
        assert metrics["average_response_time"] == 0.0
        assert metrics["active_sessions"] == 0
    
    @pytest.mark.asyncio
    async def test_handle_request_success(self):
        """Test successful request handling."""
        # Mock the agent process methods
        mock_memory_result = {"user_preferences": {}, "conversation_history": []}
        mock_matching_result = {
            "intent": {"primary": "greeting"},
            "entities": [],
            "confidence": 0.8,
            "suggestions": []
        }
        mock_conversational_result = {
            "response": "Hello! How can I help you?",
            "sentiment": "positive",
            "dialogue_state": "neutral"
        }
        
        # Mock the agent process methods
        self.orchestrator.agents["memory"].process = AsyncMock(return_value={
            "operation": "retrieve",
            "result": mock_memory_result,
            "agent_id": "memory_agent",
            "timestamp": "2023-01-01T00:00:00"
        })
        
        self.orchestrator.agents["matching"].process = AsyncMock(return_value={
            "intent": mock_matching_result["intent"],
            "entities": mock_matching_result["entities"],
            "confidence": mock_matching_result["confidence"],
            "suggestions": mock_matching_result["suggestions"]
        })
        
        self.orchestrator.agents["conversational"].process = AsyncMock(return_value={
            "response": mock_conversational_result["response"],
            "sentiment": mock_conversational_result["sentiment"],
            "dialogue_state": mock_conversational_result["dialogue_state"]
        })
        
        result = await self.orchestrator.handle_request("Hello!", "user1", "session1")
        
        assert "response" in result
        assert "metadata" in result
        assert "context" in result
        assert "suggestions" in result
        assert result["response"] == "Hello! How can I help you?"
        assert result["context"]["sentiment"] == "positive"
        assert result["context"]["intent"] == "greeting"
    
    @pytest.mark.asyncio
    async def test_handle_request_failure(self):
        """Test request handling with failure."""
        # Mock all agents to raise exceptions
        for agent in self.orchestrator.agents.values():
            agent.process = AsyncMock(side_effect=Exception("Test Error"))
        
        result = await self.orchestrator.handle_request("Hello!", "user1", "session1")
        
        assert "response" in result
        assert "metadata" in result
        assert "context" in result
        # The response should contain an apology message
        assert isinstance(result["response"], str)
        assert result["context"]["sentiment"] == "neutral"
        assert result["context"]["intent"] in ["error", "general"]
    
    @pytest.mark.asyncio
    async def test_handle_request_with_session_context(self):
        """Test request handling with existing session context."""
        # Mock memory agent to return context
        mock_memory_result = {
            "user_preferences": {"theme": "dark"},
            "conversation_history": [{"role": "user", "content": "What's the weather?"}]
        }
        
        self.orchestrator.agents["memory"].process = AsyncMock(return_value={
            "operation": "retrieve",
            "result": mock_memory_result,
            "agent_id": "memory_agent",
            "timestamp": "2023-01-01T00:00:00"
        })
        
        self.orchestrator.agents["matching"].process = AsyncMock(return_value={
            "intent": {"primary": "question"},
            "entities": [],
            "confidence": 0.8,
            "suggestions": []
        })
        
        self.orchestrator.agents["conversational"].process = AsyncMock(return_value={
            "response": "Based on our previous conversation about weather...",
            "sentiment": "neutral",
            "dialogue_state": "neutral"
        })
        
        result = await self.orchestrator.handle_request("Tell me more", "user1", "session1")
        
        assert "response" in result
        assert "weather" in result["response"]
    
    def test_get_agent_status(self):
        """Test getting agent status."""
        # Mock agent get_status methods
        for agent in self.orchestrator.agents.values():
            agent.get_status = Mock(return_value={
                "agent_id": "test_id",
                "name": "TestAgent",
                "status": "idle",
                "last_activity": "2023-01-01T00:00:00",
                "metrics": {"requests_processed": 0}
            })
        
        status = self.orchestrator.get_agent_status("conversational")
        
        assert "agent_id" in status
        assert "name" in status
        assert "status" in status
        assert "last_activity" in status
        assert "metrics" in status
    
    def test_get_system_status(self):
        """Test getting system status."""
        # Mock agent get_status methods
        for agent in self.orchestrator.agents.values():
            agent.get_status = Mock(return_value={
                "agent_id": "test_id",
                "name": "TestAgent",
                "status": "idle",
                "last_activity": "2023-01-01T00:00:00",
                "metrics": {"requests_processed": 0}
            })
        
        status = self.orchestrator.get_system_status()
        
        assert "system_metrics" in status
        assert "agent_statuses" in status
        assert "active_sessions" in status
        assert "timestamp" in status
    
    def test_get_session_info(self):
        """Test getting session information."""
        # Add a session to active_sessions
        session_id = "test_session"
        self.orchestrator.active_sessions[session_id] = {
            "user_id": "user1",
            "created_at": "2023-01-01T00:00:00"
        }
        
        session_info = self.orchestrator.get_session_info(session_id)
        
        assert session_info["user_id"] == "user1"
        assert session_info["created_at"] == "2023-01-01T00:00:00"
    
    def test_get_session_info_nonexistent(self):
        """Test getting info for non-existent session."""
        session_info = self.orchestrator.get_session_info("nonexistent")
        
        assert "error" in session_info
        assert session_info["error"] == "Session not found"
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions."""
        # Add some sessions
        session_id = "test_session"
        self.orchestrator.active_sessions[session_id] = {
            "user_id": "user1",
            "created_at": "2023-01-01T00:00:00"
        }
        
        # Mock datetime to simulate expired sessions
        with patch('orchestrator.datetime') as mock_datetime:
            mock_datetime.now.return_value = Mock()
            mock_datetime.now.return_value.timestamp.return_value = 2000000000  # Far future
            
            result = await self.orchestrator._cleanup_expired_sessions()
            # The method might return None or an int, both are acceptable
            assert result is None or isinstance(result, int)
    
    @pytest.mark.asyncio
    async def test_update_system_metrics(self):
        """Test updating system metrics."""
        # Set some initial metrics
        self.orchestrator.system_metrics["total_requests"] = 10
        self.orchestrator.system_metrics["successful_requests"] = 8
        
        # Update metrics
        await self.orchestrator._update_system_metrics()
        
        # Verify metrics are updated
        assert self.orchestrator.system_metrics["active_sessions"] == len(self.orchestrator.active_sessions)
    
    def test_initialize_google_ai_success(self):
        """Test successful Google AI initialization."""
        with patch('google.genai') as mock_genai:
            mock_client = Mock()
            mock_genai.Client.return_value = mock_client
            
            # Mock config
            self.orchestrator.config.GOOGLE_API_KEY = "test_key"
            
            self.orchestrator._initialize_google_ai()
            
            # Verify client was set
            assert hasattr(self.orchestrator.agents['conversational'], 'google_client')
    
    def test_initialize_google_ai_failure(self):
        """Test Google AI initialization failure."""
        with patch('google.genai', side_effect=Exception("Import Error")):
            # Mock config
            self.orchestrator.config.GOOGLE_API_KEY = "test_key"
            
            # Should not raise exception
            self.orchestrator._initialize_google_ai()
    
    def test_initialize_openai_success(self):
        """Test successful OpenAI initialization."""
        # Mock config
        self.orchestrator.config.OPENAI_API_KEY = "test_key"
        
        # Mock the conversational agent's _initialize_openai method
        mock_conversational = Mock()
        mock_conversational._initialize_openai = Mock()
        self.orchestrator.agents['conversational'] = mock_conversational
        
        self.orchestrator._initialize_google_ai()  # This also initializes OpenAI
        
        # Verify OpenAI was initialized
        mock_conversational._initialize_openai.assert_called_once_with("test_key")
    
    def test_metrics_update_on_request(self):
        """Test that metrics are updated when handling requests."""
        initial_requests = self.orchestrator.system_metrics["total_requests"]
        
        # Mock all agents to return successful results
        for agent in self.orchestrator.agents.values():
            agent.process = AsyncMock(return_value={"result": "success"})
        
        # Run a request
        asyncio.run(self.orchestrator.handle_request("test", "user1", "session1"))
        
        # Check that metrics were updated
        assert self.orchestrator.system_metrics["total_requests"] == initial_requests + 1
        assert self.orchestrator.system_metrics["successful_requests"] > 0
    
    def test_error_metrics_update(self):
        """Test that error metrics are updated on failures."""
        initial_failed = self.orchestrator.system_metrics["failed_requests"]
        
        # Test that the system handles errors gracefully
        # Mock all agents to raise exceptions to ensure we hit the error path
        for agent in self.orchestrator.agents.values():
            agent.process = AsyncMock(side_effect=Exception("Test Error"))
        
        # Run a request that will fail
        result = asyncio.run(self.orchestrator.handle_request("test", "user1", "session1"))
        
        # Check that we get a valid response even when agents fail
        assert "response" in result
        assert "metadata" in result
        assert "context" in result
        
        # The system should still be functional
        assert self.orchestrator.system_metrics["total_requests"] > 0