"""
Base Agent class for the multi-agent system.
Provides common functionality for all specialized agents.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any
import uuid

class BaseAgent(ABC):
    """
    Abstract base class for all agents in the multi-agent system.
    Provides common functionality and interface for agent communication.
    """
    
    def __init__(self, agent_id: str = None, name: str = "BaseAgent"):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.name = name
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{self.agent_id}")
        self.status = "idle"  # idle, processing, error
        self.last_activity = datetime.now()
        self.metrics = {
            "requests_processed": 0,
            "average_response_time": 0.0,
            "error_count": 0
        }
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process input data and return response.
        Must be implemented by all concrete agents.
        
        Args:
            input_data: Input data to process
            context: Additional context information
            
        Returns:
            Dict containing the agent's response
        """
        pass
    
    def update_metrics(self, response_time: float, success: bool = True):
        """Update agent performance metrics."""
        self.metrics["requests_processed"] += 1
        if success:
            # Update average response time
            total_time = self.metrics["average_response_time"] * (self.metrics["requests_processed"] - 1)
            self.metrics["average_response_time"] = (total_time + response_time) / self.metrics["requests_processed"]
        else:
            self.metrics["error_count"] += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status and metrics."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status,
            "last_activity": self.last_activity.isoformat(),
            "metrics": self.metrics
        }
    
    def set_status(self, status: str):
        """Set agent status."""
        self.status = status
        self.last_activity = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary representation."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status,
            "last_activity": self.last_activity.isoformat(),
            "metrics": self.metrics
        }
