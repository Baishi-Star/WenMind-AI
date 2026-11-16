import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'
const demoPassword = process.env.E2E_DEMO_PASSWORD || 'Demo@2026'
const imagePath = fileURLToPath(new URL('../../作文/mmexport1794135091178.jpg', import.meta.url))
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

try {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle' })
  await page.locator('.role-card').filter({ hasText: '学生' }).click()
  await page.locator('input[placeholder="请输入用户名"]').fill('demo_student')
  await page.locator('input[placeholder="请输入演示密码"]').fill(demoPassword)
  await page.locator('.login-panel__submit').click()
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 })

  await page.goto(`${baseUrl}/student/tasks`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(1000)

  const cards = page.locator('.task-card')
  const count = await cards.count()
  let targetIndex = -1
  for (let index = 0; index < count; index += 1) {
    const text = await cards.nth(index).innerText()
    const button = cards.nth(index).locator('button', { hasText: '上传作文照片' })
    if (!text.includes('我的提交：') && (await button.isEnabled())) {
      targetIndex = index
      break
    }
  }
  check(targetIndex >= 0, `存在未提交且可用的「上传作文照片」入口（${count} 个任务）`)
  if (targetIndex < 0) throw new Error('没有可用的图片提交任务')

  const card = cards.nth(targetIndex)
  const taskTitle = (await card.locator('h2').innerText()).trim()
  await card.locator('button', { hasText: '上传作文照片' }).click()
  await page.waitForSelector('.image-uploader', { timeout: 15000 })
  check(true, `图片弹窗已打开（任务：${taskTitle}）`)

  const nextButton = page.locator('.el-dialog__footer button').filter({ hasText: '下一步：识别文字' })
  check(await nextButton.isDisabled(), '未上传时「下一步：识别文字」置灰')

  await page.locator('.image-uploader input[type="file"]').setInputFiles(imagePath)
  await page.waitForSelector('.thumb-list .thumb', { timeout: 30000 })
  await page.waitForTimeout(1500)
  check(await nextButton.isEnabled(), '上传后可点「下一步：识别文字」')

  const mode = process.env.IMAGE_FLOW_MODE || 'normal'
  await nextButton.click()
  await page.waitForTimeout(1200)
  if (mode === 'failed') {
    const manualButton = page.locator('.el-dialog__footer button').filter({ hasText: '手动录入' })
    await manualButton.waitFor({ state: 'visible', timeout: 60000 })
    check(true, '识别失败时显示失败提示与「手动录入」降级入口')
    await manualButton.click()
    await page.waitForSelector('.page-card textarea', { timeout: 20000 })
    check(await page.locator('.page-card').count() >= 1, '手动录入进入逐页校对')
  } else {
    const loadingText = await page.locator('.el-dialog__footer').innerText()
    check(loadingText.includes('正在识别') || (await page.locator('.page-card').count()) > 0, '识别阶段出现 loading 或结果')
    await page.waitForSelector('.page-card textarea', { timeout: 240000 })
    check(await page.locator('.page-card').count() >= 1, '识别完成出现逐页校对卡片')
  }
  const textarea = page.locator('.page-card textarea').first()
  const recognized = (await textarea.inputValue()).trim()
  if (mode === 'failed') {
    await textarea.fill('识别失败后手动录入的校对文本，用于验证降级路径。')
    check((await textarea.inputValue()).trim().length > 0, '识别失败后可手动填写并继续')
  } else {
    check(recognized.length > 20, `识别文本已填入且可编辑（${recognized.length} 字）`)
    await textarea.fill(`${recognized}\n（已人工校对）`)
  }
  await page.locator('.el-dialog__footer button').filter({ hasText: '下一步：确认' }).click()
  await page.waitForTimeout(600)
  const summary = await page.locator('.confirm-summary').innerText()
  check(summary.includes('页') && summary.includes('合计'), `确认摘要显示页数与字数：${summary.replace(/\s+/g, ' ')}`)

  await page.locator('.el-dialog__footer button').filter({ hasText: '确认并提交' }).click()
  await page.waitForTimeout(3500)
  const bodyText = await page.locator('body').innerText()
  check(bodyText.includes('我的提交：'), '提交后任务列表出现「我的提交」状态')
  check(
    bodyText.includes('评价中') || bodyText.includes('已提交'),
    '提交后状态为「已提交 / 评价中」',
  )
  await page.waitForTimeout(1500)
  const unexpectedErrors = mode === 'failed'
    ? consoleErrors.filter((text) => !text.includes('400'))
    : consoleErrors
  check(unexpectedErrors.length === 0, `非预期控制台错误 ${unexpectedErrors.length}`)
  if (unexpectedErrors.length) console.log(unexpectedErrors.slice(0, 5))
  check(pageErrors.length === 0, `页面异常 ${pageErrors.length}`)
  if (pageErrors.length) console.log(pageErrors.slice(0, 5))
  console.log(`TASK_TITLE=${taskTitle}`)
} catch (error) {
  console.log(`FAIL 执行异常：${error.message}`)
  ok = false
} finally {
  await browser.close()
}
console.log(ok ? 'SUMMARY ALL_PASS' : 'SUMMARY HAS_FAIL')
process.exit(ok ? 0 : 1)