import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { postChatStream } from '../lib/chatApi.js'

let nextId = 0
const uid = () => String(++nextId)

function toUiMessages(initialMessages) {
  return (initialMessages ?? []).map((m) => ({
    id: uid(),
    role: m.role,
    content: m.content ?? '',
    status: 'done',
  }))
}

function toTranscript(messages) {
  return messages
    .filter((m) => m.role === 'user' || (m.content && m.content.trim()))
    .map(({ role, content }) => ({ role, content: content ?? '' }))
}

const ChatWindow = forwardRef(function ChatWindow(
  { readOnly = false, headerTitle = 'Chat', initialMessages = [], pastLoading = false },
  ref,
) {
  const [messages, setMessages] = useState(() => (readOnly ? toUiMessages(initialMessages) : []))
  const [input, setInput] = useState('')
  const [isBusy, setIsBusy] = useState(false)
  const bottomRef = useRef(null)
  const abortRef = useRef(null)

  useImperativeHandle(ref, () => ({
    getTranscript: () => toTranscript(messages),
    isBusy: () => isBusy,
  }), [messages, isBusy])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, pastLoading])

  useEffect(() => {
    if (readOnly && !pastLoading) setMessages(toUiMessages(initialMessages))
  }, [readOnly, pastLoading, initialMessages])

  useEffect(() => () => abortRef.current?.abort(), [])

  const send = async () => {
    const text = input.trim()
    if (!text || isBusy || readOnly) return
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
        <h1>{headerTitle}</h1>
        {readOnly && <p className="chat__readonly">Past conversation — read only, not continued here.</p>}
      </header>
      <div className="chat__messages" role="log" aria-live="polite">
        {pastLoading && <p className="chat__empty">Loading…</p>}
        {!pastLoading && messages.length === 0 && !readOnly && (
          <p className="chat__empty">Send a message to start.</p>
        )}
        {!pastLoading &&
          messages.map((m) => (
            <div
              key={m.id}
              className={`chat__bubble chat__bubble--${m.role}${m.status === 'streaming' ? ' chat__bubble--streaming' : ''}${m.status === 'error' ? ' chat__bubble--error' : ''}`}
            >
              <span className="chat__role">{m.role === 'user' ? 'You' : 'Assistant'}</span>
              {m.role === 'assistant' ? (
                <div className="chat__text chat__markdown">
                  {m.content ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                  ) : (
                    m.status === 'streaming' ? '…' : ''
                  )}
                </div>
              ) : (
                <p className="chat__text">{m.content}</p>
              )}
            </div>
          ))}
        <div ref={bottomRef} />
      </div>
      {!readOnly && (
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
      )}
    </div>
  )
})

export default ChatWindow
