const BASE = '/api'

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json()
}

export const getListings = (params = {}) => {
  const q = new URLSearchParams()
  if (params.min_score != null) q.set('min_score', params.min_score)
  if (params.status) q.set('status', params.status)
  if (params.source) q.set('source', params.source)
  q.set('limit', params.limit ?? 200)
  return req(`/listings?${q}`)
}

export const updateListingStatus = (id, status) =>
  req(`/listings/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })

export const getStats = () => req('/stats')

export const getAffiliates = () => req('/affiliates')

export const createAffiliate = (body) =>
  req('/affiliates', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

export const updateAffiliateStatus = (id, status) =>
  req(`/affiliates/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })

export const getReport = () => req('/affiliates/report')
