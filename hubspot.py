import httpx
import asyncio

HUBSPOT_CONTACTS_BASE = "https://api.hubapi.com/crm/v3/objects/contacts"
HUBSPOT_COMPANIES_BASE = "https://api.hubapi.com/crm/v3/objects/companies"

async def push_contact(contact, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "properties": {
            "email": contact.get("email"),
            "firstname": contact.get("first_name"),
            "lastname": contact.get("last_name"),
            "phone": contact.get("phone"),
            "jobtitle": contact.get("title"),
            "company": contact.get("organization")
        }
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(HUBSPOT_CONTACTS_BASE, json=data, headers=headers)
        if res.status_code not in [200, 201]:
            return {"error": res.text, "status": res.status_code, "email": contact.get("email")}
        return res.json()

async def push_contacts_async(contacts, api_key):
    tasks = [push_contact(c, api_key) for c in contacts if c.get("email")]
    return await asyncio.gather(*tasks)

async def push_company(company, api_key):
    """Push a single company to HubSpot"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "properties": {
            "name": company.get("name"),
            "domain": company.get("website_url", "").replace("https://", "").replace("http://", "").split("/")[0] if company.get("website_url") else "",
            "website": company.get("website_url"),
            "phone": company.get("phone"),
            "city": company.get("city"),
            "state": company.get("state"),
            "country": company.get("country"),
            "industry": company.get("industry"),
            "numberofemployees": company.get("estimated_num_employees"),
            "linkedin_company_page": company.get("linkedin_url")
        }
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.post(HUBSPOT_COMPANIES_BASE, json=data, headers=headers)
        if res.status_code not in [200, 201]:
            return {"error": res.text, "status": res.status_code, "company": company.get("name")}
        return res.json()

async def push_companies_async(companies, api_key):
    """Push multiple companies to HubSpot"""
    tasks = [push_company(c, api_key) for c in companies if c.get("name")]
    return await asyncio.gather(*tasks)

async def push_person_to_company(person, company_id, api_key):
    """Push a person and associate them with a company in HubSpot"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # First create the contact
    contact_data = {
        "properties": {
            "email": person.get("email"),
            "firstname": person.get("first_name"),
            "lastname": person.get("last_name"),
            "phone": person.get("phone"),
            "jobtitle": person.get("title"),
            "company": person.get("organization_name")
        }
    }
    
    async with httpx.AsyncClient() as client:
        # Create contact
        contact_res = await client.post(HUBSPOT_CONTACTS_BASE, json=contact_data, headers=headers)
        
        if contact_res.status_code not in [200, 201]:
            return {"error": contact_res.text, "status": contact_res.status_code, "person": f"{person.get('first_name')} {person.get('last_name')}"}
        
        contact_data = contact_res.json()
        contact_id = contact_data.get("id")
        
        # Associate contact with company
        if company_id and contact_id:
            association_data = {
                "inputs": [{
                    "from": {"id": contact_id},
                    "to": {"id": company_id},
                    "type": "contact_to_company"
                }]
            }
            
            association_res = await client.put(
                f"{HUBSPOT_CONTACTS_BASE}/{contact_id}/associations/companies/{company_id}",
                json=association_data,
                headers=headers
            )
            
            if association_res.status_code not in [200, 201]:
                return {"warning": f"Contact created but association failed: {association_res.text}", "contact_id": contact_id}
        
        return contact_data

async def push_people_to_companies_async(people, company_id, api_key):
    """Push multiple people and associate them with a company"""
    tasks = [push_person_to_company(p, company_id, api_key) for p in people if p.get("first_name")]
    return await asyncio.gather(*tasks)