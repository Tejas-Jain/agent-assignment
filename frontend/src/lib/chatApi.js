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
