import request from './request'

export function fetchEssays(params = { page: 1, page_size: 50 }) {
  return request.get('/essays', { params })
}

export function fetchEvaluations(params = { page: 1, page_size: 20 }) {
  return request.get('/evaluations', { params })
}

export function createEvaluation(essayId) {
  return request.post(`/evaluations/${essayId}`)
}

export function executeEvaluation(evaluationId) {
  return request.post(`/evaluations/${evaluationId}/execute`)
}

export function fetchEvaluation(evaluationId) {
  return request.get(`/evaluations/${evaluationId}`, { silent: true })
}