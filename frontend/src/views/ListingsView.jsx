import { useState, useEffect, useCallback } from 'react'
import { getListings, updateListingStatus } from '../api.js'

function ScoreBadge({ score }) {
  const cls =
    score >= 70 ? 'bg-green-500/20 text-green-400 ring-1 ring-green-500/30' :
    score >= 40 ? 'bg-yellow-500/20 text-yellow-400 ring-1 ring-yellow-500/30' :
                  'bg-red-500/20 text-red-400 ring-1 ring-red-500/30'
  return <span className={`px-2 py-0.5 rounded text-xs font-bold ${cls}`}>{score}</span>
}

function SourceBadge({ source }) {
  const isFb = !source || source === 'facebook'
  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
      isFb ? 'bg-blue-500/20 text-blue-400' : 'bg-orange-500/20 text-orange-400'
    }`}>
      {isFb ? 'FB' : 'eBay'}
    </span>
  )
}

function ListingCard({ listing, onStatusChange }) {
  const [copied, setCopied] = useState(false)
  const isEbay = listing.source === 'ebay'
  const price = parseFloat(listing.price) || 0
  const soldAvg = listing.sold_price_avg
  const margin = soldAvg ? ((soldAvg - price) / soldAvg * 100) : null
  const isHighValue = listing.score >= 70
  const isNegMargin = margin !== null && margin < 0

  const borderClass = isHighValue
    ? 'border-l-4 border-l-green-500'
    : isNegMargin
    ? 'border-l-4 border-l-red-500'
    : 'border-l-4 border-l-gray-700'

  const copy = () => {
    navigator.clipboard.writeText(listing.outreach_message || '')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={`bg-gray-900 rounded-xl border border-gray-800 overflow-hidden flex flex-col ${borderClass}`}>
      {listing.image_url && (
        <img
          src={listing.image_url}
          alt=""
          className="w-full h-36 object-cover opacity-80"
          onError={e => { e.target.style.display = 'none' }}
        />
      )}
      <div className="p-4 flex flex-col gap-2 flex-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold text-gray-100 leading-snug line-clamp-2 flex-1">
            {listing.title}
          </h3>
          <div className="flex items-center gap-1 shrink-0 mt-0.5">
            <SourceBadge source={listing.source} />
            <ScoreBadge score={listing.score} />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-bold text-white">${price.toFixed(2)}</span>
          {soldAvg && (
            <>
              <span className="text-gray-600">·</span>
              <span className="text-purple-400 text-xs">avg ${soldAvg}</span>
              <span className={`text-xs font-medium ${margin >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {margin >= 0 ? '+' : ''}{margin.toFixed(1)}%
              </span>
            </>
          )}
          {listing.location && (
            <span className="text-gray-500 text-xs truncate">· {listing.location}</span>
          )}
        </div>

        {listing.reason && (
          <p className="text-xs text-gray-400 bg-gray-800/50 rounded p-2 leading-relaxed">
            {listing.reason}
          </p>
        )}

        {listing.suggested_offer && (
          <p className="text-xs text-indigo-400 font-medium">
            Offer: {listing.suggested_offer}
          </p>
        )}

        {listing.outreach_message && (
          <p className="text-xs text-gray-500 italic line-clamp-2">
            "{listing.outreach_message}"
          </p>
        )}

        <div className="mt-auto pt-3 flex gap-2 flex-wrap">
          {listing.outreach_message && (
            <button
              onClick={copy}
              className="text-xs px-2.5 py-1.5 rounded-lg bg-indigo-500/20 text-indigo-400 hover:bg-indigo-500/30 transition-colors"
            >
              {copied ? '✓ Copied' : 'Copy Message'}
            </button>
          )}
          {listing.status !== 'contacted' && (
            <button
              onClick={() => onStatusChange(listing.id, 'contacted')}
              className="text-xs px-2.5 py-1.5 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors"
            >
              Mark Contacted
            </button>
          )}
          {listing.status !== 'skipped' && (
            <button
              onClick={() => onStatusChange(listing.id, 'skipped')}
              className="text-xs px-2.5 py-1.5 rounded-lg bg-gray-700 text-gray-400 hover:bg-gray-600 transition-colors"
            >
              Skip
            </button>
          )}
          {listing.url && (
            <a
              href={listing.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs px-2.5 py-1.5 rounded-lg bg-gray-700 text-gray-400 hover:bg-gray-600 transition-colors ml-auto"
            >
              View ↗
            </a>
          )}
        </div>

        {listing.status !== 'new' && (
          <span className={`text-xs font-medium mt-1 ${
            listing.status === 'contacted' ? 'text-green-500' : 'text-gray-600'
          }`}>
            {listing.status === 'contacted' ? '✓ Contacted' : '— Skipped'}
          </span>
        )}
      </div>
    </div>
  )
}

export default function ListingsView() {
  const [listings, setListings] = useState([])
  const [minScore, setMinScore] = useState(0)
  const [status, setStatus] = useState('all')
  const [source, setSource] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getListings({ min_score: minScore, status, source })
      setListings(data)
    } catch (e) {
      setError('Cannot reach API — is marketplace_api.py running on :8001?')
    } finally {
      setLoading(false)
    }
  }, [minScore, status, source])

  useEffect(() => { load() }, [load])

  const handleStatus = async (id, newStatus) => {
    try {
      await updateListingStatus(id, newStatus)
      setListings(prev => prev.map(l => l.id === id ? { ...l, status: newStatus } : l))
    } catch { /* swallow */ }
  }

  const sources = [
    { value: 'all', label: 'All Sources' },
    { value: 'facebook', label: 'Facebook' },
    { value: 'ebay', label: 'eBay' },
  ]

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-white">Listings</h1>
          <p className="text-sm text-gray-400">{listings.length} results</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="text-sm px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg disabled:opacity-50 transition-colors"
        >
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {/* Filters */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex flex-wrap gap-5 items-center">
        <div className="flex gap-1">
          {sources.map(s => (
            <button
              key={s.value}
              onClick={() => setSource(s.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                source === s.value
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3 flex-1 min-w-48">
          <span className="text-xs text-gray-400 whitespace-nowrap">Min score: {minScore}</span>
          <input
            type="range" min={0} max={100} value={minScore}
            onChange={e => setMinScore(Number(e.target.value))}
            className="flex-1 accent-indigo-500"
          />
        </div>

        <select
          value={status}
          onChange={e => setStatus(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
        >
          <option value="all">All Statuses</option>
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="skipped">Skipped</option>
        </select>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-4 text-sm">
          {error}
        </div>
      )}

      {!loading && listings.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <p className="text-4xl mb-3">📦</p>
          <p className="font-medium text-gray-400">No listings found</p>
          <p className="text-sm mt-1">Run the agent scripts to populate data</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {listings.map(l => (
            <ListingCard key={l.id} listing={l} onStatusChange={handleStatus} />
          ))}
        </div>
      )}
    </div>
  )
}
