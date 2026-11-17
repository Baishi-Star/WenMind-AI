import { existsSync } from 'node:fs'
import { chromium } from 'playwright-core'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'
const demoPassword = process.env.E2E_DEMO_PASSWORD || 'Demo@2026'
const evaluationId = process.env.EVALUATION_ID || '16'
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
const page = await browser.newPage({ viewport: { width: 1400, height: 950 } })
const consoleErrors = []
const pageErrors = []
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()) })
page.on('pageerror', (e) => pageErrors.push(e.message))

try {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle' })
  await page.locator('.role-card').filter({ hasText: '学生' }).click()
  await page.locator('input[placeholder="请输入用户名"]').fill('demo_student')
  await page.locator('input[placeholder="请输入演示密码"]').fill(demoPassword)
  await page.locator('.login-panel__submit').click()
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 })

  await page.goto(`${baseUrl}/student/evaluations?evaluationId=${evaluationId}`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(1500)
  const bodyText = await page.locator('body').innerText()
  check(bodyText.includes('评价失败'), '显示「评价失败」标题')
  check(bodyText.includes('LLM_AGENT_MAX_TOKENS') || bodyText.includes('截断'), '显示可读失败原因')
  check(bodyText.includes('技术详情（可复制）'), '提供折叠「技术详情（可复制）」')
  check((await page.locator('button').filter({ hasText: '重新执行失败任务' }).count()) > 0, '提供「重新执行失败任务」按钮')
  check(consoleErrors.length === 0, `控制台错误 ${consoleErrors.length}`)
  check(pageErrors.length === 0, `页面异常 ${pageErrors.length}`)
} catch (error) {
  console.log(`FAIL 执行异常：${error.message}`)
  ok = false
} finally {
  await browser.close()
}
console.log(ok ? 'SUMMARY ALL_PASS' : 'SUMMARY HAS_FAIL')
process.exit(ok ? 0 : 1)