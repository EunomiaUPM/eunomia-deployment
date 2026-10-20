import Link from 'next/link';
import type { Metadata } from 'next';
import { Architecture } from '@/components/diagrams';
import { HackathonBanner } from '@/components/hackathon/banner';
import { ArrowIcon, GitHubIcon } from '@/components/landing/icons';
import { ButtonLink, Glow, Heading, Lead, Marquee, Section, Terminal, type TerminalLine } from '@/components/landing/primitives';
import { asset, components, site, standards, team } from '@/lib/site';

export const metadata: Metadata = {
  title: { absolute: site.title },
  description: site.description,
};

const heroScript: TerminalLine[] = [
  { kind: 'cmd', text: './eunomia up' },
  { kind: 'ok', text: 'Authority is ready' },
  { kind: 'ok', text: 'Provider is ready' },
  { kind: 'ok', text: 'Consumer is ready' },
  { kind: 'ok', text: 'consumer holds gx_LabelCredential_jwt_vc_json' },
  { kind: 'ok', text: 'consumer is connected to provider' },
  { kind: 'ok', text: 'Catalog populated' },
  { kind: 'cmd', text: './eunomia e2e' },
  { kind: 'dim', text: '  8/8 FINALIZED  agreement=urn:agreement:3b72dec8…' },
  { kind: 'ok', text: 'Dataplane proxy -> HTTP 200, 5 robot(s)' },
  { kind: 'ok', text: 'event received: robot_temperature = 47.30' },
  { kind: 'info', text: 'END-TO-END TEST PASSED' },
];

const goals = [
  {
    title: 'Trust as commitment',
    body: 'Every participant proves who it is with verifiable credentials from an authority, and every exchange starts with a contract both sides agreed to. Trust is checked, never assumed.',
  },
  {
    title: 'Exploring the data space',
    body: 'Providers publish DCAT catalogs with ODRL policies attached. Consumers see what exists, and on what terms, before a single byte moves.',
  },
  {
    title: 'Joining data efficiently',
    body: 'Pull on demand or stream as events, through the provider’s own data plane. The backend’s credentials never leave the provider.',
  },
];

const steps = [
  {
    n: '01',
    title: 'Onboard',
    body: 'The authority issues each participant its credentials over OID4VCI, Gaia-X legal and label credentials included. Wallets keep the keys.',
  },
  {
    n: '02',
    title: 'Agree',
    body: 'Consumer and provider negotiate over the Dataspace Protocol: eight states, from request to a finalized agreement on an ODRL policy.',
  },
  {
    n: '03',
    title: 'Exchange',
    body: 'Under that agreement the data flows: pulled through the provider’s proxy, or pushed as events to the consumer’s endpoint.',
  },
];

const principles = [
  {
    letter: 'A',
    title: 'Radically simple',
    body: 'One CLI, one command per step, and every step checks its own result. Docker is the only thing your machine needs.',
  },
  {
    letter: 'B',
    title: 'Interoperable by design',
    body: 'Dataspace Protocol, DCAT, ODRL, GNAP, OpenID for Verifiable Credentials, W3C VCs and DIDs. Open protocols end to end, no proprietary handshake.',
  },
  {
    letter: 'C',
    title: 'Sovereign by default',
    body: 'Your keys stay in your wallet, your backend credentials in your provider, your terms in your policies.',
  },
  {
    letter: 'D',
    title: 'Open source, no asterisks',
    body: 'GPL-3.0, every component. No open core, no enterprise edition holding back the piece you need.',
  },
];

const stats = [
  { value: '3', label: 'commands from git clone to data flowing' },
  { value: '8', label: 'Dataspace Protocol states to an agreement' },
  { value: '4', label: 'Rust components, each with its own database' },
  { value: '100%', label: 'open source, under GPL-3.0' },
];

const faq = [
  {
    q: 'What is a data space?',
    a: 'A network where organisations share data under rules they agree on: who may use it, for what and until when. Participants prove their identity with verifiable credentials, every exchange starts with a contract, and the data travels through the provider’s own connector.',
  },
  {
    q: 'How does EUNOMIA relate to Gaia-X and IDSA?',
    a: 'EUNOMIA supports Gaia-X ISBL and DSBA. Its agents speak the Dataspace Protocol 2025-1, published by IDSA and on its way to an Eclipse specification, and its authority issues Gaia-X legal and label credentials.',
  },
  {
    q: 'Can it talk to other connectors?',
    a: 'That is the point of building on the Dataspace Protocol and open identity standards rather than on a platform: any implementation that speaks them can take part in the same data space.',
  },
  {
    q: 'Is it ready for production?',
    a: 'The single-machine deployment runs end to end in CI. The production deployment, one participant per server with HashiCorp Vault, TLS and did:web, is documented but not yet validated against a real Vault: treat it as the way there, not as a finished recipe.',
  },
];

function initials(name: string) {
  return name
    .split(' ')
    .map((p) => p[0])
    .slice(0, 2)
    .join('');
}

