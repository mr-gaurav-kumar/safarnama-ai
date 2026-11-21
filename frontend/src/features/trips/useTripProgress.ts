import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { getAccessToken, refreshSession } from '@/lib/api'
import { tripKeys } from '@/features/trips/api'

export interface ProgressStep {
  step: string
  message: string
  seq: number
  /** The "thinking" step carries the planner's reasoning, line by line. */
  thoughts?: string[]
}

type Phase = 'idle' | 'connecting' | 'live' | 'done' | 'unavailable'

/**
 * Follows WS /ws/trips/{id} while a trip is being planned.
 *
 * The server sends the trip's current state first, so opening the page late or
 * reconnecting never waits on events that already went by. When the job
 * finishes, the trip query is refetched to pick up the itinerary.
 *
 * An expired access token (close code 4401) is refreshed once and the socket
 * reopened. If the socket cannot be used at all, `phase` becomes 'unavailable'
 * and the page's polling fallback takes over -- nothing depends on it.
 */
export function useTripProgress(tripId: string | undefined, active: boolean) {
  const qc = useQueryClient()
  const [steps, setSteps] = useState<ProgressStep[]>([])
  const [phase, setPhase] = useState<Phase>('idle')

  useEffect(() => {
    if (!tripId || !active) return

    let stopped = false
    let finished = false
    let authRetried = false
    let socket: WebSocket | null = null
    setSteps([])

    function connect() {
      const token = getAccessToken()
      if (!token) {
        setPhase('unavailable')
        return
      }
      const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${scheme}://${window.location.host}/api/ws/trips/${tripId}`)
      socket = ws
      setPhase('connecting')

      ws.onopen = () => {
        // The token goes in the first message, never the URL, so it stays out
        // of server and proxy logs.
        ws.send(JSON.stringify({ type: 'auth', token }))
        setPhase('live')
      }

      ws.onmessage = (message) => {
        const event = JSON.parse(message.data as string) as {
          type: string
          step?: string
          message?: string
          seq?: number
          thoughts?: string[]
        }
        if (event.type === 'progress' && event.step && event.message) {
          const next: ProgressStep = {
            step: event.step,
            message: event.message,
            seq: event.seq ?? 0,
            thoughts: event.thoughts,
          }
          setSteps((prev) => (prev.some((s) => s.seq === next.seq) ? prev : [...prev, next]))
        }
        if (event.type === 'done') {
          finished = true
          setPhase('done')
          void qc.invalidateQueries({ queryKey: tripKeys.detail(tripId!) })
          void qc.invalidateQueries({ queryKey: tripKeys.all })
        }
      }

      ws.onclose = (event) => {
        if (stopped || finished) return
        if (event.code === 4401 && !authRetried) {
          authRetried = true
          void refreshSession().then((user) => {
            if (stopped) return
            if (user) connect()
            else setPhase('unavailable')
          })
          return
        }
        setPhase('unavailable')
      }
    }

    connect()
    return () => {
      stopped = true
      socket?.close()
    }
  }, [tripId, active, qc])

  return { steps, phase }
}
