import re

NAME_PATTERNS = [
    r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # simple proper names
]
EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
ID_PATTERN = r'\b\d{8,}\b'  # long numeric IDs like student IDs

def redact_text(text: str) -> str:
    """Remove PII before sending to external LLM (NFR-06)."""
    text = re.sub(EMAIL_PATTERN, '[EMAIL]', text)
    text = re.sub(ID_PATTERN, '[ID]', text)
    for pattern in NAME_PATTERNS:
        text = re.sub(pattern, '[NAME]', text)
    return text
