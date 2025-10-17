import asyncio
import httpx
import json

HUBSPOT_BASE = "https://api.hubapi.com"
HUBSPOT_CONTACTS_BASE = f"{HUBSPOT_BASE}/crm/v3/objects/contacts"
HUBSPOT_COMPANIES_BASE = f"{HUBSPOT_BASE}/crm/v3/objects/companies"
HUBSPOT_ASSOCIATIONS_BASE = f"{HUBSPOT_BASE}/crm/v4/associations/contacts/companies/batch/create"


async def push_contact(contact, api_key):
    """Push a single contact to HubSpot - only sends non-None values"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    properties = {}
    
    if contact.get("email"):
        properties["email"] = contact["email"]
    if contact.get("first_name"):
        properties["firstname"] = contact["first_name"]
    if contact.get("last_name"):
        properties["lastname"] = contact["last_name"]
    if contact.get("phone"):
        properties["phone"] = str(contact["phone"])
    if contact.get("title"):
        properties["jobtitle"] = contact["title"]
    
    if not properties.get("email"):
        return {"error": "Email is required", "status": 400, "contact": contact}
    
    data = {"properties": properties}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            res = await client.post(HUBSPOT_CONTACTS_BASE, json=data, headers=headers)
            
            if res.status_code not in [200, 201]:
                error_detail = res.text
                try:
                    error_json = res.json()
                    error_detail = error_json.get("message", res.text)
                except json.JSONDecodeError:
                    pass
                    
                if res.status_code == 401:
                    error_detail = "Invalid HubSpot API Key or token expired. Check Authorization scopes."
                
                print(f"❌ Failed Contact: {contact.get('email')} [{res.status_code}] {error_detail[:100]}")
                return {"error": error_detail, "status": res.status_code, "email": contact.get("email")}
            
            return res.json()
        except Exception as e:
            return {"error": f"Exception: {str(e)}", "status": 500, "email": contact.get("email")}


async def push_contacts_async(contacts, api_key):
    """Push multiple contacts to HubSpot"""
    if not contacts:
        return []
    valid_contacts = [c for c in contacts if c.get("email")]
    if not valid_contacts:
        return [{"error": "No contacts with email found", "status": 400}]
    tasks = [push_contact(c, api_key) for c in valid_contacts]
    return await asyncio.gather(*tasks)


async def push_company(company, api_key):
    """
    Push a single company to HubSpot.
    CRITICAL: Only sends non-None values to avoid HubSpot API errors.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    company_name = company.get("name")
    if not company_name or str(company_name).strip() == "":
        return {"error": "Company name is required", "status": 400, "company": company}

    properties = {"name": str(company_name).strip()}
    
    website_url = company.get("website_url")
    if website_url and str(website_url).strip():
        website_url = str(website_url).strip()
        properties["website"] = website_url
        
        domain = (
            website_url.replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
            .split("/")[0]
        )
        if domain:
            properties["domain"] = domain
    
    if company.get("phone"):
        phone = str(company["phone"]).strip()
        if phone and phone.lower() not in ["none", "null", ""]:
            properties["phone"] = phone
    
    if company.get("city"):
        city = str(company["city"]).strip()
        if city and city.lower() not in ["none", "null", ""]:
            properties["city"] = city
    
    if company.get("state"):
        state = str(company["state"]).strip()
        if state and state.lower() not in ["none", "null", ""]:
            properties["state"] = state
    
    if company.get("country"):
        country = str(company["country"]).strip()
        if country and country.lower() not in ["none", "null", ""]:
            properties["country"] = country
    
    if company.get("industry"):
        industry = str(company["industry"]).strip()
        if industry and industry.lower() not in ["none", "null", ""]:
            properties["industry"] = industry
    
    if company.get("estimated_num_employees") is not None:
        employees = company["estimated_num_employees"]
        if employees:
            properties["numberofemployees"] = str(employees)

    data = {"properties": properties}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            res = await client.post(HUBSPOT_COMPANIES_BASE, json=data, headers=headers)
            
            if res.status_code not in [200, 201]:
                error_detail = res.text
                try:
                    error_json = res.json()
                    error_detail = error_json.get("message", error_detail)
                    
                    if res.status_code == 401:
                        error_detail = "Invalid HubSpot API Key or token expired. Check Authorization scopes."
                    elif res.status_code == 403:
                        error_detail = f"Missing required HubSpot permission (scope): {error_detail}"
                    elif res.status_code == 409 or "DUPLICATE" in error_detail.upper():
                        error_detail = f"Company '{company_name}' already exists (duplicate by domain/name)."
                        
                except json.JSONDecodeError:
                    pass 
                    
                print(f"❌ Failed: {company_name} [{res.status_code}] {error_detail[:100]}")
                return {"error": error_detail, "status": res.status_code, "company": company_name}
            
            result = res.json()
            print(f"✅ Success: {company_name} (ID: {result.get('id')})")
            return result
            
        except Exception as e:
            print(f"❌ Exception: {company_name} - {str(e)}")
            return {"error": f"Exception: {str(e)}", "status": 500, "company": company_name}


