import requests
from typing import Dict, Any, Optional, List
import logging
from bs4 import BeautifulSoup
import time
import re
import os
from dotenv import load_dotenv
import google.generativeai as genai
from urllib.parse import quote_plus
import json
from requests import Response

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebScraper:
    """Utility class for web scraping using search-based discovery"""
    
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.gemini_model = None
        self._initialize_gemini()
    
    def _initialize_gemini(self):
        """Initialize Gemini model for keyword generation"""
        try:
            # Use already loaded environment variables
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
                self.gemini_model = genai.GenerativeModel("models/gemini-1.5-pro")
                logger.info("Gemini model initialized successfully")
            else:
                logger.warning("Gemini API key not found in environment variables")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {str(e)}")
    
    def initialize(self):
        """Initialize the session"""
        try:
            self.session.headers.update(self.headers)
            logger.info("Session initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize session: {str(e)}")
            raise
    
    def close(self):
        """Close the session"""
        if self.session:
            try:
                self.session.close()
                logger.info("Session closed successfully")
            except Exception as e:
                logger.error(f"Error closing session: {str(e)}")
    
    def _make_request(self, url: str) -> Optional[Response]:
        """Make HTTP request with retries and logging"""
        try:
            logger.info(f"\nMaking request to: {url}")
            
            # Add more robust headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
            
            # Add retry mechanism with exponential backoff
            max_retries = 3
            base_delay = 2
            
            for attempt in range(max_retries):
                try:
                    # Enable SSL verification by default
                    response = requests.get(
                        url,
                        headers=headers,
                        timeout=30,
                        verify=True,  # Enable SSL verification
                        allow_redirects=True
                    )
                    
                    logger.info(f"Response status code: {response.status_code}")
                    logger.info(f"Response headers: {dict(response.headers)}")
                    
                    if response.status_code == 200:
                        return response
                    elif response.status_code in [429, 502]:  # Too Many Requests or Bad Gateway
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Server error {response.status_code}. Waiting {delay} seconds...")
                        time.sleep(delay)
                    else:
                        logger.error(f"HTTP {response.status_code} error")
                        return None
                        
                except requests.exceptions.SSLError as e:
                    logger.warning(f"SSL verification failed: {str(e)}")
                    # Try again with SSL verification disabled only if it fails
                    response = requests.get(
                        url,
                        headers=headers,
                        timeout=30,
                        verify=False,
                        allow_redirects=True
                    )
                    if response.status_code == 200:
                        return response
                except requests.exceptions.RequestException as e:
                    logger.error(f"Request attempt {attempt + 1} failed: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(base_delay * (2 ** attempt))
                    else:
                        raise
            
            return None
            
        except Exception as e:
            logger.error(f"Error making request to {url}: {str(e)}", exc_info=True)
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing extra whitespace and newlines"""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.strip())
    
    def _generate_search_keywords(self, query: str, context: str) -> List[str]:
        """Generate search keywords using Gemini"""
        if not self.gemini_model:
            logger.warning("Gemini model not initialized")
            return [query]
        
        try:
            prompt = f"""
            Given the following research query and context, generate 3-5 specific search keywords or phrases 
            that would help find accurate information. Focus on unique identifiers and specific terms.
            
            Query: {query}
            Context: {context}
            
            Respond with only the keywords, one per line, no numbering or additional text.
            """
            
            response = self.gemini_model.generate_content(prompt)
            keywords = [k.strip() for k in response.text.split('\n') if k.strip()]
            logger.info(f"Generated keywords: {keywords}")
            return keywords
        except Exception as e:
            logger.error(f"Error generating keywords: {str(e)}")
            return [query]
    
    def _search_google(self, query: str) -> List[Dict[str, str]]:
        """Search using Google Custom Search API"""
        try:
            logger.info(f"Starting Google search for query: {query}")
            
            # Get API credentials from environment
            api_key = os.getenv('GOOGLE_API_KEY')
            search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
            
            if not api_key or not search_engine_id:
                logger.error("Google API credentials not found in environment variables")
                return []
            
            # Construct the API URL
            base_url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': api_key,
                'cx': search_engine_id,
                'q': query,
                'num': 5,  # Get top 5 results
                'fields': 'items(title,link,snippet,pagemap)'  # Request additional fields
            }
            
            logger.info(f"Making request to Google Search API")
            response = requests.get(base_url, params=params)
            
            if response.status_code != 200:
                logger.error(f"Google API error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return []
            
            data = response.json()
            logger.info(f"Received {len(data.get('items', []))} results from Google")
            
            results = []
            for item in data.get('items', []):
                # Extract pagemap data
                pagemap = item.get('pagemap', {})
                metatags = pagemap.get('metatags', [{}])[0] if pagemap.get('metatags') else {}
                organization = pagemap.get('organization', [{}])[0] if pagemap.get('organization') else {}
                person = pagemap.get('person', [{}])[0] if pagemap.get('person') else {}
                
                result = {
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'source': 'google',
                    'metadata': {
                        'description': metatags.get('og:description', ''),
                        'type': metatags.get('og:type', ''),
                        'site_name': metatags.get('og:site_name', ''),
                        'published_time': metatags.get('article:published_time', ''),
                        'modified_time': metatags.get('article:modified_time', ''),
                        'author': metatags.get('article:author', ''),
                        'section': metatags.get('article:section', ''),
                        'organization_name': organization.get('name', ''),
                        'organization_url': organization.get('url', ''),
                        'person_name': person.get('name', ''),
                        'person_job_title': person.get('jobtitle', ''),
                        'person_affiliation': person.get('affiliation', '')
                    }
                }
                logger.info(f"Found result: {result['title']}")
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in Google search: {str(e)}", exc_info=True)
            return []
    
    def _search_duckduckgo(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Search using DuckDuckGo"""
        try:
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            content = self._make_request(search_url)
            
            if not content:
                return []
            
            soup = BeautifulSoup(content.text, 'html.parser')
            results = []
            
            for result in soup.find_all('div', {'class': 'result'})[:num_results]:
                title_elem = result.find('a', {'class': 'result__title'})
                snippet_elem = result.find('a', {'class': 'result__snippet'})
                
                if title_elem and snippet_elem:
                    results.append({
                        'title': self._clean_text(title_elem.text),
                        'url': snippet_elem.get('href', ''),
                        'snippet': self._clean_text(snippet_elem.text)
                    })
            
            return results
        except Exception as e:
            logger.error(f"Error searching DuckDuckGo: {str(e)}")
            return []
    
    def _extract_raw_content(self, url: str) -> str:
        """Extract raw content from a webpage without Gemini analysis"""
        try:
            logger.info(f"\nExtracting raw content from: {url}")
            response = self._make_request(url)
            if not response:
                logger.error("Failed to get webpage content")
                return ""
            
            soup = BeautifulSoup(response.text, 'html.parser')
            logger.info("Successfully parsed webpage HTML")
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'noscript']):
                element.decompose()
            
            # Get text content with better structure
            text = ""
            
            # Try to find main content areas
            main_content = soup.find(['main', 'article', 'div'], class_=['content', 'main', 'article'])
            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
            else:
                text = soup.get_text(separator=' ', strip=True)
            
            logger.info(f"Extracted text length: {len(text)} characters")
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Limit content length
            text = text[:4000]
            logger.info(f"Cleaned text length: {len(text)} characters")
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting raw content: {str(e)}", exc_info=True)
            return ""
    
    def _select_relevant_urls(self, urls: List[Dict[str, str]], target_name: str, 
                           target_type: str = "prospect", company_name: Optional[str] = None) -> List[Dict[str, str]]:
        """Use Gemini to select the most relevant URLs based on metadata and content"""
        try:
            # Prepare URL information for Gemini with detailed metadata
            url_info = "\n".join([
                f"URL {i+1}:\n"
                f"Title: {url['title']}\n"
                f"URL: {url['url']}\n"
                f"Snippet: {url['snippet']}\n"
                f"Metadata:\n"
                f"- Description: {url['metadata']['description']}\n"
                f"- Content Type: {url['metadata']['type']}\n"
                f"- Site Name: {url['metadata']['site_name']}\n"
                f"- Publication Date: {url['metadata']['published_time']}\n"
                f"- Last Modified: {url['metadata']['modified_time']}\n"
                f"- Author: {url['metadata']['author']}\n"
                f"- Content Section: {url['metadata']['section']}\n"
                f"- Organization Name: {url['metadata']['organization_name']}\n"
                f"- Organization URL: {url['metadata']['organization_url']}\n"
                f"- Person Name: {url['metadata']['person_name']}\n"
                f"- Person Title: {url['metadata']['person_job_title']}\n"
                f"- Person Affiliation: {url['metadata']['person_affiliation']}\n"
                f"---"
                for i, url in enumerate(urls)
            ])
            
            if target_type == "prospect":
                prompt = f"""Given the following prospect information and URLs, analyze each URL and determine if it's relevant for researching this prospect.
                Consider these factors for each URL:
                1. Relevance to the prospect's professional information
                2. Presence of LinkedIn profile
                3. Source credibility (company website, professional networks, etc.)
                4. Information freshness (recent updates)
                5. Content type (profile pages, news articles, etc.)
                6. Organization and person metadata matching
                7. URL structure and domain credibility
                
                Prospect Name: {target_name}
                Company Name: {company_name if company_name else 'Not specified'}
                
                URLs to analyze:
                {url_info}
                
                Return ONLY a JSON array of URLs with their relevance assessment in this format:
                [
                    {{
                        "url": "URL to evaluate",
                        "is_relevant": true/false,
                        "relevance_score": "1-10 score",
                        "reason": "detailed explanation of why this URL is relevant or not",
                        "content_type": "linkedin, company_profile, news, etc.",
                        "key_factors": ["list of key factors that make this URL relevant or irrelevant"]
                    }}
                ]
                
                Include ALL URLs in the response, marking irrelevant ones with is_relevant: false.
                Do not include any other text or markdown formatting."""
            else:  # company research
                prompt = f"""Given the following company information and URLs, analyze each URL and determine if it's relevant for researching this company.
                Consider these factors for each URL:
                1. Official company website and pages
                2. Company profiles on business directories
                3. Recent news and updates
                4. Source credibility
                5. Information freshness
                6. Organization metadata matching
                7. URL structure and domain credibility
                8. Content type and depth
                
                Company Name: {target_name}
                
                URLs to analyze:
                {url_info}
                
                Return ONLY a JSON array of URLs with their relevance assessment in this format:
                [
                    {{
                        "url": "URL to evaluate",
                        "is_relevant": true/false,
                        "relevance_score": "1-10 score",
                        "reason": "detailed explanation of why this URL is relevant or not",
                        "content_type": "company_website, business_directory, news, etc.",
                        "key_factors": ["list of key factors that make this URL relevant or irrelevant"]
                    }}
                ]
                
                Include ALL URLs in the response, marking irrelevant ones with is_relevant: false.
                Do not include any other text or markdown formatting."""
            
            logger.info("Sending URLs to Gemini for relevance analysis")
            response = self.gemini_model.generate_content(prompt)
            logger.info("Received URL relevance analysis from Gemini")
            
            try:
                # Clean and parse the response
                response_text = response.text.strip()
                response_text = response_text.replace('```json', '').replace('```', '').strip()
                selected_urls = json.loads(response_text)
                
                # Convert selected URLs back to original format
                relevant_urls = []
                for selected in selected_urls:
                    matching_url = next((url for url in urls if url['url'] == selected['url']), None)
                    if matching_url:
                        matching_url['relevance_score'] = selected['relevance_score']
                        matching_url['relevance_reason'] = selected['reason']
                        matching_url['content_type'] = selected['content_type']
                        matching_url['key_factors'] = selected['key_factors']
                        matching_url['is_relevant'] = selected['is_relevant']
                        relevant_urls.append(matching_url)
                
                # Filter to only include relevant URLs
                relevant_urls = [url for url in relevant_urls if url['is_relevant']]
                logger.info(f"Selected {len(relevant_urls)} relevant URLs out of {len(urls)} total URLs")
                
                # Log detailed selection information
                for url in relevant_urls:
                    logger.info(f"\nSelected URL: {url['url']}")
                    logger.info(f"Relevance Score: {url['relevance_score']}")
                    logger.info(f"Content Type: {url['content_type']}")
                    logger.info(f"Key Factors: {', '.join(url['key_factors'])}")
                    logger.info(f"Reason: {url['relevance_reason']}")
                
                return relevant_urls
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse URL selection response: {str(e)}")
                logger.error(f"Raw response: {response_text}")
                return urls  # Fallback to all URLs if parsing fails
                
        except Exception as e:
            logger.error(f"Error in URL selection: {str(e)}")
            return urls  # Fallback to all URLs if selection fails

    def scrape_company_info(self, company_name: str) -> Dict[str, Any]:
        """Scrape company information using search-based discovery"""
        if not self.session:
            self.initialize()
        
        company_data = {
            "name": company_name,
            "description": None,
            "industry": None,
            "headquarters": None,
            "founded": None,
            "size": None,
            "ceo": None,
            "website": None,
            "executive_summary": None
        }
        
        try:
            # Generate search keywords
            keywords = self._generate_search_keywords(
                company_name,
                "Find accurate company information including description, industry, headquarters, founding date, size, and CEO"
            )
            
            # Collect all URLs from search results
            all_urls = []
            seen_urls = set()  # For deduplication
            
            # Search and collect URLs
            for keyword in keywords:
                search_query = f"{keyword} company information"
                results = self._search_google(search_query)
                
                for result in results:
                    if result['url'] not in seen_urls:
                        seen_urls.add(result['url'])
                        all_urls.append(result)
            
            if all_urls:
                # Select most relevant URLs using Gemini
                relevant_urls = self._select_relevant_urls(all_urls, company_name, target_type="company")
                
                # Extract content from selected URLs
                all_content = []
                for url_info in relevant_urls:
                    content = self._extract_raw_content(url_info['url'])
                    if content:
                        all_content.append(content)
                        logger.info(f"Added content from: {url_info['url']}")
                
                if all_content:
                    # Combine all content
                    combined_content = "\n\n".join(all_content)
                    logger.info(f"Combined content length: {len(combined_content)} characters")
                    
                    # Analyze content with Gemini
                    prompt = f"""Analyze this text and extract company information in JSON format:
                    {combined_content}
                    
                    Return ONLY a JSON object with these fields:
                    {{
                        "description": "Brief company description",
                        "industry": "Main industry",
                        "location": "Company headquarters location",
                        "founding_date": "When the company was founded",
                        "size": "Company size/employee count",
                        "ceo_name": "Current CEO name",
                        "website": "Company website URL",
                        "executive_summary": {{
                            "overview": "Comprehensive overview of the company's business, mission, and key operations",
                            "market_position": "Company's position in their industry and market share",
                            "key_products_services": ["List of main products or services"],
                            "recent_developments": ["Recent significant news, acquisitions, or changes"],
                            "sales_insights": {{
                                "pain_points": ["Potential challenges or pain points the company might be facing"],
                                "opportunities": ["Potential opportunities for a SAAS product based on company's situation"],
                                "decision_makers": ["Key decision makers and their roles"],
                                "budget_indicators": "Indicators of company's budget capacity and spending patterns",
                                "technology_stack": ["Current technology solutions or stack if mentioned"],
                                "growth_indicators": "Signs of company growth or expansion",
                                "recommended_approach": "Suggested approach for reaching out to this company"
                            }}
                        }}
                    }}
                    
                    For the sales_insights section, analyze the company's situation and provide actionable insights for a SAAS sales approach. Consider:
                    1. Company's current challenges and pain points
                    2. Growth stage and trajectory
                    3. Technology adoption patterns
                    4. Budget capacity indicators
                    5. Decision-making structure
                    6. Recent developments that might create opportunities
                    
                    If a field cannot be found, use null. Do not include any other text or markdown formatting."""
                    
                    logger.info("Sending content to Gemini model")
                    response = self.gemini_model.generate_content(prompt)
                    logger.info("Received response from Gemini model")
                    
                    try:
                        # Clean and parse the response
                        response_text = response.text.strip()
                        # Remove any markdown code block markers if present
                        response_text = response_text.replace('```json', '').replace('```', '').strip()
                        # Parse the JSON response
                        info = json.loads(response_text)
                        logger.info("Successfully parsed JSON response")
                        logger.info(f"Extracted company info: {json.dumps(info, indent=2)}")
                        
                        # Update company data with extracted information
                        for key, value in info.items():
                            if value:
                                company_data[key] = value
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {str(e)}")
                        logger.error(f"Raw response: {response_text}")
                        # Try to extract information from the raw response
                        try:
                            # Look for key information in the raw text
                            description = None
                            industry = None
                            location = None
                            founding_date = None
                            size = None
                            ceo_name = None
                            website = None
                            
                            # Extract description
                            if "description" in response_text.lower():
                                desc_start = response_text.lower().find("description")
                                desc_end = response_text.find("\n", desc_start)
                                if desc_end == -1:
                                    desc_end = len(response_text)
                                description = response_text[desc_start:desc_end].split(":", 1)[1].strip()
                            
                            # Extract industry
                            if "industry" in response_text.lower():
                                ind_start = response_text.lower().find("industry")
                                ind_end = response_text.find("\n", ind_start)
                                if ind_end == -1:
                                    ind_end = len(response_text)
                                industry = response_text[ind_start:ind_end].split(":", 1)[1].strip()
                            
                            # Extract location
                            if "location" in response_text.lower():
                                loc_start = response_text.lower().find("location")
                                loc_end = response_text.find("\n", loc_start)
                                if loc_end == -1:
                                    loc_end = len(response_text)
                                location = response_text[loc_start:loc_end].split(":", 1)[1].strip()
                            
                            # Extract founding date
                            if "founding" in response_text.lower():
                                found_start = response_text.lower().find("founding")
                                found_end = response_text.find("\n", found_start)
                                if found_end == -1:
                                    found_end = len(response_text)
                                founding_date = response_text[found_start:found_end].split(":", 1)[1].strip()
                            
                            # Extract size
                            if "size" in response_text.lower():
                                size_start = response_text.lower().find("size")
                                size_end = response_text.find("\n", size_start)
                                if size_end == -1:
                                    size_end = len(response_text)
                                size = response_text[size_start:size_end].split(":", 1)[1].strip()
                            
                            # Extract CEO name
                            if "ceo" in response_text.lower():
                                ceo_start = response_text.lower().find("ceo")
                                ceo_end = response_text.find("\n", ceo_start)
                                if ceo_end == -1:
                                    ceo_end = len(response_text)
                                ceo_name = response_text[ceo_start:ceo_end].split(":", 1)[1].strip()
                            
                            # Extract website
                            if "website" in response_text.lower():
                                web_start = response_text.lower().find("website")
                                web_end = response_text.find("\n", web_start)
                                if web_end == -1:
                                    web_end = len(response_text)
                                website = response_text[web_start:web_end].split(":", 1)[1].strip()
                            
                            # Update company data with extracted information
                            if description:
                                company_data["description"] = description
                            if industry:
                                company_data["industry"] = industry
                            if location:
                                company_data["headquarters"] = location
                            if founding_date:
                                company_data["founded"] = founding_date
                            if size:
                                company_data["size"] = size
                            if ceo_name:
                                company_data["ceo"] = ceo_name
                            if website:
                                company_data["website"] = website
                            
                        except Exception as e:
                            logger.error(f"Failed to extract information from raw response: {str(e)}")
            
            return company_data
            
        except Exception as e:
            logger.error(f"Error scraping company info: {str(e)}")
            return company_data
    
    def scrape_prospect_info(self, prospect_name: str, company_name: Optional[str] = None) -> Dict[str, Any]:
        """Scrape prospect information using search-based discovery"""
        if not self.session:
            self.initialize()
        
        prospect_data = {
            "name": prospect_name,
            "title": None,
            "company": company_name,
            "location": None,
            "experience": None,
            "education": None,
            "linkedin_url": None
        }
        
        try:
            # Generate search keywords
            context = f"Find information about {prospect_name}"
            if company_name:
                context += f" who works at {company_name}"
            context += " including their title, location, experience, education, and LinkedIn profile"
            
            keywords = self._generate_search_keywords(prospect_name, context)
            
            # Collect all URLs from search results
            all_urls = []
            seen_urls = set()  # For deduplication
            
            # Search and collect URLs
            for keyword in keywords:
                search_query = f"{keyword} profile information"
                results = self._search_google(search_query)
                
                for result in results:
                    if result['url'] not in seen_urls:
                        seen_urls.add(result['url'])
                        all_urls.append(result)
            
            if all_urls:
                # Select most relevant URLs using Gemini
                relevant_urls = self._select_relevant_urls(all_urls, prospect_name, target_type="prospect", company_name=company_name)
                
                # Extract content from selected URLs
                all_content = []
                for url_info in relevant_urls:
                    content = self._extract_raw_content(url_info['url'])
                    if content:
                        all_content.append(content)
                        logger.info(f"Added content from: {url_info['url']}")
                
                if all_content:
                    # Combine all content
                    combined_content = "\n\n".join(all_content)
                    logger.info(f"Combined content length: {len(combined_content)} characters")
                    
                    # Analyze content with Gemini
                    prompt = f"""Analyze this text and extract prospect information in JSON format:
                    {combined_content}
                    
                    Return ONLY a JSON object with these fields:
                    {{
                        "current_title": "Current job title",
                        "company_name": "Current company name",
                        "location": "Current location",
                        "experience": ["List of previous job titles and companies"],
                        "education": ["List of educational background"],
                        "linkedin_url": "LinkedIn profile URL if found"
                    }}
                    
                    If a field cannot be found, use null. Do not include any other text."""
                    
                    logger.info("Sending content to Gemini model")
                    response = self.gemini_model.generate_content(prompt)
                    logger.info("Received response from Gemini model")
                    
                    try:
                        # Parse the response
                        info = json.loads(response.text)
                        logger.info("Successfully parsed JSON response")
                        logger.info(f"Extracted prospect info: {json.dumps(info, indent=2)}")
                        
                        # Update prospect data with extracted information
                        for key, value in info.items():
                            if value:
                                prospect_data[key] = value
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {str(e)}")
                        logger.error(f"Raw response: {response.text}")
            
            return prospect_data
            
        except Exception as e:
            logger.error(f"Error scraping prospect info: {str(e)}")
            return prospect_data 