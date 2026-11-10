import { chromium } from 'playwright-core'

const baseUrl = 'http://127.0.0.1:5173'
const chromePath = 'C:/Program Files/Google/Chrome/Application/chrome.exe'

const errors = []
const browser = await chromium.launch({ executablePath: chromePath, headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
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
  const rows = await page.locator('.el-table__body tr').count()
  console.log(`PASS 作文列表加载，行数 ${rows}`)
  if (rows === 0) throw new Error('作文列表为空，无法验证原文查看')

  // 查找带图片的作文：逐一打开抽屉，直到出现原始图片 tab 或图片元素
  let foundImage = false
  let detailInfo = null
  for (let index = 0; index < rows && !foundImage; index += 1) {
    await page.locator('.el-table__body tr').nth(index).locator('button').filter({ hasText: '查看原文' }).click()
    await page.waitForSelector('.el-drawer', { timeout: 15000 })
    await page.waitForTimeout(2500)
    const viewerCount = await page.locator('.essay-viewer').count()
    const thumbCount = await page.locator('.viewer-thumb').count()
    const imgCount = await page.locator('.viewer-canvas img').count()
    if (viewerCount > 0) {
      foundImage = true
      detailInfo = await page.evaluate(() => {
        const stage = document.querySelector('.viewer-canvas img')
        const active = document.querySelector('.viewer-thumb.is-active .viewer-thumb__label')
        const toolbar = document.querySelector('.viewer-toolbar span')
        const textPre = document.querySelector('.viewer-text pre')
        return {
          imageSrcPrefix: stage ? stage.getAttribute('src').slice(0, 5) : null,
          imageRendered: stage ? stage.complete && stage.naturalWidth > 0 : false,
          imageNaturalWidth: stage ? stage.naturalWidth : 0,
          activePage: active ? active.textContent.trim() : null,
          toolbar: toolbar ? toolbar.textContent.trim() : null,
          hasRecognizedText: Boolean(textPre && textPre.textContent.trim().length > 30),
        }
      })
      console.log(`PASS 找到图片作文（第 ${index + 1} 行）：缩略图 ${thumbCount}，主图 ${imgCount}`)
      console.log('查看器详情:', JSON.stringify(detailInfo, null, 2))
    } else {
      await page.keyboard.press('Escape')
      await page.waitForTimeout(600)
    }
  }

  if (!foundImage) throw new Error('未找到带图片的作文，无法验证图片原文查看')
  if (!detailInfo.imageRendered) throw new Error('主图未渲染')
  if (!detailInfo.hasRecognizedText) console.log('注意：该作文未展示识别文本（可能未识别）')

  await page.screenshot({ path: 'D:/1学习/华为开发者大赛/CodeArts Agent/backend/data/_verify_essay_image_viewer.png' })
  console.log('PASS 已保存截图')
  console.log('控制台错误数:', errors.length)
  if (errors.length) console.log('错误样例:', errors.slice(0, 3))
} finally {
  await browser.close()
}