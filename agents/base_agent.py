from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel

class AgentResponse(BaseModel):
    """Base response model for all agents"""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None

class BaseAgent(ABC):
    """Base class for all agents in the system"""
    
    def __init__(self, name: str):
        self.name = name
        
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Execute the agent's main task"""
        pass
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data before processing"""
        return True
    
    def handle_error(self, error: Exception) -> AgentResponse:
        """Handle errors in a standardized way"""
        return AgentResponse(
            success=False,
            data={},
            error=str(error)
        ) 