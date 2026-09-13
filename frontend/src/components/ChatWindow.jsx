import { useEffect, useRef, useState } from 'react'
import { postChatStream } from '../lib/chatApi.js'

let nextId = 0
const uid = () => String(++nextId)

export default function ChatWindow() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isBusy, setIsBusy] = useState(false)
  const bottomRef = useRef(null)
  const abortRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => () => abortRef.current?.abort(), [])

  const send = async () => {
    const text = input.trim()
    if (!text || isBusy) return
    setInput('')
    setIsBusy(true)
    const userMsg = { id: uid(), role: 'user', content: text }
    const assistantId = uid()
    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: assistantId, role: 'assistant', content: '', status: 'streaming' },
    ])
    const history = [...messages, userMsg].map(({ role, content }) => ({ role, content }))
    abortRef.current = new AbortController()
    try {
      await postChatStream({
        messages: history,
        message: text,
        signal: abortRef.current.signal,
        onEvent: (event) => {
          if (event.type === 'token' && event.content) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: m.content + event.content } : m,
              ),
            )
          } else if (event.type === 'done') {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, status: 'done' } : m)),
            )
          } else if (event.type === 'error') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: event.content || 'Something went wrong.', status: 'error' }
                  : m,
              ),
            )
          }
        },
      })
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId && m.status === 'streaming' ? { ...m, status: 'done' } : m)),
      )
    } catch (err) {
      if (err.name === 'AbortError') return
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: err.message || 'Request failed.', status: 'error' }
            : m,
        ),
      )
    } finally {
      setIsBusy(false)
      abortRef.current = null
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="chat">
      <header className="chat__header">
        <h1>Chat</h1>
      </header>
      <div className="chat__messages" role="log" aria-live="polite">
        {messages.length === 0 && <p className="chat__empty">Send a message to start.</p>}
        {messages.map((m) => (
          <div key={m.id} className={`chat__bubble chat__bubble--${m.role}${m.status === 'streaming' ? ' chat__bubble--streaming' : ''}${m.status === 'error' ? ' chat__bubble--error' : ''}`}>
            <span className="chat__role">{m.role === 'user' ? 'You' : 'Assistant'}</span>
            <p className="chat__text">{m.content || (m.status === 'streaming' ? '…' : '')}</p>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <footer className="chat__composer">
        <textarea
          className="chat__input"
          rows={2}
          placeholder="Message… (Enter to send, Shift+Enter for newline)"
          value={input}
          disabled={isBusy}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <button type="button" className="chat__send" disabled={isBusy || !input.trim()} onClick={send}>
          Send
        </button>
      </footer>
    </div>
  )
}
