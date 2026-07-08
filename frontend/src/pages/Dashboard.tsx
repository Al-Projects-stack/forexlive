import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { PAIRS, Pair, Alert } from '../types'
import { useAuth } from '../context/AuthContext'
import { useChartData } from '../hooks/useChartData'
import { useDesktopNotifications } from '../hooks/useDesktopNotifications'
import { SessionIndicator } from '../components/SessionIndicator'
import { LiveTicker } from '../components/LiveTicker'
import { PriceChart } from '../components/PriceChart'
import { ConsolidationOverlay } from '../components/ConsolidationOverlay'
import { AlertPanel } from '../components/AlertPanel'
import { KeyLevelAlert } from '../components/KeyLevelAlert'
import { NewsCalendar } from '../components/NewsCalendar'
import { NewsWarningBanner } from '../components/NewsWarningBanner'
import { PositionPnL } from '../components/PositionPnL'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const Dashboard = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [activePair, setActivePair] = useState<Pair>('EUR/USD')
  const [alerts, setAlerts] = useState<Alert[]>([])

  const handleLogout = () => { logout(); navigate('/') }

  const { candles, currentPrice, consolidationZone, lastMessage, isConnected, connectionError } = useChartData(activePair)

  useDesktopNotifications(lastMessage)

  // Fetch persisted alerts on mount and pair change
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/alerts?pair=${encodeURIComponent(activePair)}`)
        if (res.ok) {
          const data: Alert[] = await res.json()
          setAlerts(data)
        }
      } catch {
        // Will retry on next pair switch
      }
    }
    fetchAlerts()
  }, [activePair])

  const handleAlertAdded = useCallback((alert: Alert) => {
    setAlerts((prev) => [...prev, alert])
  }, [])

  const handleAlertRemoved = useCallback((id: number) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id))
  }, [])

  const priceDigits = activePair === 'USD/JPY' ? 3 : 5
  const isUp = currentPrice !== null && candles.length > 1
    ? currentPrice >= candles[candles.length - 2]?.close
    : null

  return (
    <div className="flex flex-col h-screen bg-terminal-bg text-gray-100 font-sans overflow-hidden">
      <Toaster position="top-right" />

      {/* Session bar */}
      <SessionIndicator />

      {/* News warning banner */}
      <NewsWarningBanner lastMessage={lastMessage} />

      {/* Alert notifications */}
      <KeyLevelAlert lastMessage={lastMessage} pair={activePair} />

      {/* Ticker */}
      <LiveTicker />

      {/* Pair selector */}
      <div className="flex items-center gap-0 px-4 pt-3 pb-0 border-b border-terminal-border">
        {PAIRS.map((pair) => (
          <button
            key={pair}
            onClick={() => setActivePair(pair)}
            className={`px-4 py-2 text-sm font-mono font-medium border-b-2 transition-colors ${
              activePair === pair
                ? 'border-green-400 text-green-400'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            {pair}
          </button>
        ))}

        {/* Connection status + user */}
        <div className="ml-auto flex items-center gap-4 pb-2">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-500'}`} />
            <span className={`text-xs font-mono ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
              {isConnected ? 'Live' : connectionError ?? 'Reconnecting...'}
            </span>
          </div>
          {user && (
            <div className="flex items-center gap-2 border-l border-terminal-border pl-4">
              <span className="text-xs text-gray-500 font-mono">{user.full_name}</span>
              <button
                onClick={handleLogout}
                className="text-xs text-gray-600 hover:text-red-400 font-mono transition-colors"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chart — 70% */}
        <div className="flex-1 min-w-0 p-3">
          <PriceChart
            pair={activePair}
            candles={candles}
            consolidationZone={consolidationZone}
            alerts={alerts}
            newsEventTime={null}
          />
        </div>

        {/* Sidebar — 30% */}
        <div className="w-72 shrink-0 flex flex-col gap-4 p-4 border-l border-terminal-border overflow-y-auto">
          {/* Price display */}
          <div className="flex flex-col gap-1">
            <span className="text-gray-500 text-xs uppercase tracking-widest">{activePair}</span>
            <span
              className={`font-mono font-bold text-3xl ${
                isUp === true ? 'text-green-400' : isUp === false ? 'text-red-400' : 'text-gray-200'
              }`}
            >
              {currentPrice !== null ? currentPrice.toFixed(priceDigits) : '—'}
            </span>
            <div className="flex gap-3 text-xs font-mono text-gray-500">
              <span>
                Candles: <span className="text-gray-300">{candles.length}</span>
              </span>
            </div>
          </div>

          <div className="w-full h-px bg-terminal-border" />

          {/* Consolidation badge */}
          <ConsolidationOverlay pair={activePair} zone={consolidationZone} />

          <div className="w-full h-px bg-terminal-border" />

          {/* Alert panel */}
          <AlertPanel
            pair={activePair}
            alerts={alerts}
            onAlertAdded={handleAlertAdded}
            onAlertRemoved={handleAlertRemoved}
          />

          <div className="w-full h-px bg-terminal-border" />

          {/* News calendar */}
          <NewsCalendar />

          <div className="w-full h-px bg-terminal-border" />

          {/* Positions */}
          <PositionPnL currentPrice={currentPrice} activePair={activePair} />
        </div>
      </div>
    </div>
  )
}
