"""
Conversational Agent - Handles natural language interactions and dialogue management.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List
import openai
from .base_agent import BaseAgent
import time

class ConversationalAgent(BaseAgent):
    """
    Specialized agent for handling conversational interactions.
    Manages dialogue context, sentiment analysis, and response generation.
    """
    
    def __init__(self, agent_id: str = None):
        super().__init__(agent_id, "ConversationalAgent")
        self.conversation_history = []
        self.sentiment_context = {}
        self.dialogue_state = "neutral"
        
        self.google_client = None
        self.openai_client = None
        self.api_calls_this_minute = 0
        self.last_reset_time = time.time()
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within the free tier rate limits (10 calls per minute)."""
        current_time = time.time()
        
        if current_time - self.last_reset_time >= 60:
            self.api_calls_this_minute = 0
            self.last_reset_time = current_time
        
        if self.api_calls_this_minute >= 8:
            return False
        
        self.api_calls_this_minute += 1
        return True
    
    def _initialize_openai(self, api_key: str):
        """Initialize OpenAI client."""
        try:
            if api_key:
                self.openai_client = openai.OpenAI(
                    api_key=api_key,
                    timeout=30.0
                )
                self.logger.info("OpenAI client initialized successfully")
            else:
                self.logger.warning("OpenAI API key not provided")
                self.openai_client = None
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            self.openai_client = None
    
    async def process(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process conversational input and generate appropriate response.
        
        Args:
            input_data: Contains 'message', 'user_id', 'session_id'
            context: Additional context from other agents
            
        Returns:
            Dict with response, sentiment, and dialogue state
        """
        start_time = datetime.now()
        self.set_status("processing")
        
        try:
            message = input_data.get('message', '')
            user_id = input_data.get('user_id', 'unknown')
            session_id = input_data.get('session_id', 'unknown')
            
            
            # Always use fallback if AI services are not available or failed to initialize
            if not self.google_client and not self.openai_client:
                self.logger.info("Using pattern matching fallback - AI services not available")
                sentiment = self._fallback_sentiment_analysis(message)
                dialogue_intent = self._fallback_intent_analysis(message)
                response = self._generate_fallback_response(message)
            else:
                try:
                    sentiment = await asyncio.wait_for(self._analyze_sentiment(message), timeout=5.0)
                    dialogue_intent = await asyncio.wait_for(self._analyze_intent(message), timeout=5.0)
                    response = await asyncio.wait_for(self._generate_response(message, context, sentiment), timeout=10.0)
                except (asyncio.TimeoutError, Exception) as e:
                    self.logger.warning(f"AI services failed, using pattern matching fallback: {e}")
                    sentiment = self._fallback_sentiment_analysis(message)
                    dialogue_intent = self._fallback_intent_analysis(message)
                    response = self._generate_fallback_response(message)
            
            self._update_conversation_history(user_id, session_id, message, response, sentiment)
            self._update_dialogue_state(sentiment, dialogue_intent)
            
            response_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(response_time, True)
            self.set_status("idle")
            
            return {
                "response": response,
                "sentiment": sentiment,
                "dialogue_state": self.dialogue_state,
                "intent": dialogue_intent,
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error in conversational processing: {e}")
            response_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(response_time, False)
            self.set_status("error")
            
            return {
                "response": "I apologize, but I encountered an error processing your message.",
                "sentiment": "neutral",
                "dialogue_state": "error",
                "intent": "error",
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def _analyze_sentiment(self, message: str) -> str | None | Any:
        """Analyze sentiment of the input message."""
        try:
            if not self.google_client or not self._check_rate_limit():
                return await self._openai_sentiment_analysis(message)
            
            prompt = f"""
            Analyze the sentiment of this message and respond with only one word: positive, negative, or neutral.
            
            Message: "{message}"
            """
            
            for attempt in range(3):
                try:
                    response = await asyncio.to_thread(
                        self.google_client.models.generate_content,
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                    sentiment = response.text.strip().lower()
                    
                    if sentiment in ['positive', 'negative', 'neutral']:
                        return sentiment
                    else:
                        return "neutral"
                except Exception as e:
                    if "503" in str(e) or "overloaded" in str(e).lower() or "429" in str(e):
                        if attempt < 2:
                            await asyncio.sleep(1 + attempt)
                            continue
                        else:
                            return await self._openai_sentiment_analysis(message)
                    raise e
                
        except Exception as e:
            self.logger.warning(f"Google AI sentiment analysis failed, using fallback: {e}")
            return await self._openai_sentiment_analysis(message)
    
    async def _openai_sentiment_analysis(self, message: str) -> str:
        """Analyze sentiment using OpenAI as fallback."""
        try:
            if not self.openai_client:
                return self._fallback_sentiment_analysis(message)
            
            prompt = f"""
            Analyze the sentiment of this message and respond with only one word: positive, negative, or neutral.
            
            Message: "{message}"
            """
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1
            )
            
            sentiment = response.choices[0].message.content.strip().lower()
            if sentiment in ['positive', 'negative', 'neutral']:
                return sentiment
            else:
                return "neutral"
                
        except Exception as e:
            self.logger.warning(f"OpenAI sentiment analysis failed, using pattern matching: {e}")
            return self._fallback_sentiment_analysis(message)
    
    def _fallback_sentiment_analysis(self, message: str) -> str:
        """Fallback sentiment analysis when Google AI is unavailable."""
        message_lower = message.lower()
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'love', 'like', 'happy', 'pleased', 'awesome', 'brilliant', 'perfect']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'dislike', 'angry', 'frustrated', 'sad', 'disappointed', 'horrible', 'worst', 'annoying']
        
        if any(word in message_lower for word in positive_words):
            return "positive"
        elif any(word in message_lower for word in negative_words):
            return "negative"
        else:
            return "neutral"
    
    async def _analyze_intent(self, message: str) -> str | None | Any:
        """Analyze the intent of the input message."""
        try:
            if not self.google_client or not self._check_rate_limit():
                return await self._openai_intent_analysis(message)
            
            prompt = f"""
            Analyze the intent of this message and respond with only one word from: greeting, question, request, complaint, compliment, goodbye, or general.
            
            Message: "{message}"
            """
            
            for attempt in range(3):
                try:
                    response = await asyncio.to_thread(
                        self.google_client.models.generate_content,
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                    intent = response.text.strip().lower()
                    
                    valid_intents = ['greeting', 'question', 'request', 'complaint', 'compliment', 'goodbye', 'general']
                    if intent in valid_intents:
                        return intent
                    else:
                        return "general"
                except Exception as e:
                    if "503" in str(e) or "overloaded" in str(e).lower() or "429" in str(e):
                        if attempt < 2:
                            await asyncio.sleep(1 + attempt)
                            continue
                        else:
                            return await self._openai_intent_analysis(message)
                    raise e
                
        except Exception as e:
            self.logger.warning(f"Google AI intent analysis failed, using fallback: {e}")
            return await self._openai_intent_analysis(message)
    
    async def _openai_intent_analysis(self, message: str) -> str:
        """Analyze intent using OpenAI as fallback."""
        try:
            if not self.openai_client:
                return self._fallback_intent_analysis(message)
            
            prompt = f"""
            Analyze the intent of this message and respond with only one word from: greeting, question, request, complaint, compliment, goodbye, or general.
            
            Message: "{message}"
            """
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0.1
            )
            
            intent = response.choices[0].message.content.strip().lower()
            valid_intents = ['greeting', 'question', 'request', 'complaint', 'compliment', 'goodbye', 'general']
            if intent in valid_intents:
                return intent
            else:
                return "general"
                
        except Exception as e:
            self.logger.warning(f"OpenAI intent analysis failed, using pattern matching: {e}")
            return self._fallback_intent_analysis(message)
    
    def _fallback_intent_analysis(self, message: str) -> str:
        """Fallback intent analysis when Google AI is unavailable."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'greetings']):
            return "greeting"
        elif '?' in message or any(word in message_lower for word in ['what', 'how', 'why', 'when', 'where', 'who', 'explain', 'describe']):
            return "question"
        elif any(word in message_lower for word in ['please', 'can you', 'could you', 'help me', 'show me', 'tell me', 'assist', 'support']):
            return "request"
        elif any(word in message_lower for word in ['problem', 'issue', 'error', 'bug', 'broken', 'complain', 'trouble', 'difficulty']):
            return "complaint"
        elif any(word in message_lower for word in ['thank you', 'thanks', 'great', 'awesome', 'excellent', 'good job', 'appreciate']):
            return "compliment"
        elif any(word in message_lower for word in ['bye', 'goodbye', 'see you', 'farewell', 'later', 'exit']):
            return "goodbye"
        else:
            return "general"
    
    async def _generate_response(self, message: str, context: Dict[str, Any], sentiment: str) -> str | None | Any:
        """Generate contextual response using Google AI."""
        try:
            if not self.google_client or not self._check_rate_limit():
                return await self._openai_generate_response(message, context, sentiment)
            
            context_str = ""
            if context:
                context_str = f"\nContext from other agents: {json.dumps(context, indent=2)}"
            
            recent_history = self._get_recent_history(5)
            history_str = ""
            if recent_history:
                history_str = "\nRecent conversation:\n" + "\n".join(recent_history)
            
            prompt = f"""
            You are a helpful AI assistant in a multi-agent system. Respond naturally and helpfully to the user's message.
            
            User message: "{message}"
            Sentiment: {sentiment}
            {context_str}
            {history_str}
            
            Provide a helpful, contextual response. Keep it concise but informative.
            """
            
            for attempt in range(3):
                try:
                    response = await asyncio.to_thread(
                        self.google_client.models.generate_content,
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                    return response.text.strip()
                except Exception as e:
                    if "503" in str(e) or "overloaded" in str(e).lower() or "429" in str(e):
                        if attempt < 2:
                            await asyncio.sleep(1 + attempt)
                            continue
                        else:
                            return await self._openai_generate_response(message, context, sentiment)
                    raise e
            
        except Exception as e:
            self.logger.warning(f"Google AI response generation failed, using fallback: {e}")
            return await self._openai_generate_response(message, context, sentiment)
    
    async def _openai_generate_response(self, message: str, context: Dict[str, Any], sentiment: str) -> str:
        """Generate response using OpenAI as fallback."""
        try:
            if not self.openai_client:
                return self._generate_fallback_response(message)
            
            context_str = ""
            if context:
                context_str = f"\nContext from other agents: {json.dumps(context, indent=2)}"
            
            recent_history = self._get_recent_history(5)
            history_str = ""
            if recent_history:
                history_str = "\nRecent conversation:\n" + "\n".join(recent_history)
            
            prompt = f"""
            You are a helpful AI assistant in a multi-agent system. Respond naturally and helpfully to the user's message.
            
            User message: "{message}"
            Sentiment: {sentiment}
            {context_str}
            {history_str}
            
            Provide a helpful, contextual response. Keep it concise but informative.
            """
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
                
        except Exception as e:
            self.logger.warning(f"OpenAI response generation failed, using pattern matching: {e}")
            return self._generate_fallback_response(message)
    
    def _generate_fallback_response(self, message: str) -> str:
        """Generate fallback responses when Google AI is not available."""
        message_lower = message.lower()
        
        # Greeting responses
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
            return "Hello! I'm a multi-agent AI system with specialized agents for conversation, memory, and task matching. I'm currently running in limited mode due to high demand on AI services, but I can still help you. How can I assist you today?"
        
        # Question responses
        elif '?' in message or any(word in message_lower for word in ['what', 'how', 'why', 'when', 'where', 'who']):
            return "That's a great question! I'm a multi-agent system with specialized AI agents that work together. Currently, I'm running in limited mode without full AI capabilities. What would you like to know about?"
        
        # Help requests
        elif any(word in message_lower for word in ['help', 'assist', 'support']):
            return "I'm here to help! I'm a multi-agent system with Conversational, Memory, and Matching agents. While I'm running in limited mode, I can still demonstrate the system architecture and capabilities. What would you like to explore?"
        
        # System-related questions
        elif any(word in message_lower for word in ['system', 'architecture', 'agent', 'multi-agent']):
            return "I'm a sophisticated multi-agent system with three specialized agents: Conversational Agent (handles dialogue), Memory Agent (manages context), and Matching Agent (analyzes intent). The AI Orchestrator coordinates all agents. Would you like to know more about any specific component?"
        
        # Default response
        else:
            return f"I understand you said: '{message}'. I'm a multi-agent AI system currently running in limited mode. I can help explain the system architecture, demonstrate agent coordination, and show real-time monitoring capabilities. What would you like to explore?"
    
    def _update_conversation_history(self, user_id: str, session_id: str, message: str, response: str, sentiment: str):
        """Update conversation history with new interaction."""
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            "user_message": message,
            "agent_response": response,
            "sentiment": sentiment
        }
        
        self.conversation_history.append(interaction)
        
        # Keep only last 100 interactions to manage memory
        if len(self.conversation_history) > 100:
            self.conversation_history = self.conversation_history[-100:]
    
    def _get_recent_history(self, count: int = 5) -> List[str]:
        """Get recent conversation history for context."""
        recent = self.conversation_history[-count:]
        return [f"User: {item['user_message']}\nAssistant: {item['agent_response']}" for item in recent]
    
    def _update_dialogue_state(self, sentiment: str, intent: str):
        """Update dialogue state based on sentiment and intent."""
        if intent == "greeting":
            self.dialogue_state = "welcoming"
        elif intent == "goodbye":
            self.dialogue_state = "closing"
        elif sentiment == "negative" and intent == "complaint":
            self.dialogue_state = "problem_solving"
        elif sentiment == "positive":
            self.dialogue_state = "positive"
        elif intent == "question":
            self.dialogue_state = "answering"
        else:
            self.dialogue_state = "neutral"
    
    def get_conversation_summary(self, user_id: str = None) -> Dict[str, Any]:
        """Get conversation summary for a specific user or all users."""
        if user_id:
            user_conversations = [c for c in self.conversation_history if c.get('user_id') == user_id]
        else:
            user_conversations = self.conversation_history
        
        if not user_conversations:
            return {"summary": "No conversations found", "count": 0}
        
        sentiments = [c['sentiment'] for c in user_conversations]
        sentiment_distribution = {s: sentiments.count(s) for s in set(sentiments)}
        
        return {
            "total_interactions": len(user_conversations),
            "sentiment_distribution": sentiment_distribution,
            "recent_dialogue_state": self.dialogue_state,
            "last_interaction": user_conversations[-1] if user_conversations else None
        }
