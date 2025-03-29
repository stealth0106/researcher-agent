import asyncio
import json
import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from agents.researcher_agent import ResearcherAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Debug .env file location
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, '.env')
logger.info(f"Looking for .env file at: {env_path}")
logger.info(f".env file exists: {os.path.exists(env_path)}")

# Load environment variables
load_dotenv(env_path)

# Initialize Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
logger.info(f"Loaded GEMINI_API_KEY: {'Present' if GEMINI_API_KEY else 'Missing'}")
if GEMINI_API_KEY:
    logger.info(f"API Key length: {len(GEMINI_API_KEY)} characters")
    logger.info(f"API Key starts with: {GEMINI_API_KEY[:10]}...")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in .env file")

try:
    # Configure the API
    genai.configure(api_key=GEMINI_API_KEY)
    
    # List available models
    logger.info("Listing available models:")
    for m in genai.list_models():
        logger.info(f"Model: {m.name}")
        logger.info(f"Display name: {m.display_name}")
        logger.info(f"Description: {m.description}")
        logger.info("---")
    
    # Initialize the model with the correct name
    model = genai.GenerativeModel("models/gemini-1.5-pro")
    
    # Test the model with a simple generation
    response = model.generate_content("Hello, this is a test.")
    logger.info(f"Test response: {response.text}")
    logger.info("Gemini model initialized and tested successfully")
except Exception as e:
    logger.error(f"Failed to initialize Gemini model: {str(e)}")
    logger.error("Please check if your API key is valid and properly formatted")
    raise

async def parse_user_input(user_input: str) -> dict:
    """Parse user input using Gemini to identify research requirements"""
    try:
        prompt = f"""
        Analyze the following text and extract:
        1. Company name (if mentioned)
        2. Prospect name (if mentioned)
        3. Type of research needed (company research, prospect research, or both)
        
        Text: {user_input}
        
        You must respond with ONLY a JSON object in the following format, with no additional text or explanation:
        {{
            "company_name": "extracted company name or null",
            "prospect_name": "extracted prospect name or null",
            "research_type": "company", "prospect", or "both"
        }}
        """
        
        logger.info(f"Sending prompt to Gemini: {prompt}")
        response = model.generate_content(prompt)
        logger.info(f"Received response from Gemini: {response.text}")
        
        try:
            # Clean the response text to ensure it's valid JSON
            response_text = response.text.strip()
            # Remove any markdown code block markers if present
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            # Parse the JSON response
            parsed_data = json.loads(response_text)
            logger.info(f"Successfully parsed response: {parsed_data}")
            return parsed_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw response: {response.text}")
            # Try to extract information from the raw response
            try:
                # Look for company name
                company_name = None
                if "company" in response.text.lower():
                    company_name = response.text.split("company")[1].split()[0].strip()
                
                # Look for prospect name
                prospect_name = None
                if "prospect" in response.text.lower():
                    prospect_name = response.text.split("prospect")[1].split()[0].strip()
                
                # Determine research type
                research_type = "unknown"
                if company_name and prospect_name:
                    research_type = "both"
                elif company_name:
                    research_type = "company"
                elif prospect_name:
                    research_type = "prospect"
                
                return {
                    "company_name": company_name,
                    "prospect_name": prospect_name,
                    "research_type": research_type
                }
            except Exception as e:
                logger.error(f"Failed to extract information from raw response: {str(e)}")
                return {
                    "company_name": None,
                    "prospect_name": None,
                    "research_type": "unknown"
                }
    except Exception as e:
        logger.error(f"Error in parse_user_input: {str(e)}")
        return {
            "company_name": None,
            "prospect_name": None,
            "research_type": "unknown"
        }

