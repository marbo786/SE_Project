import sys

with open('backend/app/pipeline/analyzer.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('loop = asyncio.new_event_loop()            try:', 'loop = asyncio.new_event_loop()\n            try:')
with open('backend/app/pipeline/analyzer.py', 'w', encoding='utf-8') as f:
    f.write(c)

with open('backend/app/routers/submissions.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('"\\"\\"Compare this submission with a previous version."\\"\\"', '"""Compare this submission with a previous version."""')
with open('backend/app/routers/submissions.py', 'w', encoding='utf-8') as f:
    f.write(c)
