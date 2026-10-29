import React from 'react'
import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useDocumentTitle } from '../../hooks/useData'

export interface Breadcrumb {
  label: string
  href?: string
}

interface PageHeaderProps {
  title: React.ReactNode
  docTitle?: string
  eyebrow?: React.ReactNode
  description?: React.ReactNode
  breadcrumbs?: Breadcrumb[]
  actions?: React.ReactNode
}

export function PageHeader({ title, docTitle, eyebrow, description, breadcrumbs, actions }: PageHeaderProps) {
  useDocumentTitle(docTitle ?? (typeof title === 'string' ? title : 'NYAYA SETU'))
  return (
    <div className="mb-6 animate-fade-up">
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="mb-3 flex items-center gap-1 text-xs font-medium text-slate-400" aria-label="Breadcrumb">
          {breadcrumbs.map((c, i) => (
            <React.Fragment key={i}>
              {i > 0 && <ChevronRight className="h-3.5 w-3.5" />}
              {c.href ? (
                <Link to={c.href} className="transition hover:text-slate-700">{c.label}</Link>
              ) : (
                <span className="text-slate-600">{c.label}</span>
              )}
            </React.Fragment>
          ))}
        </nav>
      )}
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          {eyebrow && <div className="label-eyebrow mb-1.5">{eyebrow}</div>}
          <h1 className="text-[26px] font-extrabold leading-tight text-slate-900 sm:text-[28px]">{title}</h1>
          {description && <p className="mt-1.5 max-w-3xl text-sm text-slate-500">{description}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  )
}
