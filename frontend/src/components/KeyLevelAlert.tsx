import { useEffect } from 'react'
import toast from 'react-hot-toast'
import { Target, Lightning, Waves, TrendUp, TrendDown, Stack, ArrowsOutLineVertical } from '@phosphor-icons/react'
import { WSMessage, Pair, StructureAlert } from '../types'

interface KeyLevelAlertProps {
  lastMessage: WSMessage | null
  pair: Pair
  structureAlerts?: boolean
}

const STRUCTURE_STYLES = {
  BULLISH: { background: '#052e16', color: '#86efac', border: '1px solid #22c55e' },
  BEARISH: { background: '#450a0a', color: '#fca5a5', border: '1px solid #ef4444' },
}

const structureIcon = (alert: StructureAlert, color: string) => {
  const props = { size: 18, weight: 'bold' as const, color, 'aria-hidden': true }
  switch (alert.kind) {
    case 'SWEEP': return <Waves {...props} />
    case 'CHOCH': return alert.direction === 'BULLISH' ? <TrendUp {...props} /> : <TrendDown {...props} />
    case 'OB_TAP': return <Stack {...props} />
    default: return <ArrowsOutLineVertical {...props} />
  }
}

export const KeyLevelAlert = ({ lastMessage, pair, structureAlerts = true }: KeyLevelAlertProps) => {
  useEffect(() => {
    if (!lastMessage) return

    if (lastMessage.type === 'KEY_LEVEL_ALERT' && lastMessage.key_level_triggered) {
      const { level, direction } = lastMessage.key_level_triggered
      const digits = pair === 'USD/JPY' ? 3 : 5
      toast(
        `${pair} touched ${level.toFixed(digits)} (${direction})`,
        {
          duration: 5000,
          style: {
            background: '#1e3a5f',
            color: '#93c5fd',
            border: '1px solid #3b82f6',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '13px',
          },
          icon: <Target size={18} weight="bold" color="#93c5fd" aria-hidden="true" />,
        }
      )
    }

    if (structureAlerts && lastMessage.type === 'STRUCTURE_ALERT' && lastMessage.structure_alert) {
      const alert = lastMessage.structure_alert
      const style = STRUCTURE_STYLES[alert.direction] ?? STRUCTURE_STYLES.BULLISH
      toast(alert.message, {
        duration: 8000,
        style: { ...style, fontFamily: 'JetBrains Mono, monospace', fontSize: '13px' },
        icon: structureIcon(alert, style.color),
      })
    }

    if (lastMessage.type === 'NEWS_WARNING' && lastMessage.news_warning) {
      const { event, minutes_away, impact } = lastMessage.news_warning
      if (impact === 'HIGH') {
        toast(
          `HIGH IMPACT: ${event} in ${minutes_away}m`,
          {
            duration: 10000,
            style: {
              background: '#450a0a',
              color: '#fca5a5',
              border: '1px solid #ef4444',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '13px',
            },
            icon: <Lightning size={18} weight="bold" color="#fca5a5" aria-hidden="true" />,
          }
        )
      }
    }
  }, [lastMessage, pair, structureAlerts])

  return null
}
