import React from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import { cn } from '../../lib/cn'

export type SortDir = 'asc' | 'desc'

export interface TableColumn<T> {
  key: string
  header: React.ReactNode
  render: (row: T, index: number) => React.ReactNode
  sortable?: boolean
  className?: string
  headerClassName?: string
}

interface TableProps<T> {
  columns: TableColumn<T>[]
  data: T[]
  rowKey: (row: T) => string | number
  onRowClick?: (row: T) => void
  sortKey?: string
  sortDir?: SortDir
  onSort?: (key: string) => void
  empty?: React.ReactNode
  className?: string
  rowClassName?: (row: T) => string | undefined
}

export function Table<T>({ columns, data, rowKey, onRowClick, sortKey, sortDir, onSort, empty, className, rowClassName }: TableProps<T>) {
  return (
    <div className={cn('overflow-x-auto', className)}>
      <table className="table-modern w-full min-w-[720px] border-separate border-spacing-0">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} className={cn('first:rounded-tl-xl last:rounded-tr-xl', col.headerClassName)}>
                {col.sortable && onSort ? (
                  <button className="inline-flex items-center gap-1 hover:text-slate-800" onClick={() => onSort(col.key)}>
                    {col.header}
                    {sortKey === col.key ? (
                      sortDir === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                    ) : (
                      <ArrowUpDown className="h-3 w-3 opacity-40" />
                    )}
                  </button>
                ) : (
                  col.header
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="!py-14 text-center text-sm text-slate-400">
                {empty ?? 'No records found'}
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cn(onRowClick && 'cursor-pointer', rowClassName?.(row))}
                style={{ animation: `fade-up .45s var(--ease-out) ${Math.min(i, 12) * 0.025}s both` }}
              >
                {columns.map((col) => (
                  <td key={col.key} className={col.className}>
                    {col.render(row, i)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
