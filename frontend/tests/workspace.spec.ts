import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import path from 'node:path'

async function workspace(page: Page) {
  const project = { id: 41, name: 'Library lending review', status: 'done', version: 1, current_revision_id: 1, published_run_id: 'run-a', latest_run_id: 'run-a', analysis_mode: 'deterministic', analysis_profile: 'srs_only', created_at: '2026-11-04T12:00:00Z' }
  const run = { id: 'run-a', project_id: 41, revision_id: 1, status: 'completed', stage: 'finished', has_report: true, created_at: project.created_at, attempt_count: 1 }
  const revision = { id: 1, project_id: 41, number: 1, state: 'sealed', edit_version: 1, analysis_profile: 'srs_only', analysis_mode: 'deterministic', artifacts: [] }
  const report = { findings: [{ id: 3, element_id: 'req-1', rule_id: 'FR-201', severity: 'major', requirement_id: 'FR-1', explanation: 'The response target is ambiguous.', quoted_text: 'The catalog shall respond fast.', source_ref: 'Paragraph 2' }], trace_links: [{ id: 7, source_type: 'requirement', source_id: 'req-1', source_label: 'FR-1', target_type: 'class', target_id: 'class-1', target_label: 'Catalog', status: 'suggested', origin: 'lexical_similarity', confidence: 0.6, evidence: { note: 'Shared catalog term' } }], reviews: [] as any[], extractions: { '1': { requirements: [{ internal_id: 'req-1', id: 'FR-1', text: 'The catalog shall respond fast.', source_ref: 'Paragraph 2', artifact_id: 1 }] } }, score: { overall_score: 80, computed_at: project.created_at, details: { profile: 'srs_only', rubric_version: '2', note: 'Deterministic checks completed.', categories: { requirements: { applicable: true, percentage: 80, eligible_count: 1, contribution: 80, weight: 100 } } } } }
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    let json: unknown
    if (path === '/api/auth/me') json = { id: 1, name: 'Reviewer', email: 'reviewer@example.com' }
    else if (path === '/api/projects/41') json = project
    else if (path === '/api/v1/projects/41/runs') json = { items: [run], total: 1 }
    else if (path === '/api/v1/projects/41/revisions') json = { items: [revision], total: 1 }
    else if (path === '/api/v1/projects/41/revisions/1') json = revision
    else if (path === '/api/v1/runs/run-a') json = run
    else if (path === '/api/v1/runs/run-a/report') json = report
    else if (path === '/api/v1/runs/run-a/trace-endpoints') json = []
    else if (path === '/api/v1/runs/run-a/decisions') {
      const data = route.request().postDataJSON()
      expect(data.expected_decision_id).toBe(0)
      report.reviews = [{ id: 10, finding_id: data.target_type === 'finding' ? data.target_id : null, trace_id: data.target_type === 'trace' ? data.target_id : null, status: data.status }]
      json = report.reviews[0]
    } else return route.fulfill({ status: 404, json: { detail: `Unmocked route: ${path}` } })
    await route.fulfill({ json })
  })
  return { project, run, report }
}

