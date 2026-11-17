import request from './request'

export function login(payload) {
  return request.post('/auth/login', payload, { silent: true })
}

export function fetchCurrentUser() {
  return request.get('/auth/me', { silent: true })
}
export function fetchDemoStatus() {
  return request.get('/auth/demo-status', { silent: true })
}

export function demoLogin(role) {
  return request.post('/auth/demo-login', { role }, { silent: true })
}