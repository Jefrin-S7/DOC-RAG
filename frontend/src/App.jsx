import { useState, useEffect } from 'react'
import axios from 'axios'
import Chat from './components/Chat'
import Sidebar from './components/Sidebar'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const [status,    setStatus]    = useState({ status: 'idle', message: 'No documents loaded.', file_count: 0, index_exists: false })
  const [loading,   setLoading]   = useState(false)
  const [reloading, setReloading] = useState(false)

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${API}/status`)
      setStatus(res.data)
    } catch (_) {}
  }

  useEffect(() => {
    fetchStatus()
    const id = setInterval(fetchStatus, 3000)
    return () => clearInterval(id)
  }, [])

  const handleLoad = async () => {
    setLoading(true)
    try { await axios.post(`${API}/load`) }
    catch (e) { alert(e.response?.data?.detail || 'Failed to load.') }
    finally   { setLoading(false) }
  }

  // ✅ PRIORITY 2: Reload handler
  const handleReload = async () => {
    if (!window.confirm('This will clear and re-index all documents. Continue?')) return
    setReloading(true)
    try { await axios.post(`${API}/reload`) }
    catch (e) { alert(e.response?.data?.detail || 'Failed to reload.') }
    finally   { setReloading(false) }
  }

  // ✅ PRIORITY 2: Pass history for conversation memory
  const handleAsk = async (question, topK = 5, history = []) => {
    const res = await axios.post(`${API}/ask`, {
      question,
      top_k:   topK,
      history,
    })
    return res.data
  }

  const isIndexing = ['loading', 'indexing'].includes(status.status)

  return (
    <div style={{ display: 'flex', height: '100vh', background: 'var(--paper)', overflow: 'hidden' }}>
      <Sidebar
        status={status}
        loading={loading || isIndexing}
        reloading={reloading}
        onLoad={handleLoad}
        onReload={handleReload}
      />
      <Chat onAsk={handleAsk} isReady={status.index_exists} />
    </div>
  )
}