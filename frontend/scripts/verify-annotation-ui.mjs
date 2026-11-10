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
  await page.locator('.role-card').filter({ hasText: '学生' }).click()
  await page.locator('input[placeholder="请输入用户名"]').fill('demo_student')
  await page.locator('input[placeholder="请输入密码"]').fill('Demo@2026')
  await page.locator('.login-panel__submit').click()
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 })
  console.log('PASS 学生登录成功')

  await page.goto(`${baseUrl}/student/essays`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)

  // 逐行打开抽屉，找到带图片且带标注的作文
  const rows = await page.locator('.el-table__body tr').count()
  let verified = false
  for (let index = 0; index < rows && !verified; index += 1) {
    const rowText = await page.locator('.el-table__body tr').nth(index).innerText()
    const essayIdMatch = rowText.match(/#?(\d+)/)
    await page.locator('.el-table__body tr').nth(index).locator('button').filter({ hasText: '查看原文' }).click()
    await page.waitForSelector('.el-drawer', { timeout: 15000 })
    await page.waitForTimeout(2200)
    const hasViewer = (await page.locator('.essay-viewer').count()) > 0
    const switchCount = await page.locator('.viewer-meta .el-switch').count()
    if (hasViewer && switchCount > 0) {
      const annText = await page.locator('.viewer-hint').innerText()
      console.log(`PASS 打开图片作文（第 ${index + 1} 行${essayIdMatch ? ` #${essayIdMatch[1]}` : ''}）：${annText}`)
      if (annText.includes('暂无标注')) {
        await page.keyboard.press('Escape')
        await page.waitForTimeout(500)
        continue
      }
      // 打开标注开关
      await page.locator('.viewer-meta .el-switch').click()
      await page.waitForTimeout(800)
      const boxes = await page.locator('.annotation-box').count()
      const boxInfo = await page.evaluate(() => {
        const box = document.querySelector('.annotation-box')
        if (!box) return null
        const style = getComputedStyle(box)
        return {
          left: style.left,
          top: style.top,
          width: style.width,
          height: style.height,
          borderStyle: style.borderStyle,
          className: box.className,
        }
      })
      console.log(`PASS 标注框渲染数量 ${boxes}`)
      console.log('标注框样式:', JSON.stringify(boxInfo))
      if (boxes === 0) throw new Error('标注开关打开后未渲染标注框')
      verified = true
    } else {
      await page.keyboard.press('Escape')
      await page.waitForTimeout(500)
    }
  }

  if (!verified) throw new Error('未找到带标注的图片作文')
  await page.screenshot({ path: 'D:/1学习/华为开发者大赛/CodeArts Agent/backend/data/_verify_annotation.png' })
  console.log('PASS 已保存截图')
  console.log('控制台错误数:', errors.length)
  if (errors.length) console.log('错误样例:', errors.slice(0, 3))
} finally {
  await browser.close()
}