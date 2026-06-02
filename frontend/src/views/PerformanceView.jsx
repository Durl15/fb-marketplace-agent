import { useState, useEffect } from 'react'
import { getStats, getListings } from '../api.js'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'

function StatCard({ label, value, sub, color }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${color || 'text-white'}`}>{value ?? '—'}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  )
}

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs max-w-xs shadow-xl">
      <p className="font-semibold text-white mb-1 leading-snug">{d.title}</p>
      <p className="text-indigo-400">Score: {d.score}</p>
      {d.source && <p className="text-gray-400">{d.source}</p>}
    </div>
  )
}

export default function PerformanceView() {
  const [stats, setStats] = useState(null)
  const [topListings, setTopListings] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getStats(), getListings({ limit: 10 })])
      .then(([s, l]) => {
        setStats(s)
        setTopListings(
          l.slice(0, 10).map(item => ({
            title: item.title?.slice(0, 28) + (item.title?.length > 28 ? '…' : '') || 'Untitled',
            score: item.score || 0,
            source: item.source || 'facebook',
          }))
        )
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        Loading…
      </div>
    )
  }

  const fbPct = stats
    ? Math.round((stats.facebook_count / (stats.total_scanned || 1)) * 100)
    : 0
  const ebayPct = stats ? 100 - fbPct : 0

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-lg font-bold text-white">Performance</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Scanned"
          value={stats?.total_scanned?.toLocaleString()}
        />
        <StatCard
          label="High Value (70+)"
          value={stats?.high_value?.toLocaleString()}
          color="text-green-400"
          sub="score ≥ 70"
        />
        <StatCard
          label="Contacted"
          value={stats?.contacted?.toLocaleString()}
          color="text-indigo-400"
        />
        <StatCard
          label="Avg Score"
          value={stats?.avg_score}
          color="text-yellow-400"
          sub="across all listings"
        />
      </div>

      {/* Source breakdown */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <h2 className="text-sm font-semibold text-white mb-4">Source Breakdown</h2>
        <div className="flex gap-8 items-center">
          <div className="flex-1">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>Facebook</span>
              <span>{stats?.facebook_count ?? 0} ({fbPct}%)</span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-500"
                style={{ width: `${fbPct}%` }}
              />
            </div>
          </div>
          <div className="flex-1">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>eBay</span>
              <span>{stats?.ebay_count ?? 0} ({ebayPct}%)</span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-orange-500 rounded-full transition-all duration-500"
                style={{ width: `${ebayPct}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Bar chart */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <h2 className="text-sm font-semibold text-white mb-5">Top 10 Listings by Score</h2>
        {topListings.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-8">No listings yet</p>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={topListings} margin={{ top: 0, right: 0, bottom: 60, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
              <XAxis
                dataKey="title"
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                angle={-40}
                textAnchor="end"
                interval={0}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: '#9ca3af', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(99,102,241,0.08)' }} />
              <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                {topListings.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={entry.score >= 70 ? '#22c55e' : entry.score >= 40 ? '#eab308' : '#ef4444'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
