import { useState, useEffect } from 'react'
import { getAffiliates, createAffiliate, updateAffiliateStatus } from '../api.js'

export default function AffiliatesView() {
  const [affiliates, setAffiliates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ name: '', url: '' })
  const [adding, setAdding] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      setAffiliates(await getAffiliates())
      setError(null)
    } catch {
      setError('Cannot reach API')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleToggle = async (aff) => {
    const next = aff.status === 'active' ? 'paused' : 'active'
    try {
      await updateAffiliateStatus(aff.id, next)
      setAffiliates(prev => prev.map(a => a.id === aff.id ? { ...a, status: next } : a))
    } catch { /* swallow */ }
  }

  const handleAdd = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return
    setAdding(true)
    try {
      const created = await createAffiliate(form)
      setAffiliates(prev => [...prev, created])
      setForm({ name: '', url: '' })
    } catch (e) {
      alert(e.message)
    } finally {
      setAdding(false)
    }
  }

  const convRate = (a) =>
    a.clicks > 0 ? ((a.conversions / a.clicks) * 100).toFixed(1) + '%' : '—'

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-lg font-bold text-white">Affiliates</h1>
        <p className="text-sm text-gray-400">{affiliates.length} links tracked</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-4 text-sm">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              {['Name', 'Clicks', 'Conversions', 'Conv. Rate', 'Revenue', 'Status'].map(h => (
                <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wide">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="text-center py-10 text-gray-500">Loading…</td>
              </tr>
            ) : affiliates.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-10 text-gray-500">
                  No affiliates yet — add one below
                </td>
              </tr>
            ) : (
              affiliates.map(a => (
                <tr key={a.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-medium text-white">{a.name}</div>
                    {a.url && (
                      <a
                        href={a.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-indigo-400 hover:underline truncate block max-w-xs"
                      >
                        {a.url}
                      </a>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-300">{a.clicks.toLocaleString()}</td>
                  <td className="px-4 py-3 text-gray-300">{a.conversions.toLocaleString()}</td>
                  <td className="px-4 py-3 text-gray-300">{convRate(a)}</td>
                  <td className="px-4 py-3 font-semibold text-green-400">
                    ${a.total_revenue.toFixed(2)}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleToggle(a)}
                      className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                        a.status === 'active'
                          ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                          : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                      }`}
                    >
                      {a.status === 'active' ? 'Active' : 'Paused'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Add form */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <h2 className="text-sm font-semibold text-white mb-4">Add New Affiliate</h2>
        <form onSubmit={handleAdd} className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-40">
            <label className="block text-xs text-gray-400 mb-1">Name *</label>
            <input
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Partner name"
              required
              className="w-full bg-gray-800 border border-gray-700 text-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 placeholder-gray-600"
            />
          </div>
          <div className="flex-1 min-w-60">
            <label className="block text-xs text-gray-400 mb-1">URL</label>
            <input
              value={form.url}
              onChange={e => setForm(f => ({ ...f, url: e.target.value }))}
              placeholder="https://..."
              className="w-full bg-gray-800 border border-gray-700 text-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 placeholder-gray-600"
            />
          </div>
          <button
            type="submit"
            disabled={adding}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
          >
            {adding ? 'Adding…' : '+ Add'}
          </button>
        </form>
      </div>
    </div>
  )
}
