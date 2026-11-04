import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { randomUUID } from 'node:crypto'

test('review extraction, analyze, branch, and reopen immutable history', async ({ page }, testInfo) => {
  if (!process.env.BROWSER_SRS_PATH) throw new Error('Run with scripts/check_http_local.py --browser to use disposable services and input')
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  const auth = await page.request.post('/api/auth/register', { data: { name: 'Browser reviewer', email: `browser-${randomUUID()}@example.com`, password: 'browser-test-password-123' } })
  expect(auth.ok()).toBeTruthy()
  const cookies = await page.context().cookies()
  const headers = { 'X-CSRF-Token': cookies.find(cookie => cookie.name === 'srs_csrf')!.value }
  const created = await page.request.post('/api/v1/projects', { headers, data: { name: 'Response time review' } })
  expect(created.status()).toBe(201)
  const project = await created.json()
  const uploaded = await page.request.post(`/api/v1/projects/${project.id}/revisions/${project.current_revision_id}/artifacts`, {
    headers: { ...headers, 'If-Match': '1' }, multipart: { kind: 'srs', file: { name: 'source.docx', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', buffer: readFileSync(process.env.BROWSER_SRS_PATH) } },
  })
  expect(uploaded.status()).toBe(201)
  await page.goto(`/projects/${project.id}/revisions/${project.current_revision_id}`)
  await expect(page.getByRole('heading', { name: 'Response time review' })).toBeVisible()
  await page.getByRole('button', { name: 'Extract requirements', exact: true }).click()
  const text = page.getByRole('textbox', { name: 'Requirement text' })
  await expect(text).toHaveValue('FR-1 The system shall respond fast.')
  await text.fill('FR-1 The system shall respond within 2 seconds.')
  await page.getByRole('button', { name: 'Save requirement', exact: true }).click()
  await expect(page.getByRole('checkbox')).toBeEnabled()
  await page.getByRole('checkbox').check()
  await expect(page.getByRole('button', { name: 'Analyze this revision' })).toBeEnabled()
  await page.screenshot({ path: testInfo.outputPath('draft-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await page.screenshot({ path: testInfo.outputPath('draft-mobile.png'), fullPage: true })
  await page.getByRole('button', { name: 'Analyze this revision' }).click()
  await expect(page).toHaveURL(/\/projects\/\d+\?run=/)
  const firstReportUrl = page.url()
  await expect(page.getByRole('region', { name: 'Quality score' })).toBeVisible()
  await page.setViewportSize({ width: 1365, height: 900 })
  await page.screenshot({ path: testInfo.outputPath('report-history.png'), fullPage: true })
  await page.getByRole('button', { name: 'Edit a new draft' }).click()
  await expect(page).toHaveURL(/\/revisions\/\d+$/)
  await expect(page.getByText('Revision 2 draft', { exact: true })).toBeVisible()
  await expect(page.getByRole('textbox', { name: 'Requirement text' })).toHaveValue('FR-1 The system shall respond within 2 seconds.')
  await page.goto(firstReportUrl)
  await expect(page.getByRole('region', { name: 'Quality score' })).toBeVisible()
  // Controlled provider/report fixture exercises suggestion UI; API mutation
  // isolation, CAS and immutable publication are covered by backend integration tests.
  let decision: { id: number; finding_id: number; status: string; draft_id?: number } | null = null
  const submitted: Record<string, unknown>[] = []
  await page.route('**/api/v1/runs/*/report', async route => {
    const response = await route.fetch()
    const payload = await response.json()
    payload.findings = [{ id: 9001, rule_id: 'FR-401', severity: 'major', artifact_type: 'srs',
      requirement_id: 'FR-1', quoted_text: 'The system shall respond fast.', explanation: 'Missing metric.',
      rewrite_suggestion: 'The system shall respond within 2 seconds.', rewrite_passed: false,
      rewrite_checks: { quantities_and_units_preserved: false } }]
    payload.suggestion_decisions = decision ? [decision] : []
    await route.fulfill({ response, json: payload })
  })
  await page.route('**/api/v1/runs/*/suggestions/9001/decisions', async route => {
    const body = route.request().postDataJSON()
    submitted.push(body)
    expect(route.request().headers()['idempotency-key']).toBeTruthy()
    decision = { id: submitted.length, finding_id: 9001, status: body.action, draft_id: body.draft_id }
    await route.fulfill({ status: 201, json: { decision, draft_id: body.draft_id } })
  })
  await page.reload()
  const review = page.getByRole('region', { name: 'Review rewrite suggestion' })
  await expect(review).toBeVisible()
  await review.screenshot({ path: testInfo.outputPath('suggestion-review-form.png') })
  await expect(review.getByRole('button', { name: 'Apply to draft' })).toBeDisabled()
  await review.getByRole('button', { name: 'Reject suggestion' }).click()
  await expect(review.getByText('Suggestion rejected.', { exact: false })).toBeVisible()
  await review.getByRole('textbox', { name: 'Proposed requirement' }).fill('The system shall respond within 3 seconds.')
  await review.getByRole('checkbox').check()
  await review.getByRole('button', { name: 'Apply to draft' }).click()
  await expect(review.getByRole('link', { name: 'Open draft and analyze' })).toBeVisible()
  expect(submitted[0].action).toBe('rejected')
  expect(submitted[1]).toMatchObject({ action: 'edited', text: 'The system shall respond within 3 seconds.', confirm_intent: true, expected_decision_id: 1 })
  await review.screenshot({ path: testInfo.outputPath('suggestion-decision.png') })
  expect(errors).toEqual([])
})
