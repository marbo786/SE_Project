import sys

with open('backend/app/main.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_upgrade = '''alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
command.upgrade(alembic_cfg, "head")'''

new_upgrade = '''alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
with engine.begin() as connection:
    alembic_cfg.attributes["connection"] = connection
    command.upgrade(alembic_cfg, "head")'''

text = text.replace(old_upgrade, new_upgrade)

with open('backend/app/main.py', 'w', encoding='utf-8') as f:
    f.write(text)
