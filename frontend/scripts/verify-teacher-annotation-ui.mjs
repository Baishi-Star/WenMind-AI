import { chromium } from 'playwright-core'

const baseUrl = 'http://127.0.0.1:5173'
const chromePath = 'C:/Program Files/Google/Chrome/Application/chrome.exe'

const errors = []
const browser = await chromium.launch({ executablePath: chromePath, headless: true })
const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } })
page.on('console', (message) => {
  if (message.type() === 'error') errors.push(message.text())
})
page.on('pageerror', (error) => errors.push(`PAGEERROR ${error.message}`))

try {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle' })
  await page.locator('.role-card').filter({ hasText: '教师' }).click()
  await page.locator('input[placeholder="请输入用户名"]').fill('demo_teacher')
  await page.locator('input[placeholder="请输入密码"]').fill('Demo@2026')
  await page.locator('.login-panel__submit').click()
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 })
  console.log('PASS 教师登录成功')

  await page.goto(`${baseUrl}/teacher/appeals`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  const rows = await page.locator('.el-table__body tr').count()
  console.log(`PASS 申诉列表加载，行数 ${rows}`)
  if (rows === 0) throw new Error('申诉列表为空')

  let found = false
  for (let index = 0; index < rows && !found; index += 1) {
    await page.locator('.el-table__body tr').nth(index).locator('button').filter({ hasText: /复核|查看/ }).first().click()
    await page.waitForSelector('.el-drawer', { timeout: 15000 })
    await page.waitForTimeout(2000)
    const tab = page.locator('.el-tabs__item').filter({ hasText: '图片原文与批注' })
    if ((await tab.count()) === 0) {
      await page.keyboard.press('Escape')
      await page.waitForTimeout(500)
      continue
    }
    await tab.click()
    await page.waitForTimeout(2500)
    const hasViewer = (await page.locator('.essay-viewer').count()) > 0
    if (!hasViewer) {
      console.log('该申诉无图片原文，跳过')
      await page.keyboard.press('Escape')
      await page.waitForTimeout(500)
      continue
    }
    console.log('PASS 打开图片原文与批注 tab')
    const before = await page.locator('.annotation-box').count()

    // 在图片上点击创建批注
    await page.locator('.viewer-image-wrap').first().click({ position: { x: 80, y: 40 } })
    await page.waitForTimeout(2500)
    const after = await page.locator('.annotation-box').count()
    console.log(`批注数量：创建前 ${before}，创建后 ${after}`)
    found = true
  }

  if (!found) throw new Error('未找到可批注的图片申诉')
  console.log('控制台错误数:', errors.length)
  if (errors.length) console.log('错误样例:', errors.slice(0, 3))
} finally {
  await browser.close()
}