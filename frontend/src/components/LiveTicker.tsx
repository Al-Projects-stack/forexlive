import { useState, useEffect } from 'react'
import { PAIRS, Pair, TickerEntry } from '../types'
import { useWebSocket } from '../hooks/useWebSocket'

const TickerItem = ({ pair }: { pair: Pair }) => {
  const { lastMessage } = useWebSocket(pair)
  const [entry, setEntry] = useState<TickerEntry>({
    pair,
    price: 0,
    previousPrice: 0,
    change: 0,
    changePct: 0,
  })

  useEffect(() => {
    if (!lastMessage?.price) return
    setEntry((prev) => {
      const price = lastMessage.price!
      const change = prev.price > 0 ? price - prev.price : 0
      const changePct = prev.price > 0 ? (change / prev.price) * 100 : 0
      return { ...prev, previousPrice: prev.price, price, change, changePct }
    })
  }, [lastMessage])

  const isUp = entry.change >= 0
  const priceColor = entry.change > 0 ? 'text-green-400' : entry.change < 0 ? 'text-red-400' : 'text-gray-300'
  const digits = pair === 'USD/JPY' ? 3 : 5

  return (
    <div className="flex items-center gap-2 px-4 py-1.5 border-r border-terminal-border shrink-0">
      <span className="text-gray-400 text-xs">{pair}</span>
      <span className={`font-mono font-semibold text-sm ${priceColor}`}>
        {entry.price > 0 ? entry.price.toFixed(digits) : '—'}
      </span>
      {entry.price > 0 && (
        <span className={`text-xs font-mono ${isUp ? 'text-green-500' : 'text-red-500'}`}>
          {isUp ? '▲' : '▼'} {Math.abs(entry.changePct).toFixed(3)}%
        </span>
      )}
    </div>
  )
}

export const LiveTicker = () => {
  return (
    <div className="flex items-center bg-terminal-surface border-b border-terminal-border overflow-x-auto">
      <div className="flex items-center px-3 py-1.5 text-xs text-gray-500 border-r border-terminal-border shrink-0">
        LIVE
      </div>
      {PAIRS.map((pair) => (
        <TickerItem key={pair} pair={pair} />
      ))}
    </div>
  )
}
