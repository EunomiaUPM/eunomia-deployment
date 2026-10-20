'use client';
import { useEffect, useState } from 'react';

function parts(ms: number) {
  const s = Math.max(0, Math.floor(ms / 1000));
  return {
    days: Math.floor(s / 86400),
    hours: Math.floor((s % 86400) / 3600),
    minutes: Math.floor((s % 3600) / 60),
    seconds: s % 60,
  };
}

/** Time left until the event; "Live now" during it, "That was fun" after. */
export function Countdown({ start, durationMinutes }: { start: string; durationMinutes: number }) {
  const target = new Date(start).getTime();
  const end = target + durationMinutes * 60_000;
  // Rendered statically at build time: wait for the browser before showing numbers.
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  if (now !== null && now >= target && now < end) {
    return <p className="font-mono text-lg text-[#5af78e]">● Live now</p>;
  }
  if (now !== null && now >= end) {
    return <p className="font-mono text-lg text-fd-muted-foreground">That was fun. See you at the next one.</p>;
  }

  const p = parts(now === null ? 0 : target - now);
  const cells: [string, number][] = [
    ['days', p.days],
    ['hours', p.hours],
    ['min', p.minutes],
    ['sec', p.seconds],
  ];
  return (
    <div className="flex gap-3" aria-label="Time until the event starts">
      {cells.map(([label, value]) => (
        <div key={label} className="min-w-[78px] rounded-xl border border-fd-border bg-fd-card/70 px-3 py-3 text-center backdrop-blur">
          <p className="font-mono text-3xl font-semibold tabular-nums text-fd-foreground">
            {now === null ? '--' : String(value).padStart(2, '0')}
          </p>
          <p className="mt-1 font-mono text-[11px] uppercase tracking-widest text-fd-muted-foreground">{label}</p>
        </div>
      ))}
    </div>
  );
}
