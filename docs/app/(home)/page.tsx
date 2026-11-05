import Link from 'next/link';
import type { Metadata } from 'next';
import { Architecture } from '@/components/diagrams';
import { ArrowIcon, GitHubIcon } from '@/components/landing/icons';
import { ButtonLink, Glow, Heading, Lead, Marquee, Section, Terminal, type TerminalLine } from '@/components/landing/primitives';
import { asset, components, site, standards } from '@/lib/site';

export const metadata: Metadata = {
  title: { absolute: site.title },
  description: site.description,
};

const heroScript: TerminalLine[] = [
  { kind: 'cmd', text: './eunomia authority add authority' },
  { kind: 'ok', text: 'authority is ready' },
  { kind: 'cmd', text: './eunomia agent add alice && ./eunomia agent add bob' },
  { kind: 'ok', text: 'alice holds gx_LabelCredential_jwt_vc_json' },
  { kind: 'ok', text: 'bob holds gx_LabelCredential_jwt_vc_json' },
  { kind: 'cmd', text: './eunomia demo publish alice' },
  { kind: 'cmd', text: './eunomia demo test --consumer bob --provider alice' },
  { kind: 'ok', text: 'bob is connected to alice' },
  { kind: 'dim', text: '  8/8 FINALIZED  agreement=urn:agreement:3b72dec8…' },
  { kind: 'ok', text: 'Dataplane proxy -> HTTP 200, 5 robot(s)' },
  { kind: 'ok', text: 'event received: robot_temperature = 47.30' },
  { kind: 'info', text: 'END-TO-END TEST PASSED' },
];

const paths = [
  {
    title: 'On one machine',
    body: 'Any number of authorities and agents as Docker Compose projects, for development, demos and workshops. Docker is the only requirement.',
    href: '/docs/deployment/local',
    link: 'Local deployment',
  },
  {
    title: 'One per server',
    body: 'Every participant on its own server: HashiCorp Vault, TLS and did:web. The eunomia CLI manages them by name from anywhere.',
    href: '/docs/deployment/production',
    link: 'Production',
  },
  {
    title: 'From a pipeline',
    body: 'A GitHub Actions workflow that deploys the authority first and then every agent over SSH, with the images pinned in versions.env.',
    href: '/docs/deployment/production/automated-deployment',
    link: 'Automated deployment',
  },
];

const steps = [
  {
    n: '01',
    title: 'Onboard',
    body: 'The authority issues each agent its credentials over OID4VCI, Gaia-X legal and label credentials included. Wallets keep the keys.',
  },
  {
    n: '02',
    title: 'Agree',
    body: 'One agent asks for another’s catalog and negotiates over the Dataspace Protocol: eight states, from request to a finalized agreement on an ODRL policy.',
  },
  {
    n: '03',
    title: 'Exchange',
    body: 'Under that agreement the data flows: pulled through the publishing agent’s proxy, or pushed as events to the other’s endpoint. Next time, they swap.',
  },
];

const extensionPoints = [
  { name: 'commands()', body: 'Actions of its own: eunomia <name> <action>.' },
  { name: 'services()', body: 'The stacks it runs, known to status, logs, stop, down and doctor.' },
  { name: 'test()', body: 'Its end-to-end test between any two agents.' },
  { name: 'notebooks()', body: 'Its exchange, call by call, in Jupyter.' },
];

const faq = [
  {
    q: 'What is a data space?',
    a: 'A network where organisations share data under rules they agree on: who may use it, for what and until when. Participants prove their identity with verifiable credentials, every exchange starts with a contract, and the data travels through the agent of whoever owns it.',
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
    a: 'A local data space, authority and agents included, runs end to end in CI in both directions. The production deployment, one participant per server with HashiCorp Vault, TLS and did:web, is documented but not yet validated against a real Vault: treat it as the way there, not as a finished recipe.',
  },
];

