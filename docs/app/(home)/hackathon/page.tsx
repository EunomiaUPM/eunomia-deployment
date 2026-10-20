import type { Metadata } from 'next';
import { Countdown } from '@/components/hackathon/countdown';
import { ArrowIcon } from '@/components/landing/icons';
import { ButtonLink, Glow, Heading, Lead, Section, Terminal } from '@/components/landing/primitives';
import { agenda, challenges, faq, hackathon, milestones, needs, rules } from '@/lib/hackathon';
import { site } from '@/lib/site';

export const metadata: Metadata = {
  title: hackathon.name,
  description:
    'A live, online and free hackathon: deploy your own data space nodes, prove your identity, negotiate an ODRL contract and exchange real data, all in sixty minutes on the clock.',
};

const audiences = [
  {
    who: 'Developers and architects',
    pain: 'Weeks of configuration files and heavy containers before two nodes say hello.',
    answer: 'From git clone to an interoperable data space in minutes. One CLI, every step checked.',
  },
  {
    who: 'EU projects and consortia',
    pain: 'Most of the work package goes into making two connectors talk, not into the use case.',
    answer: 'Open protocols out of the box. Spend the budget on your data, not on the plumbing.',
  },
  {
    who: 'CTOs and sovereignty leads',
    pain: 'Solutions that tie you to one cloud, one vendor or one consultancy dressed as open source.',
    answer: 'Real open source under GPL-3.0, no open core. Technical sovereignty from end to end.',
  },
];

function RegisterButton() {
  if (hackathon.registrationUrl) {
    return (
      <ButtonLink href={hackathon.registrationUrl} external>
        Save your seat <ArrowIcon className="size-4" />
      </ButtonLink>
    );
  }
  return (
    <span className="inline-flex cursor-default items-center gap-2 rounded-full border border-dashed border-fd-border px-5 py-2.5 text-sm text-fd-muted-foreground">
      Registration opens soon
    </span>
  );
}

