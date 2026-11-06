import { test, expect } from '@playwright/test'
import { randomUUID } from 'node:crypto'
import path from 'node:path'
import { readFileSync } from 'node:fs'

test('demo sign-in, sample upload, mock analysis, draft comparison and trace CSV', async ({ page }) => {
  test.setTimeout(180000)
  if (!process.env.BROWSER_SRS_PATH) throw new Error('Run through scripts/check_http_local.py --browser')
  const email = `demo-${randomUUID()}@example.com`
  const password = 'demo-browser-password-123'
  const registered = await page.request.post('/api/auth/register', { data: { name: 'Demo reviewer', email, password } })
  expect(registered.ok()).toBeTruthy()
  await page.context().clearCookies()
  await page.goto('/login')
  await page.getByLabel('OPERATOR EMAIL').fill(email)
  await page.getByLabel('PASSWORD', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Authenticate', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Review dashboard' })).toBeVisible()
  await page.getByText('Try a sample review', { exact: true }).click()
  const sample = page.getByRole('link', { name: 'Download the library SRS sample' })
  const sampleResponse = await page.request.get((await sample.getAttribute('href'))!)
  expect(sampleResponse.ok()).toBeTruthy()
  const directory = path.resolve('public/Sample_Requirement')
  expect(await sampleResponse.body()).toEqual(readFileSync(path.join(directory, 'sample-requirements.docx')))
  await page.getByRole('main').getByRole('link', { name: 'New project', exact: true }).click()
  await page.getByLabel('Specification Name').fill('Library demo review')
  await page.getByLabel('What should this review cover?').selectOption('architecture')
  await page.getByRole('checkbox', { name: /Include AI suggestions/ }).check()
  await page.getByRole('button', { name: 'Continue to Document Upload' }).click()
  await page.locator('input[type=file]').setInputFiles(path.join(directory, 'sample-requirements.docx'))
  await page.getByRole('button', { name: 'Continue to UML Diagrams' }).click()
  for (const [label, filename] of [
    ['Use Case Diagram', 'library_usecase.puml'],
    ['Class Diagram', 'library_class.puml'],
    ['Sequence Diagram', 'library_sequence_fixed.puml'],
  ]) {
    await page.getByRole('main').getByRole('combobox').click()
    await page.getByRole('option', { name: label, exact: true }).click()
    await page.getByLabel('PlantUML file').setInputFiles(path.join(directory, filename))
    await page.getByRole('button', { name: 'Add Model', exact: true }).click()
  }
  await page.getByRole('button', { name: 'Review files and scope' }).click()
  await page.getByRole('button', { name: 'Save draft and review extraction' }).click()
  await page.getByRole('button', { name: 'Extract requirements', exact: true }).click()
  await expect(page.getByRole('textbox', { name: 'Requirement text' })).toHaveCount(3)
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Analyze this revision' }).click()
  await expect(page.getByRole('region', { name: 'Quality score' })).toBeVisible()
  const firstRun = new URL(page.url()).searchParams.get('run')!
  const firstReport = await (await page.request.get(`/api/v1/runs/${firstRun}`)).json()
  expect(firstReport.status).toBe('completed')
  await page.getByRole('button', { name: 'Edit a new draft' }).click()
  const requirement = page.locator('form').filter({ has: page.getByRole('heading', { name: 'FR-2', exact: true }) })
  await requirement.getByRole('textbox', { name: 'Requirement text' }).fill('FR-2 The catalog shall respond within 2 seconds.')
  await requirement.getByRole('button', { name: 'Save requirement', exact: true }).click()
  await expect(page.getByRole('checkbox')).toBeEnabled()
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Analyze this revision' }).click()
  await expect(page.getByRole('region', { name: 'Quality score' })).toBeVisible()
  const secondRun = new URL(page.url()).searchParams.get('run')!
  expect(secondRun).not.toBe(firstRun)
  const secondReport = await (await page.request.get(`/api/v1/runs/${secondRun}`)).json()
  expect(secondReport.status).toBe('completed')
  await page.getByRole('button', { name: 'Compare revisions', exact: true }).click()
  await page.getByLabel('Compare the selected report with').selectOption(firstRun)
  await expect(page.getByText('Requirements: 0 added, 1 changed, 0 removed.')).toBeVisible()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Traceability CSV', exact: true }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toMatch(/^traceability_.*\.csv$/)
  const csv = readFileSync((await download.path())!, 'utf8')
  expect(csv.trim().split(/\r?\n/).length).toBeGreaterThan(1)
  expect(csv).toContain('FR-1')
})
