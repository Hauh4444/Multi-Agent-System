"""
Unit tests for MemoryAgent.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from agents.memory_agent import MemoryAgent


class TestMemoryAgent:
    """Test cases for MemoryAgent."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = MemoryAgent()
    
    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        assert self.agent.agent_id is not None
        assert self.agent.name == "MemoryAgent"
        assert self.agent.status == "idle"
        assert self.agent.metrics is not None
    
    @pytest.mark.asyncio
    async def test_process_store_operation(self):
        """Test storing session data."""
        input_data = {
            "operation": "store",
            "user_id": "test_user",
            "session_id": "test_session",
            "context_key": "session_data",
            "context_value": {"key": "value", "timestamp": "2023-01-01"}
        }
        
        result = await self.agent.process(input_data)
        
        assert result["operation"] == "store"
        assert "result" in result
        assert result["agent_id"] == self.agent.agent_id
    
    @pytest.mark.asyncio
    async def test_process_retrieve_operation(self):
        """Test retrieving session data."""
        input_data = {
            "operation": "retrieve",
            "user_id": "test_user",
            "session_id": "test_session"
        }
        
        result = await self.agent.process(input_data)
        
        assert result["operation"] == "retrieve"
        assert "result" in result
        assert result["agent_id"] == self.agent.agent_id
    
    @pytest.mark.asyncio
    async def test_process_update_preferences(self):
        """Test updating user preferences."""
        input_data = {
            "operation": "update_preferences",
            "user_id": "test_user",
            "preferences": {"theme": "dark", "language": "en"}
        }
        
        result = await self.agent.process(input_data)
        
        assert result["operation"] == "update_preferences"
        assert "result" in result
    
    @pytest.mark.asyncio
    async def test_process_get_preferences(self):
        """Test getting user preferences."""
        input_data = {
            "operation": "get_preferences",
            "user_id": "test_user"
        }
        
        result = await self.agent.process(input_data)
        
        assert result["operation"] == "get_preferences"
        assert "result" in result
    
    @pytest.mark.asyncio
    async def test_process_store_conversation(self):
        """Test storing conversation history."""
        input_data = {
            "operation": "store_conversation",
            "user_id": "test_user",
            "session_id": "test_session",
            "message": "Hello",
            "response": "Hi there!",
            "sentiment": "positive",
            "intent": "greeting"
        }
        
        result = await self.agent.process(input_data)
        
        assert result["operation"] == "store_conversation"
        assert "result" in result
    
    @pytest.mark.asyncio
    async def test_process_get_conversation_history(self):
        """Test getting conversation history."""
        input_data = {
            "operation": "get_conversation_history",
            "user_id": "test_user",
            "session_id": "test_session"
        }
        
        result = await self.agent.process(input_data)
        
        assert result["operation"] == "get_conversation_history"
        assert "result" in result
    
    @pytest.mark.asyncio
    async def test_process_unknown_operation(self):
        """Test handling unknown operation."""
        input_data = {
            "operation": "unknown_operation",
            "user_id": "test_user"
        }
        
        result = await self.agent.process(input_data)
        
        assert result["operation"] == "unknown_operation"
        assert "error" in result["result"]
    
    def test_get_status(self):
        """Test getting agent status."""
        status = self.agent.get_status()
        
        assert "agent_id" in status
        assert "name" in status
        assert "status" in status
        assert "last_activity" in status
        assert "metrics" in status
        assert status["name"] == "MemoryAgent"
    
    def test_update_metrics(self):
        """Test updating agent metrics."""
        initial_requests = self.agent.metrics["requests_processed"]
        
        self.agent.update_metrics(1.0, True)
        
        assert self.agent.metrics["requests_processed"] == initial_requests + 1
        assert self.agent.metrics["average_response_time"] > 0
    
    def test_set_status(self):
        """Test setting agent status."""
        self.agent.set_status("processing")
        
        assert self.agent.status == "processing"
        assert self.agent.last_activity is not None
    
    def test_cleanup_expired_data(self):
        """Test cleanup of expired data."""
        # This should not raise an exception
        result = self.agent.cleanup_expired_data()
        # The method might return None or an int, both are acceptable
        assert result is None or isinstance(result, int)