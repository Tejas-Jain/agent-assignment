function parseEventBlock(block, onEvent) {
  const lines = block.split('\n')
  const dataLines = []
  for (const line of lines) {
    if (line.startsWith(':')) continue
    if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
  }
  if (dataLines.length === 0) return
  const payload = dataLines.join('\n')
  if (payload === '[DONE]') {
    onEvent({ type: 'done' })
    return
  }
  try {
    onEvent(JSON.parse(payload))
  } catch {
    onEvent({ type: 'token', content: payload })
  }
}

/** @param {Response} response @param {(event: { type: string, content?: string }) => void} onEvent */
export async function parseSseStream(response, onEvent) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let sep
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const block = buffer.slice(0, sep)
        buffer = buffer.slice(sep + 2)
        if (block.trim()) parseEventBlock(block, onEvent)
      }
    }
    if (buffer.trim()) parseEventBlock(buffer, onEvent)
  } finally {
    reader.releaseLock()
  }
}
