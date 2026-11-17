import { existsSync } from 'node:fs'
import { chromium } from 'playwright-core'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'
const demoPassword = process.env.E2E_DEMO_PASSWORD || 'Demo@2026'
const mode = process.env.DEMO_MODE || 'enabled'
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

async function logout() {
  await page.locator('.user-entry').click()
  await page.locator('.el-dropdown-menu__item').filter({ hasText: '退出登录' }).click()
  await page.locator('.el-message-box__btns button').filter({ hasText: '退出登录' }).click()
  await page.waitForURL((url) => url.pathname === '/login', { timeout: 20000 })
  await page.waitForTimeout(500)
}

try {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1000)
  const bodyText = await page.locator('body').innerText()
  check(!bodyText.includes('Demo@2026'), '登录页无明文演示密码')
  check((await page.locator('input[type="password"]').inputValue().catch(() => '')) === '', '密码输入框默认值为空')

  if (mode === 'enabled') {
    check((await page.locator('.role-card__badge').filter({ hasText: '一键进入' }).count()) === 3, '三个角色卡片均显示「一键进入」')

    await page.locator('.role-card').filter({ hasText: '教师' }).click()
    await page.waitForURL((url) => url.pathname === '/teacher/dashboard', { timeout: 20000 })
    check(true, '点击教师卡片直接进入教师工作台（无需密码）')

    await logout()
    await page.locator('.role-card').filter({ hasText: '学生' }).click()
    await page.waitForURL((url) => url.pathname === '/student/dashboard', { timeout: 20000 })
    check(true, '点击学生卡片直接进入学生首页')

    await logout()
    await page.locator('input[placeholder="请输入用户名"]').fill('demo_admin')
    await page.locator('input[placeholder="请输入演示密码"]').fill(demoPassword)
    await page.locator('.login-panel__submit').click()
    await page.waitForURL((url) => url.pathname === '/admin/dashboard', { timeout: 20000 })
    check(true, '手动账号密码登录仍可用')
  } else {
    check((await page.locator('.role-card__badge').count()) === 0, '关闭时角色卡片不显示「一键进入」')
    await page.locator('.role-card').filter({ hasText: '学生' }).click()
    await page.waitForTimeout(1200)
    const messages = await page.locator('.el-message').allInnerTexts()
    check(messages.some((text) => text.includes('演示登录已关闭')), '关闭时点击卡片提示「演示登录已关闭」')
    check(new URL(page.url()).pathname === '/login', '关闭时点击卡片不跳转（停留在登录页）')
  }

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