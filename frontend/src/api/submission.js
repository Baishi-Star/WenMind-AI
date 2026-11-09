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

export function fetchStudentSubmissions() {
  return request.get('/student/submissions')
}

export function fetchStudentSubmission(submissionId) {
  return request.get(`/student/submissions/${submissionId}`)
}