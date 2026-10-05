import sys

with open('frontend/src/pages/ReportPage.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

old_rewrite = '''                  {f.rewrite_suggestion && (
                    <p className="text-sm text-blue-600 mt-3 font-medium bg-blue-50 p-3 rounded-md">
                      dY' Suggestion: {f.rewrite_suggestion}
                    </p>
                  )}'''

new_rewrite = '''                  {f.rewrite_suggestion && (
                    <div className="mt-3 bg-blue-50 p-3 rounded-md border border-blue-100">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-blue-800 text-sm">AI Rewrite Suggestion</span>
                          <span className={px-2 py-0.5 text-xs rounded-full \}>
                            {f.rewrite_passed ? 'Passed Checks' : 'Still Failing'} 
                          </span>
                          <span className="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">
                            {f.rewrite_attempts} Attempt{f.rewrite_attempts !== 1 ? 's' : ''}
                          </span>
                        </div>
                        <button 
                          onClick={() => navigator.clipboard.writeText(f.rewrite_suggestion)}
                          className="text-xs px-2 py-1 bg-white border border-blue-200 text-blue-600 rounded hover:bg-blue-50 transition-colors print:hidden"
                        >
                          Copy
                        </button>
                      </div>
                      <p className="text-sm text-blue-900 font-medium whitespace-pre-wrap">
                        {f.rewrite_suggestion}
                      </p>
                    </div>
                  )}'''

# Handle the weird emoji encoding issue
import re
text = re.sub(r'\{\s*f\.rewrite_suggestion && \(\s*<p className="text-sm text-blue-600 mt-3 font-medium bg-blue-50 p-3 rounded-md">\s*.*?Suggestion: \{f\.rewrite_suggestion\}\s*</p>\s*\)\s*\}', new_rewrite, text, flags=re.DOTALL)

with open('frontend/src/pages/ReportPage.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
