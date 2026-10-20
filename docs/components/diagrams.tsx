/**
 * Architecture diagrams as inline SVG. Colours come from the theme tokens, so
 * they read the same in light and dark mode.
 */
import type { ReactNode } from 'react';

type BoxProps = {
  x: number;
  y: number;
  w: number;
  h: number;
  title: string;
  subtitle?: string;
  chip?: string;
  accent?: boolean;
};

function Box({ x, y, w, h, title, subtitle, chip, accent }: BoxProps) {
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={12}
        className={accent ? 'fill-fd-accent stroke-fd-primary' : 'fill-fd-card stroke-fd-border'}
        strokeWidth={accent ? 1.5 : 1}
      />
      <text x={x + 16} y={y + 28} className="fill-fd-foreground" fontSize={15} fontWeight={600}>
        {title}
      </text>
      {subtitle && (
        <text x={x + 16} y={y + 48} className="fill-fd-muted-foreground" fontSize={12}>
          {subtitle}
        </text>
      )}
      {chip && (
        <g>
          <rect
            x={x + w - 92}
            y={y + h - 26}
            width={80}
            height={18}
            rx={9}
            className="fill-fd-secondary stroke-fd-border"
            strokeWidth={1}
          />
          <text x={x + w - 52} y={y + h - 13} textAnchor="middle" className="fill-fd-muted-foreground" fontSize={10}>
            {chip}
          </text>
        </g>
      )}
    </g>
  );
}

function Arrow({ d, label, lx, ly, dashed, anchor = 'middle' }: {
  d: string;
  label?: string;
  lx?: number;
  ly?: number;
  dashed?: boolean;
  anchor?: 'start' | 'middle' | 'end';
}) {
  return (
    <g>
      <path
        d={d}
        fill="none"
        className="stroke-fd-muted-foreground"
        strokeWidth={1.4}
        strokeDasharray={dashed ? '5 5' : undefined}
        markerEnd="url(#arrow)"
      />
      {label && lx !== undefined && ly !== undefined && (
        <text x={lx} y={ly} textAnchor={anchor} className="fill-fd-muted-foreground" fontSize={11}>
          {label}
        </text>
      )}
    </g>
  );
}

function Frame({ viewBox, title, children }: { viewBox: string; title: string; children: ReactNode }) {
  return (
    <figure className="not-prose my-6 overflow-x-auto rounded-xl border bg-fd-background p-4">
      <svg viewBox={viewBox} role="img" aria-label={title} className="h-auto w-full min-w-[560px] font-sans">
        <title>{title}</title>
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" className="fill-fd-muted-foreground" />
          </marker>
        </defs>
        {children}
      </svg>
    </figure>
  );
}

/** Authority, provider, consumer, their wallets, the backend and the consumer application. */
export function Architecture() {
  return (
    <Frame viewBox="0 0 760 440" title="EUNOMIA architecture: an authority, a provider and a consumer">
      <Box x={270} y={16} w={220} h={86} title="Authority" subtitle="Heimdall · issues credentials" chip="Fafnir wallet" accent />
      <Box x={30} y={186} w={240} h={86} title="Provider" subtitle="DS-Agent · catalog, contracts" chip="Fafnir wallet" />
      <Box x={490} y={186} w={240} h={86} title="Consumer" subtitle="DS-Agent · negotiates, transfers" chip="Fafnir wallet" />
      <Box x={30} y={354} w={240} h={70} title="Data backend" subtitle="the demo factory, or yours" />
      <Box x={490} y={354} w={240} h={70} title="Consumer application" subtitle="your code, e2e, demo events" />

      <Arrow d="M 320 102 C 260 136 190 156 160 182" label="credentials · OID4VCI" lx={200} ly={140} anchor="end" />
      <Arrow d="M 440 102 C 500 136 570 156 600 182" label="credentials · OID4VCI / OID4VP" lx={560} ly={140} anchor="start" />
      <Arrow d="M 274 214 L 486 214" label="GNAP grant · DSP catalog" lx={380} ly={206} />
      <Arrow d="M 486 240 L 274 240" label="contract · ODRL" lx={380} ly={258} />
      <Arrow d="M 274 262 C 380 300 380 300 486 262" label="data plane: pull, push" lx={380} ly={312} dashed />
      <Arrow d="M 150 276 L 150 350" label="OAuth2 · provider-held token" lx={160} ly={318} anchor="start" />
      <Arrow d="M 610 276 L 610 350" label="data, events" lx={620} ly={318} anchor="start" />
    </Frame>
  );
}

