const base = 'http://127.0.0.1:8000/api/v1'
const sampleDir = 'D:/1学习/华为开发者大赛/CodeArts Agent/作文'

async function req(path, options = {}) {
  const response = await fetch(base + path, options)
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
const authHeaders = (token) => ({ Authorization: `Bearer ${token}` })

function ok(name, condition, detail = '') {
  if (!condition) throw new Error(`${name} 失败 ${detail}`)
  console.log('PASS', name, detail)
}

async function main() {
  const fs = await import('node:fs/promises')
  const path = await import('node:path')

  const teacher = await login('demo_teacher')
  const rubric = (await req('/teacher/rubric-versions', { headers: authHeaders(teacher) })).body.data.find(
    (item) => item.status === 'published',
  )
  const task = (await req('/teacher/tasks', {
    method: 'POST',
    headers: jsonHeaders(teacher),
    body: JSON.stringify({
      title: `图片作文上传验收 ${Date.now()}`,
      prompt_text: '上传纸质作文照片验证图片提交链路。',
      rubric_version_id: rubric.id,
      word_min: 0,
      word_max: 0,
      allow_resubmit: true,
      targets: [{ target_type: 'class', target_id: 1 }],
      questions: [{ label: '问题一', question_text: '上传你的作文照片。', answer_type: 'image' }],
    }),
  })).body.data
  await req(`/teacher/tasks/${task.id}/publish`, { method: 'POST', headers: authHeaders(teacher) })

  const student = await login('demo_student')
  const images = (await fs.readdir(sampleDir)).filter((name) => name.toLowerCase().endsWith('.jpg')).sort()
  ok('作文图片素材可读', images.length >= 3, `找到 ${images.length} 张`)

  const boundary = '----wenmindtest'
  const buildForm = (entries, kind = 'photo') => {
    const parts = []
    for (const [field, value] of entries) {
      parts.push(`--${boundary}\r\n`)
      if (value.filename) {
        parts.push(`Content-Disposition: form-data; name="${field}"; filename="${value.filename}"\r\n`)
        parts.push(`Content-Type: ${value.contentType}\r\n\r\n`)
      } else {
        parts.push(`Content-Disposition: form-data; name="${field}"\r\n\r\n`)
      }
      parts.push(value.data ?? '')
      parts.push('\r\n')
    }
    if (kind) {
      parts.push(`--${boundary}\r\nContent-Disposition: form-data; name="file_kind"\r\n\r\n${kind}\r\n`)
    }
    parts.push(`--${boundary}--\r\n`)
    return Buffer.concat(parts.map((part) => (Buffer.isBuffer(part) ? part : Buffer.from(part))))
  }

  const submission = (await req('/student/submissions/image', {
    method: 'POST',
    headers: jsonHeaders(student),
    body: JSON.stringify({ task_id: task.id }),
  })).body.data
  ok('创建图片提交流程', Boolean(submission?.id), `提交 #${submission.id}，状态 ${submission.status}`)

  const uploadOnce = async (filename) => {
    const buffer = await fs.readFile(path.join(sampleDir, filename))
    const form = buildForm([['files', { filename, contentType: 'image/jpeg', data: buffer }]])
    return req(`/student/submissions/${submission.id}/files`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${student}`, 'Content-Type': `multipart/form-data; boundary=${boundary}` },
      body: form,
    })
  }

  let result = await uploadOnce(images[0])
  ok('上传真实作文照片', result.response.status === 201 && result.body.data.length === 1, `文件 #${result.body.data[0].id} ${result.body.data[0].width}x${result.body.data[0].height}`)
  const firstFileId = result.body.data[0].id

  result = await uploadOnce(images[0])
  ok('重复图片被拒绝', result.response.status === 409, `业务码 ${result.body.code}`)

  const fakeForm = buildForm([['files', { filename: 'fake.jpg', contentType: 'image/jpeg', data: Buffer.from('not an image content at all') }]])
  result = await req(`/student/submissions/${submission.id}/files`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${student}`, 'Content-Type': `multipart/form-data; boundary=${boundary}` },
    body: fakeForm,
  })
  ok('伪装成 jpg 的非图片被拒绝', result.response.status === 400, `业务码 ${result.body.code}`)

  result = await uploadOnce(images[1])
  ok('上传第二页', result.response.status === 201)
  const secondFileId = result.body.data[0].id

  result = await req(`/student/submissions/${submission.id}/files/order`, {
    method: 'PUT',
    headers: jsonHeaders(student),
    body: JSON.stringify([
      { file_id: secondFileId, rotation: 90 },
      { file_id: firstFileId, rotation: 0 },
    ]),
  })
  ok('页序与旋转更新', result.response.status === 200 && result.body.data[0].id === secondFileId, `首页为 #${result.body.data[0].id}，旋转 ${result.body.data[0].rotation}`)

  result = await req(`/student/submissions/${submission.id}/files`, { headers: authHeaders(student) })
  ok('学生读取本人提交图片', result.response.status === 200 && result.body.data.length === 2, `共 ${result.body.data.length} 张`)

  result = await req(`/files/${firstFileId}`, { headers: authHeaders(student) })
  ok('学生可读取本人图片文件', result.response.status === 200 && result.response.headers.get('content-type').startsWith('image/'), result.response.headers.get('content-type'))

  const other = await login('demo_student2')
  result = await req(`/student/submissions/${submission.id}/files`, { headers: authHeaders(other) })
  ok('其他学生不能读取他人提交图片', result.response.status === 403 || result.response.status === 404, `HTTP ${result.response.status}`)

  result = await req(`/files/${firstFileId}`, { headers: authHeaders(other) })
  ok('其他学生不能读取他人图片文件', result.response.status === 403, `业务码 ${result.body.code}`)

  result = await req(`/files/${firstFileId}`)
  ok('匿名读取图片被拒绝', result.response.status === 401 || result.response.status === 403, `HTTP ${result.response.status}`)

  result = await req(`/student/submissions/${submission.id}/files/${secondFileId}`, {
    method: 'DELETE',
    headers: authHeaders(student),
  })
  ok('删除图片', result.response.status === 200, `删除 #${secondFileId}`)

  result = await req(`/student/submissions/${submission.id}/files`, { headers: authHeaders(student) })
  ok('删除后列表与页序重排', result.response.status === 200 && result.body.data.length === 1 && result.body.data[0].sort_order === 1)

  const { body: filesOnDisk } = { body: await fs.readdir(`D:/1学习/华为开发者大赛/CodeArts Agent/backend/data/submission_uploads/${submission.id}`).catch(() => []) }
  ok('存储目录按提交隔离', filesOnDisk.length === 1, `实际文件 ${filesOnDisk.length} 个`)

  console.log('RESULT', JSON.stringify({ taskId: task.id, submissionId: submission.id, remainingFileId: firstFileId }))
}

main().catch((error) => {
  console.error(error.message)
  process.exit(1)
})