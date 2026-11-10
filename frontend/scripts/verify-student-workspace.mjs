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
  if (message.type() === 'error') consoleErrors.push(message.text())
})
page.on('pageerror', (error) => pageErrors.push(error.message))

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
  await page.waitForTimeout(400)
}

try {
  await login('demo_student', '学生')
  await page.goto(`${baseUrl}/student/dashboard`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(1500)
  const studentText = (await page.locator('body').innerText()).trim()

  for (const word of ['界面' + '框架', '待' + '接入', '规划' + '中', '框架' + '阶段', '业务数据待' + '后端接入']) {
    check(!studentText.includes(word), `学生首页不含「${word}」`)
  }
  for (const word of ['待评价作文', '最近一次诊断', '待处理申诉', '训练进度', '提交新作文', '最近作文', '核心业务闭环']) {
    check(studentText.includes(word), `学生首页含「${word}」`)
  }

  const cards = await page.locator('.stat-card').allInnerTexts()
  check(cards.length === 4, `四张数据卡渲染（实际 ${cards.length}）`)
  cards.forEach((card, index) => {
    console.log(`  卡片${index + 1}: ${card.replace(/\s+/g, ' ').trim()}`)
    check(!card.includes('加载中'), `卡片${index + 1} 已完成加载`)
  })

  const recentCount = await page.locator('.recent-list li').count()
  console.log(`  最近作文条目: ${recentCount}`)
  check(recentCount <= 3, `最近作文不超过 3 条（实际 ${recentCount}）`)

  const submitButton = page.locator('button').filter({ hasText: '提交新作文' }).first()
  check(await submitButton.isVisible().catch(() => false), '主按钮「提交新作文」可见')

  await logout()

  await login('demo_teacher', '教师')
  await page.goto(`${baseUrl}/teacher/dashboard`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(500)
  const teacherText = (await page.locator('body').innerText()).trim()
  check(teacherText.includes('功能导航'), '教师首页保留原有「功能导航」')
  check(teacherText.includes('数据接入状态'), '教师首页保留原有「数据接入状态」')
  check(!teacherText.includes('待评价作文'), '教师首页未混入学生看板')
  await logout()

  await login('demo_admin', '管理员')
  await page.goto(`${baseUrl}/admin/dashboard`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(500)
  const adminText = (await page.locator('body').innerText()).trim()
  check(adminText.includes('功能导航'), '管理端首页保留原有「功能导航」')
  check(adminText.includes('数据接入状态'), '管理端首页保留原有「数据接入状态」')
} catch (error) {
  console.log(`FAIL 执行异常：${error.message}`)
  ok = false
} finally {
  await browser.close()
}

check(consoleErrors.length === 0, `控制台错误 ${consoleErrors.length}`)
if (consoleErrors.length) console.log(consoleErrors.slice(0, 5))
check(pageErrors.length === 0, `页面异常 ${pageErrors.length}`)
if (pageErrors.length) console.log(pageErrors.slice(0, 5))
console.log(ok ? 'SUMMARY ALL_PASS' : 'SUMMARY HAS_FAIL')
process.exit(ok ? 0 : 1)