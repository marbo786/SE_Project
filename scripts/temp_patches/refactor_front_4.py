import os

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

# --- REPORT PAGE ---
report_content = read_file('frontend/src/pages/ReportPage.tsx')

# Replace API calls and variables
report_content = report_content.replace('submissionsApi', 'projectsApi')
report_content = report_content.replace('submissionId', 'projectId')
report_content = report_content.replace('const { id } = useParams()', 'const { id } = useParams()\n  const projectId = id')
report_content = report_content.replace('const [submission, setSubmission]', 'const [project, setProject]')
report_content = report_content.replace('setSubmission(sRes.data)', 'setProject(sRes.data)')
report_content = report_content.replace('{submission && (', '{project && (')
report_content = report_content.replace('submission.', 'project.')
report_content = report_content.replace('submission?', 'project?')
report_content = report_content.replace("to=\"/submissions\"", "to=\"/projects\"")
report_content = report_content.replace("Back to Submissions", "Back to Projects")
report_content = report_content.replace("submission.team_name", "project.name")

write_file('frontend/src/pages/ReportPage.tsx', report_content)

delete_file('frontend/src/pages/SubmitPage.tsx')
