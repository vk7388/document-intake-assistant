import { useEffect, useRef, useState } from 'react'
import './App.css'

const API_BASE = 'http://localhost:8000'

function StateField({ label, value }) {
  let display = value
  if (value === null || value === undefined || value === '') display = '—'
  if (Array.isArray(value)) display = value.length ? value.join(', ') : '—'
  if (typeof value === 'boolean') display = value ? 'Yes' : 'No'
  return (
    <div className="state-field">
      <span className="state-label">{label}</span>
      <span className="state-value">{display}</span>
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState([
    { role: 'ai', text: "Hi! I'll help you draft a personal wishes document. What is your full name?" },
  ])
  const [input, setInput] = useState('')
  const [state, setState] = useState({
    full_name: null,
    home_address: null,
    covers_worldwide_assets: null,
    has_children: null,
    children: [],
    executor: { name: null, relationship: null },
    specific_gifts: [],
    additional_wishes: null,
  })
  const [document, setDocument] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const chatEndRef = useRef(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendMessage(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    setMessages((m) => [...m, { role: 'user', text }])
    setInput('')
    setLoading(true)
    setError('')

    try {
      const resp = await fetch(`${API_BASE}/api/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      if (!resp.ok) throw new Error('Server error')
      const data = await resp.json()
      setMessages((m) => [...m, { role: 'ai', text: data.reply }])
      setState(data.state)
      setDocument(data.document)
    } catch (err) {
      setError("Sorry, I'm having trouble reaching the server. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  async function handleReset() {
    setLoading(true)
    try {
      const resp = await fetch(`${API_BASE}/api/reset`, { method: 'POST' })
      const data = await resp.json()
      setState(data.state)
      setDocument('')
      setMessages([{ role: 'ai', text: data.reply || 'What is your full name?' }])
      setError('')
    } catch {
      setError('Could not reset. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Document Intake Assistant</h1>
        <button className="reset-btn" onClick={handleReset}>Start Over</button>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="main-panels">
        <section className="panel chat-panel">
          <h2>Chat</h2>
          <div className="chat-window">
            {messages.map((m, i) => (
              <div key={i} className={`bubble ${m.role}`}>
                <span className="bubble-role">{m.role === 'ai' ? 'Assistant' : 'You'}</span>
                <p>{m.text}</p>
              </div>
            ))}
            {loading && <div className="bubble ai typing">Thinking…</div>}
            <div ref={chatEndRef} />
          </div>
          <form className="chat-input" onSubmit={sendMessage}>
            <input
              type="text"
              value={input}
              placeholder="Type your message…"
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <button type="submit" disabled={loading || !input.trim()}>Send</button>
          </form>
        </section>

        <section className="panel state-panel">
          <h2>Information Collected</h2>
          <StateField label="Full Name" value={state.full_name} />
          <StateField label="Home Address" value={state.home_address} />
          <StateField label="Covers Worldwide Assets" value={state.covers_worldwide_assets} />
          <StateField label="Has Children" value={state.has_children} />
          <StateField label="Children" value={state.children} />
          <StateField label="Executor" value={state.executor?.name} />
          <StateField label="Executor Relationship" value={state.executor?.relationship} />
          <StateField label="Specific Gifts" value={state.specific_gifts} />
          <StateField label="Additional Wishes" value={state.additional_wishes} />
        </section>
      </div>

      <section className="panel document-panel">
        <h2>Document Preview</h2>
        <pre className="document-preview">{document || 'Start chatting to build your document…'}</pre>
      </section>
    </div>
  )
}
