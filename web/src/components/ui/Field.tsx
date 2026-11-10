import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';
import { cn } from '../../lib/cn';

const CONTROL =
  'w-full rounded-sm border border-control bg-surface-1 px-2.5 text-sm text-text placeholder:text-muted ' +
  'transition-[border-color,background-color] duration-[var(--dur-fast)] ease-out ' +
  'hover:border-[color-mix(in_oklab,var(--text)_30%,var(--line-strong))] focus-visible:border-focus focus-visible:outline-offset-0 ' +
  'disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-stop';

interface FieldShellProps {
  label: string;
  hint?: ReactNode;
  error?: string;
  hideLabel?: boolean;
  className?: string;
  children: (ids: { id: string; describedBy: string | undefined; invalid: boolean }) => ReactNode;
}

function FieldShell({ label, hint, error, hideLabel, className, children }: FieldShellProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errId = error ? `${id}-err` : undefined;
  const describedBy = [hintId, errId].filter(Boolean).join(' ') || undefined;
  return (
    <div className={cn('flex min-w-0 flex-col gap-1', className)}>
      <label htmlFor={id} className={cn('field-label', hideLabel && 'sr-only')}>
        {label}
      </label>
      {children({ id, describedBy, invalid: Boolean(error) })}
      {hint && !error ? (
        <p id={hintId} className="text-xs text-muted">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errId} className="text-xs text-stop">
          <span className="font-semibold">Error:</span> {error}
        </p>
      ) : null}
    </div>
  );
}

type Common = { label: string; hint?: ReactNode; error?: string; hideLabel?: boolean; wrapperClassName?: string };

export function TextField({ label, hint, error, hideLabel, wrapperClassName, className, ...rest }: Common & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <FieldShell label={label} hint={hint} {...(error ? { error } : {})} {...(hideLabel ? { hideLabel } : {})} {...(wrapperClassName ? { className: wrapperClassName } : {})}>
      {({ id, describedBy, invalid }) => (
        <input id={id} aria-describedby={describedBy} aria-invalid={invalid || undefined} className={cn(CONTROL, 'h-9', className)} {...rest} />
      )}
    </FieldShell>
  );
}

export function SelectField({ label, hint, error, hideLabel, wrapperClassName, className, children, ...rest }: Common & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <FieldShell label={label} hint={hint} {...(error ? { error } : {})} {...(hideLabel ? { hideLabel } : {})} {...(wrapperClassName ? { className: wrapperClassName } : {})}>
      {({ id, describedBy, invalid }) => (
        <select id={id} aria-describedby={describedBy} aria-invalid={invalid || undefined} className={cn(CONTROL, 'h-9 pr-7', className)} {...rest}>
          {children}
        </select>
      )}
    </FieldShell>
  );
}

export function TextAreaField({ label, hint, error, hideLabel, wrapperClassName, className, ...rest }: Common & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <FieldShell label={label} hint={hint} {...(error ? { error } : {})} {...(hideLabel ? { hideLabel } : {})} {...(wrapperClassName ? { className: wrapperClassName } : {})}>
      {({ id, describedBy, invalid }) => (
        <textarea id={id} aria-describedby={describedBy} aria-invalid={invalid || undefined} className={cn(CONTROL, 'min-h-20 py-2 leading-relaxed', className)} {...rest} />
      )}
    </FieldShell>
  );
}

/** Toggle switch with a visible on/off word. */
export function Switch({
  checked,
  onChange,
  label,
  description,
  disabled,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
  description?: ReactNode;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <div className="flex items-start gap-3">
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        aria-describedby={description ? `${id}-d` : undefined}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          'mt-0.5 inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-[background-color,border-color] duration-[var(--dur-fast)] ease-out disabled:opacity-50',
          checked ? 'border-ok bg-ok-bg' : 'border-control bg-surface-2',
        )}
      >
        <span
          aria-hidden
          className={cn(
            'block size-3.5 rounded-full transition-transform duration-[var(--dur-base)] ease-out motion-reduce:transition-none',
            checked ? 'translate-x-[18px] bg-ok' : 'translate-x-[2px] bg-muted',
          )}
        />
      </button>
      <div className="min-w-0">
        <label htmlFor={id} className="flex items-center gap-2 text-sm font-semibold">
          {label}
          <span className={cn('font-mono text-2xs font-medium uppercase tracking-wide', checked ? 'text-ok' : 'text-muted')}>{checked ? 'On' : 'Off'}</span>
        </label>
        {description ? (
          <p id={`${id}-d`} className="mt-0.5 text-xs text-muted">
            {description}
          </p>
        ) : null}
      </div>
    </div>
  );
}
