import request from './request'

export function fetchTeacherClasses() {
  return request.get('/classes')
}

export function fetchTeacherAppeals(params = {}) {
  return request.get('/teacher/appeals', { params })
}

export function fetchTeacherAppeal(appealId) {
  return request.get(`/teacher/appeals/${appealId}`)
}

export function submitTeacherReview(appealId, payload) {
  return request.post(`/teacher/appeals/${appealId}/review`, payload)
}

export function fetchAppealPatterns(params = {}) {
  return request.get('/teacher/analytics/appeal-patterns', { params })
}

export function fetchRuleProposals(params = {}) {
  return request.get('/teacher/rule-proposals', { params })
}

export function generateRuleProposals(windowDays = 30) {
  return request.post('/teacher/rule-proposals/generate', null, { params: { window_days: windowDays } })
}

export function approveRuleProposal(proposalId, payload) {
  return request.post(`/teacher/rule-proposals/${proposalId}/approve`, payload)
}

export function rejectRuleProposal(proposalId, payload) {
  return request.post(`/teacher/rule-proposals/${proposalId}/reject`, payload)
}

export function fetchRubricVersions() {
  return request.get('/teacher/rubric-versions')
}

export function runRubricRegression(versionId) {
  return request.post(`/teacher/rubric-versions/${versionId}/regression-test`)
}

export function publishRubricVersion(versionId) {
  return request.post(`/teacher/rubric-versions/${versionId}/publish`)
}