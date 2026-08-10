import { useState, useRef, useEffect } from 'react'

export default function Chat({ onAsk, isReady }) {
  const [messages, setMessages] = useState([{
    role: 'ai',
    text: 'Good day. I have access to your document library. Ask me anything — I remember our conversation.',
    sources: [],
  }])
  const [input,    setInput]    = useState('')
  const [thinking, setThinking] = useState(false)
  const bottomRef = useRef(null)

  // ✅ PRIORITY 2: Build history from messages for multi-turn chat
  const buildHistory = () => {
    return messages
      .slice(1)           // skip welcome message
      .slice(-6)          // keep last 6 messages only
      .map(m => ({
        role:    m.role === 'user' ? 'user' : 'assistant',
        content: m.text,
      }))
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const send = async () => {
    const q = input.trim()
    if (!q || thinking) return
    if (!isReady) { alert('Please load documents first.'); return }

    setMessages(prev => [...prev, { role: 'user', text: q }])
    setInput('')
    setThinking(true)

    try {
      const data = await onAsk(q, 5, buildHistory())   // ✅ pass history
      setMessages(prev => [...prev, {
        role:    'ai',
        text:    data.answer,
        sources: data.sources || [],
        tokens:  data.tokens_used,
        model:   data.model,
      }])
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'ai',
        text: '⚠ ' + (e.response?.data?.detail || 'Something went wrong.'),
        sources: [],
      }])
    } finally {
      setThinking(false)
    }
  }

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  // ✅ PRIORITY 2: Clear conversation
  const clearChat = () => {
    setMessages([{
      role: 'ai',
      text: 'Chat cleared. Ask me anything about your documents.',
      sources: [],
    }])
  }

  const questionCount = messages.filter(m => m.role === 'user').length

  return (
    <div style={s.wrap}>
      <div style={s.header}>
        <div>
          <h1 style={s.title}>Document Assistant</h1>
          <p style={s.sub}>Powered by NVIDIA · Pinecone · Google Drive</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {isReady && (
            <div style={s.live}>
              <span style={s.liveDot} />
              Live
            </div>
          )}
          {/* ✅ Clear chat button */}
          {questionCount > 0 && (
            <button style={s.clearBtn} onClick={clearChat}>
              ✕ Clear
            </button>
          )}
        </div>
      </div>

      <div style={s.messages}>
        {messages.map((msg, i) => (
          <div key={i} style={{ ...s.row, justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', animation: 'fadeUp 0.3s ease' }}>
            {msg.role === 'ai' && <div style={s.avatar}>AI</div>}
            <div style={msg.role === 'user' ? s.userBubble : s.aiBubble}>
              <p style={msg.role === 'user' ? s.userText : s.aiText}>{msg.text}</p>
              {msg.sources?.length > 0 && (
                <div style={s.sources}>
                  <span style={s.srcLabel}>Sources:</span>
                  {msg.sources.map((src, j) => (
                    <span key={j} style={s.srcTag}>{src}</span>
                  ))}
                </div>
              )}
              {msg.tokens && (
                <span style={s.meta}>{msg.model} · {msg.tokens} tokens</span>
              )}
            </div>
          </div>
        ))}

        {thinking && (
          <div style={{ ...s.row, justifyContent: 'flex-start' }}>
            <div style={s.avatar}>AI</div>
            <div style={s.aiBubble}>
              <div style={s.dots}>
                {[0, 160, 320].map(d => (
                  <span key={d} style={{ ...s.dot, animationDelay: `${d}ms` }} />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* ✅ Session counter */}
      {questionCount > 0 && (
        <div style={s.historyBar}>
          <span style={s.historyText}>
            {questionCount} question{questionCount > 1 ? 's' : ''} · AI remembers this session
          </span>
        </div>
      )}

      <div style={s.inputArea}>
        <div style={s.inputRow}>
          <textarea
            style={s.textarea}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKey}
            placeholder={isReady ? 'Ask a question or follow up...' : 'Load documents to begin...'}
            disabled={!isReady || thinking}
            rows={1}
          />
          <button
            style={{ ...s.sendBtn, opacity: (!isReady || thinking || !input.trim()) ? 0.3 : 1 }}
            onClick={send}
            disabled={!isReady || thinking || !input.trim()}
          >
            Send
          </button>
        </div>
        <p style={s.hint}>Enter to send · Shift+Enter for new line · AI remembers your conversation</p>
      </div>
    </div>
  )
}

const s = {
  wrap:       { flex: 1, display: 'flex', flexDirection: 'column', background: 'var(--paper)', overflow: 'hidden' },
  header:     { padding: '20px 32px', borderBottom: '2px solid var(--ink)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--surface)' },
  title:      { fontFamily: 'var(--font-serif)', fontSize: 22, color: 'var(--ink)', fontWeight: 400 },
  sub:        { fontSize: 10, color: 'var(--muted)', fontFamily: 'var(--font-mono)', marginTop: 3, letterSpacing: 1 },
  live:       { display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: '#27ae60', fontFamily: 'var(--font-mono)', border: '1px solid #27ae6040', padding: '4px 10px' },
  liveDot:    { width: 6, height: 6, borderRadius: '50%', background: '#27ae60', boxShadow: '0 0 6px #27ae60' },
  clearBtn:   { background: 'transparent', color: 'var(--muted)', border: '1px solid var(--border)', padding: '4px 10px', fontFamily: 'var(--font-mono)', fontSize: 10, cursor: 'pointer', borderRadius: 'var(--radius)' },
  messages:   { flex: 1, overflowY: 'auto', padding: '28px 32px', display: 'flex', flexDirection: 'column', gap: 20 },
  row:        { display: 'flex', alignItems: 'flex-start', gap: 12 },
  avatar:     { width: 32, height: 32, background: 'var(--ink)', color: 'var(--paper)', fontFamily: 'var(--font-mono)', fontSize: 9, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, letterSpacing: 1 },
  aiBubble:   { background: 'var(--surface)', border: '1px solid var(--border)', padding: '14px 18px', maxWidth: 620, borderRadius: 'var(--radius)' },
  userBubble: { background: 'var(--ink)', padding: '14px 18px', maxWidth: 500, borderRadius: 'var(--radius)' },
  aiText:     { fontSize: 14, lineHeight: 1.75, color: 'var(--text)', whiteSpace: 'pre-wrap' },
  userText:   { fontSize: 14, lineHeight: 1.75, color: 'var(--paper)', whiteSpace: 'pre-wrap' },
  sources:    { marginTop: 10, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 6, paddingTop: 10, borderTop: '1px solid var(--border)' },
  srcLabel:   { fontSize: 9, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: 1.5, fontFamily: 'var(--font-mono)' },
  srcTag:     { fontSize: 9, background: 'var(--cream)', color: 'var(--text)', border: '1px solid var(--warm)', padding: '2px 8px', fontFamily: 'var(--font-mono)' },
  meta:       { display: 'block', marginTop: 8, fontSize: 9, color: 'var(--muted)', fontFamily: 'var(--font-mono)' },
  dots:       { display: 'flex', gap: 5, padding: '4px 0' },
  dot:        { width: 6, height: 6, borderRadius: '50%', background: 'var(--muted)', display: 'inline-block', animation: 'pulse 1.2s infinite' },
  historyBar: { padding: '4px 32px', background: 'var(--cream)', borderTop: '1px solid var(--border)' },
  historyText:{ fontSize: 9, color: 'var(--muted)', fontFamily: 'var(--font-mono)' },
  inputArea:  { padding: '16px 32px 20px', borderTop: '1px solid var(--border)', background: 'var(--surface)' },
  inputRow:   { display: 'flex', gap: 10, alignItems: 'flex-end' },
  textarea:   { flex: 1, background: 'var(--paper)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '12px 16px', color: 'var(--text)', fontSize: 14, resize: 'none', lineHeight: 1.5, transition: 'border-color 0.2s' },
  sendBtn:    { background: 'var(--ink)', color: 'var(--paper)', border: 'none', padding: '12px 22px', fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: 1.5, textTransform: 'uppercase', cursor: 'pointer', transition: 'opacity 0.2s', flexShrink: 0, borderRadius: 'var(--radius)' },
  hint:       { marginTop: 8, fontSize: 9, color: 'var(--warm)', fontFamily: 'var(--font-mono)' },
}