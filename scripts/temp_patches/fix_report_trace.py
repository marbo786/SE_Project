import sys

with open('frontend/src/pages/ReportPage.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

# Add download function
fetch_func = '''    const fetchReport = async () => {'''
download_func = '''    const downloadTraceability = () => {
        window.open(http://localhost:8000/traceability/project/\/export, "_blank");
    };
    
    const updateLinkStatus = async (linkId: number, status: string) => {
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(http://localhost:8000/traceability/\, {
                method: 'PATCH',
                headers: { 'Authorization': Bearer \, 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
            if (res.ok) fetchReport();
        } catch (e) {
            console.error(e);
        }
    };
    
    const fetchReport = async () => {'''

text = text.replace(fetch_func, download_func)

# Add Download button
h2_tag = '''        <div className={activeTab === 'traceability' ? "block mt-8" : "hidden print:block print:mt-8"}>
          <h2 className="text-2xl font-bold mb-4 hidden print:block">Traceability Matrix</h2>'''
h2_new = '''        <div className={activeTab === 'traceability' ? "block mt-8" : "hidden print:block print:mt-8"}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold hidden print:block">Traceability Matrix</h2>
            <button onClick={downloadTraceability} className="px-4 py-2 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700">Download CSV</button>
          </div>'''
text = text.replace(h2_tag, h2_new)

# Add Confirm/Reject buttons
old_row = '''                        <tr key={t.id}>
                          <td className="px-6 py-4">
                            <span className="font-medium">{t.source_id}</span> ({t.source_type})
                          </td>
                          <td className="px-6 py-4 text-center">
                            <Link2 className="h-4 w-4 inline text-blue-400" />
                          </td>
                          <td className="px-6 py-4">
                            <span className="font-medium">{t.target_id}</span> ({t.target_type})
                          </td>
                        </tr>'''
                        
new_row = '''                        <tr key={t.id}>
                          <td className="px-6 py-4">
                            <span className="font-medium">{t.source_id}</span> ({t.source_type})
                          </td>
                          <td className="px-6 py-4 text-center flex items-center justify-center gap-2">
                            <span className={px-2 py-1 text-xs rounded-full \}>{t.status}</span>
                            {t.status === 'suggested' && (
                                <>
                                    <button onClick={() => updateLinkStatus(t.id, 'confirmed')} className="px-2 py-1 bg-green-500 text-white rounded text-xs">Confirm</button>
                                    <button onClick={() => updateLinkStatus(t.id, 'rejected')} className="px-2 py-1 bg-red-500 text-white rounded text-xs">Reject</button>
                                </>
                            )}
                          </td>
                          <td className="px-6 py-4">
                            <span className="font-medium">{t.target_id}</span> ({t.target_type})
                          </td>
                        </tr>'''
text = text.replace(old_row, new_row)

with open('frontend/src/pages/ReportPage.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
