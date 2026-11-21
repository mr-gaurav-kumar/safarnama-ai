import { useCallback, useEffect, useRef, useState } from 'react'
import { getAccessToken, refreshSession, wsUrl } from '@/lib/api'

export interface ChatMessage {
  id: string
  sender: 'user' | 'bot'
  message: string
  created_at: string
}

export type ChatStatus = 'idle' | 'connecting' | 'open' | 'reconnecting' | 'signed-out'

const MAX_RETRIES = 5

/**
 * The support conversation over WS /ws/chat.
 *
 * Connects only while `active` (the widget is open). On an unexpected drop it
 * reconnects with backoff and the server re-sends the history, so nothing is
 * lost or duplicated. A 4401 close means the access token expired: refresh it
 * once and reconnect; if that fails the session is really gone.
 */
export function useChat(active: boolean) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [status, setStatus] = useState<ChatStatus>('idle')
  const [typing, setTyping] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [escalated, setEscalated] = useState(false)
  const socket = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!active) return

    let stopped = false
    let retries = 0
    // One refresh-and-retry when the server rejects an expired access token.
    let authRetried = false
    let timer: ReturnType<typeof setTimeout> | undefined

    function connect() {
      const token = getAccessToken()
      if (!token) {
        setStatus('signed-out')
        return
      }
      setStatus(retries === 0 ? 'connecting' : 'reconnecting')
      const ws = new WebSocket(wsUrl('/ws/chat'))
      socket.current = ws

      ws.onopen = () => ws.send(JSON.stringify({ type: 'auth', token }))

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data as string)
        switch (data.type) {
          case 'history':
            retries = 0
            authRetried = false
            setStatus('open')
            setMessages(data.messages as ChatMessage[])
            break
          case 'typing':
            setTyping(true)
            break
          case 'reply':
            setTyping(false)
            setMessages((prev) => [...prev, data.message as ChatMessage])
            if (data.escalated) setEscalated(true)
            break
          case 'error':
            setTyping(false)
            setNotice(String(data.detail ?? 'That message could not be sent.'))
            // A refused message never reached the server's history.
            setMessages((prev) => prev.filter((m) => !m.id.startsWith('local-')))
            break
        }
      }

      ws.onclose = (event) => {
        socket.current = null
        setTyping(false)
        if (stopped) return
        if (event.code === 4401) {
          if (!authRetried) {
            authRetried = true
            setStatus('reconnecting')
            void refreshSession().then((user) => {
              if (stopped) return
              if (user) connect()
              else setStatus('signed-out')
            })
            return
          }
          setStatus('signed-out')
          return
        }
        if (retries >= MAX_RETRIES) {
          setStatus('idle')
          setNotice('Chat is unavailable right now. Please try again later.')
          return
        }
        retries += 1
        setStatus('reconnecting')
        timer = setTimeout(connect, 1000 * 2 ** (retries - 1))
      }
    }

    connect()
    return () => {
      stopped = true
      clearTimeout(timer)
      socket.current?.close()
      socket.current = null
      setStatus('idle')
    }
  }, [active])

  /** `page` tells the server where in the app the question comes from, so
   *  the answer is about that page (see backend/app/chat/pages.py). */
  const send = useCallback((text: string, page?: string | null) => {
    const ws = socket.current
    const trimmed = text.trim()
    if (!ws || ws.readyState !== WebSocket.OPEN || !trimmed) return false
    setNotice(null)
    // Shown at once; the server's history replaces it on the next reconnect.
    setMessages((prev) => [
      ...prev,
      { id: `local-${Date.now()}`, sender: 'user', message: trimmed, created_at: new Date().toISOString() },
    ])
    ws.send(JSON.stringify({ type: 'message', text: trimmed, page: page ?? undefined }))
    return true
  }, [])

  return { messages, status, typing, notice, escalated, send }
}
