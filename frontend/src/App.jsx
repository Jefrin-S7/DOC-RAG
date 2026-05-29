import { useState, useEffect } from 'react'
import axios from 'axios'
import Chat from './components/Chat'
import Sidebar from './components/Sidebar'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const [status,  setStatus]  = useState({ status: 'idle', message: 'No documents loaded.', file_count: 0, index_exists: false })
  const [loading, setLoading] = useState(false)

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

  const handleAsk = async (question, topK = 3) => {
    const res = await axios.post(`${API}/ask`, { question, top_k: topK })
    return res.data
  }

  const isIndexing = ['loading', 'indexing'].includes(status.status)

  return (
    <div style={s.layout}>
      <Sidebar
        status={status}
        loading={loading || isIndexing}
        onLoad={handleLoad}
      />
      <Chat
        onAsk={handleAsk}
        isReady={status.index_exists}
      />
    </div>
  )
}

const s = {
  layout: {
    display:   'flex',
    height:    '100vh',
    background: 'var(--paper)',
    overflow:  'hidden',
  },
}