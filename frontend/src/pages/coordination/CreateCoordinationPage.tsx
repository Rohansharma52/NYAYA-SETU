import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { addDays, format } from 'date-fns'
import { GitMerge } from 'lucide-react'
import { createCoordination } from '../../api/coordination'
import { apiError } from '../../api/client'
import { PageHeader } from '../../components/layout/PageHeader'
import { Button, Card, Input, Textarea } from '../../components/ui'
import { useBureaus } from '../../hooks/useData'
import { toast } from '../../hooks/useToast'
import { bureauStyle } from '../../lib/domain'

export default function CreateCoordinationPage() {
  const navigate = useNavigate()
  const { bureaus } = useBureaus()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [selected, setSelected] = useState<number[]>([])
  const [ack, setAck] = useState(format(addDays(new Date(), 3), 'yyyy-MM-dd'))
  const [due, setDue] = useState(format(addDays(new Date(), 15), 'yyyy-MM-dd'))
  const m = useMutation({
    mutationFn: () => createCoordination({ title, description, bureau_ids: selected, acknowledge_by: new Date(ack).toISOString(), action_due_date: new Date(due).toISOString() }),
    onSuccess: (c) => { toast.success(`${c.reference_number} created`); navigate(`/coordination/${c.id}`) },
    onError: (e) => toast.error(apiError(e)),
  })
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader breadcrumbs={[{ label: 'Coordination', href: '/coordination' }, { label: 'New' }]} title="New coordination item"
        description="Tip: for an institution flagged on the Overlap Radar, use “Start One-Voice coordination” — it pre-fills the lead bureau, participants and tasks." />
      <Card icon={<GitMerge className="h-5 w-5" />} title="Details">
        <div className="space-y-4">
          <Input label="Title" required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Fee regulation — joint review" />
          <Textarea label="Context" rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
          <div>
            <p className="mb-2 text-[13px] font-semibold text-slate-700">Participating Bureaus / Cells</p>
            <div className="flex flex-wrap gap-2">
              {bureaus.map((b) => {
                const on = selected.includes(b.id)
                const st = bureauStyle(b.code)
                return (
                  <button key={b.id} onClick={() => setSelected((s) => on ? s.filter((x) => x !== b.id) : [...s, b.id])}
                    className="rounded-xl border px-3 py-2 text-left text-sm transition"
                    style={on ? { background: `${st.color}12`, borderColor: st.color, color: st.color } : { borderColor: '#E2E8F0' }}>
                    <b>{b.code}</b> <span className="text-xs opacity-80">{b.name}</span>
                  </button>
                )
              })}
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Acknowledge by" type="date" value={ack} onChange={(e) => setAck(e.target.value)} />
            <Input label="Action due" type="date" value={due} onChange={(e) => setDue(e.target.value)} />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => navigate(-1)}>Cancel</Button>
            <Button disabled={title.trim().length < 5 || selected.length < 2} loading={m.isPending} onClick={() => m.mutate()}>Create</Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
