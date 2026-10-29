import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Building2, MapPin } from 'lucide-react'
import { listInstitutions } from '../../api/institutions'
import { PageHeader } from '../../components/layout/PageHeader'
import { Card, EmptyState, ErrorState, Pagination, SearchBar, Select, SkeletonCard } from '../../components/ui'
import { useDebounce } from '../../hooks/useData'
import { REGIONS } from '../../lib/domain'

const LIMIT = 24

export default function InstitutionListPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [region, setRegion] = useState('')
  const [skip, setSkip] = useState(0)
  const ds = useDebounce(search, 300)
  const q = useQuery({
    queryKey: ['institutions', ds, region, skip],
    queryFn: () => listInstitutions({ search: ds || undefined, region: region || undefined, skip, limit: LIMIT }),
    placeholderData: keepPreviousData,
  })
  return (
    <div>
      <PageHeader
        eyebrow="Centralized institution profile"
        title="Institutions"
        description="One profile per institution with AICTE Permanent ID, region and the consolidated history of complaints across every Bureau/Cell."
      />
      <div className="mb-5 flex flex-col gap-3 sm:flex-row">
        <SearchBar value={search} onChange={(v) => { setSearch(v); setSkip(0) }} placeholder="Search name, acronym, city…" className="flex-1" />
        <Select value={region} onChange={(e) => { setRegion(e.target.value); setSkip(0) }} placeholder="All regions" options={REGIONS.map((r) => ({ value: r, label: r }))} wrapperClassName="sm:w-56" />
      </div>
      {q.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}</div>
      ) : q.isError ? <ErrorState onRetry={() => q.refetch()} /> : (q.data?.items ?? []).length === 0 ? (
        <Card><EmptyState icon={Building2} title="No institutions found" /></Card>
      ) : (
        <>
          <div className="stagger grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {q.data!.items.map((i) => {
              const aicte = i.identifiers?.find((x) => x.id_type === 'aicte_permanent_id')?.id_value
              const open = i.open_cases ?? 0
              return (
                <button key={i.id} onClick={() => navigate(`/institutions/${i.id}`)} className="card card-hover group p-5 text-left">
                  <div className="flex items-start gap-3">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-royal-50 to-white text-sm font-extrabold text-royal-700 ring-1 ring-royal-100">
                      {(i.short_name ?? i.canonical_name).slice(0, 4)}
                    </span>
                    <div className="min-w-0">
                      <p className="line-clamp-2 text-sm font-bold leading-snug text-slate-900 group-hover:text-royal-700">{i.canonical_name}</p>
                      <p className="mt-1 flex items-center gap-1 text-xs text-slate-500"><MapPin className="h-3 w-3" />{[i.city, i.state].filter(Boolean).join(', ')} · {i.region}</p>
                    </div>
                  </div>
                  <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-xs">
                    <span className="font-mono text-slate-400">{aicte ?? '—'}</span>
                    <span className="flex gap-3">
                      <span><b className="text-slate-800">{i.total_cases ?? 0}</b> <span className="text-slate-400">cases</span></span>
                      <span><b className={open ? 'text-orange-600' : 'text-slate-800'}>{open}</b> <span className="text-slate-400">open</span></span>
                    </span>
                  </div>
                </button>
              )
            })}
          </div>
          <div className="mt-5"><Pagination total={q.data!.total} skip={skip} limit={LIMIT} onPageChange={setSkip} /></div>
        </>
      )}
    </div>
  )
}
