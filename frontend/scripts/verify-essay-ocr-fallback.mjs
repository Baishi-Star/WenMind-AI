import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const mode = process.env.FALLBACK_MODE || 'disabled'
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
  await page.waitForTimeout(600)
  await page.locator('input.hidden-input').setInputFiles(imagePath)
  await page.waitForSelector('.preview-thumb', { timeout: 30000 })
  await page.waitForTimeout(2500)
  check(true, `[${mode}] 图片上传后预览正常（上传可用）`)

  if (mode === 'disabled') {
    const recognizeCount = await page.locator('button').filter({ hasText: '识别图片文字' }).count()
    check(recognizeCount === 0, '[disabled] 识别按钮已隐藏')
    const bodyText = await page.locator('body').innerText()
    check(bodyText.includes('当前仅支持图片存档'), '[disabled] 显示「当前仅支持图片存档」提示')
    await page.locator('textarea').fill('这是关闭识别后手动录入的作文正文，用于验证仍可正常提交。')
    const submitButton = page.locator('button').filter({ hasText: '提交作文' }).first()
    check(await submitButton.isEnabled(), '[disabled] 手动录入后可提交')
  }

  if (mode === 'failed') {
    await page.locator('button').filter({ hasText: '识别图片文字' }).first().click()
    await page.waitForFunction(() => document.body.innerText.includes('识别失败'), null, { timeout: 120000 })
    check(true, '[failed] 显示识别失败提示')
    const bodyText = await page.locator('body').innerText()
    check(bodyText.includes('改用文本输入'), '[failed] 提供「改用文本输入」入口')
    await page.locator('textarea').fill('识别失败后改用手动录入的正文，应当仍可提交。')
    const submitButton = page.locator('button').filter({ hasText: '提交作文' }).first()
    check(await submitButton.isEnabled(), '[failed] 手动录入后可提交（不阻塞）')
  }
} catch (error) {
  console.log(`FAIL 执行异常：${error.message}`)
  ok = false
} finally {
  await browser.close()
}

check(consoleErrors.length === 0, `控制台错误 ${consoleErrors.length}`)
if (consoleErrors.length) console.log(consoleErrors.slice(0, 5))
check(pageErrors.length === 0, `页面异常 ${pageErrors.length}`)
console.log(ok ? 'SUMMARY ALL_PASS' : 'SUMMARY HAS_FAIL')
process.exit(ok ? 0 : 1)