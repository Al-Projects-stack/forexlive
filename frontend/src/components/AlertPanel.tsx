import { useState } from 'react'
import { Alert, Pair } from '../types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

interface AlertPanelProps {
  pair: Pair
  alerts: Alert[]
  onAlertAdded: (alert: Alert) => void
  onAlertRemoved: (id: number) => void
}

export const AlertPanel = ({ pair, alerts, onAlertAdded, onAlertRemoved }: AlertPanelProps) => {
  const [level, setLevel] = useState('')
  const [direction, setDirection] = useState<'ABOVE' | 'BELOW' | 'EITHER'>('EITHER')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleAdd = async () => {
    const parsed = parseFloat(level)
    if (isNaN(parsed) || parsed <= 0) {
      setError('Enter a valid price level')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pair, level: parsed, direction }),
      })
      if (!res.ok) throw new Error('Failed to create alert')
      const newAlert: Alert = await res.json()
      onAlertAdded(newAlert)
      setLevel('')
    } catch (e) {
      setError('Could not save alert')
    } finally {
      setLoading(false)
    }
  }

  const handleRemove = async (id: number) => {
    try {
      await fetch(`${API_URL}/api/v1/alerts/${id}`, { method: 'DELETE' })
      onAlertRemoved(id)
    } catch {
      // Optimistic — remove from UI anyway
      onAlertRemoved(id)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <span className="text-gray-400 text-xs tracking-widest uppercase">Key Levels</span>

      <div className="flex flex-col gap-2">
        <div className="flex gap-2">
          <input
            type="number"
            step="0.001"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            placeholder="Price level"
            className="flex-1 bg-terminal-bg border border-terminal-border text-gray-200 text-xs font-mono px-2 py-1.5 rounded focus:outline-none focus:border-blue-500"
          />
          <select
            value={direction}
            onChange={(e) => setDirection(e.target.value as 'ABOVE' | 'BELOW' | 'EITHER')}
            className="bg-terminal-bg border border-terminal-border text-gray-200 text-xs px-2 py-1.5 rounded focus:outline-none focus:border-blue-500"
          >
            <option value="EITHER">Either</option>
            <option value="ABOVE">Above</option>
            <option value="BELOW">Below</option>
          </select>
        </div>
        <button
          onClick={handleAdd}
          disabled={loading}
          className="w-full py-1.5 text-xs font-semibold bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded transition-colors"
        >
          {loading ? 'Adding...' : '+ Add Alert'}
        </button>
        {error && <span className="text-red-400 text-xs">{error}</span>}
      </div>

      <div className="flex flex-col gap-1 max-h-48 overflow-y-auto">
        {alerts.length === 0 && (
          <span className="text-gray-600 text-xs">No key levels set</span>
        )}
        {alerts.map((a) => (
          <div
            key={a.id}
            className="flex items-center justify-between px-2 py-1.5 bg-blue-500/10 border border-blue-500/20 rounded"
          >
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />
              <span className="font-mono text-blue-300 text-xs">{a.level.toFixed(pair === 'USD/JPY' ? 3 : 5)}</span>
              <span className="text-gray-500 text-xs">{a.direction}</span>
            </div>
            <button
              onClick={() => handleRemove(a.id)}
              className="text-gray-600 hover:text-red-400 text-xs transition-colors"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
