const fs = require('node:fs')
const path = require('node:path')

const base = 'http://127.0.0.1:8000/api/v1'
const sampleDir = 'D:/1学习/华为开发者大赛/CodeArts Agent/作文'

async function req(p, options = {}) {
  const response = await fetch(base + p, options)
  const type = response.headers.get('content-type') || ''
  const body = type.includes('application/json') ? await response.json() : await response.blob()
  return { response, body }
}

async function login(username) {
  const result = await req('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password: 'Demo@2026' }),
  })
  return result.body.data.access_token
}

const jsonHeaders = (token) => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' })

function ok(name, condition, detail = '') {
  if (!condition) throw new Error(`${name} 失败 ${detail}`)
  console.log('PASS', name, detail)
}

async function uploadOne(submissionId, token, filename) {
  const buffer = fs.readFileSync(path.join(sampleDir, filename))
  const boundary = '----wenmindvision'
  const parts = []
  parts.push(`--${boundary}\r\n`)
  parts.push(`Content-Disposition: form-data; name="files"; filename="${filename}"\r\n`)
  parts.push('Content-Type: image/png\r\n\r\n')
  parts.push(buffer)
  parts.push('\r\n')
  parts.push(`--${boundary}\r\nContent-Disposition: form-data; name="file_kind"\r\n\r\nphoto\r\n`)
  parts.push(`--${boundary}--\r\n`)
  const form = Buffer.concat(parts.map((part) => (Buffer.isBuffer(part) ? part : Buffer.from(part))))
  return req(`/student/submissions/${submissionId}/files`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': `multipart/form-data; boundary=${boundary}` },
    body: form,
  })
}

async function main() {
  const teacher = await login('demo_teacher')
  const rubric = (await req('/teacher/rubric-versions', { headers: { Authorization: `Bearer ${teacher}` } })).body.data.find(
    (item) => item.status === 'published',
  )
  const task = (await req('/teacher/tasks', {
    method: 'POST',
    headers: jsonHeaders(teacher),
    body: JSON.stringify({
      title: `图片作文视觉识别验收 ${Date.now()}`,
      prompt_text: '上传纸质作文照片，用于验证 DeepSeek 视觉识别链路。',
      rubric_version_id: rubric.id,
      word_min: 0,
      word_max: 20000,
      allow_resubmit: true,
      targets: [{ target_type: 'class', target_id: 1 }],
      questions: [{ label: '问题一', question_text: '上传并识别你的作文。', answer_type: 'image' }],
    }),
  })).body.data
  await req(`/teacher/tasks/${task.id}/publish`, { method: 'POST', headers: { Authorization: `Bearer ${teacher}` } })
  console.log('PASS 教师创建并发布图片任务', `任务 #${task.id}`)

  const student = await login('demo_student')
  const images = fs.readdirSync(sampleDir).filter((name) => name.toLowerCase().endsWith('.jpg')).sort()
  const submission = (await req('/student/submissions/image', {
    method: 'POST',
    headers: jsonHeaders(student),
    body: JSON.stringify({ task_id: task.id }),
  })).body.data
  ok('创建图片提交流程', submission.status === 'draft', `提交 #${submission.id}`)

  let result = await uploadOne(submission.id, student, images[0])
  ok('上传作文照片', result.response.status === 201, `文件 #${result.body.data[0].id}`)
  const fileId = result.body.data[0].id

  console.log('... 正在调用视觉模型识别（可能耗时 1-3 分钟）')
  result = await req(`/student/submissions/${submission.id}/transcribe`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${student}` },
  })
  ok('视觉识别完成', result.response.status === 200, `HTTP ${result.response.status} ${JSON.stringify(result.body).slice(0, 200)}`)
  const file = result.body.data[0]
  ok('识别文本已写入且状态为 done', file.extraction_status === 'done' && (file.extracted_text || '').length > 50, `识别 ${(file.extracted_text || '').length} 字`)
  console.log('识别文本片段:', (file.extracted_text || '').slice(0, 120).replace(/\n/g, ' / '))

  result = await req(`/student/submissions/${submission.id}`, { headers: { Authorization: `Bearer ${student}` } })
  ok('识别后提交进入待确认', result.body.data.status === 'needs_confirmation', `状态 ${result.body.data.status}`)

  const confirmedText = `${file.extracted_text}（已校对）`
  result = await req(`/student/submissions/${submission.id}/confirm`, {
    method: 'POST',
    headers: jsonHeaders(student),
    body: JSON.stringify({ pages: [{ file_id: fileId, confirmed_text: confirmedText }] }),
  })
  ok('学生确认校对文本', result.response.status === 200 && result.body.data.status === 'ready', `状态 ${result.body.data.status}`)

  result = await req(`/student/submissions/${submission.id}/submit`, {
    method: 'POST',
    headers: jsonHeaders(student),
  })
  ok('确认后提交进入评价队列', result.response.status === 200, `状态 ${result.body.data.status}`)
  const evaluationIds = result.body.data.answers.map((item) => item.evaluation_id).filter(Boolean)
  ok('自动创建评价任务', evaluationIds.length > 0, `评价 ${evaluationIds.join(',')}`)

  const other = await login('demo_student2')
  result = await req(`/student/submissions/${submission.id}/transcribe`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${other}` },
  })
  ok('他人不能识别本人提交', result.response.status === 403 || result.response.status === 404, `HTTP ${result.response.status}`)

  console.log('RESULT', JSON.stringify({ taskId: task.id, submissionId: submission.id, fileId, evaluationIds, textLength: confirmedText.length }))
}

main().catch((error) => {
  console.error(error.message)
  process.exit(1)
})