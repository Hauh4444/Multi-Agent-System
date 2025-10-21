"""
Unit tests for ConversationalAgent.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from agents.conversational_agent import ConversationalAgent


class TestConversationalAgent:
    """Test cases for ConversationalAgent."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = ConversationalAgent()
    
    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        assert self.agent.agent_id is not None
        assert self.agent.name == "ConversationalAgent"
        assert self.agent.conversation_history == []
        assert self.agent.sentiment_context == {}
        assert self.agent.dialogue_state == "neutral"
    
    def test_rate_limit_check(self):
        """Test rate limiting functionality."""
        # Should allow calls when under limit
        assert self.agent._check_rate_limit() is True
        
        # Should block when at limit
        self.agent.api_calls_this_minute = 8
        assert self.agent._check_rate_limit() is False
    
    def test_fallback_sentiment_analysis(self):
        """Test fallback sentiment analysis."""
        # Test positive sentiment
        result = self.agent._fallback_sentiment_analysis("I love this!")
        assert result == "positive"
        
        # Test negative sentiment
        result = self.agent._fallback_sentiment_analysis("This is terrible!")
        assert result == "negative"
        
        # Test neutral sentiment
        result = self.agent._fallback_sentiment_analysis("The weather is okay.")
        assert result == "neutral"
    
    def test_fallback_intent_analysis(self):
        """Test fallback intent analysis."""
        # Test greeting
        result = self.agent._fallback_intent_analysis("Hello there!")
        assert result == "greeting"
        
        # Test question
        result = self.agent._fallback_intent_analysis("What is the weather?")
        assert result == "question"
        
        # Test goodbye
        result = self.agent._fallback_intent_analysis("Goodbye!")
        assert result == "goodbye"
    
    def test_fallback_response_generation(self):
        """Test fallback response generation."""
        # Test greeting response
        response = self.agent._generate_fallback_response("Hello!", "positive")
        assert "Hello!" in response
        assert "multi-agent" in response.lower()
        
        # Test question response
        response = self.agent._generate_fallback_response("What can you do?", "neutral")
        assert "multi-agent" in response.lower() or "help" in response.lower()
    
    @pytest.mark.asyncio
    async def test_openai_sentiment_analysis(self):
        """Test OpenAI sentiment analysis fallback."""
        # Mock OpenAI client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "positive"
        
        # Create synchronous mock (asyncio.to_thread expects sync function)
        def mock_create(*args, **kwargs):
            return mock_response
        
        mock_client.chat.completions.create = mock_create
        self.agent.openai_client = mock_client
        
        result = await self.agent._openai_sentiment_analysis("I love this!")
        assert result == "positive"
    
    @pytest.mark.asyncio
    async def test_openai_sentiment_analysis_fallback(self):
        """Test OpenAI sentiment analysis falls back to pattern matching."""
        self.agent.openai_client = None
        
        result = await self.agent._openai_sentiment_analysis("I love this!")
        assert result == "positive"
    
    @pytest.mark.asyncio
    async def test_openai_intent_analysis(self):
        """Test OpenAI intent analysis fallback."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "greeting"
        # Create synchronous mock (asyncio.to_thread expects sync function)
        def mock_create(*args, **kwargs):
            return mock_response
        
        mock_client.chat.completions.create = mock_create
        
        self.agent.openai_client = mock_client
        
        result = await self.agent._openai_intent_analysis("Hello!")
        assert result == "greeting"
    
    @pytest.mark.asyncio
    async def test_openai_response_generation(self):
        """Test OpenAI response generation fallback."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hello! How can I help you?"
        # Create synchronous mock (asyncio.to_thread expects sync function)
        def mock_create(*args, **kwargs):
            return mock_response
        
        mock_client.chat.completions.create = mock_create
        
        self.agent.openai_client = mock_client
        
        result = await self.agent._openai_generate_response("Hello!", {}, "positive")
        assert "Hello!" in result
    
    @pytest.mark.asyncio
    async def test_google_ai_sentiment_analysis_success(self):
        """Test successful Google AI sentiment analysis."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "positive"
        
        # Create synchronous mock (asyncio.to_thread expects sync function)
        def mock_generate_content(*args, **kwargs):
            return mock_response
        
        mock_client.models.generate_content = mock_generate_content
        self.agent.google_client = mock_client
        
        result = await self.agent._analyze_sentiment("I love this!")
        assert result == "positive"
    
    @pytest.mark.asyncio
    async def test_google_ai_sentiment_analysis_retry(self):
        """Test Google AI sentiment analysis with retry on 503 error."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "positive"
        
        # First call fails with 503, second succeeds
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("503 Service Unavailable")
            return mock_response
        
        mock_client.models.generate_content = side_effect
        
        self.agent.google_client = mock_client
        
        result = await self.agent._analyze_sentiment("I love this!")
        assert result == "positive"
    
    @pytest.mark.asyncio
    async def test_google_ai_sentiment_analysis_fallback(self):
        """Test Google AI sentiment analysis falls back to OpenAI on persistent failure."""
        mock_client = Mock()
        def mock_generate_content(*args, **kwargs):
            raise Exception("503 Service Unavailable")
        
        mock_client.models.generate_content = mock_generate_content
        
        self.agent.google_client = mock_client
        self.agent.openai_client = None  # Will use pattern matching
        
        result = await self.agent._analyze_sentiment("I love this!")
        assert result == "positive"
    
    def test_get_recent_history(self):
        """Test getting recent conversation history."""
        # Add some conversation history
        self.agent.conversation_history = [
            {"user_message": "Hello", "agent_response": "Hi there!", "sentiment": "positive"},
            {"user_message": "How are you?", "agent_response": "I'm doing well!", "sentiment": "positive"},
            {"user_message": "What's the weather?", "agent_response": "I can't check the weather.", "sentiment": "neutral"}
        ]
        
        recent = self.agent._get_recent_history(3)
        assert len(recent) == 3
        assert "What's the weather?" in recent[-1]
    
    def test_update_conversation_history(self):
        """Test updating conversation history."""
        self.agent._update_conversation_history("user1", "session1", "Hello", "Hi there!", "positive")
        
        assert len(self.agent.conversation_history) == 1
        assert self.agent.conversation_history[0]["user_message"] == "Hello"
        assert self.agent.conversation_history[0]["agent_response"] == "Hi there!"
        assert self.agent.conversation_history[0]["sentiment"] == "positive"
