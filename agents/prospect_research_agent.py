from typing import Any, Dict, Optional
from .base_agent import BaseAgent, AgentResponse
from pydantic import BaseModel
from utils.web_scraper import WebScraper

class ProspectData(BaseModel):
    """Model for prospect research data"""
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    experience: list = []
    education: list = []
    skills: list = []

class ProspectResearchAgent(BaseAgent):
    """Agent responsible for researching prospect information"""
    
    def __init__(self):
        super().__init__("Prospect Research Agent")
        self.scraper = WebScraper()
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResponse:
        try:
            if not self.validate_input(input_data):
                return AgentResponse(
                    success=False,
                    data={},
                    error="Invalid input data"
                )
            
            prospect_name = input_data.get("prospect_name")
            company_name = input_data.get("company_name")
            
            if not prospect_name:
                return AgentResponse(
                    success=False,
                    data={},
                    error="Prospect name is required"
                )
            
            # Initialize web scraper
            self.scraper.initialize()
            
            # Scrape prospect information
            prospect_data = self.scraper.scrape_prospect_info(prospect_name, company_name)
            
            # Close web scraper
            self.scraper.close()
            
            return AgentResponse(
                success=True,
                data=prospect_data
            )
            
        except Exception as e:
            if self.scraper:
                self.scraper.close()
            return self.handle_error(e)
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return isinstance(input_data, dict) and "prospect_name" in input_data 