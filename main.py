from fastapi import FastAPI
from models import FetchRequest,NLQuery
from apollo import fetch_contacts
from hunter import verify_contacts_async
from hubspot import push_contacts_async
import asyncio


app = FastAPI(title="Lead Researcher")

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