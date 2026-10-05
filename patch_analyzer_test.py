import sys

with open('backend/tests/test_analyzer.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('def test_analysis_reaches_done(monkeypatch):', '@pytest.mark.asyncio\nasync def test_analysis_reaches_done(monkeypatch):')
text = text.replace('def test_analysis_reaches_partial(monkeypatch):', '@pytest.mark.asyncio\nasync def test_analysis_reaches_partial(monkeypatch):')

text = text.replace('run_analysis_pipeline(project.id)', 'await run_analysis_pipeline(project.id)')

with open('backend/tests/test_analyzer.py', 'w', encoding='utf-8') as f:
    f.write(text)
