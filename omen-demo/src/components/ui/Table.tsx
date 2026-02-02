import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';

export interface TableProps {
  children: ReactNode;
  className?: string;
}

export function Table({ children, className = '' }: TableProps) {
  return (
    <div className={cn('overflow-x-auto overflow-thin-scroll rounded-[var(--radius-card)] border border-[var(--border-subtle)]', className)}>
      <table className="w-full border-collapse text-left text-sm font-body">
        {children}
      </table>
    </div>
  );
}

export interface TableHeaderProps {
  children: ReactNode;
  className?: string;
}

export function TableHeader({ children, className = '' }: TableHeaderProps) {
  return (
    <thead>
      <tr className={cn('border-b border-[var(--border-subtle)] bg-[var(--bg-tertiary)]', className)}>
        {children}
      </tr>
    </thead>
  );
}

export interface TableBodyProps {
  children: ReactNode;
  className?: string;
}

export function TableBody({ children, className = '' }: TableBodyProps) {
  return <tbody className={cn('divide-y divide-[var(--border-subtle)]', className)}>{children}</tbody>;
}

export interface TableRowProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}

export function TableRow({ children, className = '', hover = true }: TableRowProps) {
  return (
    <tr
      className={cn(
        'transition-colors',
        hover && 'hover:bg-[var(--bg-tertiary)]/50',
        className
      )}
    >
      {children}
    </tr>
  );
}

export interface TableHeadProps {
  children: ReactNode;
  className?: string;
}

export function TableHead({ children, className = '' }: TableHeadProps) {
  return (
    <th
      className={cn(
        'px-4 py-3 text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] font-mono',
        className
      )}
    >
      {children}
    </th>
  );
}

export interface TableCellProps {
  children: ReactNode;
  className?: string;
  mono?: boolean;
}

export function TableCell({ children, className = '', mono }: TableCellProps) {
  return (
    <td
      className={cn(
        'px-4 py-3 text-[var(--text-primary)]',
        mono && 'font-mono text-[var(--text-secondary)]',
        className
      )}
    >
      {children}
    </td>
  );
}
