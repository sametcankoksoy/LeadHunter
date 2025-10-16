from fastapi import HTTPException
import requests

def search_organizations(api_key, keywords=None, locations=None, industries=None, company_sizes=None, limit=10):
    url = "https://api.apollo.io/api/v1/organizations/search"
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": api_key
    }
    
    payload = {
        "page": 1,
        "per_page": limit
    }

    def normalize_param(param):
        if not param:
            return None
        if isinstance(param, str):
            return [p.strip() for p in param.split(",") if p.strip()]
        if isinstance(param, list):
            flattened = []
            for p in param:
                if isinstance(p, list):
                    flattened.extend(p)
                else:
                    flattened.append(p)
            return flattened
        return [param]
    
    keywords = normalize_param(keywords)
    locations = normalize_param(locations)
    industries = normalize_param(industries)
    company_sizes = normalize_param(company_sizes)
    
    if keywords:
        payload["q_organization_keywords"] = keywords
    if locations:
        payload["q_organization_locations"] = locations
    if industries:
        payload["q_organization_industries"] = industries
    if company_sizes:
        payload["q_organization_num_employees_ranges"] = company_sizes
    
    try:
        r = requests.post(url, headers=headers, json=payload)

        if r.status_code == 401:
            raise HTTPException(status_code=401, detail="Unauthorized. Check your Apollo API key.")
        elif r.status_code == 403:
            raise HTTPException(status_code=403, detail="Forbidden. Check your Apollo subscription plan.")
        elif r.status_code == 429:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
        
        r.raise_for_status()
        response_data = r.json()
        
        organizations = response_data.get("organizations", [])
        if not organizations:
            raise HTTPException(status_code=404, detail="No organizations found. Try broader search terms.")

        formatted_orgs = []
        for org in organizations:
            formatted_orgs.append({
                "id": org.get("id"),
                "name": org.get("name"),
                "website_url": org.get("website_url"),
                "industry": org.get("industry"),
                "estimated_num_employees": org.get("estimated_num_employees"),
                "city": org.get("city"),
                "state": org.get("state"),
                "country": org.get("country"),
                "phone": org.get("phone"),
                "linkedin_url": org.get("linkedin_url")
            })
        
        return formatted_orgs
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apollo Organizations API Error: {str(e)}")


def get_organization_top_people(api_key, organization_id):
    """Get top people from an organization (free tier)"""
    
    url = "https://api.apollo.io/api/v1/mixed_people/organization_top_people"
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": api_key
    }
    
    payload = {
        "organization_id": organization_id,
        "page": 1,
        "per_page": 25
    }
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        r.raise_for_status()
        response_data = r.json()
        
        people = response_data.get("people", [])
        formatted_people = []
        for person in people:
            formatted_people.append({
                "id": person.get("id"),
                "first_name": person.get("first_name"),
                "last_name": person.get("last_name"),
                "title": person.get("title"),
                "email": person.get("email"),
                "phone": person.get("phone"),
                "linkedin_url": person.get("linkedin_url"),
                "organization_name": (
                    person.get("organization", {}).get("name") if person.get("organization") else None
                )
            })
        return formatted_people
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apollo Top People API Error: {str(e)}")
