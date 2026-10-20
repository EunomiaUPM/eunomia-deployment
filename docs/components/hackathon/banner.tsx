import Link from 'next/link';
import { hackathon } from '@/lib/hackathon';

/** The strip on top of the home page that points to the event. Off with `banner: false`. */
export function HackathonBanner() {
  if (!hackathon.banner) return null;
  return (
    <Link
      href="/hackathon"
      className="group relative z-10 flex items-center justify-center gap-3 border-b border-fd-border bg-fd-card/70 px-4 py-2.5 text-sm backdrop-blur transition-colors hover:bg-fd-accent"
    >
      <span className="rounded-full bg-gradient-brand px-2.5 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wider text-brand-night">
        {hackathon.kicker}
      </span>
      <span className="font-medium text-fd-foreground">{hackathon.name}</span>
      <span className="hidden text-fd-muted-foreground sm:inline">· {hackathon.dateLabel}</span>
      <span aria-hidden className="text-fd-muted-foreground transition-transform group-hover:translate-x-0.5">
        →
      </span>
    </Link>
  );
}
