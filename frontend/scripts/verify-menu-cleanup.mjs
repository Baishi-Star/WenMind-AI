import { existsSync } from 'node:fs'
import { chromium } from 'playwright-core'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'
const demoPassword = process.env.E2E_DEMO_PASSWORD || 'Demo@2026'
const browserCandidates = [
  process.env.E2E_CHROME,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
].filter((candidate) => candidate && existsSync(candidate))

const consoleErrors = []
const pageErrors = []
let ok = true

function check(condition, message) {
  console.log(`${condition ? 'PASS' : 'FAIL'} ${message}`)
  if (!condition) ok = false
}

async function launchBrowser() {
  for (const executablePath of browserCandidates) {
    try {
      return await chromium.launch({ executablePath, headless: true })
    } catch {
      // 尝试下一个本机浏览器
    }
  }
  for (const channel of ['chrome', 'msedge']) {
    try {
      return await chromium.launch({ channel, headless: true })
    } catch {
      // 尝试 Playwright 浏览器通道
    }
  }
  throw new Error('未找到可用 Chrome/Edge；请设置 E2E_CHROME')
}

const browser = await launchBrowser()
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
const page = await context.newPage()

page.on('console', (message) => {
  if (message.type() === 'error') consoleErrors.push({ url: page.url(), text: message.text() })
})
page.on('pageerror', (error) => pageErrors.push({ url: page.url(), text: error.message }))

async function login(username, roleLabel) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle' })
  if (roleLabel) {
    await page.locator('.role-card').filter({ hasText: roleLabel }).click()
  }
  await page.locator('input[placeholder="请输入用户名"]').fill(username)
  await page.locator('input[placeholder="请输入密码"]').fill(demoPassword)
  await page.locator('.login-panel__submit').click()
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 })
  await page.waitForTimeout(500)
}

async function logout() {
  await page.locator('.user-entry').click()
  await page.locator('.el-dropdown-menu__item').filter({ hasText: '退出登录' }).click()
  await page.locator('.el-message-box__btns button').filter({ hasText: '退出登录' }).click()
  await page.waitForURL((url) => url.pathname === '/login', { timeout: 20000 })
  await page.waitForTimeout(300)
}

async function checkRole(role, username, roleLabel, expectedMenu, deletedRoutes) {
  await login(username, roleLabel)
  await page.goto(`${baseUrl}/${role}/dashboard`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(800)

  const dashboardText = (await page.locator('body').innerText()).trim()
  for (const word of ['界面' + '框架', '待' + '接入', '规划' + '中', 'API ' + '契约']) {
    check(!dashboardText.includes(word), `${roleLabel}首页不含「${word}」`)
  }

  const items = page.locator('.portal-menu .el-menu-item')
  const count = await items.count()
  check(count === expectedMenu, `${roleLabel}左侧菜单 ${count} 项（期望 ${expectedMenu}）`)

  for (let index = 0; index < count; index += 1) {
    const name = (await items.nth(index).innerText()).trim().split('\n')[0]
    await items.nth(index).click()
    await page.waitForTimeout(700)
    const currentUrl = new URL(page.url())
    const bodyText = (await page.locator('body').innerText()).trim()
    check(
      currentUrl.pathname.startsWith(`/${role}`) && bodyText.length > 40,
      `${roleLabel}「${name}」→ ${currentUrl.pathname} 正常打开`,
    )
    if (role === 'student' && name === '我的作文') {
      const submitButton = page.locator('button').filter({ hasText: '提交新作文' }).first()
      check(await submitButton.isVisible().catch(() => false), '「我的作文」页有「提交新作文」按钮')
      await submitButton.click()
      await page.waitForTimeout(700)
      check(new URL(page.url()).pathname === '/student/essays/new', '「提交新作文」跳转到 /student/essays/new')
    }
    if (role === 'student' && name === '成长档案') {
      check(bodyText.includes('训练'), '「成长档案」页包含个性化训练区块')
    }
  }

  for (const [from, to] of deletedRoutes) {
    await page.goto(`${baseUrl}${from}`, { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(600)
    check(new URL(page.url()).pathname === to, `${from} 自动重定向到 ${to}`)
  }

  await logout()
}

try {
  await checkRole(
    'student',
    'demo_student',
    '学生',
    5,
    [
      ['/student/tasks', '/student/essays'],
      ['/student/revision', '/student/evaluations'],
      ['/student/training', '/student/growth'],
    ],
  )
  await checkRole(
    'teacher',
    'demo_teacher',
    '教师',
    6,
    [
      ['/teacher/classes', '/teacher/dashboard'],
      ['/teacher/assignments', '/teacher/reviews'],
    ],
  )
  await checkRole(
    'admin',
    'demo_admin',
    '管理员',
    3,
    [
      ['/admin/model', '/admin/dashboard'],
      ['/admin/prompts', '/admin/dashboard'],
      ['/admin/logs', '/admin/dashboard'],
    ],
  )
} catch (error) {
  console.log(`FAIL 执行异常：${error.message}`)
  ok = false
} finally {
  await browser.close()
}

check(consoleErrors.length === 0, `控制台错误 ${consoleErrors.length}`)
if (consoleErrors.length) console.log(consoleErrors.slice(0, 6))
check(pageErrors.length === 0, `页面异常 ${pageErrors.length}`)
if (pageErrors.length) console.log(pageErrors.slice(0, 6))
console.log(ok ? 'SUMMARY ALL_PASS' : 'SUMMARY HAS_FAIL')
process.exit(ok ? 0 : 1)