import request from './request'

export function fetchAppeals() {
  return request.get('/appeals')
}

export function fetchAppeal(appealId) {
  return request.get(`/appeals/${appealId}`)
}

export function createAppeal(payload) {
  return request.post('/appeals', payload)
}