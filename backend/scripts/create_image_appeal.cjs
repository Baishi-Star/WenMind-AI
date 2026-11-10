const base = 'http://127.0.0.1:8000/api/v1'

async function req(p, options = {}) {
  const response = await fetch(base + p, options)
  const body = await response.json()
  return { response, body }
}
const json = (token) => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' })
const auth = (token) => ({ Authorization: `Bearer ${token}` })
async function login(u) {
  return (await req('/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: u, password: 'Demo@2026' }) })).body.data.access_token
}

async function main() {
  const student = await login('demo_student')
  // 找到带图片且已在评价中的作文，取出其 essay 与 evaluation
  const essays = (await req('/essays', { headers: auth(student) })).body.data.items
  let target = null
  for (const item of essays) {
    const files = (await req(`/essays/${item.id}/files`, { headers: auth(student) })).body.data
    if (files.length && item.status === 'completed') {
      target = { essayId: item.id, fileId: files[0].id }
      break
    }
  }
  if (!target) throw new Error('未找到带图片且评价完成的作文')
  console.log('目标作文:', JSON.stringify(target))

  const evaluations = (await req('/evaluations', { headers: auth(student) })).body.data.items
  const evaluation = evaluations.find((item) => item.essay_id === target.essayId)
  if (!evaluation) throw new Error('该作文没有评价记录')
  const detail = (await req(`/evaluations/${evaluation.id}`, { headers: auth(student) })).body.data
  const feedback = detail.feedback_items.find((item) => item.evidence.some((e) => e.verified_status === 'verified')) || detail.feedback_items[0]
  const evidence = (feedback.evidence || []).find((e) => e.verified_status === 'verified')

  const appeal = await req('/appeals', {
    method: 'POST',
    headers: json(student),
    body: JSON.stringify({
      evaluation_id: evaluation.id,
      feedback_item_id: feedback.id,
      reason_type: 'creative_expression_misjudged',
      dimension: feedback.dimension === 'overall' ? 'overall' : feedback.dimension,
      description: '这是图片作文，希望教师在原图上标注并复核表达是否被误判。',
      evidence: evidence || null,
    }),
  })
  console.log('创建图片作文申诉:', appeal.response.status, '申诉ID', appeal.body.data?.id, appeal.body.message || '')
  console.log('RESULT', JSON.stringify({ essayId: target.essayId, evaluationId: evaluation.id, appealId: appeal.body.data?.id }))
}

main().catch((error) => {
  console.error(error.message)
  process.exit(1)
})