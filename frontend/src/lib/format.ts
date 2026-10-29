import { format, formatDistanceToNowStrict, differenceInCalendarDays, parseISO, isValid } from 'date-fns'

function toDate(value?: string | Date | null): Date | null {
  if (!value) return null
  // The API stores timestamps in UTC; SQLite returns them without an offset, so treat
  // any date-time string lacking a zone designator as UTC (date-only strings stay local).
  const d = typeof value === 'string'
    ? parseISO(/T\d{2}:\d{2}/.test(value) && !/(Z|[+-]\d{2}:?\d{2})$/.test(value) ? `${value}Z` : value)
    : value
  return isValid(d) ? d : null
}

export function fmtDate(value?: string | Date | null, pattern = 'dd MMM yyyy'): string {
  const d = toDate(value)
  return d ? format(d, pattern) : '—'
}

export function fmtDateTime(value?: string | Date | null): string {
  return fmtDate(value, 'dd MMM yyyy, HH:mm')
}

export function fromNow(value?: string | Date | null): string {
  const d = toDate(value)
  return d ? `${formatDistanceToNowStrict(d)} ago` : '—'
}

/** Positive = days remaining, negative = days overdue */
export function daysUntil(value?: string | Date | null): number | null {
  const d = toDate(value)
  return d ? differenceInCalendarDays(d, new Date()) : null
}

export function ageInDays(value?: string | Date | null): number | null {
  const d = toDate(value)
  return d ? Math.max(0, differenceInCalendarDays(new Date(), d)) : null
}

export function titleCase(value?: string | null): string {
  if (!value) return '—'
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export function compact(n: number): string {
  if (n >= 100000) return `${(n / 100000).toFixed(1)}L`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

export function pct(n?: number | null, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return `${n.toFixed(digits)}%`
}

export function initials(name?: string | null): string {
  if (!name) return '?'
  return name
    .replace(/^(Dr|Mr|Ms|Mrs|Prof)\.?\s+/i, '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('')
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  // Keep the object URL alive long enough for slow disks / "Save as" dialogs
  setTimeout(() => URL.revokeObjectURL(url), 60000)
}

export function toCSV(rows: Record<string, unknown>[], columns?: { key: string; label: string }[]): string {
  if (!rows.length) return ''
  const cols = columns ?? Object.keys(rows[0]).map((k) => ({ key: k, label: k }))
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? '' : String(v)
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const lines = [cols.map((c) => esc(c.label)).join(',')]
  for (const r of rows) lines.push(cols.map((c) => esc(r[c.key])).join(','))
  return lines.join('\n')
}

export function downloadCSV(filename: string, rows: Record<string, unknown>[], columns?: { key: string; label: string }[]) {
  const note = '\n\nDEMO DATA - synthetic records for the SIH prototype. Not official AICTE data.\n'
  // UTF-8 BOM so Excel opens ₹, — and Hindi text correctly; header row stays on line 1
  const blob = new Blob(['\uFEFF' + toCSV(rows, columns) + note], { type: 'text/csv;charset=utf-8' })
  const stamp = format(new Date(), 'yyyyMMdd_HHmm')
  downloadBlob(blob, filename.replace(/\.csv$/, `_${stamp}.csv`))
}
