import { Link } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'

const TICKER_PAIRS = [
  { pair: 'EUR/USD', price: '1.08432', change: '+0.021%', up: true },
  { pair: 'USD/JPY', price: '149.872', change: '-0.043%', up: false },
  { pair: 'GBP/USD', price: '1.26541', change: '+0.018%', up: true },
  { pair: 'USD/ZAR', price: '18.6230', change: '+0.127%', up: true },
]

const FEATURES = [
  {
    icon: '⚡',
    title: 'Live WebSocket Streaming',
    desc: 'Tick-level price data delivered over WebSocket with zero polling. Price updates the instant the market moves.',
  },
  {
    icon: '📊',
    title: 'Consolidation Detector',
    desc: 'Automatically identifies when price is ranging. A shaded zone appears on the chart when the last 20 candles stay within 0.15%.',
  },
  {
    icon: '🎯',
    title: 'Key Level Alerts',
    desc: 'Set a price level once. Get an instant browser notification the moment price crosses it — no tab-watching needed.',
  },
  {
    icon: '📰',
    title: 'News Impact Calendar',
    desc: 'High-impact events with live countdowns. A red banner fires when a HIGH-impact release is within 5 minutes.',
  },
  {
    icon: '🌏',
    title: 'Session Indicator',
    desc: 'Tokyo, London, New York and the London/NY overlap — all displayed in SAST. Know exactly which session is driving liquidity.',
  },
  {
    icon: '🔒',
    title: 'Secure & Persistent',
    desc: 'Your key levels are saved across sessions. JWT-authenticated, rate-limited API. Nothing exposed to the client.',
  },
]

function AnimatedPrice() {
  const [price, setPrice] = useState(1.08432)
  const [up, setUp] = useState(true)

  useEffect(() => {
    const id = setInterval(() => {
      const delta = (Math.random() - 0.5) * 0.0003
      setPrice(p => {
        const next = parseFloat((p + delta).toFixed(5))
        setUp(next >= p)
        return next
      })
    }, 900)
    return () => clearInterval(id)
  }, [])

  return (
    <span className={`font-mono font-bold tabular-nums transition-colors duration-300 ${up ? 'text-green-400' : 'text-red-400'}`}>
      {price.toFixed(5)}
    </span>
  )
}

