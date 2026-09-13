import { useCallback, useEffect, useRef, useState } from 'react'
import ChatWindow from './components/ChatWindow.jsx'
import { fetchPastConversation, fetchPastConversations, savePastConversation } from './lib/chatApi.js'
import './App.css'

function formatWhen(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return iso
  }
}

function App() {
  const [pastList, setPastList] = useState([])
  const [listError, setListError] = useState('')
  const [selectedPastId, setSelectedPastId] = useState(null)
  const [pastDetail, setPastDetail] = useState(null)
  const [pastLoading, setPastLoading] = useState(false)
  const [liveChatKey, setLiveChatKey] = useState(0)
  const [saving, setSaving] = useState(false)
  const chatRef = useRef(null)

  const loadPastList = useCallback(async () => {
    try {
      setListError('')
      setPastList(await fetchPastConversations())
    } catch (err) {
      setListError(err.message || 'Could not load past conversations.')
    }
  }, [])

  useEffect(() => {
    loadPastList()
  }, [loadPastList])

  const startNewChat = async () => {
    if (!selectedPastId && chatRef.current) {
      const transcript = chatRef.current.getTranscript()
      if (transcript.length > 0) {
        setSaving(true)
        try {
          await savePastConversation(transcript)
          await loadPastList()
        } catch (err) {
          setListError(err.message || 'Could not save conversation.')
          setSaving(false)
          return
        }
        setSaving(false)
      }
    }
    setSelectedPastId(null)
    setPastDetail(null)
    setLiveChatKey((k) => k + 1)
  }

  const openPast = async (id) => {
    setSelectedPastId(id)
    setPastLoading(true)
    setPastDetail(null)
    try {
      setPastDetail(await fetchPastConversation(id))
    } catch (err) {
      setListError(err.message || 'Could not load conversation.')
      setSelectedPastId(null)
    } finally {
      setPastLoading(false)
    }
  }

  const pastSummary = selectedPastId ? pastList.find((p) => p.id === selectedPastId) : null
  const pastReady = Boolean(selectedPastId && pastDetail?.id === selectedPastId)

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Past conversations">
        <div className="sidebar__head">
          <h2 className="sidebar__title">Conversations</h2>
          <button type="button" className="sidebar__new" disabled={saving} onClick={startNewChat}>
            {saving ? 'Saving…' : 'New chat'}
          </button>
        </div>
        {listError && <p className="sidebar__error">{listError}</p>}
        <ul className="sidebar__list">
          {pastList.length === 0 && !listError && (
            <li className="sidebar__empty">Completed chats appear here.</li>
          )}
          {pastList.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className={`sidebar__item${selectedPastId === item.id ? ' sidebar__item--active' : ''}`}
                onClick={() => openPast(item.id)}
                disabled={saving}
              >
                <span className="sidebar__item-title">{item.title}</span>
                <span className="sidebar__item-meta">{formatWhen(item.created_at)}</span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <ChatWindow
        ref={chatRef}
        key={pastReady ? selectedPastId : selectedPastId ? `${selectedPastId}-loading` : `new-${liveChatKey}`}
        readOnly={Boolean(selectedPastId)}
        headerTitle={pastReady ? pastDetail.title : pastSummary?.title ?? 'Chat'}
        initialMessages={pastReady ? pastDetail.messages : []}
        pastLoading={pastLoading && Boolean(selectedPastId)}
      />
    </div>
  )
}

export default App
