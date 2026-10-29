import React, { useId } from 'react'
import { cn } from '../../lib/cn'

interface FieldShellProps {
  label?: string
  hint?: string
  error?: string
  required?: boolean
  htmlFor?: string
  children: React.ReactNode
  className?: string
}

export function Field({ label, hint, error, required, htmlFor, children, className }: FieldShellProps) {
  return (
    <div className={cn('space-y-1.5', className)}>
      {label && (
        <label htmlFor={htmlFor} className="block text-[13px] font-semibold text-slate-700">
          {label}
          {required && <span className="ml-0.5 text-rose-500">*</span>}
        </label>
      )}
      {children}
      {error ? (
        <p role="alert" className="text-xs font-medium text-rose-600">{error}</p>
      ) : hint ? (
        <p className="text-xs text-slate-500">{hint}</p>
      ) : null}
    </div>
  )
}

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  hint?: string
  error?: string
  leftIcon?: React.ReactNode
  rightSlot?: React.ReactNode
  wrapperClassName?: string
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, hint, error, required, leftIcon, rightSlot, className, wrapperClassName, id, ...rest },
  ref,
) {
  const auto = useId()
  const inputId = id ?? auto
  return (
    <Field label={label} hint={hint} error={error} required={required} htmlFor={inputId} className={wrapperClassName}>
      <div className="relative">
        {leftIcon && (
          <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-slate-400">{leftIcon}</span>
        )}
        <input
          ref={ref}
          id={inputId}
          required={required}
          aria-invalid={!!error}
          className={cn(
            'input-base',
            leftIcon && 'pl-10',
            rightSlot && 'pr-11',
            error && 'border-rose-300 focus:border-rose-400 focus:ring-rose-100',
            className,
          )}
          {...rest}
        />
        {rightSlot && <span className="absolute inset-y-0 right-2 flex items-center">{rightSlot}</span>}
      </div>
    </Field>
  )
})

export interface SelectOption {
  value: string
  label: string
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  hint?: string
  error?: string
  options: SelectOption[]
  placeholder?: string
  wrapperClassName?: string
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, hint, error, options, placeholder, required, className, wrapperClassName, id, ...rest },
  ref,
) {
  const auto = useId()
  const selectId = id ?? auto
  return (
    <Field label={label} hint={hint} error={error} required={required} htmlFor={selectId} className={wrapperClassName}>
      <div className="relative">
        <select
          ref={ref}
          id={selectId}
          required={required}
          className={cn('input-base appearance-none pr-9', error && 'border-rose-300', className)}
          {...rest}
        >
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <svg className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
          <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
        </svg>
      </div>
    </Field>
  )
})

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  hint?: string
  error?: string
  wrapperClassName?: string
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, hint, error, required, className, wrapperClassName, id, rows = 4, ...rest },
  ref,
) {
  const auto = useId()
  const areaId = id ?? auto
  return (
    <Field label={label} hint={hint} error={error} required={required} htmlFor={areaId} className={wrapperClassName}>
      <textarea
        ref={ref}
        id={areaId}
        rows={rows}
        required={required}
        className={cn('input-base resize-y leading-relaxed', error && 'border-rose-300', className)}
        {...rest}
      />
    </Field>
  )
})
