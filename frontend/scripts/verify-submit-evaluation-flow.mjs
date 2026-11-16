import { existsSync } from 'node:fs'
import { chromium } from 'playwright-core'

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'
const demoPassword = process.env.E2E_DEMO_PASSWORD || 'Demo@2026'
const failedEvaluationId = process.env.FAILED_EVALUATION_ID || '10'
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
  let card = null
  let wordRange = null
  for (let index = 0; index < count; index += 1) {
    const text = await cards.nth(index).innerText()
    const hasAction = (await cards.nth(index).locator('button', { hasText: '在线作答' }).count()) > 0
    if (!text.includes('我的提交：') && hasAction) {
      card = cards.nth(index)
      const match = text.match(/(\d+)\s*~\s*(\d+|不限)\s*字/)
      wordRange = match ? { min: Number(match[1]), max: match[2] === '不限' ? Infinity : Number(match[2]) } : null
      break
    }
  }
  check(Boolean(card), `存在未提交且可作答的任务（${count} 个）`)
  if (!card) throw new Error('没有可提交的任务')

  const taskTitle = (await card.locator('h2').innerText()).trim()
  await card.locator('button', { hasText: '在线作答' }).click()
  await page.waitForSelector('.el-dialog textarea', { timeout: 15000 })
  const targetLength = wordRange
    ? Math.min(wordRange.max, Math.max(wordRange.min + 50, 600))
    : 800
  const longText = '这是用于验收提交后评价跳转与进度展示的测试作文正文，内容用于满足字数要求并验证评价链路。'.repeat(300).slice(0, targetLength)
  const textareas = page.locator('.el-dialog textarea')
  const textareaCount = await textareas.count()
  for (let index = 0; index < textareaCount; index += 1) {
    await textareas.nth(index).fill(longText)
  }
  await page.locator('.el-dialog__footer button').filter({ hasText: '提交并开始评价' }).click()

  await page.waitForURL(
    (url) => url.pathname === '/student/evaluations' && Boolean(url.searchParams.get('evaluationId')),
    { timeout: 30000 },
  )
  const evaluationId = new URL(page.url()).searchParams.get('evaluationId')
  check(Boolean(evaluationId), `提交后自动跳转评价详情（evaluationId=${evaluationId}）`)

  await page.waitForTimeout(2500)
  const hasProgress = (await page.locator('.progress-card').count()) > 0
  const hasFailure = (await page.locator('.el-alert').filter({ hasText: '评价失败' }).count()) > 0
  const hasReport = (await page.locator('.el-alert').filter({ hasText: '评分维度' }).count()) > 0
  check(hasProgress || hasFailure || hasReport, `跳转后显示进度态/失败态/报告（progress=${hasProgress}, failed=${hasFailure}）`)

  let pollCount = 0
  page.on('request', (request) => {
    if (request.method() === 'GET' && request.url().includes(`/evaluations/${evaluationId}`)) pollCount += 1
  })
  await page.waitForTimeout(6000)
  const beforeLeave = pollCount
  await page.goto(`${baseUrl}/student/dashboard`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(6000)
  check(pollCount === beforeLeave, `离开页面后停止轮询（${beforeLeave} → ${pollCount}）`)

  await page.goto(`${baseUrl}/student/essays`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(1200)
  check((await page.locator('th').filter({ hasText: '最近评价等级' }).count()) > 0, '「我的作文」含最近评价等级列')
  const essayRows = await page.locator('.el-table__body tr').count()
  check(essayRows > 0, `「我的作文」显示记录（${essayRows} 行）`)
  const essayBody = await page.locator('body').innerText()
  check(
    ['评价中', '评价完成', '已提交'].some((word) => essayBody.includes(word)),
    '「我的作文」出现刚提交作文的评价状态',
  )

  await page.goto(`${baseUrl}/student/tasks`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(1200)
  const submittedCard = page.locator('.task-card').filter({ hasText: taskTitle }).first()
  check((await submittedCard.innerText()).includes('我的提交：'), '写作任务卡片显示「我的提交」状态')

  await page.goto(`${baseUrl}/student/evaluations?evaluationId=${failedEvaluationId}`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(1500)
  check(
    (await page.locator('.el-alert').filter({ hasText: '评价失败' }).count()) > 0,
    `失败评价 #${failedEvaluationId} 显示失败态`,
  )
  check(
    (await page.locator('button').filter({ hasText: '重新执行失败任务' }).count()) > 0,
    '失败态提供「重新执行失败任务」按钮',
  )

  check(consoleErrors.length === 0, `控制台错误 ${consoleErrors.length}`)
  if (consoleErrors.length) console.log(consoleErrors.slice(0, 5))
  check(pageErrors.length === 0, `页面异常 ${pageErrors.length}`)
  if (pageErrors.length) console.log(pageErrors.slice(0, 5))
  console.log(`TASK_TITLE=${taskTitle} EVAL_ID=${evaluationId}`)
} catch (error) {
  console.log(`FAIL 执行异常：${error.message}`)
  ok = false
} finally {
  await browser.close()
}
console.log(ok ? 'SUMMARY ALL_PASS' : 'SUMMARY HAS_FAIL')
process.exit(ok ? 0 : 1)