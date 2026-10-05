import re
from typing import Dict, Tuple

EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
ID_PATTERN = r'\b\d{8,}\b'
PHONE_PATTERN = r'\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'

class Redactor:
    def __init__(self):
        self.mapping: Dict[str, str] = {}
        self.counter = 0

    def redact(self, text: str) -> str:
        def repl(match, prefix):
            self.counter += 1
            token = f"[{prefix}_{self.counter}]"
            self.mapping[token] = match.group(0)
            return token

        text = re.sub(EMAIL_PATTERN, lambda m: repl(m, 'EMAIL'), text)
        text = re.sub(ID_PATTERN, lambda m: repl(m, 'ID'), text)
        text = re.sub(PHONE_PATTERN, lambda m: repl(m, 'PHONE'), text)
        return text

    def unredact(self, text: str) -> str:
        if not text:
            return text
        for token, original in self.mapping.items():
            text = text.replace(token, original)
        return text

# Legacy compat
def redact_text(text: str) -> str:
    return Redactor().redact(text)
