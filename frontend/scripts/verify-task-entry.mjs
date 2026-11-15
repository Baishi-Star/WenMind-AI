import { existsSync } from 'node:fs'
import { chromium } from 'playwright-core'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'
const demoPassword = process.env.E2E_DEMO_PASSWORD || 'Demo@2026'
const title = `入口修复验收 ${Date.now()}`
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
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
const consoleErrors = []
const pageErrors = []
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()) })
page.on('pageerror', (e) => pageErrors.push(e.message))

async function login(username, roleLabel) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle' })
  await page.locator('.role-card').filter({ hasText: roleLabel }).click()
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
  await login('demo_teacher', '教师')
  await page.goto(`${baseUrl}/teacher/dashboard`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(700)

  const menuCount = await page.locator('.portal-menu .el-menu-item').count()
  check(menuCount === 7, `教师菜单 7 项（实际 ${menuCount}）`)
  const assignItem = page.locator('.portal-menu .el-menu-item').filter({ hasText: '作文任务' })
  check(await assignItem.count() === 1, '教师菜单含「作文任务」')

  await assignItem.click()
  await page.waitForURL((url) => url.pathname === '/teacher/assignments', { timeout: 15000 })
  check(new URL(page.url()).pathname === '/teacher/assignments', '进入 /teacher/assignments（未被重定向到 reviews）')
  await page.waitForTimeout(900)
  const pageText = await page.locator('body').innerText()
  check(pageText.includes('作文任务'), '页面标题含「作文任务」')
  const createButton = page.locator('button').filter({ hasText: '新建任务' }).first()
  check(await createButton.isVisible(), '页面有「新建任务」按钮')

  await createButton.click()
  const dialog = page.locator('.el-dialog')
  await dialog.waitFor({ state: 'visible', timeout: 10000 })
  check(true, '「新建任务」弹窗已打开')

  const titleItem = page.locator('.el-form-item').filter({ hasText: '任务标题' })
  await titleItem.locator('input').fill(title)
  const promptItem = page.locator('.el-form-item').filter({ hasText: '作文题目 / 材料' })
  await promptItem.locator('textarea').fill('围绕邻里关系写一篇议论文，观点明确。')
  const requirementItem = page.locator('.el-form-item').filter({ hasText: '写作要求' })
  await requirementItem.locator('textarea').fill('不少于 100 字，观点明确。')

  const targetItem = page.locator('.el-form-item').filter({ hasText: '下发范围' })
  await targetItem.locator('.el-select').click()
  await page.waitForTimeout(500)
  const firstOption = page.locator('.el-select-dropdown__item:visible').first()
  await firstOption.click()
  await page.keyboard.press('Escape')
  await page.waitForTimeout(300)

  await page.locator('.el-dialog__footer button').filter({ hasText: '创建草稿' }).click()
  await dialog.waitFor({ state: 'hidden', timeout: 20000 })
  await page.waitForTimeout(1200)
  const listText = await page.locator('body').innerText()
  check(listText.includes(title), '创建后在列表中看到新任务')

  const row = page.locator('tr').filter({ hasText: title }).first()
  const publishButton = row.locator('button').filter({ hasText: '发布' }).first()
  check(await publishButton.isVisible().catch(() => false), '草稿任务行有「发布」按钮')
  await publishButton.click()
  await page.waitForTimeout(600)
  await page.locator('.el-message-box__btns .el-button--primary').click()
  await page.waitForTimeout(1800)
  const rowText = await row.innerText()
  check(rowText.includes('已发布'), '发布后任务状态为「已发布」')

  await logout()

  await login('demo_student', '学生')
  await page.goto(`${baseUrl}/student/dashboard`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(700)
  const studentMenuCount = await page.locator('.portal-menu .el-menu-item').count()
  check(studentMenuCount === 6, `学生菜单 6 项（实际 ${studentMenuCount}）`)
  const taskItem = page.locator('.portal-menu .el-menu-item').filter({ hasText: '写作任务' })
  check(await taskItem.count() === 1, '学生菜单含「写作任务」')
  await taskItem.click()
  await page.waitForURL((url) => url.pathname === '/student/tasks', { timeout: 15000 })
  await page.waitForTimeout(1200)
  const studentText = await page.locator('body').innerText()
  check(studentText.includes(title), '学生「写作任务」页看到教师发布的任务')

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
console.log(`TASK_TITLE=${title}`)
console.log(ok ? 'SUMMARY ALL_PASS' : 'SUMMARY HAS_FAIL')
process.exit(ok ? 0 : 1)