import { useState, useEffect, useRef } from 'react'
import { getReport } from '../api.js'

export default function ReportView() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)
  const timerRef = useRef(null)

  const fetch = async (showLoader = true) => {
    if (showLoader) setLoading(true)
    setError(null)
    try {
      const data = await getReport()
      setReport(data)
      setLastRefresh(new Date())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // Auto-refresh every 60s
  useEffect(() => {
    fetch()
    timerRef.current = setInterval(() => fetch(false), 60000)
    return () => clearInterval(timerRef.current)
  }, [])

  const timeAgo = lastRefresh
    ? `${Math.round((Date.now() - lastRefresh) / 1000)}s ago`
    : null

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-white">Weekly Report</h1>
          <p className="text-sm text-gray-400">
            AI-generated analysis · auto-refreshes every 60s
            {timeAgo && <span className="ml-2 text-gray-600">· last: {timeAgo}</span>}
          </p>
        </div>
        <button
          onClick={() => fetch()}
          disabled={loading}
          className="text-sm px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg disabled:opacity-50 transition-colors flex items-center gap-2"
        >
          {loading && (
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          )}
          {loading ? 'Generating…' : 'Generate Now'}
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-4 text-sm">
          {error}
        </div>
      )}

      {report ? (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-4">
          <div className="flex items-center gap-3 pb-4 border-b border-gray-800">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/30 flex items-center justify-center text-lg">
              🤖
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Claude Analysis</p>
              {report.generated_at && (
                <p className="text-xs text-gray-500">
                  {new Date(report.generated_at).toLocaleString()}
                </p>
              )}
            </div>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
            {report.report}
          </p>
        </div>
      ) : !loading ? (
        <div className="text-center py-20 text-gray-500">
          <p className="text-4xl mb-3">🤖</p>
          <p className="font-medium text-gray-400">No report yet</p>
          <p className="text-sm mt-1">Click Generate Now to create an AI analysis</p>
        </div>
      ) : (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center gap-3 text-gray-400">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <span className="text-sm">Claude is analyzing your listings and affiliate data…</span>
          </div>
        </div>
      )}
    </div>
  )
}
