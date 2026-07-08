export type Pair = 'USD/JPY' | 'EUR/USD' | 'GBP/USD' | 'USD/ZAR'

export const PAIRS: Pair[] = ['USD/JPY', 'EUR/USD', 'GBP/USD', 'USD/ZAR']

export interface Candle {
  open: number
  high: number
  low: number
  close: number
  volume: number
  timestamp?: string
}

export interface ConsolidationZone {
  active: boolean
  upper: number | null
  lower: number | null
  midpoint: number | null
}

export interface KeyLevelTriggered {
  level: number
  direction: 'ABOVE' | 'BELOW' | 'EITHER'
}

export interface NewsWarning {
  event: string
  minutes_away: number
  impact: 'HIGH' | 'MEDIUM' | 'LOW'
}

export type WSMessageType =
  | 'CANDLE_UPDATE'
  | 'KEY_LEVEL_ALERT'
  | 'NEWS_WARNING'
  | 'CONSOLIDATION'
  | 'CONNECTED'
  | 'PING'

export interface WSMessage {
  type: WSMessageType
  pair: Pair
  timestamp: string
  price?: number
  candle?: Candle
  consolidation_zone?: ConsolidationZone
  key_level_triggered?: KeyLevelTriggered
  news_warning?: NewsWarning
}

export interface Alert {
  id: number
  pair: Pair
  level: number
  direction: 'ABOVE' | 'BELOW' | 'EITHER'
  active: boolean
  created_at: string
}

export interface NewsEvent {
  name: string
  currency: string
  impact: 'HIGH' | 'MEDIUM' | 'LOW'
  scheduled_at: string
  minutes_away: number
}

export type Session = 'Tokyo' | 'London' | 'New York' | 'Overlap' | 'Off-Hours'

export interface SessionInfo {
  name: Session
  active: boolean
  start: string
  end: string
  color: string
}

export interface TickerEntry {
  pair: Pair
  price: number
  previousPrice: number
  bid?: number
  ask?: number
  change: number
  changePct: number
}

export type PositionDirection = 'LONG' | 'SHORT'

export interface PositionEntry {
  id: string
  pair: Pair
  direction: PositionDirection
  entryPrice: number
  quantity: number
  createdAt: string
}
