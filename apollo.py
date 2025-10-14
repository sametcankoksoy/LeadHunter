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
        "Authorization": f"Bearer {data.api_key}",
        "Content-Type": "application/json",
        "Cache-Control": "no-cache"
    }

    all_contacts = []
    page = data.start_page
    per_page = data.per_page or 1

    while len(all_contacts) < data.total_records:
        payload = {
            "page": page,
            "per_page": per_page,
            "q_keywords": data.q_keywords,
            "person_titles": titles,
            "organization_keywords": keywords,
            "organization_locations": locations,
            "organization_num_employees_ranges": employee_ranges,
            "contact_email_status": "verified"
        }

        try:
            r = requests.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        contacts = data.get("contacts", [])
        if not contacts:
            break

        for c in contacts:
            normalized = extract_contact_info(c)
            all_contacts.append(normalized)

        page += 1

    return all_contacts[:data.total_records]