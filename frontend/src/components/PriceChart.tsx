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
import { Candle, ConsolidationZone, Alert, Pair } from '../types'

interface PriceChartProps {
  pair: Pair
  candles: Candle[]
  consolidationZone: ConsolidationZone | null
  alerts: Alert[]
  newsEventTime?: string | null
}

function toUnixTime(timestamp: string): Time {
  return Math.floor(new Date(timestamp).getTime() / 1000) as Time
}

export const PriceChart = ({ pair: _pair, candles, consolidationZone, alerts, newsEventTime: _newsEventTime }: PriceChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const consolidationTopRef = useRef<ISeriesApi<'Line'> | null>(null)
  const consolidationBotRef = useRef<ISeriesApi<'Line'> | null>(null)
  const priceLinesRef = useRef<IPriceLine[]>([])

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

  return <div ref={containerRef} className="w-full h-full" />
}
