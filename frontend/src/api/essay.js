import request from './request'

export function fetchEssayPrompts() {
  return request.get('/essays/prompts')
}

export function fetchEssays(params = { page: 1, page_size: 50 }) {
  return request.get('/essays', { params })
}

export function fetchEssay(essayId) {
  return request.get(`/essays/${essayId}`)
}

export function createEssay(payload) {
  return request.post('/essays', payload)
}

export function updateEssay(essayId, payload) {
  return request.put(`/essays/${essayId}`, payload)
}
export function fetchOcrStatus() {
  return request.get('/essays/ocr/status')
}

export function uploadEssayImage(formData) {
  return request.post('/essays/upload-image', formData, {
    headers: { 'Content-Type': undefined },
  })
}

export function ocrEssay(imageToken) {
  return request.post('/essays/ocr', { image_token: imageToken }, { timeout: 180000 })
}