/** The four onboarding steps. */
export function Onboarding() {
  const steps = [
    { n: '1', t: 'Wallets', s: 'POST /wallet/link', d: 'keys and DID in Fafnir' },
    { n: '2', t: 'Register', s: 'DataSpaceParticipant', d: 'from the authority' },
    { n: '3', t: 'Gaia-X', s: 'gx:VatId · gx:Label', d: 'legal and label VCs' },
    { n: '4', t: 'Connect', s: 'GNAP grant', d: 'token for the provider' },
  ];
  return (
    <Frame viewBox="0 0 760 150" title="Onboarding: wallets, register, Gaia-X, connect">
      {steps.map((st, i) => {
        const x = 16 + i * 186;
        return (
          <g key={st.n}>
            <rect x={x} y={20} width={168} height={108} rx={12} className="fill-fd-card stroke-fd-border" strokeWidth={1} />
            <circle cx={x + 26} cy={48} r={13} className="fill-fd-accent stroke-fd-primary" strokeWidth={1.2} />
            <text x={x + 26} y={52} textAnchor="middle" className="fill-fd-foreground" fontSize={12} fontWeight={700}>
              {st.n}
            </text>
            <text x={x + 48} y={53} className="fill-fd-foreground" fontSize={15} fontWeight={600}>
              {st.t}
            </text>
            <text x={x + 16} y={88} className="fill-fd-foreground font-mono" fontSize={11}>
              {st.s}
            </text>
            <text x={x + 16} y={110} className="fill-fd-muted-foreground" fontSize={11}>
              {st.d}
            </text>
            {i < steps.length - 1 && <Arrow d={`M ${x + 170} 74 L ${x + 184} 74`} />}
          </g>
        );
      })}
    </Frame>
  );
}

/** Pull and push transfers through the provider's data plane. */
export function Transfers() {
  return (
    <Frame viewBox="0 0 760 300" title="Pull and push transfers through the data plane">
      <text x={16} y={30} className="fill-fd-foreground" fontSize={13} fontWeight={700}>
        PULL
      </text>
      <Box x={16} y={44} w={170} h={60} title="Consumer app" subtitle="GET the proxy URL" />
      <Box x={296} y={44} w={170} h={60} title="Provider" subtitle="data plane proxy" accent />
      <Box x={574} y={44} w={170} h={60} title="Backend" subtitle="GET /robots/" />
      <Arrow d="M 190 66 L 292 66" label="request" lx={241} ly={58} />
      <Arrow d="M 470 66 L 570 66" label="+ OAuth2 token" lx={520} ly={58} />
      <Arrow d="M 570 88 L 470 88" />
      <Arrow d="M 292 88 L 190 88" label="the robots" lx={241} ly={102} />

      <text x={16} y={170} className="fill-fd-foreground" fontSize={13} fontWeight={700}>
        PUSH
      </text>
      <Box x={16} y={184} w={170} h={60} title="Backend" subtitle="POSTs every event" />
      <Box x={210} y={184} w={150} h={60} title="Provider" subtitle="ingress" accent />
      <Box x={384} y={184} w={150} h={60} title="Consumer" subtitle="forwards" />
      <Box x={558} y={184} w={186} h={60} title="Your endpoint" subtitle="dataAddress.endpoint" />
      <Arrow d="M 190 214 L 206 214" />
      <Arrow d="M 364 214 L 380 214" />
      <Arrow d="M 538 214 L 554 214" />
      <text x={380} y={272} textAnchor="middle" className="fill-fd-muted-foreground" fontSize={11}>
        On start the provider subscribes to the backend; on completion it unsubscribes.
      </text>
    </Frame>
  );
}
