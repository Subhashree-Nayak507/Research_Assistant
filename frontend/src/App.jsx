import { useCallback, useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Login from './pages/Login'
import Register from './pages/Register'
import Research from './pages/Research'
import SessionView from './pages/SessionView'
import { api } from './api'

function RequireAuth({ children, authed }) {
  if (authed === null) return null // still checking
  return authed ? children : <Navigate to="/login" replace />
}

function MenuIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  )
}

export default function App() {
  const [authed, setAuthed] = useState(null) 
  const [user, setUser] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [historyKey, setHistoryKey] = useState(0) 
  const [newInquiryKey, setNewInquiryKey] = useState(0) 

  const refreshAuth = useCallback(async () => {
    try {
      const me = await api.me()
      setUser(me)
      setAuthed(true)
    } catch {
      setUser(null)
      setAuthed(false)
    }
  }, [])

  useEffect(() => {
    refreshAuth()
  }, [refreshAuth])

  const bumpHistory = useCallback(() => setHistoryKey((k) => k + 1), [])
  const startNewInquiry = useCallback(() => setNewInquiryKey((k) => k + 1), [])

  const handleLoggedOut = useCallback(() => {
    setAuthed(false)
    setUser(null)
  }, [])

  return (
    <div className="min-h-screen bg-slate-950 font-body lg:flex">
      {authed && (
        <Sidebar
          key={user?.id || 'anon'}
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          user={user}
          refreshKey={historyKey}
          onLoggedOut={handleLoggedOut}
          onNewInquiry={startNewInquiry}
        />
      )}

      <div className="flex-1 min-w-0 flex flex-col">
        {authed && (
          <header className="lg:hidden sticky top-0 z-10 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur px-4 py-3 flex items-center justify-between">
            <button
              onClick={() => setSidebarOpen(true)}
              aria-label="Open menu"
              className="text-parchment/70 hover:text-signal transition-colors focus-ring rounded p-1"
            >
              <MenuIcon />
            </button>
            <span className="w-[22px]" aria-hidden="true" />
          </header>
        )}

        <main className="flex-1 min-w-0" key={user?.id || 'anon'}>
          <Routes>
            <Route
              path="/"
              element={
                <RequireAuth authed={authed}>
                  <Research onSaved={bumpHistory} />
                </RequireAuth>
              }
            />
            <Route
              path="/session/:sessionId"
              element={
                <RequireAuth authed={authed}>
                  <SessionView />
                </RequireAuth>
              }
            />
            <Route path="/login" element={<Login onLoggedIn={() => refreshAuth()} />} />
             <Route path="/register" element={<Register onLoggedIn={() => refreshAuth()} />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}