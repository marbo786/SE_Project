const fs = require('fs');
let c = fs.readFileSync('frontend/src/pages/ReportPage.tsx', 'utf8');

c = c.replace(
  /\{activeTab === 'scores' && scores && scores\.overall_score !== undefined && \(\s*<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">/g,
  `<div className={activeTab === 'scores' ? "block" : "hidden print:block"}><div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <h2 className="hidden print:block text-2xl font-bold mb-4 col-span-full">Quality Scores</h2>`
).replace(
  /<\/Card>\s*<\/div>\s*\)\}/g,
  `</Card></div></div>`
);

c = c.replace(
  /\{activeTab === 'findings' && \(\s*<div className="space-y-4">/g,
  `<div className={activeTab === 'findings' ? "block mt-8" : "hidden print:block print:mt-8"}><div className="space-y-4">
    <h2 className="hidden print:block text-2xl font-bold mb-4">Analysis Findings</h2>`
).replace(
  /<\/div>\s*<\/div>\s*\)\}/g,
  `</div></div></div>`
);

c = c.replace(
  /\{activeTab === 'traceability' && \(\s*<div>/g,
  `<div className={activeTab === 'traceability' ? "block mt-8" : "hidden print:block print:mt-8"}><div>
    <h2 className="hidden print:block text-2xl font-bold mb-4">Traceability Matrix</h2>`
).replace(
  /<\/Table>\s*<\/div>\s*\)\}/g,
  `</Table></div></div>`
);

fs.writeFileSync('frontend/src/pages/ReportPage.tsx', c);
