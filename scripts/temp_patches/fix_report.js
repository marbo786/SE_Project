const fs = require('fs');
let c = fs.readFileSync('frontend/src/pages/ReportPage.tsx', 'utf8');

// Fix emoji
c = c.replace(/dY'\s/g, '💡 ');
c = c.replace(/\uFFFD*dY'/g, '💡');

// Add Print button and print:hidden to the Back link
c = c.replace(
  `className="flex items-center gap-2 text-gray-500 hover:text-gray-900 mb-6 text-sm"`,
  `className="flex items-center gap-2 text-gray-500 hover:text-gray-900 mb-6 text-sm print:hidden"`
);

let headerBlock = `{submission && (
          <div className="mb-6">
            <h1 className="text-3xl font-bold">{submission.team_name}</h1>
            <p className="text-gray-500">Version {submission.version} • {formatDate(submission.created_at)}</p>
            <Badge variant={submission.status === 'done' ? 'default' : submission.status === 'error' ? 'destructive' : 'outline'}
              className="mt-2">{submission.status}</Badge>
          </div>
        )}`;

let newHeaderBlock = `{submission && (
          <div className="mb-6 flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold">{submission.team_name}</h1>
              <p className="text-gray-500">Version {submission.version} • {formatDate(submission.created_at)}</p>
              <Badge variant={submission.status === 'done' ? 'default' : submission.status === 'error' ? 'destructive' : 'outline'}
                className="mt-2">{submission.status}</Badge>
            </div>
            <Button onClick={() => window.print()} className="print:hidden">
              Download PDF Report
            </Button>
          </div>
        )}`;
c = c.replace(headerBlock, newHeaderBlock);

// Hide tabs during print
c = c.replace(
  `className="flex gap-1 border-b border-gray-200 mb-6"`,
  `className="flex gap-1 border-b border-gray-200 mb-6 print:hidden"`
);

fs.writeFileSync('frontend/src/pages/ReportPage.tsx', c);
