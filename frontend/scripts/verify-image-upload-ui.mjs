import { chromium } from 'playwright-core'

const baseUrl = 'http://127.0.0.1:5173'
const chromePath = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const sampleImage = 'D:/1学习/华为开发者大赛/CodeArts Agent/作文/mmexport1794135061713.jpg'

const errors = []
const browser = await chromium.launch({ executablePath: chromePath, headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
const page = await context.newPage()
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

  await page.goto(`${baseUrl}/student/tasks`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1200)
  const cards = await page.locator('.task-card').count()
  console.log(`PASS 任务页加载，任务卡片 ${cards} 个`)
  if (cards === 0) throw new Error('任务页没有可操作任务，无法验证图片上传')

  const uploadButton = page.locator('.task-card__actions button').filter({ hasText: '上传作文照片' }).first()
  await uploadButton.click()
  await page.waitForSelector('.image-uploader', { timeout: 15000 })
  await page.waitForTimeout(1500)
  console.log('PASS 打开图片上传弹窗')

  const fileInput = page.locator('.image-uploader input[type=file]')
  await fileInput.setInputFiles(sampleImage)
  await page.waitForTimeout(4000)

  const thumbs = await page.locator('.thumb').count()
  const imagesLoaded = await page.locator('.thumb__preview img').count()
  console.log(`PASS 上传后缩略图 ${thumbs} 张，其中图片已渲染 ${imagesLoaded} 张`)
  if (thumbs === 0) throw new Error('上传后没有缩略图，上传链路可能失败')

  const bodyText = await page.locator('.image-uploader').innerText()
  console.log('上传器文本包含页数:', bodyText.includes('页'))

  await page.screenshot({ path: 'D:/1学习/华为开发者大赛/CodeArts Agent/backend/data/_verify_image_upload.png' })
  console.log('PASS 已保存截图用于人工核对')

  console.log('控制台错误数:', errors.length)
  if (errors.length) console.log('错误样例:', errors.slice(0, 3))
} finally {
  await browser.close()
}