export default function HomePage() {
  return (
    <main className="relative flex flex-1 flex-col overflow-hidden">
      <HackathonBanner />

      {/* Hero */}
      <div className="relative">
        <div aria-hidden className="bg-grid absolute inset-0 -z-10" />
        <Glow className="-top-40 left-1/2 h-[520px] w-[820px] -translate-x-1/2" />
        <Section className="grid items-center gap-14 pb-16 pt-20 md:pt-28 lg:grid-cols-[1.05fr_1fr]">
          <div>
            <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-fd-border bg-fd-card/60 px-3 py-1 font-mono text-xs uppercase tracking-[0.2em] text-fd-muted-foreground backdrop-blur">
              <span className="size-1.5 rounded-full bg-brand-sky" />
              Open-source data spaces
            </p>
            <Heading as="h1" first="Data spaces in minutes." second="Not quarters." />
            <Lead>
              EUNOMIA is an open-source framework for sovereign, interoperable data sharing. An authority, a provider and a
              consumer, with verifiable credentials and ODRL contracts over the Dataspace Protocol. Three commands from{' '}
              <code className="font-mono text-fd-foreground">git clone</code> to data flowing.
            </Lead>
            <div className="mt-10 flex flex-wrap gap-3">
              <ButtonLink href="/docs/quickstart">
                Get started <ArrowIcon className="size-4" />
              </ButtonLink>
              <ButtonLink href={site.github} variant="secondary" external>
                <GitHubIcon className="size-4" /> View on GitHub
              </ButtonLink>
            </div>
            <p className="mt-6 font-mono text-xs text-fd-muted-foreground">Docker is all you need · Rust · GPL-3.0</p>
          </div>
          <Terminal title="~/eunomia-deployment" lines={heroScript} />
        </Section>
      </div>

      <Marquee items={standards} />

      {/* 01 Why */}
      <Section number="01" label="Why EUNOMIA">
        <Heading first="Trust is the protocol." second="Not the paperwork." />
        <Lead>{site.description}</Lead>
        <div className="mt-14 grid gap-5 md:grid-cols-3">
          {goals.map((g, i) => (
            <div key={g.title} className="card-glow p-7">
              <p className="font-mono text-xs text-fd-muted-foreground">0{i + 1}</p>
              <h3 className="mt-4 text-xl font-semibold text-fd-foreground">{g.title}</h3>
              <p className="mt-3 leading-relaxed text-fd-muted-foreground">{g.body}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* 02 How it works */}
      <Section number="02" label="How it works">
        <Heading first="Three participants." second="One handshake at a time." />
        <div className="mt-14 grid gap-5 md:grid-cols-3">
          {steps.map((s) => (
            <div key={s.n} className="relative rounded-2xl border border-fd-border bg-fd-card/60 p-7">
              <span className="text-gradient font-mono text-4xl font-semibold">{s.n}</span>
              <h3 className="mt-5 text-xl font-semibold text-fd-foreground">{s.title}</h3>
              <p className="mt-3 leading-relaxed text-fd-muted-foreground">{s.body}</p>
            </div>
          ))}
        </div>
        <div className="mt-8">
          <Architecture />
        </div>
        <Link href="/docs/architecture" className="mt-2 inline-flex items-center gap-2 text-sm font-medium text-fd-primary hover:underline">
          Read the architecture <ArrowIcon className="size-4" />
        </Link>
      </Section>

      {/* 03 Components */}
      <Section number="03" label="Components">
        <Heading first="Small parts." second="Serious guarantees." />
        <Lead>Four Rust services and libraries, each with one job, wired together by configuration and open protocols.</Lead>
        <div className="mt-14 grid gap-5 sm:grid-cols-2">
          {components.map((c) => (
            <Link key={c.name} href={c.docs} className="card-glow group block p-7">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs uppercase tracking-[0.2em] text-fd-muted-foreground">{c.role}</span>
                <span className="rounded-full border border-fd-border px-2 py-0.5 font-mono text-[11px] text-fd-muted-foreground">Rust</span>
              </div>
              <h3 className="mt-5 text-2xl font-semibold text-fd-foreground">{c.name}</h3>
              <p className="mt-3 leading-relaxed text-fd-muted-foreground">{c.summary}</p>
              <span className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-fd-primary">
                Read more <ArrowIcon className="size-4 transition-transform group-hover:translate-x-0.5" />
              </span>
            </Link>
          ))}
        </div>
      </Section>

      {/* 04 Principles */}
      <div className="relative">
        <Glow className="right-[-200px] top-20 h-[420px] w-[620px]" />
        <Section number="04" label="Principles">
          <Heading first="From git clone to a data space." second="In an afternoon, not a semester." />
          <div className="mt-14 grid gap-px overflow-hidden rounded-2xl border border-fd-border bg-fd-border md:grid-cols-2">
            {principles.map((p) => (
              <div key={p.letter} className="bg-fd-background p-8">
                <span className="flex size-9 items-center justify-center rounded-lg border border-fd-border font-mono text-sm text-fd-foreground">
                  {p.letter}
                </span>
                <h3 className="mt-5 text-xl font-semibold text-fd-foreground">{p.title}</h3>
                <p className="mt-3 leading-relaxed text-fd-muted-foreground">{p.body}</p>
              </div>
            ))}
          </div>
          <div className="mt-14 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((s) => (
              <div key={s.label}>
                <p className="text-gradient text-5xl font-semibold tracking-tight">{s.value}</p>
                <p className="mt-2 text-sm text-fd-muted-foreground">{s.label}</p>
              </div>
            ))}
          </div>
        </Section>
      </div>

      {/* 05 People */}
      <Section number="05" label="Built at UPM">
        <Heading first="Research-grade." second="Open to everyone." />
        <Lead>{site.group}.</Lead>
        <div className="mt-12 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {team.map((m) => (
            <div key={m.name} className="flex items-center gap-3 rounded-xl border border-fd-border bg-fd-card/50 p-3">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-gradient-brand font-mono text-xs font-semibold text-brand-night">
                {initials(m.name)}
              </span>
              <div>
                <p className="text-sm font-medium text-fd-foreground">{m.name}</p>
                <p className="text-xs text-fd-muted-foreground">{m.role}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-10 flex flex-col items-start gap-8 rounded-2xl bg-brand-night p-8 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap items-center gap-10">
            <img src={asset('/brand/upm_logo_light.svg')} alt="Universidad Politécnica de Madrid" className="h-12 w-auto" />
            <img src={asset('/brand/incibe_logo_white.png')} alt="INCIBE" className="h-10 w-auto" />
          </div>
          <p className="max-w-md text-sm leading-relaxed text-white/70">{site.funding}</p>
        </div>
      </Section>

      {/* FAQ */}
      <Section label="Questions">
        <div className="grid gap-10 lg:grid-cols-[1fr_1.6fr]">
          <Heading first="Fair questions." second="Straight answers." />
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
          </div>
        </div>
      </Section>

      {/* CTA */}
      <div className="relative">
        <Glow className="bottom-0 left-1/2 h-[380px] w-[760px] -translate-x-1/2" />
        <Section className="text-center">
          <Heading first="Start building." second="Your data space is three commands away." className="mx-auto max-w-3xl" />
          <div className="mx-auto mt-10 max-w-xl text-left">
            <Terminal
              title="get started"
              lines={[
                { kind: 'cmd', text: 'git clone https://github.com/EunomiaUPM/eunomia-deployment.git' },
                { kind: 'cmd', text: 'cd eunomia-deployment && ./eunomia up' },
                { kind: 'cmd', text: './eunomia e2e' },
              ]}
            />
          </div>
          <div className="mt-10 flex flex-wrap justify-center gap-3">
            <ButtonLink href="/docs/quickstart">
              Read the quickstart <ArrowIcon className="size-4" />
            </ButtonLink>
            <ButtonLink href={site.codespaces} variant="secondary" external>
              Open in Codespaces
            </ButtonLink>
          </div>
        </Section>
      </div>

      <Footer />
    </main>
  );
}