export default function HackathonPage() {
  return (
    <main className="relative flex flex-1 flex-col overflow-hidden">
      {/* Hero */}
      <div className="relative">
        <div aria-hidden className="bg-dots absolute inset-0 -z-10" />
        <Glow className="-top-48 left-1/2 h-[560px] w-[900px] -translate-x-1/2" />
        <Section className="pb-12 pt-20 text-center md:pt-28">
          <p className="mx-auto mb-8 inline-flex items-center gap-2 rounded-full border border-fd-border bg-fd-card/60 px-3 py-1 font-mono text-xs uppercase tracking-[0.2em] text-fd-muted-foreground backdrop-blur">
            <span className="size-1.5 animate-pulse rounded-full bg-[#5af78e]" />
            {hackathon.kicker} · {hackathon.format}
          </p>
          <Heading as="h1" first="Build a data space." second="In one hour." className="mx-auto max-w-4xl" />
          <Lead className="mx-auto">
            If it takes six months of consulting to stand up a data space, you don’t have a standard. You have a hostage
            situation. Bring a laptop: in sixty minutes on the clock you will deploy your own nodes, prove who you are,
            negotiate an ODRL contract and move real data end to end. No tricks.
          </Lead>
          <p className="mt-8 font-mono text-sm text-fd-foreground">{hackathon.dateLabel}</p>
          <div className="mt-6 flex justify-center">
            <Countdown start={hackathon.start} durationMinutes={hackathon.durationMinutes} />
          </div>
          <div className="mt-10 flex flex-wrap justify-center gap-3">
            <RegisterButton />
            <ButtonLink href={site.codespaces} variant="secondary" external>
              Open in Codespaces
            </ButtonLink>
            <ButtonLink href="/docs/quickstart" variant="secondary">
              Warm up with the quickstart
            </ButtonLink>
          </div>
        </Section>
      </div>

      {/* 01 Manifesto */}
      <Section number="01" label="The manifesto">
        <div className="grid gap-12 lg:grid-cols-[1fr_1.1fr]">
          <Heading first="Data spaces were meant to be open." second="Then they got heavy." />
          <div className="space-y-5 text-lg leading-relaxed text-fd-muted-foreground">
            <p>
              The promise was extraordinary: organisations, cities, universities and companies sharing data while keeping
              full sovereignty over it. Executable usage policies, verifiable decentralised identity, and one common
              protocol so any node could talk to any other.
            </p>
            <p>
              Then the slides met the terminal. Monolithic stacks, endless configuration, learning curves that eat a
              project’s budget before a single useful byte moves. A standard that only one heavyweight implementation can
              run is not an open standard.
            </p>
            <p className="text-fd-foreground">
              EUNOMIA is the other way: small Rust components, open protocols end to end, one command-line tool that
              checks its own work, and real open source with nothing held back. This hackathon is the proof, with the
              clock running.
            </p>
          </div>
        </div>
        <div className="mt-14 grid gap-5 md:grid-cols-3">
          {audiences.map((a) => (
            <div key={a.who} className="card-glow p-7">
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-fd-muted-foreground">{a.who}</p>
              <p className="mt-5 text-fd-muted-foreground line-through decoration-brand-magenta/60">{a.pain}</p>
              <p className="mt-4 text-lg font-medium text-fd-foreground">{a.answer}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* 02 The challenge */}
      <Section number="02" label="The 60-minute challenge">
        <Heading first="Four milestones." second="Fifteen minutes each." />
        <Lead>
          A countdown on screen, the stage terminal on one side and yours on the other. Each milestone ends with
          something you can see.
        </Lead>
        <ol className="mt-14 space-y-6">
          {milestones.map((m) => (
            <li key={m.number} className="grid gap-6 rounded-2xl border border-fd-border bg-fd-card/50 p-6 md:grid-cols-[1.1fr_1fr] md:p-8">
              <div>
                <div className="flex items-baseline gap-4">
                  <span className="text-gradient font-mono text-5xl font-semibold">{m.number}</span>
                  <span className="font-mono text-xs uppercase tracking-[0.2em] text-fd-muted-foreground">min {m.window}</span>
                </div>
                <h3 className="mt-5 text-2xl font-semibold text-fd-foreground">{m.title}</h3>
                <p className="mt-1 text-fd-muted-foreground">{m.subtitle}</p>
                <ul className="mt-5 space-y-2 text-fd-muted-foreground">
                  {m.steps.map((s) => (
                    <li key={s} className="flex gap-3">
                      <span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-brand-violet" />
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
                <p className="mt-5 text-sm font-medium text-fd-foreground">
                  <span className="text-[#5af78e]">✔</span> {m.result}
                </p>
              </div>
              <Terminal className="self-start" title={`milestone ${m.number}`} lines={m.commands.map((c) => ({ kind: 'cmd' as const, text: c }))} />
            </li>
          ))}
        </ol>
      </Section>

      {/* 03 Run of show */}
      <div className="relative">
        <Glow className="left-[-220px] top-24 h-[420px] w-[620px]" />
        <Section number="03" label="Run of show">
          <Heading first="Ninety minutes." second="The train never stops." />
          <div className="mt-14 grid gap-5 md:grid-cols-3">
            {agenda.map((a) => (
              <div key={a.time} className="rounded-2xl border border-fd-border bg-fd-card/60 p-7">
                <p className="font-mono text-sm text-fd-primary">min {a.time}</p>
                <h3 className="mt-4 text-xl font-semibold text-fd-foreground">{a.title}</h3>
                <p className="mt-3 leading-relaxed text-fd-muted-foreground">{a.body}</p>
              </div>
            ))}
          </div>
          <div className="mt-5 grid gap-px overflow-hidden rounded-2xl border border-fd-border bg-fd-border md:grid-cols-3">
            {rules.map((r) => (
              <div key={r.title} className="bg-fd-background p-7">
                <h3 className="font-semibold text-fd-foreground">{r.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-fd-muted-foreground">{r.body}</p>
              </div>
            ))}
          </div>
        </Section>
      </div>

      {/* 04 What you need */}
      <Section number="04" label="What you need">
        <div className="grid gap-12 lg:grid-cols-2">
          <div>
            <Heading first="A laptop and Docker." second="Or just a browser." />
            <Lead>
              Check your machine before the day with <code className="font-mono text-fd-foreground">./eunomia doctor</code>:
              it tells you exactly what to fix.
            </Lead>
          </div>
          <ul className="space-y-4 self-center">
            {needs.map((n) => (
              <li key={n} className="flex gap-4 rounded-xl border border-fd-border bg-fd-card/50 p-4 text-fd-foreground">
                <span className="text-[#5af78e]">✔</span>
                {n}
              </li>
            ))}
          </ul>
        </div>
      </Section>

      {/* 05 Challenges */}
      <Section number="05" label="Keep building">
        <Heading first="Finished early?" second="Pick a challenge." />
        <div className="mt-14 grid gap-8 lg:grid-cols-3">
          {challenges.map((group) => (
            <div key={group.level}>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-fd-muted-foreground">{group.level}</p>
              <div className="mt-4 space-y-4">
                {group.items.map((c) => (
                  <div key={c.title} className="card-glow p-6">
                    <h3 className="font-semibold text-fd-foreground">{c.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-fd-muted-foreground">{c.body}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* FAQ */}
      <Section label="Questions">
        <div className="grid gap-10 lg:grid-cols-[1fr_1.6fr]">
          <Heading first="Before you ask." second="Answers." />
          <div className="divide-y divide-fd-border border-y border-fd-border">
            {faq.map((f) => (
              <details key={f.q} className="group py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between text-lg font-medium text-fd-foreground">
                  {f.q}
                  <span className="ml-4 text-fd-muted-foreground transition-transform group-open:rotate-45">+</span>
                </summary>
                <p className="mt-3 leading-relaxed text-fd-muted-foreground">{f.a}</p>
              </details>
            ))}
            {hackathon.supportUrl && (
              <p className="py-5 text-fd-muted-foreground">
                Anything else?{' '}
                <a href={hackathon.supportUrl} className="text-fd-primary hover:underline">
                  Ask us
                </a>
                .
              </p>
            )}
          </div>
        </div>
      </Section>

      {/* CTA */}
      <div className="relative">
        <Glow className="bottom-0 left-1/2 h-[380px] w-[760px] -translate-x-1/2" />
        <Section className="text-center">
          <Heading first="The clock starts soon." second="Be there when it does." className="mx-auto max-w-3xl" />
          <p className="mt-6 font-mono text-sm text-fd-foreground">{hackathon.dateLabel}</p>
          <div className="mt-10 flex flex-wrap justify-center gap-3">
            <RegisterButton />
            <ButtonLink href="/" variant="secondary">
              About EUNOMIA
            </ButtonLink>
          </div>
        </Section>
      </div>
    </main>
  );
}
