import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function Login({ onLoggedIn }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.login(email, password) // sets the httpOnly cookie server-side
      await onLoggedIn?.()   
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[calc(100vh-73px)] flex items-center justify-center px-5 py-12">
      <div className="w-full max-w-sm">
        <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-signal mb-2">Case file access</p>
        <h1 className="font-display text-3xl sm:text-4xl mb-8 text-parchment">Sign in</h1>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block font-mono text-xs uppercase tracking-wider text-parchment/50 mb-1.5">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-md px-4 py-2.5 text-parchment placeholder:text-parchment/30 focus-ring focus:border-signal transition-colors"
              placeholder="you@company.com"
            />
          </div>
          <div>
            <label className="block font-mono text-xs uppercase tracking-wider text-parchment/50 mb-1.5">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-md px-4 py-2.5 text-parchment placeholder:text-parchment/30 focus-ring focus:border-signal transition-colors"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="text-rust text-sm font-mono border border-rust/30 bg-rust/10 rounded-md px-3 py-2">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-signal text-ink font-medium rounded-md py-2.5 hover:brightness-110 disabled:opacity-50 transition focus-ring"
          >
            {loading ? 'Verifying...' : 'Sign in'}
          </button>
        </form>

        <p className="mt-6 text-sm text-parchment/50">
          No account?{' '}
          <Link to="/register" className="text-signal hover:underline focus-ring rounded">
            Register
          </Link>
        </p>
      </div>
    </div>
  )
}