test('URL review state, keyboard disclosure, decisions, and complete print', async ({ page }) => {
  await workspace(page)
  await page.goto('/projects/41?tab=findings&q=catalog&severity=major&finding=3')
  await expect(page.getByRole('region', { name: 'Source evidence' })).toContainText('Paragraph 2')
  await expect(page.getByRole('textbox', { name: 'Search findings' })).toHaveValue('catalog')
  await page.reload()
  await expect(page.getByRole('textbox', { name: 'Search findings' })).toHaveValue('catalog')
  const collapse = page.getByRole('button', { name: 'Collapse finding' })
  await collapse.focus(); await page.keyboard.press('Enter')
  await expect(page.getByRole('button', { name: 'Expand finding' })).toHaveAttribute('aria-expanded', 'false')
  await page.keyboard.press('Enter')
  await page.getByRole('button', { name: 'Accept finding', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Finding decision' })).toContainText('Review: accepted')
  await page.getByRole('textbox', { name: 'Search findings' }).fill('no such result')
  await expect(page.getByText('No findings match query')).toBeVisible()
  await page.emulateMedia({ media: 'print' })
  const print = page.getByRole('region', { name: 'Complete printable report' })
  await expect(print).toBeVisible()
  await expect(print).toContainText('All findings (1)')
  await expect(print).toContainText('All trace links (1)')
  await expect(print).toContainText('Paragraph 2')
  await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeHidden()
})

test('responsive themes, focus return, and automated accessibility', async ({ page }, info) => {
  await workspace(page)
  await page.goto('/projects/41?tab=findings')
  await expect(page.getByRole('region', { name: 'Quality score' })).toBeVisible()
  for (const width of [360, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 })
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
    await page.screenshot({ path: info.outputPath(`workspace-${width}.png`), fullPage: true })
  }
  for (const theme of ['dark', 'light']) {
    await page.getByLabel('Appearance').selectOption(theme)
    const scan = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze()
    expect(scan.violations).toEqual([])
    await page.screenshot({ path: info.outputPath(`workspace-${theme}.png`), fullPage: true })
  }
  await page.setViewportSize({ width: 360, height: 800 })
  await page.getByRole('button', { name: 'Open navigation' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Open navigation' })).toBeFocused()
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%' })
  const overflow = await page.evaluate(() => [...document.querySelectorAll('main *')].filter(el => el.getBoundingClientRect().right > innerWidth).map(el => ({ tag: el.tagName, class: el.className, text: el.textContent?.slice(0, 80) })))
  expect(overflow).toEqual([])
  await page.screenshot({ path: info.outputPath('workspace-200-percent.png'), fullPage: true })
})

test('dashboard server failures remain errors and retry recovers', async ({ page }) => {
  await workspace(page)
  let failing = true
  await page.route('**/api/dashboard/stats', route => route.fulfill(failing ? { status: 503, json: { detail: 'Service temporarily unavailable' } } : { json: { total_projects: 0, analyzed_projects: 0, analyzing_projects: 0 } }))
  await page.route('**/api/projects/', route => route.fulfill({ json: [] }))
  await page.goto('/')
  await expect(page.getByRole('alert')).toContainText('Dashboard unavailable')
  await expect(page.getByText('Start your first review')).toBeHidden()
  failing = false
  await page.getByRole('button', { name: 'Try again' }).click()
  await expect(page.getByText('Start your first review')).toBeVisible()
})

test('expired session preserves return location', async ({ page }) => {
  await workspace(page)
  await page.route('**/api/projects/41', route => route.fulfill({ status: 401, json: { detail: 'Session expired' } }))
  await page.goto('/projects/41?tab=traceability')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('status')).toContainText('Sign in to continue')
})

test('keyboard upload recovers in the same saved project after interruption', async ({ page }) => {
  await workspace(page)
  let creates = 0, uploads = 0
  const revision = { id: 1, project_id: 41, number: 1, state: 'draft', edit_version: 1, analysis_profile: 'srs_only', analysis_mode: 'deterministic', artifacts: [] as any[] }
  await page.route('**/api/v1/projects', async route => { creates++; await route.fulfill({ status: 201, json: { id: 41, current_revision_id: 1 } }) })
  await page.route('**/api/v1/projects/41/revisions/1', route => route.fulfill({ json: revision }))
  await page.route('**/api/v1/projects/41/revisions/1/extraction', route => route.fulfill({ json: { canonical: null } }))
  await page.route('**/api/v1/projects/41/revisions/1/artifacts', async route => {
    uploads++
    if (uploads === 1) return route.abort('connectionreset')
    revision.edit_version = 2
    revision.artifacts = [{ id: 8, type: 'srs', filename: 'sample-requirements.docx' }]
    await route.fulfill({ status: 201, json: { artifact_id: 8, revision } })
  })
  await page.setViewportSize({ width: 360, height: 900 })
  await page.goto('/projects/new')
  await page.getByLabel('Specification Name').fill('Interrupted upload review')
  await page.getByRole('button', { name: 'Continue to Document Upload' }).click()
  const choose = page.getByRole('button', { name: 'Choose SRS document' })
  await choose.focus()
  const chooser = page.waitForEvent('filechooser')
  await page.keyboard.press('Enter')
  await (await chooser).setFiles(path.resolve('public/sample-requirements.docx'))
  await page.getByRole('button', { name: /4 Save draft/ }).click()
  await page.getByRole('button', { name: 'Save draft and review extraction' }).click()
  await expect(page.getByText(/Your saved draft is also available/)).toBeVisible()
  await page.getByRole('button', { name: 'Save draft and review extraction' }).click()
  await expect(page).toHaveURL(/\/projects\/41\/revisions\/1$/)
  await expect(page.getByRole('link', { name: 'sample-requirements.docx' })).toBeVisible()
  expect(creates).toBe(1)
  expect(uploads).toBe(2)
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  const scan = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze()
  expect(scan.violations).toEqual([])
})

test('queued run polls into a partial report and stops at its terminal status', async ({ page }) => {
  const fixture = await workspace(page)
  let reads = 0
  await page.route('**/api/projects/41', route => route.fulfill({ json: { ...fixture.project, status: reads < 2 ? 'analyzing' : 'partial' } }))
  await page.route('**/api/v1/runs/run-a', route => {
    reads++
    return route.fulfill({ json: { ...fixture.run, status: reads < 2 ? 'queued' : 'partial', has_report: reads >= 2 } })
  })
  fixture.report.score.overall_score = null as any
  await page.goto('/projects/41?run=run-a')
  await expect(page.getByText(/Queued for analysis/)).toBeVisible()
  await expect(page.getByText('Not graded', { exact: true })).toBeVisible()
  await expect(page.getByText(/Some inputs or requested checks could not be fully evaluated/)).toBeVisible()
  // Allow the final live-project projection to catch up, then assert polling stops.
  await page.waitForTimeout(2500)
  const terminalReads = reads
  await page.waitForTimeout(2500)
  expect(reads).toBe(terminalReads)
})
