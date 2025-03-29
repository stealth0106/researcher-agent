from typing import Any, Dict, Optional
from .base_agent import BaseAgent, AgentResponse
from pydantic import BaseModel
from utils.web_scraper import WebScraper

class CompanyData(BaseModel):
    """Model for company research data"""
    name: str
    revenue: Optional[str] = None
    employee_count: Optional[str] = None
    ceo: Optional[str] = None
    industry: Optional[str] = None
    founded_year: Optional[str] = None
    headquarters: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    executive_summary: Optional[Dict[str, Any]] = None

class CompanyResearchAgent(BaseAgent):
    """Agent responsible for researching company information"""
    
    def __init__(self):
        super().__init__("Company Research Agent")
        self.scraper = WebScraper()
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResponse:
        try:
            if not self.validate_input(input_data):
                return AgentResponse(
                    success=False,
                    data={},
                    error="Invalid input data"
                )
            
            company_name = input_data.get("company_name")
            if not company_name:
                return AgentResponse(
                    success=False,
                    data={},
                    error="Company name is required"
                )
            
            # Initialize web scraper
            self.scraper.initialize()
            
            # Scrape company information
            company_data = self.scraper.scrape_company_info(company_name)
            
            # Close web scraper
            self.scraper.close()
            
            return AgentResponse(
                success=True,
                data=company_data
            )
            
        except Exception as e:
            if self.scraper:
                self.scraper.close()
            return self.handle_error(e)
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return isinstance(input_data, dict) and "company_name" in input_data 