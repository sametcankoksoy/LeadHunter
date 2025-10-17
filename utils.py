def extract_contact_info(info):
    email = info.get("email")
    phone = info.get("phone")
    if not phone and info.get("phones"):
        phone = info["phones"][0].get("number") or info["phones"][0].get("phone")
    
    if not phone and info.get("account"):
        phone = info["account"].get("phone") or info["account"].get("sanitized_phone")
    
    organization = info.get("organization") or info.get("organization_name") or (info.get("account") and info["account"].get("name"))
    
    return {
        "id": info.get("id"),
        "first_name": info.get("first_name"),
        "last_name": info.get("last_name"),
        "title": info.get("title"),
        "email": email,
        "phone": phone,
        "email_status": info.get("email_status") or info.get("contact_email_status"),
        "organization": organization
    }
