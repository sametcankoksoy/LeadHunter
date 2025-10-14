import httpx
import asyncio

HUBSPOT_BASE = "https://api.hubapi.com/crm/v3/objects/contacts"

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
        res = await client.post(HUBSPOT_BASE, json=data, headers=headers)
        if res.status_code not in [200, 201]:
            return {"error": res.text, "status": res.status_code, "email": contact.get("email")}
        return res.json()

async def push_contacts_async(contacts, api_key):
    tasks = [push_contact(c, api_key) for c in contacts if c.get("email")]
    return await asyncio.gather(*tasks)