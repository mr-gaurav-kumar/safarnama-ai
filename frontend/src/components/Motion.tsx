import { useEffect, useRef, useState, type ReactNode } from 'react'

const reducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/** True once the element has scrolled into view (then stays true). */
export function useInView<T extends Element>(margin = '0px 0px -10% 0px') {
  const ref = useRef<T>(null)
  const [seen, setSeen] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el || seen) return
    if (reducedMotion() || !('IntersectionObserver' in window)) {
      setSeen(true)
      return
    }
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setSeen(true)
          io.disconnect()
        }
      },
      { rootMargin: margin },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [margin, seen])
  return { ref, seen }
}

/** Fades and lifts its children in when they scroll into view. */
export function Reveal({
  children,
  delay = 0,
  className = '',
}: {
  children: ReactNode
  delay?: number
  className?: string
}) {
  const { ref, seen } = useInView<HTMLDivElement>()
  return (
    <div
      ref={ref}
      className={`transition-all duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none ${
        seen ? 'translate-y-0 opacity-100' : 'translate-y-6 opacity-0'
      } ${className}`}
      style={{ transitionDelay: seen ? `${delay}ms` : '0ms' }}
    >
      {children}
    </div>
  )
}

/** Counts up to `to` once visible, e.g. 2.95 with decimals=2. */
export function CountUp({
  to,
  decimals = 0,
  prefix = '',
  suffix = '',
  duration = 1600,
}: {
  to: number
  decimals?: number
  prefix?: string
  suffix?: string
  duration?: number
}) {
  const { ref, seen } = useInView<HTMLSpanElement>()
  const [value, setValue] = useState(0)
  useEffect(() => {
    if (!seen) return
    if (reducedMotion()) {
      setValue(to)
      return
    }
    let raf = 0
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      setValue(to * eased)
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [seen, to, duration])
  return (
    <span ref={ref} className="tabular-nums">
      {prefix}
      {value.toFixed(decimals)}
      {suffix}
    </span>
  )
}

/** Cycles through words with a soft blur-in. */
export function RotatingWord({ words, interval = 2400, className = '' }: { words: string[]; interval?: number; className?: string }) {
  const [i, setI] = useState(0)
  useEffect(() => {
    if (reducedMotion() || words.length < 2) return
    const id = setInterval(() => setI((n) => (n + 1) % words.length), interval)
    return () => clearInterval(id)
  }, [words.length, interval])
  return (
    <span key={i} className={`inline-block animate-word-in ${className}`}>
      {words[i]}
    </span>
  )
}

/* ------------------------------------------------------------------ */
/*  Cursor-reactive pieces                                             */
/* ------------------------------------------------------------------ */

const finePointer = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(hover: hover) and (pointer: fine)').matches && !reducedMotion()

/** Writes the pointer position into --mx / --my (px, relative to the element). */
function trackPointer(e: React.PointerEvent<HTMLElement>) {
  const el = e.currentTarget
  const r = el.getBoundingClientRect()
  el.style.setProperty('--mx', `${e.clientX - r.left}px`)
  el.style.setProperty('--my', `${e.clientY - r.top}px`)
}

/** A section whose background carries a soft light that follows the cursor. */
export function CursorGlow({
  children,
  className = '',
  color = 'rgba(99,102,241,0.18)',
  size = 520,
}: {
  children: ReactNode
  className?: string
  color?: string
  size?: number
}) {
  const [on, setOn] = useState(false)
  return (
    <section
      className={`group/glow relative ${className}`}
      onPointerMove={(e) => finePointer() && trackPointer(e)}
      onPointerEnter={() => finePointer() && setOn(true)}
      onPointerLeave={() => setOn(false)}
    >
      <div
        aria-hidden
        className={`pointer-events-none absolute inset-0 z-0 transition-opacity duration-500 ${on ? 'opacity-100' : 'opacity-0'}`}
        style={{ background: `radial-gradient(${size}px circle at var(--mx, 50%) var(--my, 30%), ${color}, transparent 60%)` }}
      />
      {children}
    </section>
  )
}

/** A card with a spotlight and a lit border under the cursor. */
export function SpotlightCard({
  children,
  className = '',
  dark = false,
}: {
  children: ReactNode
  className?: string
  dark?: boolean
}) {
  return (
    <div
      onPointerMove={(e) => finePointer() && trackPointer(e)}
      className={`group/spot relative overflow-hidden ${className}`}
    >
      <div className="relative">{children}</div>
      {/* soft fill */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 z-10 opacity-0 transition-opacity duration-300 group-hover/spot:opacity-100"
        style={{
          background: `radial-gradient(360px circle at var(--mx, 50%) var(--my, 50%), ${
            dark ? 'rgba(201,164,92,0.16)' : 'rgba(99,102,241,0.10)'
          }, transparent 65%)`,
        }}
      />
      {/* lit border */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 z-10 rounded-[inherit] opacity-0 transition-opacity duration-300 group-hover/spot:opacity-100"
        style={{
          padding: 1,
          background: `radial-gradient(240px circle at var(--mx, 50%) var(--my, 50%), ${
            dark ? 'rgba(232,211,162,0.7)' : 'rgba(99,102,241,0.55)'
          }, transparent 70%)`,
          WebkitMask: 'linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)',
          WebkitMaskComposite: 'xor',
          maskComposite: 'exclude',
        }}
      />
    </div>
  )
}

/** Tilts gently towards the cursor, like a card held in the hand. */
export function Tilt({ children, className = '', max = 6 }: { children: ReactNode; className?: string; max?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  function move(e: React.PointerEvent<HTMLDivElement>) {
    if (!finePointer() || !ref.current) return
    const r = ref.current.getBoundingClientRect()
    const x = (e.clientX - r.left) / r.width - 0.5
    const y = (e.clientY - r.top) / r.height - 0.5
    ref.current.style.transform = `perspective(1000px) rotateY(${x * max}deg) rotateX(${-y * max}deg)`
  }
  function reset() {
    if (ref.current) ref.current.style.transform = 'perspective(1000px) rotateY(0deg) rotateX(0deg)'
  }
  return (
    <div
      ref={ref}
      onPointerMove={move}
      onPointerLeave={reset}
      className={`transition-transform duration-300 ease-out will-change-transform ${className}`}
    >
      {children}
    </div>
  )
}

/** A button/link wrapper that leans a few pixels towards the cursor. */
export function Magnetic({ children, strength = 0.25 }: { children: ReactNode; strength?: number }) {
  const ref = useRef<HTMLSpanElement>(null)
  return (
    <span
      ref={ref}
      className="inline-block transition-transform duration-200 ease-out"
      onPointerMove={(e) => {
        if (!finePointer() || !ref.current) return
        const r = ref.current.getBoundingClientRect()
        const x = e.clientX - (r.left + r.width / 2)
        const y = e.clientY - (r.top + r.height / 2)
        ref.current.style.transform = `translate(${x * strength}px, ${y * strength}px)`
      }}
      onPointerLeave={() => {
        if (ref.current) ref.current.style.transform = 'translate(0, 0)'
      }}
    >
      {children}
    </span>
  )
}
