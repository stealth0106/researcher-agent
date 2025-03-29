from typing import Any, Dict, Optional
from .base_agent import BaseAgent, AgentResponse
from pydantic import BaseModel

class SynthesizedData(BaseModel):
    """Model for synthesized research data"""
    company_data: Optional[Dict[str, Any]] = None
    prospect_data: Optional[Dict[str, Any]] = None
    prospect_summary: Optional[str] = None
    insights: Optional[list] = None

class SynthesizerAgent(BaseAgent):
    """Agent responsible for synthesizing research data and creating summaries"""
    
    def __init__(self):
        super().__init__("Synthesizer Agent")
        
    async def execute(self, input_data: Dict[str, Any]) -> AgentResponse:
        try:
            if not self.validate_input(input_data):
                return AgentResponse(
                    success=False,
                    data={},
                    error="Invalid input data"
                )
            
            company_data = input_data.get("company_data")
            prospect_data = input_data.get("prospect_data")
            
            if not company_data and not prospect_data:
                return AgentResponse(
                    success=False,
                    data={},
                    error="At least one of company_data or prospect_data is required"
                )
            
            # Generate summaries and insights
            synthesized_data = SynthesizedData(
                company_data=company_data,
                prospect_data=prospect_data,
                prospect_summary=self._generate_prospect_summary(prospect_data) if prospect_data else None,
                insights=self._generate_insights(company_data, prospect_data)
            )
            
            return AgentResponse(
                success=True,
                data=synthesized_data.dict()
            )
            
        except Exception as e:
            return self.handle_error(e)
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return isinstance(input_data, dict) and (
            "company_data" in input_data or 
            "prospect_data" in input_data
        )
    
    def _generate_company_summary(self, company_data: Dict[str, Any]) -> str:
        """Generate a natural language summary of company data"""
        if not company_data:
            return ""
        
        summary_parts = []
        
        # Basic company information
        if company_data.get("name"):
            summary_parts.append(f"{company_data['name']} is")
        
        if company_data.get("industry"):
            summary_parts.append(f"in the {company_data['industry']} industry")
        
        if company_data.get("employee_count"):
            summary_parts.append(f"with approximately {company_data['employee_count']} employees")
        
        if company_data.get("revenue"):
            summary_parts.append(f"and revenue of {company_data['revenue']}")
        
        # Executive Summary
        if company_data.get("executive_summary"):
            exec_summary = company_data["executive_summary"]
            
            # Overview
            if exec_summary.get("overview"):
                summary_parts.append(f"\nOverview: {exec_summary['overview']}")
            
            # Market Position
            if exec_summary.get("market_position"):
                summary_parts.append(f"\nMarket Position: {exec_summary['market_position']}")
            
            # Key Products/Services
            if exec_summary.get("key_products_services"):
                products = ", ".join(exec_summary["key_products_services"])
                summary_parts.append(f"\nKey Products/Services: {products}")
            
            # Recent Developments
            if exec_summary.get("recent_developments"):
                developments = "\n- ".join(exec_summary["recent_developments"])
                summary_parts.append(f"\nRecent Developments:\n- {developments}")
            
            # Sales Insights
            if exec_summary.get("sales_insights"):
                sales = exec_summary["sales_insights"]
                
                # Pain Points
                if sales.get("pain_points"):
                    pains = "\n- ".join(sales["pain_points"])
                    summary_parts.append(f"\nPotential Pain Points:\n- {pains}")
                
                # Opportunities
                if sales.get("opportunities"):
                    opportunities = "\n- ".join(sales["opportunities"])
                    summary_parts.append(f"\nSales Opportunities:\n- {opportunities}")
                
                # Decision Makers
                if sales.get("decision_makers"):
                    decision_makers = "\n- ".join(sales["decision_makers"])
                    summary_parts.append(f"\nKey Decision Makers:\n- {decision_makers}")
                
                # Budget Indicators
                if sales.get("budget_indicators"):
                    summary_parts.append(f"\nBudget Indicators: {sales['budget_indicators']}")
                
                # Technology Stack
                if sales.get("technology_stack"):
                    tech_stack = ", ".join(sales["technology_stack"])
                    summary_parts.append(f"\nTechnology Stack: {tech_stack}")
                
                # Growth Indicators
                if sales.get("growth_indicators"):
                    summary_parts.append(f"\nGrowth Indicators: {sales['growth_indicators']}")
                
                # Recommended Approach
                if sales.get("recommended_approach"):
                    summary_parts.append(f"\nRecommended Sales Approach: {sales['recommended_approach']}")
        
        return "\n".join(summary_parts) if summary_parts else "No company data available"
    
    def _generate_prospect_summary(self, prospect_data: Dict[str, Any]) -> str:
        """Generate a natural language summary of prospect data"""
        if not prospect_data:
            return ""
        
        summary_parts = []
        if prospect_data.get("name"):
            summary_parts.append(f"{prospect_data['name']} is")
        
        if prospect_data.get("title"):
            summary_parts.append(f"a {prospect_data['title']}")
        
        if prospect_data.get("company"):
            summary_parts.append(f"at {prospect_data['company']}")
        
        if prospect_data.get("location"):
            summary_parts.append(f"in {prospect_data['location']}")
        
        return " ".join(summary_parts) if summary_parts else "No prospect data available"
    
    def _generate_insights(self, company_data: Dict[str, Any], prospect_data: Dict[str, Any]) -> list:
        """Generate insights based on the available data"""
        insights = []
        
        if company_data:
            if company_data.get("revenue") and company_data.get("employee_count"):
                insights.append(f"Company size and revenue indicate {company_data['name']} is a significant player in their industry")
        
        if prospect_data:
            if prospect_data.get("job_title") and prospect_data.get("department"):
                insights.append(f"{prospect_data['full_name']} holds a key position in {prospect_data['department']}")
        
        return insights 