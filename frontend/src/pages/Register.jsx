import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function Register({ onLoggedIn }) {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e) {
  e.preventDefault()
  setError('')
  setLoading(true)
  try {
    await api.register(email, password, fullName)
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
        <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-signal mb-2">Open a case file</p>
        <h1 className="font-display text-3xl sm:text-4xl mb-8 text-parchment">Create account</h1>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block font-mono text-xs uppercase tracking-wider text-parchment/50 mb-1.5">Full name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-md px-4 py-2.5 text-parchment placeholder:text-parchment/30 focus-ring focus:border-signal transition-colors"
              placeholder="Ada Lovelace"
            />
          </div>
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
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-md px-4 py-2.5 text-parchment placeholder:text-parchment/30 focus-ring focus:border-signal transition-colors"
              placeholder="At least 8 characters"
            />
          </div>

          {error && (
            <p className="text-rust text-sm font-mono border border-rust/30 bg-rust/10 rounded-md px-3 py-2">{error}</p>
          )}
          {success && (
            <p className="text-moss text-sm font-mono border border-moss/30 bg-moss/10 rounded-md px-3 py-2">
              Account created — redirecting to sign in...
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-signal text-ink font-medium rounded-md py-2.5 hover:brightness-110 disabled:opacity-50 transition focus-ring"
          >
            {loading ? 'Creating...' : 'Create account'}
          </button>
        </form>

        <p className="mt-6 text-sm text-parchment/50">
          Already have an account?{' '}
          <Link to="/login" className="text-signal hover:underline focus-ring rounded">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
