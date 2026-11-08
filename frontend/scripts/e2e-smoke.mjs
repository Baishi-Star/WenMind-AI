import { existsSync } from 'node:fs'
import { chromium } from 'playwright-core'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'
const demoPassword = process.env.E2E_DEMO_PASSWORD || 'Demo@2026'
const browserCandidates = [
  process.env.E2E_CHROME,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
].filter((candidate) => candidate && existsSync(candidate))

const routes = {
  public: ['/', '/login', '/system/status'],
  student: [
    '/student/dashboard',
    '/student/essays',
    '/student/essays/new',
    '/student/evaluations',
    '/student/revision',
    '/student/appeals',
    '/student/growth',
    '/student/training',
  ],
  teacher: [
    '/teacher/dashboard',
    '/teacher/classes',
    '/teacher/assignments',
    '/teacher/reviews',
    '/teacher/appeals',
    '/teacher/analytics',
    '/teacher/students/1/growth',
    '/teacher/disputes',
    '/teacher/rubrics',
  ],
  admin: ['/admin/dashboard', '/admin/knowledge', '/admin/agents', '/admin/model', '/admin/prompts', '/admin/logs'],
}

const consoleErrors = []
const pageErrors = []
const httpErrors = []
const blankPages = []
const routeResults = []

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
page.on('response', (response) => {
  if (response.status() >= 400) httpErrors.push({ url: response.url(), status: response.status() })
})

async function openRoute(path) {
  const response = await page.goto(`${baseUrl}${path}`, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForTimeout(900)
  const text = (await page.locator('body').innerText()).trim()
  const result = { path, status: response?.status() ?? null, textLength: text.length, url: page.url() }
  routeResults.push(result)
  if (text.length < 40) blankPages.push(result)
  return result
}

async function login(username, roleLabel) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle' })
  if (roleLabel) {
    await page.locator('.role-card').filter({ hasText: roleLabel }).click()
  }
  await page.locator('input[placeholder="请输入用户名"]').fill(username)
  await page.locator('input[placeholder="请输入密码"]').fill(demoPassword)
  await page.locator('.login-panel__submit').click()
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 })
  await page.waitForTimeout(700)
}

async function logout() {
  await page.locator('.user-entry').click()
  await page.locator('.el-dropdown-menu__item').filter({ hasText: '退出登录' }).click()
  await page.locator('.el-message-box__btns button').filter({ hasText: '退出登录' }).click()
  await page.waitForURL((url) => url.pathname === '/login', { timeout: 20000 })
}

try {
  await page.goto(`${baseUrl}/student/dashboard`, { waitUntil: 'domcontentloaded' })
  await page.waitForURL((url) => url.pathname === '/login', { timeout: 15000 })
  console.log('PASS 未登录路由守卫跳转 /login')

  for (const path of routes.public) await openRoute(path)

  await login('demo_student', '学生')
  for (const path of routes.student) await openRoute(path)
  await openRoute('/student/growth')
  await page.waitForTimeout(1200)
  const growthCanvas = await page.locator('canvas').count()
  if (growthCanvas === 0) throw new Error('成长页面未渲染 ECharts canvas')
  console.log(`PASS 学生页面与图表 canvas=${growthCanvas}`)
  await logout()
  console.log('PASS 学生退出登录并清理会话')

  await login('demo_teacher', '教师')
  for (const path of routes.teacher) await openRoute(path)
  await openRoute('/teacher/students/1/growth')
  await page.waitForTimeout(1200)
  if ((await page.locator('canvas').count()) === 0) throw new Error('教师学生成长详情未渲染 ECharts canvas')
  console.log('PASS 教师页面与学生成长详情图表')
  await logout()

  await login('demo_admin', '管理员')
  for (const path of routes.admin) await openRoute(path)
  console.log('PASS 管理员页面')
  await logout()

  console.log('ROUTES', JSON.stringify(routeResults, null, 2))
  console.log('CONSOLE_ERRORS', JSON.stringify(consoleErrors, null, 2))
  console.log('PAGE_ERRORS', JSON.stringify(pageErrors, null, 2))
  console.log('HTTP_ERRORS', JSON.stringify(httpErrors, null, 2))
  console.log('BLANK_PAGES', JSON.stringify(blankPages, null, 2))

  const failed = consoleErrors.length + pageErrors.length + blankPages.length
  console.log(`SUMMARY routes=${routeResults.length} consoleErrors=${consoleErrors.length} pageErrors=${pageErrors.length} http4xx5xx=${httpErrors.length} blank=${blankPages.length}`)
  if (failed > 0) process.exitCode = 1
} finally {
  await browser.close()
}