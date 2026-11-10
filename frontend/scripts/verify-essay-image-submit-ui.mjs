import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'
const demoPassword = process.env.E2E_DEMO_PASSWORD || 'Demo@2026'
const imagePath = fileURLToPath(new URL('../../作文/mmexport1794135091178.jpg', import.meta.url))
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
      // 尝试下一个浏览器
    }
  }
  for (const channel of ['chrome', 'msedge']) {
    try {
      return await chromium.launch({ channel, headless: true })
    } catch {
      // 尝试 Playwright 通道
    }
  }
  throw new Error('未找到可用 Chrome/Edge')
}

const browser = await launchBrowser()
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
const page = await context.newPage()
page.on('console', (message) => {
  if (message.type() === 'error') consoleErrors.push(message.text())
})
page.on('pageerror', (error) => pageErrors.push(error.message))

try {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle' })
  await page.locator('.role-card').filter({ hasText: '学生' }).click()
  await page.locator('input[placeholder="请输入用户名"]').fill('demo_student')
  await page.locator('input[placeholder="请输入密码"]').fill(demoPassword)
  await page.locator('.login-panel__submit').click()
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 })

  await page.goto(`${baseUrl}/student/essays/new`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(800)

  const activeTab = (await page.locator('.el-tabs__item.is-active').innerText()).trim()
  check(activeTab.includes('拍照上传'), `默认选中「拍照上传」（实际：${activeTab}）`)
  check(await page.locator('.desktop-upload').isVisible(), '桌面宽度下拖拽上传区可见')

  await page.setViewportSize({ width: 375, height: 820 })
  await page.waitForTimeout(400)
  check(await page.locator('.mobile-capture').isVisible(), '移动宽度下「拍照 / 选择图片」按钮可见')
  check(!(await page.locator('.desktop-upload').isVisible()), '移动宽度下拖拽上传区隐藏')
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.waitForTimeout(300)

  await page.locator('input.hidden-input').setInputFiles(imagePath)
  await page.waitForSelector('.preview-thumb', { timeout: 30000 })
  check(true, '选择图片后出现本地预览缩略图')
  await page.waitForTimeout(2500)

  const recognizeButton = page.locator('button').filter({ hasText: '识别图片文字' }).first()
  check(await recognizeButton.isVisible().catch(() => false), '上传完成后出现「识别图片文字」按钮')
  await recognizeButton.click()
  await page.waitForFunction(() => {
    const textarea = document.querySelector('textarea')
    return textarea && textarea.value.trim().length > 20
  }, null, { timeout: 190000 })
  const recognized = await page.locator('textarea').inputValue()
  check(recognized.trim().length > 20, `识别文本已填入正文且可编辑（${recognized.trim().length} 字）`)

  const submitButton = page.locator('button').filter({ hasText: '提交作文' }).first()
  check(await submitButton.isEnabled(), '正文字数大于 0 时提交按钮可用')
  await submitButton.click()
  await page.waitForURL((url) => url.pathname.includes('/student/evaluations'), { timeout: 30000 })
  check(true, '提交成功后跳转评价结果页')
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