import sys

with open('backend/app/models/finding.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('rewrite_suggestion = Column(Text, nullable=True)', 'rewrite_suggestion = Column(Text, nullable=True)\n    rewrite_attempts = Column(Integer, default=0)\n    rewrite_passed = Column(Integer, default=0)  # SQLite boolean')

# Use Boolean instead of Integer
text = text.replace('rewrite_passed = Column(Integer, default=0)  # SQLite boolean', 'rewrite_passed = Column(Boolean, default=False)')
text = text.replace('from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Enum', 'from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Enum, Boolean')

with open('backend/app/models/finding.py', 'w', encoding='utf-8') as f:
    f.write(text)

with open('backend/app/schemas/finding.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('rewrite_suggestion: Optional[str]', 'rewrite_suggestion: Optional[str]\n    rewrite_attempts: Optional[int] = 0\n    rewrite_passed: Optional[bool] = False')

with open('backend/app/schemas/finding.py', 'w', encoding='utf-8') as f:
    f.write(text)
