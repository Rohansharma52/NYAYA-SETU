import React from 'react'
import { Link } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { cn } from '../../lib/cn'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'gold' | 'dark' | 'success'
export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg'

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    'text-white bg-gradient-to-b from-royal-500 to-royal-600 shadow-[0_1px_0_rgba(255,255,255,.25)_inset,0_8px_20px_-8px_rgba(68,71,222,.7)] hover:from-royal-500 hover:to-royal-700 active:translate-y-px',
  secondary:
    'text-slate-700 bg-white border border-slate-200 shadow-soft hover:border-slate-300 hover:bg-slate-50 active:translate-y-px',
  ghost: 'text-slate-600 hover:text-slate-900 hover:bg-slate-100',
  danger:
    'text-white bg-gradient-to-b from-rose-500 to-rose-600 shadow-[0_8px_20px_-8px_rgba(225,29,72,.7)] hover:to-rose-700 active:translate-y-px',
  gold:
    'text-ink-900 bg-gradient-to-b from-gold-300 to-gold-500 shadow-[0_1px_0_rgba(255,255,255,.45)_inset,0_10px_24px_-10px_rgba(236,150,11,.9)] hover:to-gold-600 active:translate-y-px',
  dark: 'text-white bg-ink-800 hover:bg-ink-700 border border-white/10 active:translate-y-px',
  success:
    'text-white bg-gradient-to-b from-emerald-500 to-emerald-600 shadow-[0_8px_20px_-8px_rgba(5,150,105,.7)] hover:to-emerald-700 active:translate-y-px',
}

const SIZES: Record<ButtonSize, string> = {
  xs: 'h-7 px-2.5 text-xs gap-1 rounded-lg',
  sm: 'h-8 px-3 text-[13px] gap-1.5 rounded-lg',
  md: 'h-10 px-4 text-sm gap-2 rounded-xl',
  lg: 'h-12 px-6 text-[15px] gap-2 rounded-xl',
}

interface BaseProps {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  className?: string
  children?: React.ReactNode
}

type ButtonProps = BaseProps & React.ButtonHTMLAttributes<HTMLButtonElement>

export function Button({
  variant = 'primary',
  size = 'md',
  loading,
  leftIcon,
  rightIcon,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={cn(
        'inline-flex select-none items-center justify-center whitespace-nowrap font-semibold transition-all duration-200 disabled:pointer-events-none disabled:opacity-55',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : leftIcon}
      {children}
      {!loading && rightIcon}
    </button>
  )
}

interface ButtonLinkProps extends BaseProps {
  to: string
}

export function ButtonLink({ to, variant = 'primary', size = 'md', leftIcon, rightIcon, className, children }: ButtonLinkProps) {
  return (
    <Link
      to={to}
      className={cn(
        'inline-flex select-none items-center justify-center whitespace-nowrap font-semibold transition-all duration-200',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
    >
      {leftIcon}
      {children}
      {rightIcon}
    </Link>
  )
}

export function IconButton({
  className,
  children,
  label,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button
      aria-label={label}
      title={label}
      {...rest}
      className={cn(
        'inline-flex h-9 w-9 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-800',
        className,
      )}
    >
      {children}
    </button>
  )
}
