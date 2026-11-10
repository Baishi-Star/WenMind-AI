import request from './request'

export function fetchStudentTasks(params = {}) {
  return request.get('/student/tasks', { params })
}

export function fetchStudentTask(taskId) {
  return request.get(`/student/tasks/${taskId}`)
}

export function createSubmission(payload) {
  return request.post('/student/submissions', payload, { timeout: 120000 })
}

export function createImageSubmission(taskId) {
  return request.post('/student/submissions/image', { task_id: taskId })
}

export function fetchStudentSubmissions() {
  return request.get('/student/submissions')
}

export function fetchStudentSubmission(submissionId) {
  return request.get(`/student/submissions/${submissionId}`)
}

export function fetchEssayFiles(essayId) {
  return request.get(`/essays/${essayId}/files`)
}

export function fetchEssayAnnotations(essayId) {
  return request.get(`/essays/${essayId}/annotations`)
}

export function createEssayAnnotation(essayId, payload) {
  return request.post(`/essays/${essayId}/annotations`, payload)
}

export function transcribeSubmission(submissionId) {
  return request.post(`/student/submissions/${submissionId}/transcribe`, null, { timeout: 600000 })
}

export function confirmSubmissionExtraction(submissionId, pages) {
  return request.post(`/student/submissions/${submissionId}/confirm`, { pages })
}

export function submitImageSubmission(submissionId) {
  return request.post(`/student/submissions/${submissionId}/submit`)
}
export function uploadSubmissionFiles(submissionId, files, fileKind = 'photo') {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  formData.append('file_kind', fileKind)
  return request.post(`/student/submissions/${submissionId}/files`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export function fetchSubmissionFiles(submissionId) {
  return request.get(`/student/submissions/${submissionId}/files`)
}

export function deleteSubmissionFile(submissionId, fileId) {
  return request.delete(`/student/submissions/${submissionId}/files/${fileId}`)
}

export function reorderSubmissionFiles(submissionId, items) {
  return request.put(`/student/submissions/${submissionId}/files/order`, items)
}

/**
 * 以带鉴权头的方式拉取图片，返回 objectURL。
 * 不使用 ?token= 查询参数，避免令牌进入浏览器历史和服务端访问日志。
 */
export async function loadAuthorizedImage(fileId) {
  const token = localStorage.getItem('wenmind_token') || ''
  const base = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  const response = await fetch(`${base}/files/${fileId}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    throw new Error(`图片加载失败（HTTP ${response.status}）`)
  }
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}