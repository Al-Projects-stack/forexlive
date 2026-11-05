import { useEffect, useRef } from 'react'
import {
  createChart,
  IChartApi,
  ISeriesApi,
  IPriceLine,
  Time,
  ColorType,
  LineStyle,
} from 'lightweight-charts'
import { Candle, ConsolidationZone, Alert, Pair, SmartMoneyZones } from '../types'

interface PriceChartProps {
  pair: Pair
  candles: Candle[]
  consolidationZone: ConsolidationZone | null
  alerts: Alert[]
  newsEventTime?: string | null
  smartMoney?: SmartMoneyZones | null
  showSmartMoney?: boolean
}

function toUnixTime(timestamp: string): Time {
  return Math.floor(new Date(timestamp).getTime() / 1000) as Time
}

const ORDER_BLOCK_COLORS = {
  BULLISH: 'rgba(74, 222, 128, 0.55)',
  BEARISH: 'rgba(248, 113, 113, 0.55)',
}

const FVG_COLORS = {
  BULLISH: 'rgba(96, 165, 250, 0.5)',
  BEARISH: 'rgba(192, 132, 252, 0.5)',
}

export const PriceChart = ({
  pair: _pair,
  candles,
  consolidationZone,
  alerts,
  newsEventTime: _newsEventTime,
  smartMoney,
  showSmartMoney = true,
}: PriceChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const consolidationTopRef = useRef<ISeriesApi<'Line'> | null>(null)
  const consolidationBotRef = useRef<ISeriesApi<'Line'> | null>(null)
  const priceLinesRef = useRef<IPriceLine[]>([])
  const zoneSeriesRef = useRef<ISeriesApi<'Line'>[]>([])
  const structureLineRef = useRef<IPriceLine | null>(null)

  // Initialise chart once
  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#030712' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: '#1f2937' },
        horzLines: { color: '#1f2937' },
      },
      crosshair: {
        vertLine: { color: '#4b5563', width: 1, style: LineStyle.Dashed },
        horzLine: { color: '#4b5563', width: 1, style: LineStyle.Dashed },
      },
      rightPriceScale: { borderColor: '#1f2937' },
      timeScale: { borderColor: '#1f2937', timeVisible: true, secondsVisible: false },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
    })

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#4ade80',
      downColor: '#f87171',
      borderUpColor: '#4ade80',
      borderDownColor: '#f87171',
      wickUpColor: '#4ade80',
      wickDownColor: '#f87171',
    })

    const consolidationTop = chart.addLineSeries({
      color: 'rgba(251, 191, 36, 0.6)',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })

    const consolidationBot = chart.addLineSeries({
      color: 'rgba(251, 191, 36, 0.6)',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })

    chartRef.current = chart
    candleSeriesRef.current = candleSeries
    consolidationTopRef.current = consolidationTop
    consolidationBotRef.current = consolidationBot

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [])

  // Update candles
  useEffect(() => {
    if (!candleSeriesRef.current || candles.length === 0) return

    const data = candles
      .filter((c) => c.timestamp)
      .map((c) => ({
        time: toUnixTime(c.timestamp!),
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
      .sort((a, b) => (a.time as number) - (b.time as number))

    if (data.length > 0) {
      candleSeriesRef.current.setData(data)
      chartRef.current?.timeScale().fitContent()
    }
  }, [candles])

  // Draw key level lines
  useEffect(() => {
    if (!candleSeriesRef.current) return
    const series = candleSeriesRef.current

    priceLinesRef.current.forEach((pl) => {
      try { series.removePriceLine(pl) } catch { /* already removed */ }
    })

    priceLinesRef.current = alerts.map((alert) =>
      series.createPriceLine({
        price: alert.level,
        color: '#60a5fa',
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: `${alert.direction} ${alert.level}`,
      })
    )
  }, [alerts])

  // Update consolidation zone
  useEffect(() => {
    if (!consolidationTopRef.current || !consolidationBotRef.current) return
    if (!consolidationZone?.active || !consolidationZone.upper || !consolidationZone.lower) {
      consolidationTopRef.current.setData([])
      consolidationBotRef.current.setData([])
      return
    }

    if (candles.length < 2) return

    const first = candles[Math.max(0, candles.length - 20)]
    const last = candles[candles.length - 1]
    if (!first.timestamp || !last.timestamp) return

    const startTime = toUnixTime(first.timestamp)
    const endTime = toUnixTime(last.timestamp)

    consolidationTopRef.current.setData([
      { time: startTime, value: consolidationZone.upper },
      { time: endTime, value: consolidationZone.upper },
    ])
    consolidationBotRef.current.setData([
      { time: startTime, value: consolidationZone.lower },
      { time: endTime, value: consolidationZone.lower },
    ])
  }, [consolidationZone, candles])

  // Smart Money Concepts: order block + fair value gap zones (dashed boundary pairs,
  // same drawing technique as the consolidation zone above)
  useEffect(() => {
    const chart = chartRef.current
    if (!chart) return

    zoneSeriesRef.current.forEach((series) => {
      try { chart.removeSeries(series) } catch { /* chart already torn down */ }
    })
    zoneSeriesRef.current = []

    if (!showSmartMoney || candles.length < 2) return
    const first = candles[Math.max(0, candles.length - 20)]
    const last = candles[candles.length - 1]
    if (!first.timestamp || !last.timestamp) return
    const startTime = toUnixTime(first.timestamp)
    const endTime = toUnixTime(last.timestamp)

    const drawZone = (top: number, bottom: number, color: string) => {
      const topSeries = chart.addLineSeries({
        color, lineWidth: 1, lineStyle: LineStyle.Dotted,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      })
      const bottomSeries = chart.addLineSeries({
        color, lineWidth: 1, lineStyle: LineStyle.Dotted,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      })
      topSeries.setData([{ time: startTime, value: top }, { time: endTime, value: top }])
      bottomSeries.setData([{ time: startTime, value: bottom }, { time: endTime, value: bottom }])
      zoneSeriesRef.current.push(topSeries, bottomSeries)
    }

    smartMoney?.order_blocks?.forEach((ob) => drawZone(ob.top, ob.bottom, ORDER_BLOCK_COLORS[ob.type]))
    smartMoney?.fair_value_gaps?.forEach((fvg) => drawZone(fvg.top, fvg.bottom, FVG_COLORS[fvg.type]))
  }, [smartMoney?.order_blocks, smartMoney?.fair_value_gaps, showSmartMoney, candles])

  // Smart Money Concepts: market structure (BOS / CHoCH) as a labelled price line
  useEffect(() => {
    const series = candleSeriesRef.current
    if (!series) return

    if (structureLineRef.current) {
      try { series.removePriceLine(structureLineRef.current) } catch { /* already removed */ }
      structureLineRef.current = null
    }

    if (!showSmartMoney || !smartMoney?.structure) return
    const { type, direction, level } = smartMoney.structure
    structureLineRef.current = series.createPriceLine({
      price: level,
      color: type === 'BOS' ? '#60a5fa' : '#c084fc',
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      axisLabelVisible: true,
      title: `${type} ${direction === 'BULLISH' ? '▲' : '▼'}`,
    })
  }, [smartMoney?.structure, showSmartMoney])

  // Smart Money Concepts: liquidity sweep marker on the triggering candle
  useEffect(() => {
    const series = candleSeriesRef.current
    if (!series) return

    if (!showSmartMoney || !smartMoney?.liquidity_sweep?.timestamp) {
      series.setMarkers([])
      return
    }

    const sweep = smartMoney.liquidity_sweep
    series.setMarkers([
      {
        time: toUnixTime(sweep.timestamp!),
        position: sweep.type === 'HIGH_SWEEP' ? 'aboveBar' : 'belowBar',
        color: sweep.type === 'HIGH_SWEEP' ? '#f87171' : '#4ade80',
        shape: sweep.type === 'HIGH_SWEEP' ? 'arrowDown' : 'arrowUp',
        text: 'SWEEP',
      },
    ])
  }, [smartMoney?.liquidity_sweep, showSmartMoney])

  return <div ref={containerRef} className="w-full h-full" />
}
