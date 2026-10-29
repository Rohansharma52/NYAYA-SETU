import { cn } from '../../lib/cn'

export interface TabItem {
  id: string
  label: string
  count?: number
  icon?: React.ReactNode
}

interface TabsProps {
  tabs: TabItem[]
  activeTab: string
  onTabChange: (id: string) => void
  className?: string
}

export function Tabs({ tabs, activeTab, onTabChange, className }: TabsProps) {
  return (
    <div className={cn('inline-flex max-w-full gap-1 overflow-x-auto rounded-xl bg-slate-100/80 p-1', className)} role="tablist">
      {tabs.map((t) => {
        const active = t.id === activeTab
        return (
          <button
            key={t.id}
            role="tab"
            aria-selected={active}
            onClick={() => onTabChange(t.id)}
            className={cn(
              'inline-flex items-center gap-2 whitespace-nowrap rounded-lg px-3.5 py-1.5 text-[13px] font-semibold transition-all duration-200',
              active ? 'bg-white text-slate-900 shadow-soft' : 'text-slate-500 hover:text-slate-800',
            )}
          >
            {t.icon}
            {t.label}
            {t.count !== undefined && (
              <span className={cn('rounded-full px-1.5 py-px text-[10px] font-bold tabular', active ? 'bg-royal-100 text-royal-700' : 'bg-slate-200 text-slate-600')}>
                {t.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
