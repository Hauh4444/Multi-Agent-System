"""
Matching Agent - Processes user inputs to match them with appropriate responses or actions.
"""

from datetime import datetime
from typing import Dict, Any, List
import re
from .base_agent import BaseAgent

class MatchingAgent(BaseAgent):
    """
    Specialized agent for matching user inputs with appropriate responses or actions.
    Handles intent classification, entity extraction, and action routing.
    """
    
    def __init__(self, agent_id: str = None):
        super().__init__(agent_id, "MatchingAgent")
        
        # Predefined patterns and rules
        self.intent_patterns = {
            "greeting": [
                r"\b(hello|hi|hey|good morning|good afternoon|good evening)\b",
                r"\b(how are you|how's it going|what's up)\b"
            ],
            "question": [
                r"\b(what|how|why|when|where|who|which)\b",
                r"\b(can you|could you|would you)\b",
                r"\?$"
            ],
            "request": [
                r"\b(please|can you|could you|would you|help me)\b",
                r"\b(show me|tell me|explain|describe)\b"
            ],
            "complaint": [
                r"\b(problem|issue|error|bug|broken|not working)\b",
                r"\b(complain|frustrated|annoyed|upset)\b"
            ],
            "compliment": [
                r"\b(thank you|thanks|great|awesome|excellent|amazing)\b",
                r"\b(good job|well done|perfect|love it)\b"
            ],
            "goodbye": [
                r"\b(bye|goodbye|see you|farewell|take care)\b",
                r"\b(exit|quit|stop|end)\b"
            ]
        }
        
        # Entity extraction patterns
        self.entity_patterns = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            "url": r"https?://[^\s]+",
            "number": r"\b\d+\b",
            "date": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            "time": r"\b\d{1,2}:\d{2}\s*(am|pm)?\b"
        }
        
        # Action routing rules
        self.action_routes = {
            "greeting": "conversational",
            "question": "conversational",
            "request": "conversational",
            "complaint": "conversational",
            "compliment": "conversational",
            "goodbye": "conversational"
        }
        
        # Confidence thresholds
        self.confidence_thresholds = {
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4
        }
    
    async def process(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process input to match with appropriate actions and extract entities.
        
        Args:
            input_data: Contains 'message', 'user_id', 'session_id'
            context: Additional context from other agents
            
        Returns:
            Dict with matched intent, entities, confidence, and routing information
        """
        start_time = datetime.now()
        self.set_status("processing")
        
        try:
            message = input_data.get('message', '')
            
            # Extract entities from the message
            entities = await self._extract_entities(message)
            
            # Classify intent
            intent_result = await self._classify_intent(message, entities)
            
            # Determine action routing
            action_route = await self._determine_action_route(intent_result, context)
            
            # Calculate confidence score
            confidence = await self._calculate_confidence(intent_result, entities, context)
            
            # Generate matching suggestions
            suggestions = await self._generate_suggestions(intent_result, entities, context)
            
            response_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(response_time, True)
            self.set_status("idle")
            
            return {
                "intent": intent_result,
                "entities": entities,
                "confidence": confidence,
                "action_route": action_route,
                "suggestions": suggestions,
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error in matching processing: {e}")
            response_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(response_time, False)
            self.set_status("error")
            
            return {
                "intent": {"primary": "error", "confidence": 0.0},
                "entities": [],
                "confidence": 0.0,
                "action_route": "error",
                "suggestions": [],
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def _extract_entities(self, message: str) -> List[Dict[str, Any]]:
        """Extract entities from the input message."""
        entities = []
        
        try:
            for entity_type, pattern in self.entity_patterns.items():
                matches = re.finditer(pattern, message, re.IGNORECASE)
                for match in matches:
                    entities.append({
                        "type": entity_type,
                        "value": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.9  # High confidence for regex matches
                    })
            
            # Extract custom entities based on context
            custom_entities = await self._extract_custom_entities(message)
            entities.extend(custom_entities)
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Error extracting entities: {e}")
            return []
    
    async def _extract_custom_entities(self, message: str) -> List[Dict[str, Any]]:
        """Extract custom entities based on context and patterns."""
        custom_entities = []
        
        try:
            # Extract names (simple heuristic - capitalized words)
            name_pattern = r"\b[A-Z][a-z]+\b"
            name_matches = re.finditer(name_pattern, message)
            for match in name_matches:
                # Skip common words that aren't names
                common_words = {"The", "This", "That", "There", "Then", "They", "These", "Those"}
                if match.group() not in common_words:
                    custom_entities.append({
                        "type": "name",
                        "value": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.6
                    })
            
            # Extract topics (nouns and noun phrases)
            topic_pattern = r"\b\w+(?:\s+\w+)*\b"
            topic_matches = re.finditer(topic_pattern, message)
            for match in topic_matches:
                if len(match.group().split()) <= 3:  # Limit to 3 words max
                    custom_entities.append({
                        "type": "topic",
                        "value": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.5
                    })
            
            return custom_entities
            
        except Exception as e:
            self.logger.error(f"Error extracting custom entities: {e}")
            return []
    
    async def _classify_intent(self, message: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Classify the intent of the input message."""
        try:
            intent_scores = {}
            message_lower = message.lower()
            
            # Score each intent based on pattern matching
            for intent, patterns in self.intent_patterns.items():
                score = 0
                for pattern in patterns:
                    matches = re.findall(pattern, message_lower, re.IGNORECASE)
                    score += len(matches) * 0.3  # Weight for pattern matches
                
                # Boost score based on entities
                if entities:
                    entity_boost = min(len(entities) * 0.1, 0.3)
                    score += entity_boost
                
                # Boost score for question marks
                if "?" in message:
                    score += 0.2
                
                intent_scores[intent] = min(score, 1.0)  # Cap at 1.0
            
            # Find the highest scoring intent
            if intent_scores:
                primary_intent = max(intent_scores, key=intent_scores.get)
                confidence = intent_scores[primary_intent]
            else:
                primary_intent = "general"
                confidence = 0.5
            
            # Determine secondary intents
            secondary_intents = []
            for intent, score in intent_scores.items():
                if intent != primary_intent and score > 0.3:
                    secondary_intents.append({"intent": intent, "confidence": score})
            
            return {
                "primary": primary_intent,
                "confidence": confidence,
                "secondary": secondary_intents,
                "all_scores": intent_scores
            }
            
        except Exception as e:
            self.logger.error(f"Error classifying intent: {e}")
            return {"primary": "general", "confidence": 0.5, "secondary": [], "all_scores": {}}
    
    async def _determine_action_route(self, intent_result: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Determine which agent should handle the action."""
        try:
            primary_intent = intent_result.get("primary", "general")
            
            # Get base route from intent
            base_route = self.action_routes.get(primary_intent, "conversational")
            
            # Modify route based on context
            if context:
                # Check if there's a specific agent preference
                if "preferred_agent" in context:
                    return context["preferred_agent"]
                
                # Check if there's a specific task type
                if "task_type" in context:
                    task_type = context["task_type"]
                    if task_type == "memory_operation":
                        return "memory"
                    elif task_type == "matching_operation":
                        return "matching"
            
            return base_route
            
        except Exception as e:
            self.logger.error(f"Error determining action route: {e}")
            return "conversational"
    
    async def _calculate_confidence(self, intent_result: Dict[str, Any], entities: List[Dict[str, Any]], context: Dict[str, Any]) -> float:
        """Calculate overall confidence score for the matching."""
        try:
            base_confidence = intent_result.get("confidence", 0.5)
            
            # Boost confidence based on entities
            entity_boost = min(len(entities) * 0.05, 0.2)
            
            # Boost confidence based on context
            context_boost = 0.0
            if context:
                if "previous_intent" in context and context["previous_intent"] == intent_result.get("primary"):
                    context_boost += 0.1
                if "user_preferences" in context:
                    context_boost += 0.05
            
            total_confidence = min(base_confidence + entity_boost + context_boost, 1.0)
            
            return round(total_confidence, 3)
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {e}")
            return 0.5
    
    async def _generate_suggestions(self, intent_result: Dict[str, Any], entities: List[Dict[str, Any]], context: Dict[str, Any]) -> List[str]:
        """Generate helpful suggestions based on the matching results."""
        suggestions = []
        
        try:
            primary_intent = intent_result.get("primary", "general")
            confidence = intent_result.get("confidence", 0.5)
            
            # Generate intent-based suggestions
            if primary_intent == "question":
                suggestions.extend([
                    "What is the system architecture?",
                    "How do the agents work together?",
                    "What can you help me with?"
                ])
            elif primary_intent == "request":
                suggestions.extend([
                    "Show me the system status",
                    "Explain the multi-agent system",
                    "Help me understand the agents"
                ])
            elif primary_intent == "complaint":
                suggestions.extend([
                    "The system is not working",
                    "I'm having trouble with the interface",
                    "Something went wrong"
                ])
            elif primary_intent == "greeting":
                suggestions.extend([
                    "Hello, how are you?",
                    "Good morning",
                    "Hi there"
                ])
            else:
                # General suggestions for any intent
                suggestions.extend([
                    "What can you do?",
                    "Show me the system status",
                    "How does this work?"
                ])
            
            # Generate entity-based suggestions
            if entities:
                entity_types = [e["type"] for e in entities]
                if "email" in entity_types:
                    suggestions.append("Send an email to support")
                if "phone" in entity_types:
                    suggestions.append("Call the support number")
                if "url" in entity_types:
                    suggestions.append("Check this website")
            
            # Generate context-based suggestions
            if context:
                if "previous_intent" in context:
                    prev_intent = context["previous_intent"]
                    if prev_intent == "question" and primary_intent == "question":
                        suggestions.append("Tell me more about that")
                    elif prev_intent == "request" and primary_intent == "request":
                        suggestions.append("Can you help me with something else?")
            
            # Limit suggestions to top 3
            return suggestions[:3]
            
        except Exception as e:
            self.logger.error(f"Error generating suggestions: {e}")
            return []
    
    def get_matching_statistics(self) -> Dict[str, Any]:
        """Get statistics about matching performance."""
        return {
            "total_patterns": sum(len(patterns) for patterns in self.intent_patterns.values()),
            "total_entity_types": len(self.entity_patterns),
            "action_routes": len(self.action_routes),
            "confidence_thresholds": self.confidence_thresholds,
            "agent_metrics": self.metrics
        }
