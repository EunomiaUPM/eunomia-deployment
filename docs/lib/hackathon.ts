/**
 * The live event: its details, its programme and the banner on the home page.
 *
 * This file, components/hackathon/ and app/(home)/hackathon/ are the only
 * places the event appears. The documentation never mentions it, so the
 * event can be removed (set `banner: false`, delete those three) without
 * touching anything else.
 */

export const hackathon = {
  /** Show the banner on the home page. */
  banner: true,
  name: 'Build a Data Space in 1 Hour',
  kicker: 'Live hackathon',
  /** Friday 30 October 2026, 16:00 CET (Europe/Madrid, after the switch from summer time). */
  start: '2026-10-30T16:00:00+01:00',
  durationMinutes: 90,
  dateLabel: 'Friday 30 October 2026 · 16:00 CET',
  format: '100% online, hands-on and free',
  /** Registration link; while null the page says registration opens soon. */
  registrationUrl: null as string | null,
  /** Where participants ask for help during the event; null hides it. */
  supportUrl: null as string | null,
};

export type Milestone = {
  number: string;
  window: string;
  title: string;
  subtitle: string;
  steps: string[];
  commands: string[];
  result: string;
};

export const milestones: Milestone[] = [
  {
    number: '01',
    window: '00 – 15',
    title: 'Zero-friction ignition',
    subtitle: 'From a clean laptop to your own authority and agent.',
    steps: [
      'Clone the repository, or open it in GitHub Codespaces and skip the install entirely.',
      'Check the machine, start an authority and your first agent: it gets its wallet, its DID and its credentials on the way up.',
    ],
    commands: ['./eunomia doctor', './eunomia authority add authority', './eunomia agent add alice'],
    result: 'An authority and an agent, healthy, with verifiable credentials in its wallet.',
  },
  {
    number: '02',
    window: '15 – 30',
    title: 'Identity and discovery',
    subtitle: 'A second agent, trust between them, a catalog.',
    steps: [
      'Add a second agent: same software, its own identity, its own Gaia-X legal and label credentials.',
      'Start the demo factory and let alice publish it. bob connects to her over GNAP and reads her DCAT catalog over the Dataspace Protocol.',
    ],
    commands: ['./eunomia agent add bob', './eunomia demo up', './eunomia catalog populate alice', './eunomia e2e --consumer bob --provider alice --list-datasets'],
    result: 'alice’s catalog in your terminal, fetched by an agent she now trusts.',
  },
  {
    number: '03',
    window: '30 – 45',
    title: 'ODRL negotiation',
    subtitle: 'Contracts the machines agree on.',
    steps: [
      'Open the ODRL policies the catalog offers (static/catalog/05 and 06), change a constraint and publish again.',
      'Run the eight-step Dataspace Protocol negotiation between bob and alice and watch every state change.',
    ],
    commands: ['./eunomia catalog populate alice --force', './eunomia e2e --consumer bob --provider alice -v'],
    result: 'A FINALIZED agreement between the two agents, with its id.',
  },
  {
    number: '04',
    window: '45 – 60',
    title: 'Live data, both ways',
    subtitle: 'Pull the fleet. Stream the robots. Swap roles.',
    steps: [
      'Pull every robot through alice’s data plane: she adds the factory token, bob never sees it. Then stream the robot events live.',
      'Publish the factory in bob too and run it the other way round: every agent provides and consumes.',
    ],
    commands: ['./eunomia demo events --consumer bob --provider alice', './eunomia catalog populate bob', './eunomia e2e --consumer alice --provider bob'],
    result: 'Real data flowing between two sovereign agents, in both directions, in under an hour.',
  },
];

export const agenda = [
  { time: '00 – 10', title: 'The manifesto', body: 'What EUNOMIA is, why it exists and what you are about to build. Three slides, then terminals.' },
  { time: '10 – 70', title: 'The 60-minute clock', body: 'A countdown on screen and four milestones of fifteen minutes. We build live; you follow on your machine.' },
  { time: '70 – 90', title: 'Victory and community', body: 'Show what you built, tell us what broke, see the roadmap, and become a contributor.' },
];

export const rules = [
  {
    title: 'The train never stops',
    body: 'Microphones stay muted while the clock runs. The pace is set on stage; questions go to the chat, where a co-pilot answers them.',
  },
  {
    title: 'The emergency lane',
    body: 'Docker misbehaving, a corporate VPN in the way, no WSL2? Open the repository in GitHub Codespaces and be back on track in under a minute.',
  },
  {
    title: 'Checkpoints in the chat',
    body: 'Finish a milestone, post its number in the chat. Watching the 1s, 2s and 3s pile up is half the fun.',
  },
];

export const needs = [
  'A laptop with Docker Desktop (Windows, macOS) or Docker Engine (Linux), running',
  'Or just a browser and a GitHub account, for Codespaces',
  'About 4 GB of free memory for Docker',
  'No Python, no Java, no build toolchain',
];

export const challenges = [
  {
    level: 'Warm-up',
    items: [
      { title: 'Fleet dashboard', body: 'An app that pulls the robots through the data space and charts OEE, defect rate and energy per robot and year.' },
      { title: 'Live alerts', body: 'A service on your own push endpoint that raises an alarm when robot_temperature or robot_vibration cross a threshold.' },
    ],
  },
  {
    level: 'Level up',
    items: [
      { title: 'Predictive maintenance', body: 'Combine the yearly MTBF, maintenance and downtime figures with the live events to guess which robot fails next.' },
      { title: 'Many factories', body: 'Start several agents with eunomia agent add, publish the factory in each and build an app that compares the fleets.' },
      { title: 'Custom policies', body: 'Write new ODRL policies for an agent’s catalog (research only, expiring, purpose-bound) and see which offers the negotiation accepts.' },
    ],
  },
  {
    level: 'Ambitious',
    items: [
      { title: 'Your own backend', body: 'Publish data of your own from your agent, with its connectors and its catalog entry.' },
      { title: 'Your own authority', body: 'Start a second authority with eunomia authority add and run a data space with your own admission rules.' },
      { title: 'A team marketplace', body: 'One agent per team, all on one authority: every team publishes something and consumes from the others.' },
      { title: 'A negotiation UI', body: 'Walk a user through catalog, offer, contract and transfer, showing the Dataspace Protocol state at every step.' },
    ],
  },
];

export const faq = [
  {
    q: 'Do I need to know what a data space is?',
    a: 'No. The first ten minutes cover it, and the milestones teach the rest by doing: identity, catalog, contract, data.',
  },
  {
    q: 'What do I need to install?',
    a: 'Docker. The command-line tool runs in a container when there is no Python on the machine. With Codespaces, not even Docker.',
  },
  {
    q: 'Is it really one hour?',
    a: 'The four milestones are timed at fifteen minutes each, and the first one includes downloading the images. Run ./eunomia doctor before the event and the clock is on your side.',
  },
  {
    q: 'Can I keep going afterwards?',
    a: 'Everything you run is open source under GPL-3.0 and stays on your machine. The documentation covers the next steps: more agents, your own data, production.',
  },
];
