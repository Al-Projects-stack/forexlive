import { useState, useEffect, useRef } from 'react'
import { Candle, Pair, ConsolidationZone, WSMessage } from '../types'
import { useWebSocket } from './useWebSocket'

const MAX_CANDLES = 100

export interface UseChartDataResult {
  candles: Candle[]
  currentPrice: number | null
  consolidationZone: ConsolidationZone | null
  lastMessage: WSMessage | null
  isConnected: boolean
  connectionError: string | null
}

export const useChartData = (pair: Pair): UseChartDataResult => {
  const [candles, setCandles] = useState<Candle[]>([])
  const [currentPrice, setCurrentPrice] = useState<number | null>(null)
  const [consolidationZone, setConsolidationZone] = useState<ConsolidationZone | null>(null)
  const { isConnected, lastMessage, connectionError } = useWebSocket(pair)
  const candleMapRef = useRef<Map<string, Candle>>(new Map())

  useEffect(() => {
    // Reset on pair change
    setCandles([])
    setCurrentPrice(null)
    setConsolidationZone(null)
    candleMapRef.current = new Map()
  }, [pair])

  useEffect(() => {
    if (!lastMessage) return
    if (lastMessage.pair !== pair) return

    if (lastMessage.price !== undefined) {
      setCurrentPrice(lastMessage.price)
    }

    if (lastMessage.consolidation_zone) {
      setConsolidationZone(lastMessage.consolidation_zone)
    }

    if (lastMessage.candle && lastMessage.timestamp) {
      const minuteKey = lastMessage.timestamp.slice(0, 16) // "YYYY-MM-DDTHH:MM"
      candleMapRef.current.set(minuteKey, {
        ...lastMessage.candle,
        timestamp: lastMessage.timestamp,
      })

      const sorted = Array.from(candleMapRef.current.entries())
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([, c]) => c)
        .slice(-MAX_CANDLES)

      setCandles(sorted)
    }
  }, [lastMessage, pair])

  return { candles, currentPrice, consolidationZone, lastMessage, isConnected, connectionError }
}
