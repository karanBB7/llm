import re

def clean_text(text):
    """Clean and normalize text content"""
    if text:
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    return ""

def get_doctor_name_from_url(url):
    """Extract doctor name from URL"""
    match = re.search(r'/doctor-profile/(.+?)(?:/|$)', url)
    if match:
        return match.group(1)
    return "doctor"