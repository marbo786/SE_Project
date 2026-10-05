import os
import sys

# Configure alembic.ini
with open('backend/alembic.ini', 'r', encoding='utf-8') as f:
    ini = f.read()
ini = ini.replace('sqlalchemy.url = driver://user:pass@localhost/dbname', 'sqlalchemy.url = sqlite:///./srs_reviewer.db')
with open('backend/alembic.ini', 'w', encoding='utf-8') as f:
    f.write(ini)

# Configure env.py
with open('backend/alembic/env.py', 'r', encoding='utf-8') as f:
    env = f.read()

import_stmt = '''import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import Base
from app.models import user, project, artifact, finding, traceability, llm_log, score
target_metadata = Base.metadata
'''

env = env.replace('target_metadata = None', import_stmt)

with open('backend/alembic/env.py', 'w', encoding='utf-8') as f:
    f.write(env)