export default function HomePage() {
  return (
    <main className="relative flex flex-1 flex-col overflow-hidden">
      {/* Hero */}
      <div className="relative">
        <div aria-hidden className="bg-grid absolute inset-0 -z-10" />
        <Glow className="-top-40 left-1/2 h-[520px] w-[820px] -translate-x-1/2" />
        <Section className="grid items-center gap-14 pb-16 pt-20 md:pt-28 lg:grid-cols-[1.05fr_1fr]">
          <div>
            <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-fd-border bg-fd-card/60 px-3 py-1 font-mono text-xs uppercase tracking-[0.2em] text-fd-muted-foreground backdrop-blur">
              <span className="size-1.5 rounded-full bg-brand-sky" />
              Deployment and operations
            </p>
            <Heading as="h1" first="Deploy a data space." second="From laptop to servers." />
            <Lead>
              Everything to run EUNOMIA: an authority and as many agents as you need, managed by name with one CLI, and
              extensions for the data you want to share. Minutes from{' '}
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
            <p className="mt-6 font-mono text-xs text-fd-muted-foreground">Docker is all you need · GPL-3.0</p>
          </div>
          <Terminal title="~/eunomia-deployment" lines={heroScript} />
        </Section>
      </div>

      <Marquee items={standards} />

      {/* 01 Where it runs */}
      <Section number="01" label="Where it runs">
        <Heading first="Same commands." second="Three ways to run them." />
        <Lead>Instances have names, and every command takes a name, wherever the instance lives.</Lead>
        <div className="mt-14 grid gap-5 md:grid-cols-3">
          {paths.map((p, i) => (
            <Link key={p.title} href={p.href} className="card-glow group block p-7">
              <p className="font-mono text-xs text-fd-muted-foreground">0{i + 1}</p>
              <h3 className="mt-4 text-xl font-semibold text-fd-foreground">{p.title}</h3>
              <p className="mt-3 leading-relaxed text-fd-muted-foreground">{p.body}</p>
              <span className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-fd-primary">
                {p.link} <ArrowIcon className="size-4 transition-transform group-hover:translate-x-0.5" />
              </span>
            </Link>
          ))}
        </div>
      </Section>

      {/* 02 How it works */}
      <Section number="02" label="How it works">
        <Heading first="Every agent publishes." second="Every agent consumes." />
        <Lead>
          There is no provider kind or consumer kind of node: only agents, and the roles they take in each exchange. The
          authority decides who belongs.
        </Lead>
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

      {/* 04 Extensions */}
      <div className="relative">
        <Glow className="right-[-200px] top-20 h-[420px] w-[620px]" />
        <Section number="04" label="Extensions">
          <Heading first="The core runs the data space." second="Extensions bring the data." />
          <Lead>
            What the agents share is not part of the core. An extension is a directory in your own repository: it gets
            a command group, and this repository stays untouched.
          </Lead>
          <div className="mt-14 grid gap-px overflow-hidden rounded-2xl border border-fd-border bg-fd-border md:grid-cols-2">
            {extensionPoints.map((p) => (
              <div key={p.name} className="bg-fd-background p-8">
                <h3 className="font-mono text-lg font-semibold text-fd-foreground">{p.name}</h3>
                <p className="mt-3 leading-relaxed text-fd-muted-foreground">{p.body}</p>
              </div>
            ))}
          </div>
          <Link href="/docs/guides/build-an-extension" className="mt-8 inline-flex items-center gap-2 text-sm font-medium text-fd-primary hover:underline">
            Build your first extension <ArrowIcon className="size-4" />
          </Link>
        </Section>
      </div>

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
          <Heading first="Start building." second="Your data space is minutes away." className="mx-auto max-w-3xl" />
          <div className="mx-auto mt-10 max-w-xl text-left">
            <Terminal
              title="get started"
              lines={[
                { kind: 'cmd', text: 'git clone https://github.com/EunomiaUPM/eunomia-deployment.git && cd eunomia-deployment' },
                { kind: 'cmd', text: './eunomia authority add authority' },
                { kind: 'cmd', text: './eunomia agent add alice && ./eunomia agent add bob' },
                { kind: 'cmd', text: './eunomia demo up && ./eunomia demo publish alice' },
                { kind: 'cmd', text: './eunomia demo test --consumer bob --provider alice' },
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
        { text: 'Extensions', href: '/docs/guides/build-an-extension' },
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
