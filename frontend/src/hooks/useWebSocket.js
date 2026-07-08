import { useEffect, useRef, useState } from 'react'

export function useEngagementStream(engagementId) {
  const [logs, setLogs] = useState([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)

  useEffect(() => {
    if (!engagementId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/engagement/${engagementId}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onerror = () => setConnected(false)

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        setLogs(prev => [...prev.slice(-2000), msg])
      } catch {}
    }

    return () => {
      ws.close()
      setLogs([])
      setConnected(false)
    }
  }, [engagementId])

  const clear = () => setLogs([])

  return { logs, connected, clear }
}