export const Landing = () => {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-sans overflow-x-hidden">

      {/* Nav */}
      <nav className="fixed top-0 inset-x-0 z-50 flex items-center justify-between px-6 py-4 bg-gray-950/80 backdrop-blur border-b border-gray-800">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="font-mono font-bold text-white tracking-wider text-lg">ForexLive</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="text-sm text-gray-400 hover:text-white transition-colors px-4 py-2">
            Sign In
          </Link>
          <Link to="/register" className="text-sm font-semibold bg-green-500 hover:bg-green-400 text-gray-950 px-4 py-2 rounded transition-colors">
            Get Started
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative flex flex-col items-center justify-center min-h-screen px-6 pt-20 text-center overflow-hidden">
        {/* Grid background */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(74,222,128,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(74,222,128,0.03)_1px,transparent_1px)] bg-[size:60px_60px]" />
        {/* Radial glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-green-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-green-500/30 bg-green-500/10 text-green-400 text-xs font-mono mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            LIVE — EUR/USD streaming now
          </div>

          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 leading-tight">
            Real-time forex<br />
            <span className="text-green-400">built for traders</span>
          </h1>

          <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            WebSocket-streamed G30 prices, automatic consolidation detection, instant key level alerts,
            and session-aware news — all in a single dark terminal dashboard.
          </p>

          {/* Live price card */}
          <div className="inline-flex items-center gap-4 px-6 py-4 bg-gray-900 border border-gray-700 rounded-xl mb-10 font-mono">
            <span className="text-gray-400 text-sm">EUR/USD</span>
            <AnimatedPrice />
            <span className="text-xs text-green-500 bg-green-500/10 px-2 py-0.5 rounded">LIVE</span>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/register"
              className="w-full sm:w-auto px-8 py-4 bg-green-500 hover:bg-green-400 text-gray-950 font-bold rounded-lg text-base transition-all hover:scale-105 active:scale-95"
            >
              Start Trading Free
            </Link>
            <Link
              to="/login"
              className="w-full sm:w-auto px-8 py-4 border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white font-semibold rounded-lg text-base transition-colors"
            >
              Sign In
            </Link>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-gray-600 text-xs">
          <span>SCROLL</span>
          <div className="w-px h-8 bg-gradient-to-b from-gray-600 to-transparent" />
        </div>
      </section>

      {/* Live Ticker strip */}
      <div className="border-y border-gray-800 bg-gray-900/50 overflow-hidden">
        <div className="flex animate-[ticker_20s_linear_infinite]">
          {[...TICKER_PAIRS, ...TICKER_PAIRS].map((t, i) => (
            <div key={i} className="flex items-center gap-3 px-8 py-3 shrink-0 border-r border-gray-800">
              <span className="text-gray-500 text-sm font-mono">{t.pair}</span>
              <span className="font-mono font-semibold text-gray-100">{t.price}</span>
              <span className={`text-xs font-mono ${t.up ? 'text-green-400' : 'text-red-400'}`}>
                {t.up ? '▲' : '▼'} {t.change}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Everything a price action trader needs
          </h2>
          <p className="text-gray-400 text-lg max-w-xl mx-auto">
            No fluff. No lagging indicators. Just raw price data and the tools that matter.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="p-6 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-600 transition-colors group"
            >
              <div className="text-2xl mb-4">{f.icon}</div>
              <h3 className="font-semibold text-white mb-2 group-hover:text-green-400 transition-colors">
                {f.title}
              </h3>
              <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Dashboard preview mock */}
      <section className="max-w-6xl mx-auto px-6 pb-24">
        <div className="relative rounded-2xl border border-gray-800 overflow-hidden bg-gray-900">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-gray-950 z-10 pointer-events-none" />
          {/* Mock terminal header */}
          <div className="flex items-center gap-2 px-4 py-3 bg-gray-800/60 border-b border-gray-700">
            <span className="w-3 h-3 rounded-full bg-red-500/70" />
            <span className="w-3 h-3 rounded-full bg-yellow-500/70" />
            <span className="w-3 h-3 rounded-full bg-green-500/70" />
            <span className="ml-4 text-xs text-gray-500 font-mono">ForexLive — EUR/USD — 1m</span>
            <span className="ml-auto flex items-center gap-1.5 text-xs text-green-400 font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              LIVE
            </span>
          </div>
          {/* Mock chart area */}
          <div className="p-6 h-64 flex items-center justify-center">
            <div className="w-full h-full relative overflow-hidden">
              {/* Fake candles */}
              <div className="flex items-end gap-1 h-full px-4 justify-center">
                {[40,55,35,62,48,70,45,80,60,55,72,50,65,42,58,75,48,82,55,70,45,88,62,74,50,66,78,55,82,70].map((h, i) => (
                  <div key={i} className="flex flex-col items-center gap-0.5 flex-1 max-w-[12px]">
                    <div className={`w-px mx-auto ${i % 3 === 0 ? 'bg-green-500' : 'bg-red-500'}`} style={{ height: `${h * 0.3}px` }} />
                    <div className={`w-full rounded-sm ${i % 3 === 0 ? 'bg-green-500' : 'bg-red-500'}`} style={{ height: `${h * 0.5}px` }} />
                    <div className={`w-px mx-auto ${i % 3 === 0 ? 'bg-green-500' : 'bg-red-500'}`} style={{ height: `${h * 0.2}px` }} />
                  </div>
                ))}
              </div>
              {/* Consolidation zone mock */}
              <div className="absolute left-8 right-8 border-y border-amber-400/40 bg-amber-400/5" style={{ top: '35%', height: '18%' }} />
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-gray-800 py-24 px-6 text-center">
        <h2 className="text-3xl md:text-4xl font-bold mb-4">Ready to trade smarter?</h2>
        <p className="text-gray-400 mb-8 max-w-md mx-auto">
          Free account. Live EUR/USD stream. No credit card required.
        </p>
        <Link
          to="/register"
          className="inline-block px-10 py-4 bg-green-500 hover:bg-green-400 text-gray-950 font-bold rounded-lg text-lg transition-all hover:scale-105 active:scale-95"
        >
          Create Free Account
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8 px-6 text-center text-gray-600 text-sm font-mono">
        <span>ForexLive</span>
        <span className="mx-3 text-gray-700">·</span>
        <span>Built by Al Mujati</span>
        <span className="mx-3 text-gray-700">·</span>
        <span>G30 price action dashboard</span>
      </footer>

      <style>{`
        @keyframes ticker {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  )
}
