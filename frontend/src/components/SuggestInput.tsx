import { useId, useMemo, useRef, useState } from 'react'

export interface SuggestOption {
  value: string
  /** Shown faintly on the right, e.g. a category. */
  hint?: string
}

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim()

/** Edit distance with swapped neighbours counting as one edit ("Thremal" vs "Thermal"). */
function distance(a: string, b: string): number {
  const d: number[][] = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)])
  for (let j = 1; j <= b.length; j++) d[0][j] = j
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1)
    }
  }
  return d[a.length][b.length]
}

/** A typo of a word, or of its start: one slip in short words, two in longer ones. */
function closeTo(q: string, word: string): boolean {
  const allowed = q.length >= 6 ? 2 : 1
  return distance(q, word.slice(0, q.length)) <= allowed || distance(q, word) <= allowed
}

/**
 * Best matches first: starts with what was typed ("Towe" -> Towel), then a word
 * that starts with it ("bott" -> Water bottle), then anywhere in the name, then
 * one-letter typos ("Towl" -> Towel).
 */
export function rankOptions(query: string, options: SuggestOption[], limit = 6): SuggestOption[] {
  const q = norm(query)
  if (!q) return []
  const scored: [number, SuggestOption][] = []
  for (const o of options) {
    const n = norm(o.value)
    if (n === q) continue // already typed in full
    let score = -1
    if (n.startsWith(q)) score = 0
    else if (n.split(' ').some((w) => w.startsWith(q))) score = 1
    else if (n.includes(q)) score = 2
    else if (q.length >= 4 && n.split(' ').some((w) => closeTo(q, w))) score = 3
    if (score >= 0) scored.push([score, o])
  }
  scored.sort((a, b) => a[0] - b[0] || a[1].value.length - b[1].value.length)
  return scored.slice(0, limit).map(([, o]) => o)
}

/** A text input that suggests as you type. Pick with a click, or arrows and Enter. */
export function SuggestInput({
  value,
  onChange,
  options,
  onPick,
  className = '',
  ...input
}: {
  value: string
  onChange: (value: string) => void
  options: SuggestOption[]
  onPick?: (option: SuggestOption) => void
  className?: string
  placeholder?: string
  maxLength?: number
  'aria-label'?: string
}) {
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)
  const listId = useId()
  const blurTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const matches = useMemo(() => rankOptions(value, options), [value, options])
  const show = open && matches.length > 0

  function pick(o: SuggestOption) {
    onChange(o.value)
    onPick?.(o)
    setOpen(false)
  }

  return (
    <span className="relative block">
      <input
        {...input}
        value={value}
        autoComplete="off"
        role="combobox"
        aria-expanded={show}
        aria-controls={listId}
        aria-autocomplete="list"
        onChange={(e) => {
          onChange(e.target.value)
          setHighlight(0)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          blurTimer.current = setTimeout(() => setOpen(false), 120)
        }}
        onKeyDown={(e) => {
          if (!show) return
          if (e.key === 'ArrowDown') {
            e.preventDefault()
            setHighlight((h) => (h + 1) % matches.length)
          } else if (e.key === 'ArrowUp') {
            e.preventDefault()
            setHighlight((h) => (h - 1 + matches.length) % matches.length)
          } else if (e.key === 'Enter' || e.key === 'Tab') {
            if (e.key === 'Enter') e.preventDefault()
            pick(matches[Math.min(highlight, matches.length - 1)])
          } else if (e.key === 'Escape') {
            setOpen(false)
          }
        }}
        className={`w-full ${className}`}
      />
      {show && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-50 mt-1 max-h-60 w-full min-w-48 overflow-auto rounded-lg border border-slate-200 bg-white py-1 text-sm shadow-lg"
        >
          {matches.map((o, i) => (
            <li
              key={o.value}
              role="option"
              aria-selected={i === highlight}
              onMouseEnter={() => setHighlight(i)}
              onMouseDown={(e) => {
                e.preventDefault()
                if (blurTimer.current) clearTimeout(blurTimer.current)
                pick(o)
              }}
              className={`flex cursor-pointer items-baseline justify-between gap-3 px-3 py-1.5 ${i === highlight ? 'bg-slate-100' : ''}`}
            >
              <span>{o.value}</span>
              {o.hint && <span className="shrink-0 text-xs text-slate-400">{o.hint}</span>}
            </li>
          ))}
        </ul>
      )}
    </span>
  )
}
