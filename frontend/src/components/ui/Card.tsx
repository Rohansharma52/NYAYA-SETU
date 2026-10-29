import React from 'react'
import { cn } from '../../lib/cn'

interface CardProps {
  title?: React.ReactNode
  subtitle?: React.ReactNode
  icon?: React.ReactNode
  action?: React.ReactNode
  children?: React.ReactNode
  className?: string
  bodyClassName?: string
  hover?: boolean
  noPadding?: boolean
}

export function Card({ title, subtitle, icon, action, children, className, bodyClassName, hover, noPadding }: CardProps) {
  return (
    <section className={cn('card overflow-hidden', hover && 'card-hover', className)}>
      {(title || action) && (
        <header className="flex items-start justify-between gap-4 px-5 pt-5">
          <div className="flex min-w-0 items-start gap-3">
            {icon && (
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-royal-50 text-royal-600">
                {icon}
              </div>
            )}
            <div className="min-w-0">
              {title && <h3 className="truncate text-[15px] font-bold text-slate-900">{title}</h3>}
              {subtitle && <p className="mt-0.5 text-[13px] text-slate-500">{subtitle}</p>}
            </div>
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </header>
      )}
      <div className={cn(!noPadding && 'p-5', (title || action) && !noPadding && 'pt-4', bodyClassName)}>{children}</div>
    </section>
  )
}
