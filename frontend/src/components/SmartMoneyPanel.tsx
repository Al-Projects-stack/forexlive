import { Stack, ArrowsOutLineVertical, Waves, TrendUp, TrendDown, Bell, BellSlash } from '@phosphor-icons/react'
import { Pair, SmartMoneyZones, StructureAlert } from '../types'

interface SmartMoneyPanelProps {
  pair: Pair
  smartMoney: SmartMoneyZones | null
  show: boolean
  onToggle: () => void
  alertsOn: boolean
  onToggleAlerts: () => void
  recentAlerts: (StructureAlert & { at: string })[]
}

const KIND_LABELS: Record<StructureAlert['kind'], string> = {
  SWEEP: 'Sweep',
  CHOCH: 'CHoCH',
  OB_TAP: 'OB tap',
  FVG_TAP: 'FVG tap',
}

export const SmartMoneyPanel = ({
  pair, smartMoney, show, onToggle, alertsOn, onToggleAlerts, recentAlerts,
}: SmartMoneyPanelProps) => {
  const digits = pair === 'USD/JPY' ? 3 : 5
  const fmt = (n: number) => n.toFixed(digits)

  const hasSignals = Boolean(
    smartMoney && (
      smartMoney.order_blocks.length > 0 ||
      smartMoney.fair_value_gaps.length > 0 ||
      smartMoney.liquidity_sweep ||
      smartMoney.structure
    )
  )

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-gray-400 text-xs tracking-widest uppercase">Smart Money</span>
        <div className="flex items-center gap-1.5">
        <button
          onClick={onToggleAlerts}
          aria-pressed={alertsOn}
          aria-label={alertsOn ? 'Mute structure alerts' : 'Turn on structure alerts'}
          title={alertsOn ? 'Alerts on: sweeps, CHoCH, OB and FVG taps' : 'Structure alerts muted'}
          className={`p-1 rounded border transition-colors ${
            alertsOn
              ? 'border-blue-500/40 bg-blue-500/10 text-blue-300'
              : 'border-terminal-border text-gray-600 hover:text-gray-400'
          }`}
        >
          {alertsOn
            ? <Bell size={12} weight="bold" aria-hidden="true" />
            : <BellSlash size={12} weight="bold" aria-hidden="true" />}
        </button>
        <button
          onClick={onToggle}
          aria-pressed={show}
          className={`text-[10px] font-mono px-2 py-0.5 rounded border transition-colors ${
            show
              ? 'border-blue-500/40 bg-blue-500/10 text-blue-300'
              : 'border-terminal-border text-gray-600 hover:text-gray-400'
          }`}
        >
          {show ? 'ON' : 'OFF'}
        </button>
        </div>
      </div>

      {!show && (
        <span className="text-gray-600 text-xs">Overlay hidden</span>
      )}

      {show && !hasSignals && (
        <span className="text-gray-600 text-xs">No active signals</span>
      )}

      {show && smartMoney?.structure && (
        <div
          className={`flex items-center gap-2 px-2 py-1.5 rounded border text-xs ${
            smartMoney.structure.type === 'BOS'
              ? 'bg-blue-500/10 border-blue-500/20 text-blue-300'
              : 'bg-purple-500/10 border-purple-500/20 text-purple-300'
          }`}
        >
          {smartMoney.structure.direction === 'BULLISH'
            ? <TrendUp size={14} weight="bold" aria-hidden="true" />
            : <TrendDown size={14} weight="bold" aria-hidden="true" />}
          <span className="font-semibold">{smartMoney.structure.type}</span>
          <span className="text-gray-500 ml-auto font-mono">{fmt(smartMoney.structure.level)}</span>
        </div>
      )}

      {show && smartMoney?.liquidity_sweep && (
        <div className="flex items-center gap-2 px-2 py-1.5 rounded border bg-amber-500/10 border-amber-500/20 text-amber-300 text-xs">
          <Waves size={14} weight="bold" aria-hidden="true" />
          <span className="font-semibold">
            {smartMoney.liquidity_sweep.type === 'HIGH_SWEEP' ? 'Liquidity swept (high)' : 'Liquidity swept (low)'}
          </span>
          <span className="text-gray-500 ml-auto font-mono">{fmt(smartMoney.liquidity_sweep.level)}</span>
        </div>
      )}

      {show && smartMoney?.order_blocks && smartMoney.order_blocks.length > 0 && (
        <div className="flex flex-col gap-1">
          {smartMoney.order_blocks.map((ob, i) => (
            <div
              key={`ob-${i}`}
              className={`flex items-center gap-2 px-2 py-1 rounded border text-xs ${
                ob.type === 'BULLISH'
                  ? 'bg-green-500/10 border-green-500/20 text-green-300'
                  : 'bg-red-500/10 border-red-500/20 text-red-300'
              }`}
            >
              <Stack size={14} weight="bold" aria-hidden="true" />
              <span>{ob.type === 'BULLISH' ? 'Bullish OB' : 'Bearish OB'}</span>
              <span className="text-gray-500 ml-auto font-mono">{fmt(ob.bottom)}–{fmt(ob.top)}</span>
            </div>
          ))}
        </div>
      )}

      {show && smartMoney?.fair_value_gaps && smartMoney.fair_value_gaps.length > 0 && (
        <div className="flex flex-col gap-1">
          {smartMoney.fair_value_gaps.map((fvg, i) => (
            <div
              key={`fvg-${i}`}
              className={`flex items-center gap-2 px-2 py-1 rounded border text-xs ${
                fvg.type === 'BULLISH'
                  ? 'bg-blue-500/10 border-blue-500/20 text-blue-300'
                  : 'bg-purple-500/10 border-purple-500/20 text-purple-300'
              }`}
            >
              <ArrowsOutLineVertical size={14} weight="bold" aria-hidden="true" />
              <span>{fvg.type === 'BULLISH' ? 'Bullish FVG' : 'Bearish FVG'}</span>
              <span className="text-gray-500 ml-auto font-mono">{fmt(fvg.bottom)}–{fmt(fvg.top)}</span>
            </div>
          ))}
        </div>
      )}

      {recentAlerts.length > 0 && (
        <div className="flex flex-col gap-1 mt-1">
          <span className="text-[10px] text-gray-600 uppercase tracking-widest">Recent alerts</span>
          {recentAlerts.map((a, i) => (
            <div key={`${a.at}-${i}`} className="flex items-center gap-2 text-[11px] font-mono">
              <span className="text-gray-600">
                {new Date(a.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              <span className={a.direction === 'BULLISH' ? 'text-green-400' : 'text-red-400'}>
                {KIND_LABELS[a.kind]}
              </span>
              <span className="text-gray-500 ml-auto">
                {a.level != null
                  ? fmt(a.level)
                  : a.bottom != null && a.top != null ? `${fmt(a.bottom)}–${fmt(a.top)}` : ''}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
