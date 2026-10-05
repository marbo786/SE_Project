import json

dataset = [
    {"id": "FR-1", "text": "The system shall load the page fast.", "class": "functional", "expected_rules": ["FR-401"]},
    {"id": "FR-2", "text": "The system shall be user-friendly.", "class": "non_functional", "expected_rules": ["FR-401", "FR-411"]},
    {"id": "FR-3", "text": "The system shall be easy to use.", "class": "non_functional", "expected_rules": ["FR-401", "FR-411"]},
    {"id": "FR-4", "text": "The system shall support pagination, etc.", "class": "functional", "expected_rules": ["FR-401"]},
    {"id": "FR-5", "text": "The system shall scale as appropriate.", "class": "non_functional", "expected_rules": ["FR-401", "FR-411"]},
    {"id": "FR-6", "text": "The system shall provide adequate performance.", "class": "non_functional", "expected_rules": ["FR-401", "FR-411"]},
    {"id": "FR-7", "text": "The system shall have a good interface.", "class": "non_functional", "expected_rules": ["FR-401", "FR-411"]},
    {"id": "FR-8", "text": "The system shall execute quick searches.", "class": "functional", "expected_rules": ["FR-401"]},
    {"id": "FR-9", "text": "The system shall be efficient.", "class": "non_functional", "expected_rules": ["FR-401", "FR-411"]},
    {"id": "FR-10", "text": "The system shall be flexible.", "class": "non_functional", "expected_rules": ["FR-401", "FR-411"]},
    
    # FR-402: multiple shall
    {"id": "FR-11", "text": "The system shall process orders and shall email users.", "class": "functional", "expected_rules": ["FR-402"]},
    {"id": "FR-12", "text": "The system shall login and the system shall logout.", "class": "functional", "expected_rules": ["FR-402"]},
    {"id": "FR-13", "text": "The admin shall add users and shall remove users.", "class": "functional", "expected_rules": ["FR-402"]},
    {"id": "FR-14", "text": "The system shall save data and it shall sync data.", "class": "functional", "expected_rules": ["FR-402"]},
    {"id": "FR-15", "text": "The system shall compress images and shall store them.", "class": "functional", "expected_rules": ["FR-402"]},
    
    # FR-409: no identifier
    {"id": None, "text": "The system shall allow users to register.", "class": "functional", "expected_rules": ["FR-409"]},
    {"id": None, "text": "The system shall allow users to login.", "class": "functional", "expected_rules": ["FR-409"]},
    {"id": None, "text": "The system shall process payments.", "class": "functional", "expected_rules": ["FR-409"]},
    {"id": None, "text": "The system shall show errors.", "class": "functional", "expected_rules": ["FR-409"]},
    {"id": None, "text": "The system shall logout the user.", "class": "functional", "expected_rules": ["FR-409"]},
    
    # FR-410: duplicate identifier (needs to share an ID with another req)
    {"id": "FR-DUP", "text": "The system shall export to PDF.", "class": "functional", "expected_rules": ["FR-410"]},
    {"id": "FR-DUP", "text": "The system shall export to CSV.", "class": "functional", "expected_rules": ["FR-410"]},
    {"id": "FR-DUP2", "text": "The system shall show dashboard.", "class": "functional", "expected_rules": ["FR-410"]},
    {"id": "FR-DUP2", "text": "The system shall show reports.", "class": "functional", "expected_rules": ["FR-410"]},
    {"id": "FR-DUP3", "text": "The system shall sync.", "class": "functional", "expected_rules": ["FR-410"]},
    {"id": "FR-DUP3", "text": "The system shall not sync.", "class": "functional", "expected_rules": ["FR-410"]},
    
    # FR-411: NFR no metric (non_functional class but no numbers/units)
    {"id": "NFR-1", "text": "The system shall be secure.", "class": "non_functional", "expected_rules": ["FR-411"]},
    {"id": "NFR-2", "text": "The system shall be highly available.", "class": "non_functional", "expected_rules": ["FR-411"]},
    {"id": "NFR-3", "text": "The system shall have low latency.", "class": "non_functional", "expected_rules": ["FR-411"]},
    
    # Good requirements (no errors)
    {"id": "FR-100", "text": "The system shall generate a monthly report.", "class": "functional", "expected_rules": []},
    {"id": "FR-101", "text": "The system shall allow users to reset their password.", "class": "functional", "expected_rules": []},
    {"id": "NFR-100", "text": "The system shall respond within 500 ms.", "class": "non_functional", "expected_rules": []},
    {"id": "NFR-101", "text": "The system shall handle 1000 concurrent users.", "class": "non_functional", "expected_rules": []}
]

with open('backend/eval/dataset.json', 'w', encoding='utf-8') as f:
    json.dump(dataset, f, indent=2)
