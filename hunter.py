import httpx
import asyncio

async def verify_email(email, api_key):
    url = "https://api.hunter.io/v2/email-verifier"
    params = {"email": email, "api_key": api_key}

    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        if r.status_code == 200:
            return r.json().get("data", {})
        return {"error": r.text, "email": email}

async def verify_contacts_async(contacts, api_key):
    tasks = [verify_email(c["email"], api_key) for c in contacts if c.get("email")]
    results = await asyncio.gather(*tasks)
    
    verified_contacts = []
    for contact, hunter_data in zip([c for c in contacts if c.get("email")], results):
        verified_contacts.append({**contact,
                                  "hunter_result": hunter_data.get("result"),
                                  "hunter_score": hunter_data.get("score"),
                                  "smtp_check": hunter_data.get("smtp_check")})
    return verified_contacts