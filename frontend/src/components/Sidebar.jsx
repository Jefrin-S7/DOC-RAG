export default function Sidebar({ status, loading, onLoad }) {
  const statusMap = {
    idle:     { color: '#b0a898', label: 'Idle'       },
    loading:  { color: '#e67e22', label: 'Loading...' },
    indexing: { color: '#e67e22', label: 'Indexing...' },
    ready:    { color: '#27ae60', label: 'Ready'       },
    error:    { color: '#c0392b', label: 'Error'       },
  }
  const info = statusMap[status.status] || statusMap.idle

  return (
    <aside style={s.sidebar}>
      {/* Logo */}
      <div style={s.logo}>
        <div style={s.logoMark}>D</div>
        <div>
          <div style={s.logoTitle}>DOC-RAG</div>
          <div style={s.logoSub}>Document Intelligence</div>
        </div>
      </div>

      <div style={s.divider} />

      {/* Status */}
      <div style={s.statusBox}>
        <div style={s.statusRow}>
          <span style={{ ...s.statusDot, background: info.color, boxShadow: `0 0 8px ${info.color}40` }} />
          <span style={{ ...s.statusLabel, color: info.color }}>{info.label}</span>
        </div>
        {status.message && <p style={s.statusMsg}>{status.message}</p>}
        {status.file_count > 0 && (
          <p style={s.statusCount}>{status.file_count} file(s) indexed</p>
        )}
      </div>

      {/* Load Button */}
      <button
        style={{ ...s.loadBtn, opacity: loading ? 0.6 : 1 }}
        onClick={onLoad}
        disabled={loading}
      >
        {loading ? 'Processing...' : 'Load Documents'}
      </button>

      <div style={s.divider} />

      {/* Stack */}
      <div style={s.stackSection}>
        <p style={s.stackTitle}>Infrastructure</p>
        {[
          ['Storage',   'Google Drive', '#4285F4'],
          ['Vectors',   'Pinecone',     '#0D9458'],
          ['Backend',   'FastAPI',      '#009688'],
          ['Frontend',  'React',        '#61DAFB'],
          ['LLM',       'NVIDIA Build', '#76B900'],
        ].map(([layer, tech, color]) => (
          <div key={layer} style={s.stackRow}>
            <span style={s.stackLayer}>{layer}</span>
            <span style={{ ...s.stackTech, color }}>{tech}</span>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={s.footer}>
        <p style={s.footerText}>DOC-RAG v1.0</p>
        <a href="http://localhost:8000/docs" target="_blank" style={s.footerLink}>
          API Docs →
        </a>
      </div>
    </aside>
  )
}

const s = {
  sidebar: {
    width: 240, minWidth: 240,
    background: 'var(--ink)',
    display: 'flex', flexDirection: 'column',
    padding: '28px 20px',
    gap: 20,
    borderRight: '1px solid #222',
  },
  logo: {
    display: 'flex', alignItems: 'center', gap: 12,
  },
  logoMark: {
    width: 38, height: 38,
    background: 'var(--accent)',
    color: '#fff',
    fontFamily: 'var(--font-serif)',
    fontSize: 22,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0,
  },
  logoTitle: {
    fontFamily: 'var(--font-mono)',
    fontSize: 13, fontWeight: 500,
    color: '#f5f0e8',
    letterSpacing: 3,
  },
  logoSub: {
    fontSize: 9,
    color: '#5a5040',
    textTransform: 'uppercase',
    letterSpacing: 1.5,
    marginTop: 2,
  },
  divider: { height: 1, background: '#1e1e1e' },
  statusBox: {
    background: '#161616',
    border: '1px solid #222',
    borderRadius: 'var(--radius)',
    padding: '12px 14px',
    display: 'flex', flexDirection: 'column', gap: 5,
  },
  statusRow:  { display: 'flex', alignItems: 'center', gap: 8 },
  statusDot:  { width: 7, height: 7, borderRadius: '50%', flexShrink: 0 },
  statusLabel:{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 500 },
  statusMsg:  { fontSize: 10, color: '#5a5040', lineHeight: 1.5 },
  statusCount:{ fontSize: 10, color: '#76B900', fontFamily: 'var(--font-mono)' },
  loadBtn: {
    background: 'transparent',
    color: '#f5f0e8',
    border: '1px solid #333',
    borderRadius: 'var(--radius)',
    padding: '11px 16px',
    fontFamily: 'var(--font-mono)',
    fontSize: 11,
    fontWeight: 500,
    letterSpacing: 1,
    textTransform: 'uppercase',
    transition: 'all 0.2s',
    cursor: 'pointer',
  },
  stackSection: { display: 'flex', flexDirection: 'column', gap: 8 },
  stackTitle: {
    fontSize: 9, color: '#3a3020',
    textTransform: 'uppercase', letterSpacing: 2,
    marginBottom: 4,
  },
  stackRow: { display: 'flex', justifyContent: 'space-between', fontSize: 11 },
  stackLayer: { color: '#4a4030' },
  stackTech: { fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 500 },
  footer: {
    marginTop: 'auto',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  },
  footerText: { fontSize: 9, color: '#3a3020', fontFamily: 'var(--font-mono)' },
  footerLink: {
    fontSize: 9, color: '#5a5040',
    fontFamily: 'var(--font-mono)',
    textDecoration: 'none',
  },
}