async def push_companies_async(companies, api_key):
    """Push multiple companies to HubSpot"""
    if not companies:
        print("❌ No companies provided")
        return []
    
    print(f"\n{'='*60}")
    print(f"📊 HUBSPOT PUSH STARTED")
    print(f"{'='*60}")
    print(f"Total companies: {len(companies)}")
    
    valid_companies = [c for c in companies if c.get("name") and str(c.get("name")).strip()]
    print(f"Valid companies (with name): {len(valid_companies)}")
    
    if not valid_companies:
        print("❌ No valid companies found!")
        if companies:
            print(f"Example company: {companies[0]}")
        return [{"error": "No valid companies (missing 'name')", "status": 400}]
    
    print(f"First company: {valid_companies[0].get('name')}\n")
    
    tasks = [push_company(c, api_key) for c in valid_companies]
    results = await asyncio.gather(*tasks)
    
    successful = [r for r in results if 'error' not in r and r.get('id')]
    failed = [r for r in results if 'error' in r]
    
    print(f"\n{'='*60}")
    print(f"📊 HUBSPOT PUSH COMPLETED")
    print(f"{'='*60}")
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    
    if failed:
        print(f"\n❌ Failed companies:")
        for i, fail in enumerate(failed[:3], 1):
            print(f"  {i}. {fail.get('company', 'Unknown')}: {fail.get('error', 'Unknown')[:80]}")
    
    print(f"{'='*60}\n")
    
    return results


async def push_person_to_company(person, company_id, api_key):
    """Create a contact and associate with a company"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    properties = {}
    if person.get("email"):
        properties["email"] = person["email"]
    if person.get("first_name"):
        properties["firstname"] = person["first_name"]
    if person.get("last_name"):
        properties["lastname"] = person["last_name"]
    if person.get("phone"):
        properties["phone"] = str(person["phone"])
    if person.get("title"):
        properties["jobtitle"] = person["title"]
    
    if not properties.get("email"):
        return {"error": "Email required", "status": 400, "person": f"{person.get('first_name', '')} {person.get('last_name', '')}"}

    contact_data = {"properties": properties}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            contact_res = await client.post(HUBSPOT_CONTACTS_BASE, json=contact_data, headers=headers)
            
            if contact_res.status_code not in [200, 201]:
                error_detail = contact_res.text
                try:
                    error_json = contact_res.json()
                    error_detail = error_json.get("message", error_detail)
                    
                    if contact_res.status_code == 401:
                        error_detail = "Invalid HubSpot API Key or token expired. Check Authorization scopes."
                    
                except json.JSONDecodeError:
                    pass
                    
                print(f"❌ Failed Contact: {person.get('email')} [{contact_res.status_code}] {error_detail[:100]}")
                return {"error": error_detail, "status": contact_res.status_code, "person": f"{person.get('first_name', '')} {person.get('last_name', '')}"}
            
            contact_json = contact_res.json()
            contact_id = contact_json.get("id")

            if company_id and contact_id:
                assoc_data = {
                    "inputs": [{
                        "from": {"id": contact_id},
                        "to": {"id": company_id},
                        "type": "contact_to_company"
                    }]
                }
                assoc_res = await client.post(HUBSPOT_ASSOCIATIONS_BASE, json=assoc_data, headers=headers)
                if assoc_res.status_code not in [200, 201, 207]:  
                    return {"warning": f"Contact created but association failed: {assoc_res.text}", "contact_id": contact_id}

            return contact_json
            
        except Exception as e:
            return {"error": f"Exception: {str(e)}", "status": 500, "person": f"{person.get('first_name', '')} {person.get('last_name', '')}"}


async def push_people_to_companies_async(people, company_id, api_key):
    """Push multiple people and associate with company"""
    if not people:
        return []
    valid_people = [p for p in people if p.get("email")]
    if not valid_people:
        return [{"error": "No people with email", "status": 400}]
    tasks = [push_person_to_company(p, company_id, api_key) for p in valid_people]
    return await asyncio.gather(*tasks)
