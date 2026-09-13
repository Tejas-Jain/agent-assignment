import { parseSseStream } from './parseSseStream.js'

const base = import.meta.env.VITE_API_BASE_URL ?? ''

async function mockChatStream({ message, onEvent }) {
  const reply = `Echo: ${message}`
  for (const ch of reply) {
    await new Promise((r) => setTimeout(r, 25))
    onEvent({ type: 'token', content: ch })
  }
  onEvent({ type: 'done' })
}

export async function postChatStream({ messages, message, signal, onEvent }) {
  if (import.meta.env.DEV && import.meta.env.VITE_MOCK_CHAT === 'true') {
    await mockChatStream({ message, onEvent })
    return
  }
  const res = await fetch(`${base}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ message, messages }),
    signal,
  })
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText))
  await parseSseStream(res, onEvent)
}

export async function fetchPastConversations() {
  const res = await fetch(`${base}/api/conversations`)
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText))
  return res.json()
}

export async function fetchPastConversation(id) {
  const res = await fetch(`${base}/api/conversations/${encodeURIComponent(id)}`)
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText))
  return res.json()
}

export async function savePastConversation(messages) {
  const res = await fetch(`${base}/api/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
  })
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText))
  return res.json()
}
