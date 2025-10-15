from fastapi import HTTPException
from utils import extract_contact_info
import requests

def fetch_contacts(data):
    titles = data.person_titles
    keywords = data.organization_keywords
    locations = data.organization_locations
    employee_ranges = data.organization_num_employees_ranges

    url = "https://api.apollo.io/api/v1/contacts/search"
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json"
    }
    
    # Try different API key header formats
    headers["X-Api-Key"] = data.api_key
    # Alternative formats if needed:
    # headers["Authorization"] = f"Bearer {data.api_key}"
    # headers["apollo-api-key"] = data.api_key

    all_contacts = []
    page = data.start_page
    per_page = data.per_page or 1

    while len(all_contacts) < data.total_records:
        # Use Apollo.io's correct parameter names based on documentation
        payload = {
            "page": page,
            "per_page": per_page
        }
        
        # Use correct Apollo.io parameter names
        if data.q_keywords:
            payload["q_keywords"] = data.q_keywords
        
        if titles:
            payload["q_titles"] = titles  # Correct parameter name
        
        if keywords:
            payload["q_organization_keywords"] = keywords  # Correct parameter name
        
        if locations:
            payload["q_organization_locations"] = locations  # Correct parameter name
        
        if employee_ranges:
            payload["q_organization_num_employees_ranges"] = employee_ranges  # Correct parameter name
        
        # Remove contact_email_status - might not be available in free tier
        # payload["contact_email_status"] = "verified"

        try:
            r = requests.post(url, headers=headers, json=payload)
            
            
            if r.status_code == 401:
                raise HTTPException(
                    status_code=401, 
                    detail=f"Unauthorized: {r.text}. Check your API key and credits."
                )
            elif r.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail=f"Forbidden: {r.text}. Check your subscription plan."
                )
            elif r.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limited: {r.text}. Wait and try again."
                )
            
            r.raise_for_status()
            response_data = r.json()
            
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Apollo API Error: {str(e)}")

        contacts = response_data.get("contacts", [])
        
        if not contacts:
            break

        for c in contacts:
            normalized = extract_contact_info(c)
            all_contacts.append(normalized)

        page += 1

    return all_contacts[:data.total_records]