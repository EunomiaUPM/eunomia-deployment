import Link from 'next/link';
import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

/** A page-wide band with an optional numbered label: "01 / Why EUNOMIA". */
export function Section({
  id,
  number,
  label,
  children,
  className,
}: {
  id?: string;
  number?: string;
  label?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section id={id} className={cn('relative mx-auto w-full max-w-6xl px-6 py-24 md:py-32', className)}>
      {label && (
        <p className="mb-6 font-mono text-xs uppercase tracking-[0.25em] text-fd-muted-foreground">
          {number && <span className="text-gradient font-semibold">{number}</span>}
          {number && <span className="mx-2 opacity-50">/</span>}
          {label}
        </p>
      )}
      {children}
    </section>
  );
}

/** A statement headline in two beats: the first plain, the second in the brand gradient. */
export function Heading({ first, second, as: Tag = 'h2', className }: {
  first: ReactNode;
  second?: ReactNode;
  as?: 'h1' | 'h2';
  className?: string;
}) {
  return (
    <Tag
      className={cn(
        'font-semibold tracking-tight text-fd-foreground',
        Tag === 'h1' ? 'text-5xl leading-[1.02] sm:text-6xl md:text-7xl' : 'text-4xl leading-[1.05] md:text-5xl',
        className,
      )}
    >
      <span className="block">{first}</span>
      {second && <span className="text-gradient block">{second}</span>}
    </Tag>
  );
}

export function Lead({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn('mt-6 max-w-2xl text-lg leading-relaxed text-fd-muted-foreground', className)}>{children}</p>;
}

export function ButtonLink({
  href,
  children,
  variant = 'primary',
  external,
}: {
  href: string;
  children: ReactNode;
  variant?: 'primary' | 'secondary';
  external?: boolean;
}) {
  const className = cn(
    'inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-all',
    variant === 'primary'
      ? 'bg-gradient-brand text-brand-night shadow-[0_8px_30px_-8px] shadow-brand-violet/60 hover:brightness-110'
      : 'border border-fd-border bg-fd-card/60 text-fd-foreground backdrop-blur hover:border-brand-violet/60',
  );
  if (external) {
    return (
      <a href={href} className={className} target="_blank" rel="noreferrer">
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}

/** Soft brand-coloured light behind a section. */
export function Glow({ className }: { className?: string }) {
  return (
    <div aria-hidden className={cn('pointer-events-none absolute -z-10', className)}>
      <div className="animate-float h-full w-full rounded-full bg-gradient-brand opacity-25 blur-[120px] dark:opacity-30" />
    </div>
  );
}

/** An infinite strip of labels. */
export function Marquee({ items }: { items: string[] }) {
  const row = [...items, ...items];
  return (
    <div className="relative overflow-hidden border-y border-fd-border py-5 [mask-image:linear-gradient(to_right,transparent,black_12%,black_88%,transparent)]">
      <div className="animate-marquee flex w-max gap-10">
        {row.map((item, i) => (
          <span key={i} className="flex items-center gap-10 whitespace-nowrap font-mono text-sm text-fd-muted-foreground">
            {item}
            <span aria-hidden className="text-brand-violet">✦</span>
          </span>
        ))}
      </div>
    </div>
  );
}

export type TerminalLine = { kind: 'cmd' | 'ok' | 'info' | 'dim'; text: string };

/** A terminal window with a script of lines; the lines appear one after another. */
export function Terminal({ title, lines, className }: { title: string; lines: TerminalLine[]; className?: string }) {
  return (
    <div className={cn('overflow-hidden rounded-2xl border border-fd-border bg-[#0b0a20] shadow-2xl shadow-brand-violet/20', className)}>
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
        <span className="size-3 rounded-full bg-[#ff5f57]" />
        <span className="size-3 rounded-full bg-[#febc2e]" />
        <span className="size-3 rounded-full bg-[#28c840]" />
        <span className="ml-3 font-mono text-xs text-white/50">{title}</span>
      </div>
      <pre className="overflow-x-auto p-5 font-mono text-[13px] leading-6">
        {lines.map((line, i) => (
          <div
            key={i}
            className="terminal-line"
            style={{ animationDelay: `${0.15 + i * 0.22}s` }}
          >
            {line.kind === 'cmd' && (
              <span>
                <span className="text-brand-sky">$ </span>
                <span className="text-white">{line.text}</span>
              </span>
            )}
            {line.kind === 'ok' && <span className="text-[#5af78e]">✔ {line.text}</span>}
            {line.kind === 'info' && <span className="text-[#c4b5fd]">{line.text}</span>}
            {line.kind === 'dim' && <span className="text-white/45">{line.text}</span>}
          </div>
        ))}
      </pre>
    </div>
  );
}
