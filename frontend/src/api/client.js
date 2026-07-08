import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT from localStorage on every request
api.interceptors.request.use(config => {
  const token = localStorage.getItem('argus_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Redirect to login on 401
api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('argus_token')
      localStorage.removeItem('argus_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const authApi = {
  login:        (data) => api.post('/auth/login', data).then(r => r.data),
  me:           ()     => api.get('/auth/me').then(r => r.data),
  listUsers:    ()     => api.get('/auth/users').then(r => r.data),
  createUser:   (data) => api.post('/auth/users', data).then(r => r.data),
  deactivateUser:(id)  => api.patch(`/auth/users/${id}/deactivate`).then(r => r.data),
}

export const settingsApi = {
  list:   ()     => api.get('/settings').then(r => r.data),
  update: (data) => api.put('/settings', { settings: data }).then(r => r.data),
}

export const engagementsApi = {
  list:      ()       => api.get('/engagements').then(r => r.data),
  get:       (id)     => api.get(`/engagements/${id}`).then(r => r.data),
  create:    (data)   => api.post('/engagements', data).then(r => r.data),
  update:    (id, d)  => api.patch(`/engagements/${id}`, d).then(r => r.data),
  delete:    (id)     => api.delete(`/engagements/${id}`),
  start:     (id)     => api.post(`/engagements/${id}/start`, {}).then(r => r.data),
  rerun:     (id)     => api.post(`/engagements/${id}/rerun`, {}).then(r => r.data),
  killChain: (id)     => api.get(`/engagements/${id}/kill-chain`).then(r => r.data),
}

export const targetsApi = {
  list:   (engId)           => api.get(`/engagements/${engId}/targets`).then(r => r.data),
  add:    (engId, data)     => api.post(`/engagements/${engId}/targets`, data).then(r => r.data),
  delete: (engId, targetId) => api.delete(`/engagements/${engId}/targets/${targetId}`),
}

export const scansApi = {
  list: (engId) => api.get(`/engagements/${engId}/scans`).then(r => r.data),
}

export const findingsApi = {
  list:    (engId, params) => api.get(`/engagements/${engId}/findings`, { params }).then(r => r.data),
  listAll: (params)        => api.get('/findings', { params }).then(r => r.data),
  update:  (id, data)      => api.patch(`/findings/${id}`, data).then(r => r.data),
  count:   ()              => api.get('/findings/count').then(r => r.data),
}

export const graphApi = {
  get:         (id) => api.get(`/graph/${id}`).then(r => r.data),
  attackPaths: (id) => api.get(`/graph/${id}/attack-paths`).then(r => r.data),
}

export const reportsApi = {
  narrativeStatus: ()  => api.get('/reports/narrative/status').then(r => r.data),
  narrative:       (id) => api.post(`/reports/${id}/narrative`, {}).then(r => r.data),
  // PDF export requires the Bearer token — a plain <a> download can't attach
  // auth headers, so fetch as a blob through the authed axios instance instead.
  pdf:             (id) => api.get(`/reports/${id}/pdf`, { responseType: 'blob' }).then(r => r.data),
}

export default api
