import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Ban, RotateCcw, X } from 'lucide-react'
import { approveUser, listUsers, reactivateUser, rejectUser, suspendUser, updateUser } from '../../api/users'
import { useAuth } from '../../contexts/AuthContext'
import { apiError } from '../../api/client'
import { PageHeader } from '../../components/layout/PageHeader'
import { Avatar, BureauChip, Button, Card, Segmented, Table, TableSkeleton } from '../../components/ui'
import { useBureaus } from '../../hooks/useData'
import { toast } from '../../hooks/useToast'
import { ROLE_LABELS } from '../../lib/domain'
import { cn } from '../../lib/cn'
import type { User } from '../../types'

export default function UserManagementPage() {
  const qc = useQueryClient()
  const { bureaus, byId } = useBureaus()
  const { user: me } = useAuth()
  const [status, setStatus] = useState<'' | 'pending' | 'active' | 'suspended'>('')
  const q = useQuery({ queryKey: ['users', status], queryFn: () => listUsers({ account_status: status || undefined, limit: 200 }) })
  const act = useMutation({
    mutationFn: ({ id, a }: { id: number; a: 'approve' | 'reject' | 'suspend' | 'reactivate' }) => (a === 'approve' ? approveUser(id) : a === 'reject' ? rejectUser(id) : a === 'reactivate' ? reactivateUser(id) : suspendUser(id)),
    onSuccess: () => { toast.success('Account updated'); qc.invalidateQueries({ queryKey: ['users'] }) },
    onError: (e) => toast.error(apiError(e)),
  })
  const edit = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) => updateUser(id, data),
    onSuccess: () => { toast.success('Role / bureau updated'); qc.invalidateQueries({ queryKey: ['users'] }) },
    onError: (e) => toast.error(apiError(e)),
  })
  const mini = 'h-8 rounded-lg border border-slate-200 bg-white px-2 text-[12.5px] text-slate-700 focus:border-royal-300 focus:outline-none'
  return (
    <div>
      <PageHeader eyebrow="Role-based access" title="Users & access" description="Approve officer sign-ups, assign roles and bureaus, suspend access. Bureau officers only see their own bureau's files; overlap metadata is visible across bureaus."
        actions={<Segmented value={status} onChange={setStatus} options={[{ value: '', label: 'All' }, { value: 'pending', label: 'Pending' }, { value: 'active', label: 'Active' }, { value: 'suspended', label: 'Suspended' }]} />} />
      <Card noPadding>
        {q.isLoading ? <TableSkeleton /> : (
          <Table<User> data={q.data?.items ?? []} rowKey={(u) => u.id} columns={[
            { key: 'u', header: 'User', render: (u) => <div className="flex items-center gap-3"><Avatar name={u.full_name} /><div><p className="font-semibold text-slate-800">{u.full_name}</p><p className="text-xs text-slate-400">{u.email}</p></div></div> },
            { key: 'r', header: 'Role', render: (u) => u.id === me?.id ? <span className="text-[13px]">{ROLE_LABELS[u.role as string] ?? u.role}</span> : (
              <select aria-label="Role" className={mini} value={u.role as string} onChange={(e) => edit.mutate({ id: u.id, data: { role: e.target.value } })}>
                {Object.entries(ROLE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            ) },
            { key: 'b', header: 'Bureau', render: (u) => u.role === 'bureau_officer' ? (
              <div className="flex items-center gap-1.5">
                <select aria-label="Bureau" className={cn(mini, !u.bureau_id && 'border-amber-300 bg-amber-50')} value={u.bureau_id ?? ''} onChange={(e) => e.target.value && edit.mutate({ id: u.id, data: { bureau_id: Number(e.target.value) } })}>
                  <option value="">Assign bureau…</option>
                  {bureaus.map((b) => <option key={b.id} value={b.id}>{b.code}</option>)}
                </select>
                {u.bureau_id && <BureauChip code={byId.get(u.bureau_id)?.code} />}
              </div>
            ) : <span className="text-xs text-slate-400">All bureaus</span> },
            { key: 'd', header: 'Designation', render: (u) => <span className="text-[13px] text-slate-500">{u.designation ?? '—'}</span> },
            { key: 's', header: 'Status', render: (u) => <span className={cn('chip', u.account_status === 'active' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : u.account_status === 'pending' ? 'border-amber-200 bg-amber-50 text-amber-700' : 'border-rose-200 bg-rose-50 text-rose-700')}>{u.account_status}</span> },
            { key: 'a', header: '', render: (u) => (
              <div className="flex justify-end gap-1">
                {u.account_status === 'pending' && <><Button size="xs" variant="success" disabled={u.role === 'bureau_officer' && !u.bureau_id} title={u.role === 'bureau_officer' && !u.bureau_id ? 'Assign a bureau first' : undefined} leftIcon={<Check className="h-3 w-3" />} onClick={() => act.mutate({ id: u.id, a: 'approve' })}>Approve</Button><Button size="xs" variant="secondary" leftIcon={<X className="h-3 w-3" />} onClick={() => act.mutate({ id: u.id, a: 'reject' })}>Reject</Button></>}
                {u.account_status === 'active' && u.id !== me?.id && <Button size="xs" variant="ghost" leftIcon={<Ban className="h-3 w-3" />} onClick={() => act.mutate({ id: u.id, a: 'suspend' })}>Suspend</Button>}
                {['suspended', 'rejected'].includes(u.account_status as string) && <Button size="xs" variant="ghost" leftIcon={<RotateCcw className="h-3 w-3" />} onClick={() => act.mutate({ id: u.id, a: 'reactivate' })}>Reactivate</Button>}
                {u.id === me?.id && <span className="text-xs text-slate-400">You</span>}
              </div>
            ) },
          ]} />
        )}
      </Card>
    </div>
  )
}
