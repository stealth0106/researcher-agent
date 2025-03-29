from typing import Any, Dict, Optional
from pydantic import BaseModel
from .base_agent import BaseAgent, AgentResponse
from .company_research_agent import CompanyResearchAgent
from .prospect_research_agent import ProspectResearchAgent
from .synthesizer_agent import SynthesizerAgent

class ResearchRequest(BaseModel):
    """Model for research request data"""
    company_name: Optional[str] = None
    prospect_name: Optional[str] = None

class ResearcherAgent(BaseAgent):
    """Main agent responsible for orchestrating research tasks"""
    
    def __init__(self):
        super().__init__("Researcher Agent")
        self.company_agent = CompanyResearchAgent()
        self.prospect_agent = ProspectResearchAgent()
        self.synthesizer_agent = SynthesizerAgent()
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResponse:
        try:
            if not self.validate_input(input_data):
                return AgentResponse(
                    success=False,
                    data={},
                    error="Invalid input data"
                )
            
            research_request = ResearchRequest(**input_data)
            company_data = None
            prospect_data = None
            
            # Execute company research if company name is provided
            if research_request.company_name:
                company_response = await self.company_agent.execute({
                    "company_name": research_request.company_name
                })
                if company_response.success:
                    company_data = company_response.data
            
            # Execute prospect research if prospect name is provided
            if research_request.prospect_name:
                prospect_response = await self.prospect_agent.execute({
                    "prospect_name": research_request.prospect_name,
                    "company_name": research_request.company_name
                })
                if prospect_response.success:
                    prospect_data = prospect_response.data
            
            # Synthesize the results
            synthesis_response = await self.synthesizer_agent.execute({
                "company_data": company_data,
                "prospect_data": prospect_data
            })
            
            return synthesis_response
            
        except Exception as e:
            return self.handle_error(e)
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return isinstance(input_data, dict) and (
            "company_name" in input_data or 
            "prospect_name" in input_data
        ) 