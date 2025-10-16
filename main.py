from hunter import verify_contacts_async
from hubspot import push_contacts_async
from apollo import fetch_contacts
from models import FetchRequest
from fastapi import FastAPI
import asyncio
import re


app = FastAPI(title="Lead Hunter")


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