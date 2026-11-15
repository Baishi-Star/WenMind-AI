import { existsSync } from 'node:fs'
import { chromium } from 'playwright-core'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'
const demoPassword = process.env.E2E_DEMO_PASSWORD || 'Demo@2026'
const candidates = [
  process.env.E2E_CHROME,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
].filter((c) => c && existsSync(c))

let ok = true
function check(cond, msg) {
  console.log(`${cond ? 'PASS' : 'FAIL'} ${msg}`)
  if (!cond) ok = false
}

async function launch() {
  for (const executablePath of candidates) {
    try { return await chromium.launch({ executablePath, headless: true }) } catch { /* next */ }
  }
  for (const channel of ['chrome', 'msedge']) {
    try { return await chromium.launch({ channel, headless: true }) } catch { /* next */ }
  }
  throw new Error('未找到可用浏览器')
}

const browser = await launch()
const page = await browser.newPage({ viewport: { width: 1360, height: 900 } })
const consoleErrors = []
const pageErrors = []
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()) })
page.on('pageerror', (e) => pageErrors.push(e.message))

try {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle' })
  await page.locator('.role-card').filter({ hasText: '学生' }).click()
  await page.locator('input[placeholder="请输入用户名"]').fill('demo_student')
  await page.locator('input[placeholder="请输入密码"]').fill(demoPassword)
  await page.locator('.login-panel__submit').click()
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 })

  await page.goto(`${baseUrl}/student/essays/new`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(700)
  const cards = page.locator('.title-card')
  check(await cards.count() === 2, '自由进入显示「作文题目/材料」与「我的作文标题」两卡片')
  const promptCardText = await cards.nth(0).innerText()
  check(promptCardText.includes('自由作文（可自拟标题）'), '自由进入命题区显示「自由作文（可自拟标题）」')
  const titleInput = cards.nth(1).locator('input')
  check((await titleInput.getAttribute('placeholder') || '').includes('学生自拟标题'), '自由进入标题框为可编辑输入')
  check(await titleInput.isEnabled(), '自由进入标题输入框可编辑')

  await page.goto(`${baseUrl}/student/essays/new?task_id=10`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(900)
  const taskPromptText = await cards.nth(0).innerText()
  check(taskPromptText.includes('教师布置'), '任务进入命题区显示「教师布置」标签')
  check(taskPromptText.includes('阅读材料') || taskPromptText.includes('远亲不如近邻'), '任务进入命题区显示任务材料')
  check(taskPromptText.includes('100~4000'), '任务进入显示字数要求')
  const taskTitleInput = cards.nth(1).locator('input')
  check(await taskTitleInput.isEnabled(), '任务进入时「我的作文标题」仍可编辑')

  check(consoleErrors.length === 0, `控制台错误 ${consoleErrors.length}`)
  if (consoleErrors.length) console.log(consoleErrors.slice(0, 6))
  check(pageErrors.length === 0, `页面异常 ${pageErrors.length}`)
  if (pageErrors.length) console.log(pageErrors.slice(0, 6))
} catch (error) {
  console.log(`FAIL 执行异常：${error.message}`)
  ok = false
} finally {
  await browser.close()
}
console.log(ok ? 'SUMMARY ALL_PASS' : 'SUMMARY HAS_FAIL')
process.exit(ok ? 0 : 1)