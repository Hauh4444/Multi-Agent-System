"""
Unit tests for MatchingAgent.
"""

import pytest
from unittest.mock import Mock, patch
from agents.matching_agent import MatchingAgent


class TestMatchingAgent:
    """Test cases for MatchingAgent."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = MatchingAgent()
    
    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        assert self.agent.agent_id is not None
        assert self.agent.name == "MatchingAgent"
        assert self.agent.status == "idle"
        assert self.agent.metrics is not None
    
    @pytest.mark.asyncio
    async def test_process_basic_matching(self):
        """Test basic matching functionality."""
        input_data = {
            "message": "Hello there!",
            "user_id": "test_user",
            "session_id": "test_session"
        }
        
        result = await self.agent.process(input_data)
        
        assert "intent" in result
        assert "entities" in result
        assert "confidence" in result
        assert "action_route" in result
        assert "suggestions" in result
    
    @pytest.mark.asyncio
    async def test_process_with_context(self):
        """Test processing with context."""
        input_data = {
            "message": "What's the weather like?",
            "user_id": "test_user",
            "session_id": "test_session"
        }
        
        context = {
            "user_preferences": {"location": "New York"},
            "conversation_history": []
        }
        
        result = await self.agent.process(input_data, context)
        
        assert "intent" in result
        assert "entities" in result
        assert "confidence" in result
        assert "action_route" in result
        assert "suggestions" in result
    
    @pytest.mark.asyncio
    async def test_process_greeting_message(self):
        """Test processing greeting messages."""
        input_data = {
            "message": "Hello! How are you?",
            "user_id": "test_user",
            "session_id": "test_session"
        }
        
        result = await self.agent.process(input_data)
        
        assert result["intent"]["primary"] == "greeting"
        assert result["confidence"] > 0.5
        assert result["action_route"] == "conversational"
    
    @pytest.mark.asyncio
    async def test_process_question_message(self):
        """Test processing question messages."""
        input_data = {
            "message": "What can you help me with?",
            "user_id": "test_user",
            "session_id": "test_session"
        }
        
        result = await self.agent.process(input_data)
        
        assert result["intent"]["primary"] == "question"
        assert result["confidence"] > 0.5
        assert result["action_route"] == "conversational"
    
    @pytest.mark.asyncio
    async def test_process_goodbye_message(self):
        """Test processing goodbye messages."""
        input_data = {
            "message": "Goodbye! See you later.",
            "user_id": "test_user",
            "session_id": "test_session"
        }
        
        result = await self.agent.process(input_data)
        
        assert result["intent"]["primary"] == "goodbye"
        assert result["confidence"] > 0.5
        assert result["action_route"] == "conversational"
    
    @pytest.mark.asyncio
    async def test_process_entity_extraction(self):
        """Test entity extraction from messages."""
        input_data = {
            "message": "I want to book a flight to Paris for next week",
            "user_id": "test_user",
            "session_id": "test_session"
        }
        
        result = await self.agent.process(input_data)
        
        assert "entities" in result
        assert len(result["entities"]) > 0
        # Should extract some entities (exact types may vary)
        entity_types = [entity["type"] for entity in result["entities"]]
        assert len(entity_types) > 0  # Should have at least one entity type
    
    @pytest.mark.asyncio
    async def test_process_with_user_preferences(self):
        """Test processing with user preferences in context."""
        input_data = {
            "message": "What's the weather like?",
            "user_id": "test_user",
            "session_id": "test_session"
        }
        
        context = {
            "user_preferences": {
                "location": "New York",
                "language": "en",
                "timezone": "EST"
            },
            "conversation_history": []
        }
        
        result = await self.agent.process(input_data, context)
        
        assert "intent" in result
        assert "entities" in result
        # Should consider user preferences in entity extraction
        if result["entities"]:
            location_entities = [e for e in result["entities"] if e["type"] == "location"]
            if location_entities:
                assert any("New York" in str(entity["value"]) for entity in location_entities)
    
    @pytest.mark.asyncio
    async def test_process_error_handling(self):
        """Test error handling in processing."""
        # Test with invalid input
        input_data = {
            "message": None,
            "user_id": "test_user",
            "session_id": "test_session"
        }
        
        result = await self.agent.process(input_data)
        
        # Should still return a valid result structure
        assert "intent" in result
        assert "entities" in result
        assert "confidence" in result
        assert "action_route" in result
        assert "suggestions" in result
    
    def test_get_status(self):
        """Test getting agent status."""
        status = self.agent.get_status()
        
        assert "agent_id" in status
        assert "name" in status
        assert "status" in status
        assert "last_activity" in status
        assert "metrics" in status
        assert status["name"] == "MatchingAgent"
    
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
    
    @pytest.mark.asyncio
    async def test_process_empty_message(self):
        """Test processing empty message."""
        input_data = {
            "message": "",
            "user_id": "test_user",
            "session_id": "test_session"
        }
        
        result = await self.agent.process(input_data)
        
        assert "intent" in result
        assert "entities" in result
        assert "confidence" in result
        assert "action_route" in result
        assert "suggestions" in result