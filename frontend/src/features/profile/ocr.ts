/**
 * Read an ID number off a photo or PDF -- in the browser.
 *
 * The image never leaves this device for OCR: tesseract.js runs here, and
 * only the language data is downloaded (once, then cached by the browser).
 * PDFs are opened with pdf.js; a password-protected one (e-Aadhaar is)
 * asks for its password, which is also only used here.
 *
 * What comes back is a suggestion: the form shows it for the traveller to
 * check before saving, and the server checks the format again.
 */

export type OcrKind = 'aadhaar' | 'pan' | 'driving_licence' | 'passport' | 'voter_id'

export interface OcrResult {
  number: string | null
  /** yyyy-mm-dd, for documents that expire, when a "valid till" date is printed */
  expires_on: string | null
  /** A masked Aadhaar shows only the last 4 digits. */
  masked: boolean
}

export class PdfPasswordNeeded extends Error {
  constructor(public wrong: boolean) {
    super(wrong ? 'That password didn’t open the PDF.' : 'This PDF has a password.')
  }
}

export const OCR_KINDS: OcrKind[] = ['aadhaar', 'pan', 'driving_licence', 'passport', 'voter_id']

// ---------------------------------------------------------------- reading

async function ocr(image: HTMLCanvasElement | File, onProgress?: (p: number) => void): Promise<string> {
  const { createWorker } = await import('tesseract.js')
  const worker = await createWorker('eng', 1, {
    logger: (m: { status: string; progress: number }) => {
      if (m.status === 'recognizing text') onProgress?.(m.progress)
    },
  })
  try {
    const { data } = await worker.recognize(image)
    return data.text
  } finally {
    await worker.terminate()
  }
}

async function pdfFirstPage(file: File, password?: string): Promise<{ text: string; canvas: HTMLCanvasElement }> {
  const pdfjs = await import('pdfjs-dist')
  const workerUrl = (await import('pdfjs-dist/build/pdf.worker.min.mjs?url')).default
  pdfjs.GlobalWorkerOptions.workerSrc = workerUrl
  let doc
  try {
    doc = await pdfjs.getDocument({ data: new Uint8Array(await file.arrayBuffer()), password }).promise
  } catch (e) {
    if ((e as { name?: string }).name === 'PasswordException') throw new PdfPasswordNeeded(Boolean(password))
    throw e
  }
  const page = await doc.getPage(1)
  const content = await page.getTextContent()
  const text = content.items.map((i) => ('str' in i ? i.str : '')).join(' ')
  const viewport = page.getViewport({ scale: 2.5 })
  const canvas = document.createElement('canvas')
  canvas.width = viewport.width
  canvas.height = viewport.height
  await page.render({ canvas, viewport }).promise
  return { text, canvas }
}

/** Photo or PDF in, a suggested number out. Throws PdfPasswordNeeded. */
export async function readDocument(
  file: File, kind: OcrKind, opts: { password?: string; onProgress?: (p: number) => void } = {},
): Promise<OcrResult> {
  if (file.type === 'application/pdf') {
    const { text, canvas } = await pdfFirstPage(file, opts.password)
    // A PDF made by the issuer has real text: no OCR needed.
    const fromText = extract(kind, text)
    if (fromText.number || fromText.masked) return fromText
    return extract(kind, await ocr(canvas, opts.onProgress))
  }
  return extract(kind, await ocr(file, opts.onProgress))
}

// ---------------------------------------------------------------- finding the number

