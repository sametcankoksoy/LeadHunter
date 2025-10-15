from fastapi import FastAPI
from models import FetchRequest,NLQuery
from apollo import fetch_contacts
from hunter import verify_contacts_async
from hubspot import push_contacts_async
import asyncio
import re


app = FastAPI(title="Lead Researcher")

async def ai_parse_query_to_payload(query: str):
    """Simple AI-like parsing of natural language queries to search parameters"""
    # This is a basic implementation - in a real scenario, you'd use an LLM
    payload = {
        "q_keywords": "",
        "person_titles": [],
        "organization_keywords": [],
        "organization_locations": [],
        "organization_num_employees_ranges": []
    }
    
    # Extract common patterns
    query_lower = query.lower()
    
    # Extract job titles
    titles = re.findall(r'\b(ceo|cto|cfo|coo|manager|director|engineer|developer|marketing|sales|hr|founder|president)\b', query_lower)
    if titles:
        payload["person_titles"] = list(set(titles))
    
    # Extract locations
    locations = re.findall(r'\b(san francisco|new york|los angeles|chicago|boston|seattle|austin|remote|usa|united states)\b', query_lower)
    if locations:
        payload["organization_locations"] = list(set(locations))
    
    # Extract company size
    if 'startup' in query_lower or 'small' in query_lower:
        payload["organization_num_employees_ranges"] = ["1-10", "11-50"]
    elif 'medium' in query_lower:
        payload["organization_num_employees_ranges"] = ["51-200", "201-500"]
    elif 'large' in query_lower or 'enterprise' in query_lower:
        payload["organization_num_employees_ranges"] = ["501-1000", "1001-5000", "5001+"]
    
    # Extract industry keywords
    if any(word in query_lower for word in ['tech', 'technology', 'software', 'saas']):
        payload["organization_keywords"] = ["technology", "software"]
    
    # Use the original query as keywords if no specific patterns found
    if not payload["q_keywords"]:
        payload["q_keywords"] = query
    
    return payload

@app.post("/fetch_verify_push_async")
async def fetch_verify_push_async(data: FetchRequest, hunter_api_key: str, hubspot_api_key: str):
    contacts = fetch_contacts(data)
    verified_contacts = await verify_contacts_async(contacts, hunter_api_key)
    hubspot_results = await push_contacts_async(verified_contacts, hubspot_api_key)

    return {
        "total": len(verified_contacts),
        "contacts": verified_contacts,
        "hubspot_results": hubspot_results
    }

@app.post("/nl_query_fetch")
async def nl_fetch(query: NLQuery):
    payload = await ai_parse_query_to_payload(query.query)
    payload["total_records"] = query.total_records
    payload["api_key"] = query.api_key
    contacts = await fetch_contacts(payload)
    return contacts