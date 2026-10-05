import sys

with open('backend/config.yaml', 'r', encoding='utf-8') as f:
    text = f.read()

text += '''
agentic_repair:
  enabled: true
  max_llm_calls_per_project: 50
'''

with open('backend/config.yaml', 'w', encoding='utf-8') as f:
    f.write(text)
