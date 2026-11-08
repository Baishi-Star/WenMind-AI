import request from './request'

export function fetchGrowthProfile(studentId) {
  return request.get('/growth/profile', { params: studentId ? { student_id: studentId } : {} })
}

export function fetchGrowthHistory(studentId) {
  return request.get('/growth/history', { params: studentId ? { student_id: studentId } : {} })
}

export function fetchTrainingTasks() {
  return request.get('/training/tasks')
}

export function completeTrainingTask(taskId, resultText) {
  return request.post(`/training/tasks/${taskId}/complete`, { result_text: resultText })
}

export function fetchClassAnalytics(classId) {
  return request.get(`/teacher/classes/${classId}/analytics`)
}