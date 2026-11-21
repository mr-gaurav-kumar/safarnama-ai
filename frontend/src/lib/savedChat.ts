/**
 * Chats that survive moving around the app and reloading the page, until
 * the person logs out.
 *
 * Kept in this browser's localStorage under the user's id, so two people
 * sharing a computer never see each other's chat, and wiped on logout.
 * Storage can be full, switched off or blocked (private mode): every call is
 * wrapped so the chat still works -- it just isn't kept.
 */
const PREFIX = 'safarnama.chat.'
const MAX_TURNS = 60

const keyFor = (scope: string, userId: string) => `${PREFIX}${scope}.${userId}`

export function loadChat<T>(scope: string, userId: string | undefined): T[] {
  if (!userId) return []
  try {
    const raw = localStorage.getItem(keyFor(scope, userId))
    const parsed: unknown = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? (parsed as T[]) : []
  } catch {
    return []
  }
}

export function saveChat<T>(scope: string, userId: string | undefined, turns: T[]): void {
  if (!userId) return
  try {
    if (turns.length === 0) localStorage.removeItem(keyFor(scope, userId))
    else localStorage.setItem(keyFor(scope, userId), JSON.stringify(turns.slice(-MAX_TURNS)))
  } catch {
    // Full or unavailable: keep chatting without saving.
  }
}

/** On logout: forget every saved chat in this browser. */
export function clearSavedChats(): void {
  try {
    for (const k of Object.keys(localStorage)) if (k.startsWith(PREFIX)) localStorage.removeItem(k)
  } catch {
    // Nothing to clear.
  }
}
