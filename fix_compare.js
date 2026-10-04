const fs = require('fs');
let c = fs.readFileSync('frontend/src/pages/ReportPage.tsx', 'utf8');

c = c.replace(
  "import { submissionsApi, findingsApi, traceabilityApi } from '@/lib/api'",
  "import { submissionsApi, findingsApi, traceabilityApi } from '@/lib/api'\nimport { BadgeCheck, AlertCircle, History } from 'lucide-react'"
);

c = c.replace(
  "const [activeTab, setActiveTab] = useState('scores')",
  "const [activeTab, setActiveTab] = useState('scores')\n  const [compareData, setCompareData] = useState<any>(null)"
);

c = c.replace(
  "setFindings(fRes.data)",
  `setFindings(fRes.data)
        if (sRes.data.version > 1) {
          submissionsApi.compare(Number(id), sRes.data.version - 1).then(cRes => setCompareData(cRes.data)).catch(() => {})
        }`
);

// Add the tab to the navigation
c = c.replace(
  `{ key: 'traceability', label: 'Traceability Matrix' }`,
  `{ key: 'traceability', label: 'Traceability Matrix' },\n    { key: 'compare', label: 'Version History' }`
);

let compareTabJSX = `
        {/* Compare Tab */}
        <div className={activeTab === 'compare' ? "block mt-8" : "hidden print:block print:mt-8"}>
          <h2 className="hidden print:block text-2xl font-bold mb-4">Version History (Changes from V{submission?.version ? submission.version - 1 : 1})</h2>
          {!compareData ? (
            <p className="text-gray-500">No previous version data available to compare against.</p>
          ) : (
            <div className="space-y-6">
              <Card className="border-l-4 border-l-green-500">
                <CardHeader><CardTitle className="flex items-center gap-2"><BadgeCheck className="text-green-500" /> Resolved Findings ({compareData.resolved_findings?.length || 0})</CardTitle></CardHeader>
                <CardContent>
                  {compareData.resolved_findings?.length === 0 ? <p className="text-gray-500">No findings were resolved.</p> : (
                    <ul className="space-y-3">
                      {compareData.resolved_findings?.map((f: any) => (
                        <li key={f.id} className="text-sm border-b pb-2">
                          <Badge variant="outline" className="mr-2">{f.rule_id}</Badge>
                          <span className="text-gray-700">{f.explanation}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>

              <Card className="border-l-4 border-l-red-500">
                <CardHeader><CardTitle className="flex items-center gap-2"><AlertCircle className="text-red-500" /> New Findings ({compareData.new_findings?.length || 0})</CardTitle></CardHeader>
                <CardContent>
                  {compareData.new_findings?.length === 0 ? <p className="text-gray-500">No new findings introduced.</p> : (
                    <ul className="space-y-3">
                      {compareData.new_findings?.map((f: any) => (
                        <li key={f.id} className="text-sm border-b pb-2">
                          <Badge variant="outline" className="mr-2">{f.rule_id}</Badge>
                          <span className="text-gray-700">{f.explanation}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
              
              <Card className="border-l-4 border-l-yellow-500">
                <CardHeader><CardTitle className="flex items-center gap-2"><History className="text-yellow-500" /> Persistent Findings ({compareData.persistent_findings?.length || 0})</CardTitle></CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-500">These findings were present in the previous version and have not yet been fixed.</p>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
`;

c = c.replace(
  `{/* Findings Tab */}`,
  compareTabJSX + `\n\n        {/* Findings Tab */}`
);

fs.writeFileSync('frontend/src/pages/ReportPage.tsx', c);
