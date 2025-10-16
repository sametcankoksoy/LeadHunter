from typing import Optional, List
from pydantic import BaseModel

class FetchRequest(BaseModel):
    api_key: str
    total_records: int = 1
    per_page: Optional[int] = 1
    start_page: Optional[int] = 1
    q_keywords: str 
    person_titles: Optional[List[str]] = None
    organization_keywords: Optional[List[str]] = None
    organization_locations: Optional[List[str]] = None
    organization_num_employees_ranges: Optional[List[str]] = None

class SimpleContact(BaseModel):
    id: str
    email: str

class NLQuery(BaseModel):
    query: str
    api_key: str
    total_records: int = 10