import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import fs from 'node:fs/promises'
import assert from 'node:assert/strict'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(path.join(root, 'frontend/package.json'))
const { chromium } = require('@playwright/test')
const { expect: baseExpect } = require('@playwright/test')
const expect = baseExpect.configure({ timeout: 30000 })
const origin = 'http://localhost:5174'
const shots = path.join(root, 'demo/screenshots')
await fs.mkdir(shots, { recursive: true })
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ viewport: { width: 1536, height: 864 }, deviceScaleFactor: 1.25 })
const page = await context.newPage()
const errors = []
page.on('pageerror', error => errors.push(error.message))
const screenshot = async name => { await page.screenshot({ path: path.join(shots, `${name}.png`) }); console.log(`Captured ${name}`) }
async function finishRun() {
  await expect(page).toHaveURL(/\?run=/)
  const id = new URL(page.url()).searchParams.get('run')
  await expect.poll(async () => (await (await page.request.get(`${origin}/api/v1/runs/${id}`)).json()).status,
    { timeout: 180000, intervals: [500, 1000] }).toBe('completed')
  await expect(page.getByRole('region', { name: 'Quality score' })).toBeVisible()
  return id
}
let resumedSecond
try {
  await page.goto(`${origin}/login`)
  await page.getByLabel('OPERATOR EMAIL').fill('demo-reviewer@example.com')
  await page.getByLabel('PASSWORD', { exact: true }).fill('Library-demo-only-2026!')
  await page.getByRole('button', { name: 'Authenticate', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Review dashboard' })).toBeVisible()
  if (process.argv.includes('--resume')) {
    const projects = await (await page.request.get(`${origin}/api/projects/`)).json()
    const project = projects.find(p => p.name === 'Library Lending')
    assert(project, 'No previous capture project to resume')
    const runs = (await (await page.request.get(`${origin}/api/v1/projects/${project.id}/runs?limit=100`)).json()).items
    const completed = runs.filter(r => r.status === 'completed')
    const first = completed.at(-1)
    resumedSecond = completed.length > 1 ? completed[0].id : undefined
    assert(first, 'No completed v1 capture report to resume')
    await page.goto(`${origin}/projects/${project.id}?run=${first.id}`)
  } else {
  await page.getByRole('main').getByRole('link', { name: 'New project', exact: true }).click()
  await page.getByLabel('Specification Name').fill('Library Lending')
  await page.getByLabel('What should this review cover?').selectOption('architecture')
  await page.getByRole('checkbox', { name: /Include AI suggestions/ }).check()
  await page.getByRole('button', { name: 'Continue to Document Upload' }).click()
  await page.locator('input[type=file]').setInputFiles(path.join(root, 'demo/library-srs-v1.docx'))
  await page.getByRole('button', { name: 'Continue to UML Diagrams' }).click()
  for (const [label, file] of [['Use Case Diagram', 'library_usecase.puml'], ['Class Diagram', 'library_class.puml'], ['Sequence Diagram', 'library_sequence.puml']]) {
    await page.getByRole('main').getByRole('combobox').click()
    await page.getByRole('option', { name: label, exact: true }).click()
    await page.getByLabel('PlantUML file').setInputFiles(path.join(root, 'demo/diagrams', file))
    await page.getByRole('button', { name: 'Add Model', exact: true }).click()
  }
  await page.getByRole('button', { name: 'Review files and scope' }).click()
  await page.getByRole('button', { name: 'Save draft and review extraction' }).click()
  await page.getByRole('button', { name: 'Extract requirements', exact: true }).click()
  await expect(page.getByRole('textbox', { name: 'Requirement text' })).toHaveCount(9)
  await page.getByRole('heading', { name: 'Review extracted requirements' }).evaluate(element => element.scrollIntoView({ block: 'start' }))
  await screenshot('A-extraction')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Analyze this revision' }).click()
  }
  const first = await finishRun()
  const pid = new URL(page.url()).pathname.split('/').at(-1)
  const firstReport = await (await page.request.get(`${origin}/api/v1/runs/${first}/report`)).json()
  assert(firstReport.findings.some(f => f.rule_id === 'FR-606'))
  await page.getByRole('region', { name: 'Quality score' }).evaluate(element => element.scrollIntoView({ block: 'start' }))
  await screenshot('B-score')
  await page.getByRole('button', { name: /^Findings/ }).click()
  await page.getByRole('textbox', { name: 'Search findings' }).fill('FR-401')
  await expect(page.locator('article[id^="finding-"]')).toHaveCount(1)
  await page.getByRole('button', { name: 'View source for NFR-1', exact: true }).click()
  await page.getByRole('region', { name: 'Source evidence' }).evaluate(element => element.scrollIntoView({ block: 'start' }))
  await expect(page.getByRole('region', { name: 'Source evidence' })).toContainText('respond fast')
  await screenshot('C-ambiguity')
  await page.getByRole('textbox', { name: 'Search findings' }).fill('FR-606')
  await expect(page.locator('article[id^="finding-"]')).toHaveCount(1)
  await expect(page.locator('article[id^="finding-"]')).toContainText('FR-606')
  await page.getByRole('button', { name: 'View source for FR-606', exact: true }).click()
  await page.getByRole('region', { name: 'Source evidence' }).evaluate(element => element.scrollIntoView({ block: 'start' }))
  await expect(page.getByRole('region', { name: 'Source evidence' })).toContainText('isBookAvailable()')
  await screenshot('D-uml-mismatch')
  await page.getByRole('button', { name: /^Traceability Matrix/ }).click()
  await page.getByRole('region', { name: 'Trace matrix scroll area' }).evaluate(element => element.scrollIntoView({ block: 'start' }))
  await screenshot('E-trace-matrix')
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Traceability CSV', exact: true }).click()
  const download = await downloadPromise
  const csv = await fs.readFile(await download.path(), 'utf8')
  assert(csv.startsWith('Run ID,Source Type,Source ID,Target Type,Target ID,'))
  assert(csv.includes(firstReport.trace_links[0].source_id))
  assert.equal(csv.trim().split(/\r?\n/).length, firstReport.trace_links.length + 1)
  await page.getByRole('button', { name: /^Findings/ }).click()
  await page.getByRole('textbox', { name: 'Search findings' }).fill('FR-401')
  await expect(page.locator('article[id^="finding-"]')).toHaveCount(1)
  if (!resumedSecond) {
  const finding = page.locator('article[id^="finding-"]').filter({ hasText: 'FR-401' })
  await finding.getByRole('button', { name: 'Accept finding', exact: true }).click()
  await expect(finding.getByRole('region', { name: 'Finding decision', exact: true })).toContainText('Review: accepted')
  const review = finding.getByRole('region', { name: 'Review rewrite suggestion' })
  if (await review.getByRole('button', { name: 'Reject suggestion', exact: true }).count()) {
  await review.getByRole('button', { name: 'Reject suggestion', exact: true }).click()
  await expect(review).toContainText('Suggestion rejected')
  await review.getByRole('textbox', { name: 'Proposed requirement' }).fill('NFR-1 The Catalog shall respond to search requests within 2 seconds for 20 concurrent users.')
  await review.getByRole('checkbox').check()
  await review.evaluate(element => element.scrollIntoView({ block: 'start' }))
  await screenshot('F-human-review')
  await review.getByRole('button', { name: 'Apply to draft', exact: true }).click()
  }
  await expect(review.getByRole('link', { name: 'Open draft and analyze' })).toBeVisible()
  await page.getByRole('button', { name: 'Edit a new draft', exact: true }).click()
  await page.getByRole('combobox').filter({ has: page.locator('option[value=uml_sequence]') }).selectOption('uml_sequence')
  const replace = page.getByRole('combobox').filter({ has: page.locator('option').filter({ hasText: 'Add a new file' }) })
  const replacementValue = await replace.locator('option').filter({ hasText: 'Replace library_sequence.puml' }).getAttribute('value')
  await replace.selectOption(replacementValue)
  await page.locator('input[type=file]').setInputFiles(path.join(root, 'demo/diagrams/library_sequence_fixed.puml'))
  await page.getByRole('button', { name: 'Save source file', exact: true }).click()
  await page.getByRole('button', { name: 'Extract requirements', exact: true }).click()
  for (const [id, text] of [
    ['FR-5', 'FR-5 The Catalog shall return search catalog titles with identifiers.'],
    ['NFR-1', 'NFR-1 The Catalog shall respond to search requests within 2 seconds for 20 concurrent users.'],
    ['NFR-2', 'NFR-2 The Catalog shall maintain service uptime of 99% per calendar month.'],
  ]) {
    const form = page.locator('form').filter({ has: page.getByRole('heading', { name: id, exact: true }) })
    await form.getByRole('textbox', { name: 'Requirement text' }).fill(text)
    await form.getByRole('button', { name: 'Save requirement', exact: true }).click()
    await expect(page.getByRole('checkbox')).toBeEnabled()
  }
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Analyze this revision', exact: true }).click()
  } else {
    await page.goto(`${origin}/projects/${pid}?run=${resumedSecond}`)
  }
  const second = await finishRun()
  const after = await (await page.request.get(`${origin}/api/v1/runs/${second}/report`)).json()
  assert(!after.findings.some(f => ['FR-401', 'FR-402', 'FR-411', 'FR-606'].includes(f.rule_id)))
  assert(after.findings.length < firstReport.findings.length)
  await page.getByRole('button', { name: 'Compare revisions', exact: true }).click()
  await page.getByLabel('Compare the selected report with').selectOption(first)
  await expect(page.getByText('Requirements: 0 added, 3 changed, 0 removed.')).toBeVisible()
  await page.getByRole('region', { name: 'Architecture impact paths' }).evaluate(element => element.scrollIntoView({ block: 'start' }))
  await expect(page.getByRole('region', { name: 'Architecture impact paths' }).getByRole('listitem').first()).toBeVisible()
  await screenshot('E-impact-paths')
  await page.getByText(/^Resolved Defects \(/).evaluate(element => element.scrollIntoView({ block: 'start' }))
  await screenshot('G-compare-resolved')
  assert.deepEqual(errors, [])
  await fs.writeFile(path.join(shots, 'capture.json'), JSON.stringify({ project_id: pid, first, second, before: firstReport.findings.length, after: after.findings.length, width: 1920, height: 1080 }, null, 2))
  console.log('Verified clips A-G through the real localhost UI and API; all screenshots are 1920x1080.')
} catch (error) {
  await page.screenshot({ path: path.join(shots, 'capture-failure.png') })
  await fs.writeFile(path.join(shots, 'capture-failure.txt'), await page.locator('body').innerText())
  throw error
} finally {
  await browser.close()
}


