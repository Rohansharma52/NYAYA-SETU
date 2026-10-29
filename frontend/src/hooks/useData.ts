import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listBureaus } from '../api/bureaus'
import type { Bureau } from '../types'

export function useBureaus() {
  const q = useQuery({ queryKey: ['bureaus'], queryFn: listBureaus, staleTime: 10 * 60 * 1000 })
  const byId = useMemo(() => {
    const m = new Map<number, Bureau>()
    for (const b of q.data ?? []) m.set(b.id, b)
    return m
  }, [q.data])
  const byCode = useMemo(() => {
    const m = new Map<string, Bureau>()
    for (const b of q.data ?? []) m.set(b.code, b)
    return m
  }, [q.data])
  return { bureaus: q.data ?? [], byId, byCode, isLoading: q.isLoading }
}

export function useDebounce<T>(value: T, delay = 300): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return v
}

export function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = `${title} · NYAYA SETU`
  }, [title])
}
