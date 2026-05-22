import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function FieldError({ msg }: { msg: string }) {
  return <p className="text-red-400 text-xs mt-1 font-mono">{msg}</p>
}

function PasswordStrength({ password }: { password: string }) {
  const checks = [
    { label: '8+ characters', ok: password.length >= 8 },
    { label: 'Uppercase letter', ok: /[A-Z]/.test(password) },
    { label: 'Lowercase letter', ok: /[a-z]/.test(password) },
    { label: 'Number', ok: /\d/.test(password) },
  ]
  const score = checks.filter(c => c.ok).length
  const colors = ['bg-gray-700', 'bg-red-500', 'bg-yellow-500', 'bg-blue-500', 'bg-green-500']
  const labels = ['', 'Weak', 'Fair', 'Good', 'Strong']

  if (!password) return null

  return (
    <div className="mt-2 space-y-2">
      <div className="flex gap-1">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${i <= score ? colors[score] : 'bg-gray-700'}`} />
        ))}
        <span className={`text-xs ml-1 font-mono ${colors[score].replace('bg-', 'text-')}`}>{labels[score]}</span>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {checks.map(c => (
          <span key={c.label} className={`text-xs font-mono flex items-center gap-1 ${c.ok ? 'text-green-400' : 'text-gray-600'}`}>
            {c.ok ? '✓' : '○'} {c.label}
          </span>
        ))}
      </div>
    </div>
  )
}

export const Register = () => {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [serverError, setServerError] = useState('')
  const [loading, setLoading] = useState(false)

  const validate = () => {
    const e: Record<string, string> = {}
    if (!fullName.trim() || fullName.trim().length < 2) e.fullName = 'Enter your full name (min 2 characters)'
    if (!email.trim()) e.email = 'Email is required'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = 'Enter a valid email address'
    if (!password) e.password = 'Password is required'
    else if (password.length < 8) e.password = 'Password must be at least 8 characters'
    else if (!/[A-Z]/.test(password)) e.password = 'Password needs at least one uppercase letter'
    else if (!/[a-z]/.test(password)) e.password = 'Password needs at least one lowercase letter'
    else if (!/\d/.test(password)) e.password = 'Password needs at least one number'
    if (!confirm) e.confirm = 'Please confirm your password'
    else if (confirm !== password) e.confirm = 'Passwords do not match'
    return e
  }

  const handleSubmit = async (ev: FormEvent) => {
    ev.preventDefault()
    setServerError('')
    const e = validate()
    setErrors(e)
    if (Object.keys(e).length > 0) return

    setLoading(true)
    try {
      await register(email.trim().toLowerCase(), password, fullName.trim())
      navigate('/dashboard')
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const clear = (field: string) => setErrors(v => ({ ...v, [field]: '' }))

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4 py-12">
      <div className="fixed inset-0 bg-[linear-gradient(rgba(74,222,128,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(74,222,128,0.02)_1px,transparent_1px)] bg-[size:60px_60px] pointer-events-none" />

      <div className="relative w-full max-w-md">
        <div className="flex items-center justify-center gap-2 mb-8">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <Link to="/" className="font-mono font-bold text-white text-xl tracking-wider hover:text-green-400 transition-colors">
            ForexLive
          </Link>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 shadow-2xl">
          <h1 className="text-2xl font-bold text-white mb-1">Create account</h1>
          <p className="text-gray-500 text-sm mb-8">Start trading with live forex data</p>

          {serverError && (
            <div className="flex items-center gap-2 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm mb-6">
              <span>⚠</span> {serverError}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="space-y-5">
            <div>
              <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={e => { setFullName(e.target.value); clear('fullName') }}
                placeholder="Al Mujati"
                className={`w-full bg-gray-800 border text-gray-100 text-sm px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500/50 transition-colors placeholder-gray-600 ${errors.fullName ? 'border-red-500' : 'border-gray-700 focus:border-green-500'}`}
              />
              {errors.fullName && <FieldError msg={errors.fullName} />}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => { setEmail(e.target.value); clear('email') }}
                placeholder="trader@example.com"
                className={`w-full bg-gray-800 border text-gray-100 text-sm px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500/50 transition-colors placeholder-gray-600 ${errors.email ? 'border-red-500' : 'border-gray-700 focus:border-green-500'}`}
              />
              {errors.email && <FieldError msg={errors.email} />}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => { setPassword(e.target.value); clear('password') }}
                placeholder="••••••••"
                className={`w-full bg-gray-800 border text-gray-100 text-sm px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500/50 transition-colors placeholder-gray-600 ${errors.password ? 'border-red-500' : 'border-gray-700 focus:border-green-500'}`}
              />
              <PasswordStrength password={password} />
              {errors.password && <FieldError msg={errors.password} />}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">
                Confirm Password
              </label>
              <input
                type="password"
                value={confirm}
                onChange={e => { setConfirm(e.target.value); clear('confirm') }}
                placeholder="••••••••"
                className={`w-full bg-gray-800 border text-gray-100 text-sm px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500/50 transition-colors placeholder-gray-600 ${
                  errors.confirm ? 'border-red-500' : confirm && confirm === password ? 'border-green-500' : 'border-gray-700 focus:border-green-500'
                }`}
              />
              {errors.confirm && <FieldError msg={errors.confirm} />}
              {confirm && confirm === password && !errors.confirm && (
                <p className="text-green-400 text-xs mt-1 font-mono">✓ Passwords match</p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-green-500 hover:bg-green-400 disabled:opacity-50 disabled:cursor-not-allowed text-gray-950 font-bold rounded-lg transition-all hover:scale-[1.02] active:scale-[0.98] text-sm"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-gray-950 border-t-transparent rounded-full animate-spin" />
                  Creating account...
                </span>
              ) : 'Create Account'}
            </button>
          </form>

          <p className="text-center text-sm text-gray-500 mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-green-400 hover:text-green-300 font-medium transition-colors">
              Sign in
            </Link>
          </p>
        </div>

        <p className="text-center text-xs text-gray-700 mt-6">
          <Link to="/" className="hover:text-gray-500 transition-colors">← Back to home</Link>
        </p>
      </div>
    </div>
  )
}
