import request from './request'

export function fetchTeacherTasks(params = {}) {
  return request.get('/teacher/tasks', { params })
}

export function fetchTeacherTask(taskId) {
  return request.get(`/teacher/tasks/${taskId}`)
}

export function createTeacherTask(payload) {
  return request.post('/teacher/tasks', payload)
}

export function updateTeacherTask(taskId, payload) {
  return request.put(`/teacher/tasks/${taskId}`, payload)
}

export function publishTeacherTask(taskId) {
  return request.post(`/teacher/tasks/${taskId}/publish`)
}

export function closeTeacherTask(taskId) {
  return request.post(`/teacher/tasks/${taskId}/close`)
}

export function fetchClassStudents(classId) {
  return request.get(`/classes/${classId}`)
}