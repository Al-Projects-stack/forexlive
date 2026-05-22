import { ConsolidationZone, Pair } from '../types'

interface ConsolidationOverlayProps {
  pair: Pair
  zone: ConsolidationZone | null
}

export const ConsolidationOverlay = ({ pair, zone }: ConsolidationOverlayProps) => {
  if (!zone?.active) return null

  const pips = zone.upper && zone.lower ? ((zone.upper - zone.lower) / zone.lower * 10000).toFixed(1) : null

  return (
    <div className="flex flex-col gap-1 p-3 bg-amber-500/10 border border-amber-500/30 rounded">
      <div className="flex items-center justify-between">
        <span className="text-amber-400 font-semibold text-xs tracking-widest">CONSOLIDATING</span>
        {pips && <span className="text-amber-500/70 text-xs font-mono">{pips} pips</span>}
      </div>
      {zone.upper && zone.lower && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-1">
          <span className="text-gray-500 text-xs">Upper</span>
          <span className="text-amber-400 font-mono text-xs">{zone.upper.toFixed(pair === 'USD/JPY' ? 3 : 5)}</span>
          <span className="text-gray-500 text-xs">Mid</span>
          <span className="text-amber-400/70 font-mono text-xs">{zone.midpoint?.toFixed(pair === 'USD/JPY' ? 3 : 5)}</span>
          <span className="text-gray-500 text-xs">Lower</span>
          <span className="text-amber-400 font-mono text-xs">{zone.lower.toFixed(pair === 'USD/JPY' ? 3 : 5)}</span>
        </div>
      )}
    </div>
  )
}
