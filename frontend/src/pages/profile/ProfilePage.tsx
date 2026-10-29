import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Save } from 'lucide-react'
import { apiClient, apiError } from '../../api/client'
import { PageHeader } from '../../components/layout/PageHeader'
import { Avatar, BureauChip, Button, Card, Input } from '../../components/ui'
import { useAuth } from '../../contexts/AuthContext'
import { useBureaus } from '../../hooks/useData'
import { toast } from '../../hooks/useToast'
import { ROLE_LABELS } from '../../lib/domain'

export default function ProfilePage() {
  const { user } = useAuth()
  const { byId } = useBureaus()
  const [name, setName] = useState(user?.full_name ?? '')
  const [desig, setDesig] = useState(user?.designation ?? '')
  const m = useMutation({ mutationFn: () => apiClient.put('/auth/me', { full_name: name, designation: desig }), onSuccess: () => toast.success('Profile saved'), onError: (e) => toast.error(apiError(e)) })
  const bureau = user?.bureau_id ? byId.get(user.bureau_id) : undefined
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="My profile" />
      <div className="bg-hero relative mb-6 overflow-hidden rounded-3xl p-6 text-white">
        <div className="absolute inset-0 bg-grid opacity-30" />
        <div className="relative flex items-center gap-4">
          <Avatar name={user?.full_name} size={64} className="ring-4 ring-white/10" />
          <div>
            <p className="text-xl font-extrabold">{user?.full_name}</p>
            <p className="text-sm text-white/60">{user?.email}</p>
            <div className="mt-2 flex items-center gap-2 text-xs"><span className="rounded-full bg-white/10 px-2.5 py-1 font-semibold">{ROLE_LABELS[user?.role ?? '']}</span>{bureau && <BureauChip code={bureau.code} solid />}</div>
          </div>
        </div>
      </div>
      <Card title="Details">
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Full name" value={name} onChange={(e) => setName(e.target.value)} />
          <Input label="Designation" value={desig} onChange={(e) => setDesig(e.target.value)} />
        </div>
        <div className="mt-5 flex justify-end"><Button leftIcon={<Save className="h-4 w-4" />} loading={m.isPending} onClick={() => m.mutate()}>Save</Button></div>
      </Card>
    </div>
  )
}