async def main():
    try:
        researcher = ResearcherAgent()
        logger.info("ResearcherAgent initialized successfully")
        
        print("Welcome to the Research Agent System!")
        print("You can ask me to research companies or prospects in natural language.")
        print("Example queries:")
        print("- 'Tell me about Microsoft'")
        print("- 'Research John Smith from Apple'")
        print("- 'Find information about Google and their CEO Sundar Pichai'")
        print("Type 'exit' to quit.")
        
        while True:
            user_input = input("\nWhat would you like to research? ").strip()
            
            if user_input.lower() == 'exit':
                break
                
            print("\nAnalyzing your request...")
            parsed_data = await parse_user_input(user_input)
            
            if parsed_data["research_type"] == "unknown":
                print("I couldn't understand your request. Please try again with more specific information.")
                continue
                
            # Prepare the research request
            research_request = {}
            if parsed_data["company_name"]:
                research_request["company_name"] = parsed_data["company_name"]
            if parsed_data["prospect_name"]:
                research_request["prospect_name"] = parsed_data["prospect_name"]
                
            print("\nResearching...")
            response = await researcher.execute(research_request)
            
            if response.success:
                print("\nResearch Results:")
                data = response.data
                
                # Display company data if available
                if data.get("company_data"):
                    company_data = data["company_data"]
                    print("\nCompany Information:")
                    print("-" * 50)
                    
                    # Basic company info
                    if company_data.get("name"):
                        print(f"Name: {company_data['name']}")
                    if company_data.get("industry"):
                        print(f"Industry: {company_data['industry']}")
                    if company_data.get("headquarters"):
                        print(f"Headquarters: {company_data['headquarters']}")
                    if company_data.get("founded_year"):
                        print(f"Founded: {company_data['founded_year']}")
                    if company_data.get("size"):
                        print(f"Size: {company_data['size']}")
                    if company_data.get("ceo"):
                        print(f"CEO: {company_data['ceo']}")
                    if company_data.get("website"):
                        print(f"Website: {company_data['website']}")
                    
                    # Executive Summary
                    if company_data.get("executive_summary"):
                        print("\nExecutive Summary:")
                        print("-" * 50)
                        exec_summary = company_data["executive_summary"]
                        
                        if exec_summary.get("overview"):
                            print(f"\nOverview:\n{exec_summary['overview']}")
                        
                        if exec_summary.get("market_position"):
                            print(f"\nMarket Position:\n{exec_summary['market_position']}")
                        
                        if exec_summary.get("key_products_services"):
                            print("\nKey Products/Services:")
                            for product in exec_summary["key_products_services"]:
                                print(f"- {product}")
                        
                        if exec_summary.get("recent_developments"):
                            print("\nRecent Developments:")
                            for dev in exec_summary["recent_developments"]:
                                print(f"- {dev}")
                        
                        # Sales Insights
                        if exec_summary.get("sales_insights"):
                            print("\nSales Insights:")
                            print("-" * 50)
                            sales = exec_summary["sales_insights"]
                            
                            if sales.get("pain_points"):
                                print("\nPotential Pain Points:")
                                for point in sales["pain_points"]:
                                    print(f"- {point}")
                            
                            if sales.get("opportunities"):
                                print("\nSales Opportunities:")
                                for opp in sales["opportunities"]:
                                    print(f"- {opp}")
                            
                            if sales.get("decision_makers"):
                                print("\nKey Decision Makers:")
                                for dm in sales["decision_makers"]:
                                    print(f"- {dm}")
                            
                            if sales.get("budget_indicators"):
                                print(f"\nBudget Indicators:\n{sales['budget_indicators']}")
                            
                            if sales.get("technology_stack"):
                                print("\nTechnology Stack:")
                                print(", ".join(sales["technology_stack"]))
                            
                            if sales.get("growth_indicators"):
                                print(f"\nGrowth Indicators:\n{sales['growth_indicators']}")
                            
                            if sales.get("recommended_approach"):
                                print(f"\nRecommended Sales Approach:\n{sales['recommended_approach']}")
                
                # Display prospect data if available
                if data.get("prospect_data"):
                    print("\nProspect Information:")
                    print("-" * 50)
                    print(json.dumps(data["prospect_data"], indent=2))
                
                # Display insights if available
                if data.get("insights"):
                    print("\nAdditional Insights:")
                    print("-" * 50)
                    for insight in data["insights"]:
                        print(f"- {insight}")
            else:
                print(f"\nError: {response.error}")
                
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"Fatal error occurred: {str(e)}") 