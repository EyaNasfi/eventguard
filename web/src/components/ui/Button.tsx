import { Loader } from 'lucide-react';
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '../../lib/cn';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ReactNode;
  /** Keyboard hint shown at the end, e.g. "A". */
  kbd?: string;
}

const VARIANT: Record<ButtonVariant, string> = {
  // Primary carries the brand; status colours stay reserved for meaning.
  primary: 'bg-brand-fill text-on-accent border-brand-fill shadow-sm hover:bg-brand-fill-hover hover:border-brand-fill-hover',
  secondary: 'bg-surface-1 text-text border-line hover:bg-surface-2 hover:text-strong',
  ghost: 'bg-transparent text-muted border-transparent hover:bg-surface-1 hover:text-text',
  danger: 'bg-transparent text-stop border-stop-line hover:bg-stop-bg',
};

const SIZE: Record<ButtonSize, string> = {
  sm: 'h-7 px-2.5 text-xs gap-1.5 font-medium',
  md: 'h-9 px-4 text-[0.8125rem] gap-2 font-medium',
};

/** The button look, for links and controls that must look like buttons (one scale everywhere). */
export function buttonClass(variant: ButtonVariant = 'secondary', size: ButtonSize = 'md', className?: string): string {
  return cn(
    'relative inline-flex shrink-0 items-center justify-center whitespace-nowrap rounded-lg border select-none no-underline',
    'transition-[background-color,border-color,color,transform] duration-[var(--dur-press)] ease-out',
    'active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100',
    'aria-disabled:cursor-not-allowed aria-disabled:opacity-60 aria-disabled:active:scale-100',
    VARIANT[variant],
    SIZE[size],
    className,
  );
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'secondary', size = 'md', loading = false, icon, kbd, className, children, disabled, type = 'button', onClick, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      // While loading the button stays focusable (aria-disabled, clicks ignored), so keyboard focus is not lost.
      disabled={disabled}
      aria-disabled={loading || undefined}
      aria-busy={loading || undefined}
      onClick={loading ? (e) => e.preventDefault() : onClick}
      className={buttonClass(variant, size, className)}
      {...rest}
    >
      {loading ? <Loader aria-hidden className="size-3.5 animate-spin motion-reduce:animate-none" /> : icon}
      {children}
      {kbd ? (
        <kbd aria-hidden className={cn('ml-1 rounded-xs border px-1 font-mono text-xs font-medium', variant === 'primary' ? 'border-white/30 text-on-accent/80' : 'border-line-strong text-muted')}>
          {kbd}
        </kbd>
      ) : null}
    </button>
  );
});
