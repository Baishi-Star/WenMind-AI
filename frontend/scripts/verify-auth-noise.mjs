import { existsSync } from 'node:fs'
import { chromium } from 'playwright-core'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'
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
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
const requests = []
const statuses = []
const consoleErrors = []
page.on('request', (r) => { if (r.url().includes('/api/v1/')) requests.push(`${r.method()} ${new URL(r.url()).pathname}`) })
page.on('response', (r) => { if (r.url().includes('/api/v1/')) statuses.push(r.status()) })
page.on('console', (m) => { if (m.type() === 'error' && !m.text().includes('401') && !m.text().includes('Failed to load resource')) consoleErrors.push(m.text()) })

const businessPaths = ['/essays', '/evaluations', '/appeals', '/training/tasks']

try {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle' })
  await page.evaluate(() => localStorage.clear())
  requests.length = 0
  statuses.length = 0

  await page.goto(`${baseUrl}/student/dashboard`, { waitUntil: 'networkidle' })
  await page.waitForURL((url) => url.pathname === '/login', { timeout: 15000 })
  const businessCalls = requests.filter((item) => businessPaths.some((p) => item.includes(p)))
  check(businessCalls.length === 0, `未登录直访不发业务请求（实际 ${businessCalls.length}）`)

  await page.evaluate(() => {
    localStorage.setItem('wenmind_token', 'invalid-token-for-test')
    localStorage.setItem('wenmind_auth_session', JSON.stringify({ user: { role: 'student', display_name: '测试学生', is_demo: true } }))
  })
  requests.length = 0
  statuses.length = 0
  await page.goto(`${baseUrl}/student/dashboard`, { waitUntil: 'networkidle' })
  await page.waitForURL((url) => url.pathname === '/login', { timeout: 15000 })
  await page.waitForTimeout(800)
  const unauthorized = statuses.filter((code) => code === 401).length
  check(unauthorized === 1, `无效 token 仅产生 1 次 401（实际 ${unauthorized}）`)
  const toasts = await page.locator('.el-message').count()
  check(toasts === 0, `无效 token 不产生重复错误弹窗（实际 ${toasts}）`)
  check(consoleErrors.length === 0, `除预期 401 外无控制台错误（实际 ${consoleErrors.length}）`)
} catch (error) {
  console.log(`FAIL 执行异常：${error.message}`)
  ok = false
} finally {
  await browser.close()
}
console.log(ok ? 'SUMMARY ALL_PASS' : 'SUMMARY HAS_FAIL')
process.exit(ok ? 0 : 1)