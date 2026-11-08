import request from './request'

export function fetchQuestions(evaluationId) {
  return request.get(`/evaluations/${evaluationId}/questions`)
}

export function createQuestion(evaluationId, payload) {
  return request.post(`/evaluations/${evaluationId}/questions`, payload, { timeout: 90000 })
}