function Footer() {
  const columns = [
    {
      title: 'Learn',
      links: [
        { text: 'Introduction', href: '/docs' },
        { text: 'Quickstart', href: '/docs/quickstart' },
        { text: 'Architecture', href: '/docs/architecture' },
        { text: 'Components', href: '/docs/components' },
      ],
    },
    {
      title: 'Build',
      links: [
        { text: 'Deployment', href: '/docs/deployment' },
        { text: 'CLI', href: '/docs/cli' },
        { text: 'API reference', href: '/docs/api' },
        { text: 'Troubleshooting', href: '/docs/troubleshooting' },
      ],
    },
    {
      title: 'Community',
      links: [
        { text: 'GitHub', href: site.github },
        { text: 'Project website', href: site.website },
        { text: 'Contact', href: `mailto:${site.contact}` },
      ],
    },
  ];
  return (
    <footer className="border-t border-fd-border">
      <div className="mx-auto grid w-full max-w-6xl gap-12 px-6 py-16 md:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div>
          <img src={asset('/brand/eunomia_logo_lg_dark.svg')} alt={site.name} className="h-7 w-auto dark:hidden" />
          <img src={asset('/brand/eunomia_logo_lg_light.svg')} alt={site.name} className="hidden h-7 w-auto dark:block" />
          <p className="mt-4 max-w-xs text-sm text-fd-muted-foreground">{site.tagline} Open source under {site.license}.</p>
          <address className="mt-4 text-xs not-italic leading-relaxed text-fd-muted-foreground">
            {site.address.map((l) => (
              <span key={l} className="block">
                {l}
              </span>
            ))}
            <a href={`mailto:${site.contact}`} className="mt-1 block hover:text-fd-foreground">
              {site.contact}
            </a>
          </address>
        </div>
        {columns.map((col) => (
          <div key={col.title}>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-fd-muted-foreground">{col.title}</p>
            <ul className="mt-4 space-y-2 text-sm">
              {col.links.map((l) => (
                <li key={l.text}>
                  {l.href.startsWith('/') ? (
                    <Link href={l.href} className="text-fd-foreground/80 hover:text-fd-foreground">
                      {l.text}
                    </Link>
                  ) : (
                    <a href={l.href} className="text-fd-foreground/80 hover:text-fd-foreground">
                      {l.text}
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </footer>
  );
}
