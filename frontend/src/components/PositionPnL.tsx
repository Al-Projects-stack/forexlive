import { useState, useEffect } from 'react'
import { X, Sparkle, CircleNotch } from '@phosphor-icons/react'
import { Pair, PositionEntry, PAIRS } from '../types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const STORAGE_KEY = 'forexlive_positions'

interface ReviewState {
  loading: boolean
  text?: string
  error?: string
}

const loadPositions = (): PositionEntry[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

const savePositions = (positions: PositionEntry[]) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(positions))
}

interface PositionPnLProps {
  currentPrice: number | null
  activePair: Pair
}

const calcPnL = (pos: PositionEntry, currentPrice: number): number => {
  const diff = currentPrice - pos.entryPrice
  return pos.direction === 'LONG' ? diff * pos.quantity : -diff * pos.quantity
}

export const PositionPnL = ({ currentPrice, activePair }: PositionPnLProps) => {
  const [positions, setPositions] = useState<PositionEntry[]>(loadPositions)
  const [pair, setPair] = useState<Pair>(activePair)
  const [direction, setDirection] = useState<'LONG' | 'SHORT'>('LONG')
  const [entryPrice, setEntryPrice] = useState('')
  const [quantity, setQuantity] = useState('')
  const [reviews, setReviews] = useState<Record<string, ReviewState>>({})

  useEffect(() => {
    savePositions(positions)
  }, [positions])

  const handleReview = async (pos: PositionEntry) => {
    if (currentPrice === null) return
    const pnl = calcPnL(pos, currentPrice)
    const heldMinutes = Math.max(
      0,
      Math.round((Date.now() - new Date(pos.createdAt).getTime()) / 60000)
    )
    setReviews((prev) => ({ ...prev, [pos.id]: { loading: true } }))
    try {
      const res = await fetch(`${API_URL}/api/v1/trade-review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pair: pos.pair,
          direction: pos.direction,
          entry_price: pos.entryPrice,
          exit_price: currentPrice,
          quantity: pos.quantity,
          pnl,
          held_minutes: heldMinutes,
        }),
      })
      if (res.status === 503) {
        setReviews((prev) => ({
          ...prev,
          [pos.id]: { loading: false, error: 'AI review is not configured on the server.' },
        }))
        return
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: { review: string } = await res.json()
      setReviews((prev) => ({ ...prev, [pos.id]: { loading: false, text: data.review } }))
    } catch {
      setReviews((prev) => ({
        ...prev,
        [pos.id]: { loading: false, error: 'Could not generate a review. Try again.' },
      }))
    }
  }

  const handleAdd = () => {
    const ep = parseFloat(entryPrice)
    const q = parseFloat(quantity)
    if (isNaN(ep) || ep <= 0 || isNaN(q) || q <= 0) return
    const newPos: PositionEntry = {
      id: crypto.randomUUID(),
      pair,
      direction,
      entryPrice: ep,
      quantity: q,
      createdAt: new Date().toISOString(),
    }
    setPositions((prev) => [...prev, newPos])
    setEntryPrice('')
    setQuantity('')
  }

  const handleRemove = (id: string) => {
    setPositions((prev) => prev.filter((p) => p.id !== id))
  }

  const filtered = positions.filter((p) => p.pair === activePair)
  const totalPnL = currentPrice !== null
    ? filtered.reduce((sum, p) => sum + calcPnL(p, currentPrice), 0)
    : null
  const digits = activePair === 'USD/JPY' ? 3 : 5

  return (
    <div className="flex flex-col gap-3">
      <span className="text-gray-400 text-xs tracking-widest uppercase">Positions</span>

      <div className="flex flex-col gap-2">
        <div className="flex gap-2">
          <label htmlFor="position-pair" className="sr-only">Pair</label>
          <select
            id="position-pair"
            value={pair}
            onChange={(e) => setPair(e.target.value as Pair)}
            className="flex-1 bg-terminal-bg border border-terminal-border text-gray-200 text-xs px-2 py-1.5 rounded focus:outline-none focus:border-blue-500"
          >
            {PAIRS.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <label htmlFor="position-direction" className="sr-only">Direction</label>
          <select
            id="position-direction"
            value={direction}
            onChange={(e) => setDirection(e.target.value as 'LONG' | 'SHORT')}
            className="bg-terminal-bg border border-terminal-border text-gray-200 text-xs px-2 py-1.5 rounded focus:outline-none focus:border-blue-500"
          >
            <option value="LONG">Long</option>
            <option value="SHORT">Short</option>
          </select>
        </div>
        <div className="flex gap-2">
          <label htmlFor="position-entry" className="sr-only">Entry price</label>
          <input
            id="position-entry"
            type="number"
            step="0.00001"
            value={entryPrice}
            onChange={(e) => setEntryPrice(e.target.value)}
            placeholder="Entry price"
            className="flex-1 bg-terminal-bg border border-terminal-border text-gray-200 text-xs font-mono px-2 py-1.5 rounded focus:outline-none focus:border-blue-500"
          />
          <label htmlFor="position-qty" className="sr-only">Quantity</label>
          <input
            id="position-qty"
            type="number"
            step="any"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="Qty"
            className="w-20 bg-terminal-bg border border-terminal-border text-gray-200 text-xs font-mono px-2 py-1.5 rounded focus:outline-none focus:border-blue-500"
          />
        </div>
        <button
          onClick={handleAdd}
          className="w-full py-1.5 text-xs font-semibold bg-emerald-700 hover:bg-emerald-600 text-white rounded transition-colors"
        >
          + Add Position
        </button>
      </div>

      {totalPnL !== null && filtered.length > 0 && (
        <div className={`flex items-center justify-between px-2 py-1.5 rounded text-xs font-mono ${
          totalPnL >= 0 ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
        }`}>
          <span>Total P&L</span>
          <span className="font-bold">{totalPnL >= 0 ? '+' : ''}{totalPnL.toFixed(2)}</span>
        </div>
      )}

      <div className="flex flex-col gap-1 max-h-48 overflow-y-auto">
        {filtered.length === 0 && (
          <span className="text-gray-600 text-xs">No open positions</span>
        )}
        {filtered.map((pos) => {
          const pnl = currentPrice !== null ? calcPnL(pos, currentPrice) : null
          const review = reviews[pos.id]
          return (
            <div
              key={pos.id}
              className={`flex flex-col gap-1.5 px-2 py-1.5 border rounded ${
                pnl !== null
                  ? pnl >= 0
                    ? 'bg-green-500/10 border-green-500/20'
                    : 'bg-red-500/10 border-red-500/20'
                  : 'bg-gray-500/10 border-gray-500/20'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-0.5 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-300 text-xs font-medium">{pos.pair}</span>
                    <span className={`text-[10px] font-mono ${pos.direction === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>
                      {pos.direction}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-gray-500 font-mono">
                    <span>Entry: {pos.entryPrice.toFixed(digits)}</span>
                    <span>Qty: {pos.quantity}</span>
                  </div>
                  {pnl !== null && (
                    <span className={`text-xs font-mono ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => handleReview(pos)}
                    disabled={currentPrice === null || review?.loading}
                    aria-label={`AI review of ${pos.direction.toLowerCase()} ${pos.pair} trade`}
                    title="AI trade review"
                    className="p-1 -m-1 text-gray-500 hover:text-blue-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    {review?.loading
                      ? <CircleNotch size={14} weight="bold" className="animate-spin" aria-hidden="true" />
                      : <Sparkle size={14} weight="bold" aria-hidden="true" />}
                  </button>
                  <button
                    onClick={() => handleRemove(pos.id)}
                    aria-label={`Remove ${pos.direction.toLowerCase()} ${pos.pair} position`}
                    className="p-1 -m-1 text-gray-600 hover:text-red-400 transition-colors"
                  >
                    <X size={14} weight="bold" aria-hidden="true" />
                  </button>
                </div>
              </div>

              {review?.text && (
                <div className="flex gap-1.5 rounded bg-blue-500/10 border border-blue-500/20 px-2 py-1.5">
                  <Sparkle size={12} weight="bold" className="shrink-0 mt-0.5 text-blue-300" aria-hidden="true" />
                  <p className="text-[11px] leading-relaxed text-blue-100 whitespace-pre-wrap">{review.text}</p>
                </div>
              )}
              {review?.error && (
                <p role="alert" className="text-[10px] text-amber-400 font-mono">{review.error}</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