// Aadhaar's last digit is a Verhoeff check digit: it rules out misreads.
const D = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
  [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
  [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
  [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
const P = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
  [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
  [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]

export function verhoeffOk(digits: string): boolean {
  let c = 0
  ;[...digits].reverse().forEach((ch, i) => { c = D[c][P[i % 8][Number(ch)]] })
  return c === 0
}

// OCR mixes up look-alikes. Where a digit must be, read the letter as the digit; and the other way round.
const TO_DIGIT: Record<string, string> = { O: '0', D: '0', Q: '0', I: '1', L: '1', '|': '1', Z: '2', S: '5', B: '8', G: '6', T: '7' }
const TO_LETTER: Record<string, string> = { '0': 'O', '1': 'I', '2': 'Z', '5': 'S', '8': 'B', '6': 'G' }
const digit = (c: string) => TO_DIGIT[c] ?? c
const letter = (c: string) => TO_LETTER[c] ?? c

/** Each character as a letter (L) or digit (D), per the shape of the number. */
function coerce(token: string, shape: string): string | null {
  if (token.length !== shape.length) return null
  let out = ''
  for (let i = 0; i < shape.length; i++) {
    const c = shape[i] === 'D' ? digit(token[i]) : letter(token[i])
    if (shape[i] === 'D' ? !/\d/.test(c) : !/[A-Z]/.test(c)) return null
    out += c
  }
  return out
}

function tokens(text: string, len: number): string[] {
  // Runs of letters/digits, also with the spaces inside numbers removed.
  const words = text.match(/[A-Z0-9|]+/g) ?? []
  const joined: string[] = []
  for (let i = 0; i < words.length; i++) {
    let acc = ''
    for (let j = i; j < Math.min(words.length, i + 4); j++) {
      acc += words[j]
      if (acc.length === len) joined.push(acc)
      if (acc.length >= len) break
    }
  }
  return joined
}

function expiry(text: string): string | null {
  const m = /(EXPIRY|EXPIRES|VALID\s*TILL|VALID\s*UPTO|VALIDITY|DATE\s*OF\s*EXPIRY)/.exec(text)
  if (!m) return null
  const after = text.slice(m.index, m.index + 80)
  const d = /(\d{2})[/\-.](\d{2})[/\-.](\d{4})/.exec(after)
  if (!d) return null
  const [, dd, mm, yyyy] = d
  const iso = `${yyyy}-${mm}-${dd}`
  return Number(mm) >= 1 && Number(mm) <= 12 && Number(dd) >= 1 && Number(dd) <= 31 ? iso : null
}

export function extract(kind: OcrKind, raw: string): OcrResult {
  const text = raw.toUpperCase().replace(/[‐-―]/g, '-')
  const none: OcrResult = { number: null, expires_on: null, masked: false }

  if (kind === 'aadhaar') {
    if (/X{4}\s?X{4}\s?\d{4}/.test(text)) return { ...none, masked: true }
    // Not the 16-digit Virtual ID: three groups of four, then no fourth group.
    const groups = /(?<![0-9A-Z])([0-9OIDLSZB]{4})[\s-]?([0-9OIDLSZB]{4})[\s-]?([0-9OIDLSZB]{4})(?![\s-]?[0-9]{4})(?![0-9])/g
    for (const m of text.matchAll(groups)) {
      const n = [...(m[1] + m[2] + m[3])].map(digit).join('')
      if (/^[2-9]\d{11}$/.test(n) && verhoeffOk(n)) return { ...none, number: n }
    }
    return none
  }
  if (kind === 'pan') {
    for (const t of tokens(text, 10)) {
      const n = coerce(t, 'LLLLLDDDDL')
      // The 4th letter is the holder type: P for a person (C company, H HUF, F firm...).
      if (n && 'PCHFATBLJG'.includes(n[3])) return { ...none, number: n }
    }
    return none
  }
  if (kind === 'passport') {
    for (const t of tokens(text, 8)) {
      const n = coerce(t, 'LDDDDDDD')
      if (n && n[1] !== '0') return { ...none, number: n, expires_on: expiry(text) }
    }
    return none
  }
  if (kind === 'voter_id') {
    for (const t of tokens(text, 10)) {
      const n = coerce(t, 'LLLDDDDDDD')
      if (n) return { ...none, number: n }
    }
    return none
  }
  // Driving licence: state code + RTO + year + serial, e.g. DL04 2019 1234567 (15), sometimes 16.
  for (const len of [15, 16]) {
    for (const t of tokens(text, len)) {
      const n = coerce(t, 'LL' + 'D'.repeat(len - 2))
      if (n) return { ...none, number: n, expires_on: expiry(text) }
    }
  }
  return none
}
