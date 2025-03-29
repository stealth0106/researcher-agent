# Researcher Agent

An intelligent agent system for researching companies and prospects, built with Python and powered by Google's Gemini AI.

## Features

- Company Research
  - Comprehensive company information gathering
  - Executive summaries with market analysis
  - Sales insights for SAAS products
  - Technology stack analysis
  - Growth indicators and opportunities

- Prospect Research
  - Professional background analysis
  - Experience and education tracking
  - LinkedIn profile integration
  - Decision-making role assessment

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

Run the main script:
```bash
python main.py
```

Example queries:
- "Tell me about Microsoft"
- "Research John Smith from Apple"
- "Find information about Google and their CEO Sundar Pichai"

## Project Structure

```
researcher_agent/
├── agents/
│   ├── base_agent.py
│   ├── company_research_agent.py
│   ├── prospect_research_agent.py
│   └── synthesizer_agent.py
├── utils/
│   └── web_scraper.py
├── main.py
├── requirements.txt
└── .env
```

## Dependencies

- Python 3.8+
- google-generativeai
- requests
- beautifulsoup4
- python-dotenv
- pydantic

## License

MIT License 