# Lead Researcher Pro

A comprehensive lead research and contact management application with both FastAPI backend and Streamlit frontend.

## Features

### 🔍 Contact Search
- Advanced contact search using Apollo.io API
- Filter by job titles, organization keywords, locations, and company size
- Configurable pagination and record limits

### 🤖 Natural Language Search
- Query contacts using natural language
- AI-powered parsing of search requests
- Smart extraction of job titles, locations, and company criteria

### ✅ Email Verification
- Hunter.io integration for email verification
- Verification scores and deliverability status
- Bulk email verification capabilities

### 📤 CRM Integration
- HubSpot integration for contact management
- Automated contact pushing to CRM
- Batch operations for efficiency

### 📊 Analytics & Insights
- Interactive visualizations of contact data
- Email verification status charts
- Organization distribution analysis
- Search history tracking

### 📥 Data Export
- Export contacts as CSV, JSON, or email lists
- Interactive data grid with filtering and sorting
- Bulk selection and export capabilities

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### API Keys
You'll need API keys from the following services:

1. **Apollo.io** - For contact search
   - Sign up at [Apollo.io](https://apollo.io)
   - Get your API key from the dashboard

2. **Hunter.io** - For email verification (optional)
   - Sign up at [Hunter.io](https://hunter.io)
   - Get your API key from the dashboard

3. **HubSpot** - For CRM integration (optional)
   - Sign up at [HubSpot](https://hubspot.com)
   - Create a private app and get the API key

## Usage

### Streamlit Frontend (Recommended)

Run the Streamlit application:
```bash
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

#### Using the Streamlit App:

1. **Configure API Keys**: Enter your API keys in the sidebar
2. **Contact Search**: Use the advanced search form to find contacts
3. **Natural Language Search**: Try the AI-powered natural language search
4. **Verify Emails**: Use Hunter.io to verify email addresses
5. **Export Data**: Export your results in various formats
6. **Analytics**: View insights and visualizations of your data

### FastAPI Backend

Run the FastAPI server:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

#### API Endpoints:

- `POST /fetch_verify_push_async` - Search, verify, and push contacts
- `POST /nl_query_fetch` - Natural language contact search

## Example Usage

### Streamlit App Examples:

**Contact Search:**
- Keywords: "software engineer"
- Person Titles: "CTO, CTO, Software Engineer"
- Organization Keywords: "technology, software"
- Organization Locations: "San Francisco, Remote"
- Employee Ranges: "11-50, 51-200"

**Natural Language Query:**
- "Find 20 software engineers at tech startups in San Francisco with 10-50 employees"

### API Usage Examples:

```python
import requests

# Search contacts
search_data = {
    "api_key": "your_apollo_key",
    "total_records": 10,
    "q_keywords": "software engineer",
    "person_titles": ["CTO", "Software Engineer"],
    "organization_keywords": ["technology"],
    "organization_locations": ["San Francisco"]
}

response = requests.post("http://localhost:8000/fetch_verify_push_async", 
                        json=search_data,
                        params={
                            "hunter_api_key": "your_hunter_key",
                            "hubspot_api_key": "your_hubspot_key"
                        })
```

## File Structure

```
├── streamlit_app.py      # Main Streamlit application
├── main.py              # FastAPI backend
├── models.py            # Pydantic models
├── apollo.py            # Apollo.io integration
├── hunter.py            # Hunter.io integration
├── hubspot.py           # HubSpot integration
├── utils.py             # Utility functions
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please open an issue in the repository.
