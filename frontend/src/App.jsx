import { useState } from 'react'
import ListingsView from './views/ListingsView.jsx'
import AffiliatesView from './views/AffiliatesView.jsx'
import PerformanceView from './views/PerformanceView.jsx'
import ReportView from './views/ReportView.jsx'

const NAV = [
  { id: 'listings',    label: 'Listings',    icon: '🏷️' },
  { id: 'affiliates',  label: 'Affiliates',  icon: '🔗' },
  { id: 'performance', label: 'Performance', icon: '📊' },
  { id: 'report',      label: 'Report',      icon: '🤖' },
]

export default function App() {
  const [view, setView] = useState('listings')

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-52 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="px-5 py-5 border-b border-gray-800">
          <div className="text-sm font-bold text-white">Marketplace</div>
          <div className="text-xs text-gray-400 mt-0.5">FB + eBay Monitor</div>
        </div>
        <nav className="flex-1 py-4 space-y-1 px-2">
          {NAV.map(n => (
            <button
              key={n.id}
              onClick={() => setView(n.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                view === n.id
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              <span>{n.icon}</span>
              {n.label}
            </button>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-500">
          API :8001
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto bg-gray-950">
        {view === 'listings'    && <ListingsView />}
        {view === 'affiliates'  && <AffiliatesView />}
        {view === 'performance' && <PerformanceView />}
        {view === 'report'      && <ReportView />}
      </main>
    </div>
  )
}
