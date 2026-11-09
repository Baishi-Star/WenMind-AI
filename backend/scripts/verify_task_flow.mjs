const base = 'http://127.0.0.1:8000/api/v1'
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function req(path, options = {}) {
  const response = await fetch(base + path, options)
  const body = await response.json()
  return { response, body }
}

async function login(username) {
  const result = await req('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password: 'Demo@2026' }),
  })
  if (result.response.status !== 200) throw new Error(`${username} 登录失败`)
  return result.body.data.access_token
}

const jsonHeaders = (token) => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' })
const authHeaders = (token) => ({ Authorization: `Bearer ${token}` })

function ok(name, condition, detail = '') {
  if (!condition) throw new Error(`${name} 失败 ${detail}`)
  console.log('PASS', name, detail)
}

const ANSWER_ONE =
  '小时候邻里之间常常互相串门，谁家做了好吃的都会分给邻居，孩子们在楼道里追逐玩耍。如今高楼林立，防盗门隔绝了往来，邻居之间甚至叫不出名字。这种变化既有生活节奏加快、人们忙于工作与家庭的原因，也源于交流方式转移到了线上，人们更愿意在手机里与远方的人交谈，却忽略了身边真实的人。'
const ANSWER_TWO =
  '我认为可以从三方面改善：一是主动打招呼，从一句问候开始建立信任，让对方知道善意并不难；二是参与社区活动，在共同事务中增进了解，让陌生感在合作中慢慢消失；第三是在力所能及时互相帮助，例如代收快递、照看老人，让善意成为日常习惯，久而久之邻里关系自然会回暖。'

async function main() {
  const teacher = await login('demo_teacher')
  let result = await req('/teacher/rubric-versions', { headers: authHeaders(teacher) })
  const rubric = result.body.data.find((item) => item.status === 'published')
  ok('读取已发布量规', Boolean(rubric), `量规 #${rubric.id} ${rubric.version}`)

  result = await req('/teacher/tasks', {
    method: 'POST',
    headers: jsonHeaders(teacher),
    body: JSON.stringify({
      title: '议论文写作：邻里关系（阶段验收）',
      prompt_text: '阅读材料，围绕远亲不如近邻的现实处境写一篇文章。',
      requirements: '议论文，观点明确，不少于600字。',
      rubric_version_id: rubric.id,
      word_min: 100,
      word_max: 4000,
      allow_resubmit: false,
      targets: [{ target_type: 'class', target_id: 1 }],
      questions: [
        { label: '问题一', question_text: '结合材料谈谈你对邻里关系变化的看法。', answer_type: 'text' },
        { label: '问题二', question_text: '提出改善邻里关系的具体做法。', answer_type: 'text' },
      ],
    }),
  })
  ok('教师创建任务草稿', result.response.status === 201, `任务 #${result.body.data.id}，子问题 ${result.body.data.question_count} 道`)
  const taskId = result.body.data.id
  ok('任务默认为草稿', result.body.data.status === 'draft')

  result = await req(`/teacher/tasks/${taskId}/publish`, { method: 'POST', headers: authHeaders(teacher) })
  ok('教师发布任务', result.response.status === 200 && result.body.data.status === 'published')

  const student = await login('demo_student')
  result = await req('/student/tasks', { headers: authHeaders(student) })
  const studentTask = result.body.data.find((item) => item.id === taskId)
  ok('学生可见已发布任务', Boolean(studentTask), `标题 ${studentTask.title}，子问题 ${studentTask.questions.length}`)
  const questions = studentTask.questions
  ok('子问题包含题目与顺序', questions.length === 2 && questions[0].question_text.length > 0, `首题 ${questions[0].label}`)

  result = await req('/student/submissions', {
    method: 'POST',
    headers: jsonHeaders(student),
    body: JSON.stringify({
      task_id: taskId,
      answers: [
        { question_id: questions[0].id, content: ANSWER_ONE },
        { question_id: questions[1].id, content: ANSWER_TWO },
      ],
    }),
  })
  ok('学生逐题提交', result.response.status === 201, `提交 #${result.body.data?.id}，作答 ${result.body.data?.answers?.length} 条`)
  const submissionId = result.body.data.id
  const evaluationIds = result.body.data.answers.map((item) => item.evaluation_id)
  ok('自动创建逐题评价任务', evaluationIds.every(Boolean), `评价 ${evaluationIds.join(',')}`)

  let statuses = []
  for (let index = 0; index < 200; index += 1) {
    await sleep(2000)
    result = await req(`/student/submissions/${submissionId}`, { headers: authHeaders(student) })
    statuses = result.body.data.answers.map((item) => item.evaluation_status)
    if (statuses.every((status) => ['completed', 'failed'].includes(status))) break
  }
  ok('逐题评价完成', statuses.every((status) => status === 'completed'), `状态 ${statuses.join(',')}`)

  result = await req(`/student/submissions/${submissionId}`, { headers: authHeaders(student) })
  console.log('提交详情:', JSON.stringify({
    submission: result.body.data.id,
    status: result.body.data.status,
    answers: result.body.data.answers.map((item) => ({
      label: item.question_label,
      essay: item.essay_id,
      evaluation: item.evaluation_id,
      status: item.evaluation_status,
      chars: item.char_count,
    })),
  }))

  const other = await login('demo_student2')
  result = await req(`/student/tasks/${taskId}`, { headers: authHeaders(other) })
  ok('同班级学生可见班级任务', result.response.status === 200, `任务 #${taskId}`)

  result = await req('/teacher/tasks', {
    method: 'POST',
    headers: jsonHeaders(teacher),
    body: JSON.stringify({
      title: '定向任务：仅指派给演示学生一',
      prompt_text: '该任务仅下发给指定学生，用于验证范围隔离。',
      rubric_version_id: rubric.id,
      word_min: 20,
      word_max: 4000,
      targets: [{ target_type: 'student', target_id: 1 }],
      questions: [{ label: '问题一', question_text: '写一段话说明你的观点。', answer_type: 'text' }],
    }),
  })
  const scopedTaskId = result.body.data.id
  await req(`/teacher/tasks/${scopedTaskId}/publish`, { method: 'POST', headers: authHeaders(teacher) })
  result = await req(`/student/tasks/${scopedTaskId}`, { headers: authHeaders(other) })
  ok('范围外学生访问定向任务被拒', result.response.status === 403, `业务码 ${result.body.code}`)

  result = await req(`/teacher/tasks/${taskId}/close`, { method: 'POST', headers: authHeaders(teacher) })
  ok('教师关闭任务', result.response.status === 200 && result.body.data.status === 'closed')

  result = await req('/student/submissions', {
    method: 'POST',
    headers: jsonHeaders(student),
    body: JSON.stringify({
      task_id: taskId,
      answers: questions.map((item) => ({ question_id: item.id, content: '关闭后不应允许提交的内容。' })),
    }),
  })
  ok('关闭后提交被拦截', result.response.status === 409, `业务码 ${result.body.code}`)

  console.log('RESULT', JSON.stringify({ taskId, submissionId, evaluationIds }))
}

main().catch((error) => {
  console.error(error.message)
  process.exit(1)
})