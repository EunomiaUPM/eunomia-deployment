/**
 * Facts about the project, in one place, for the landing page, the layout and
 * the metadata.
 */

/** Set when the site is served from a sub-path, e.g. GitHub Pages: /eunomia-deployment */
export const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? '';

/** A file under public/, with the base path in front. */
export function asset(path: string): string {
  return `${basePath}${path}`;
}

export const site = {
  name: 'EUNOMIA',
  title: 'EUNOMIA Deployment: run a data space',
  tagline: 'A secure data space.',
  description:
    'How to deploy and operate EUNOMIA data spaces: authorities and agents on one machine or one per server, and extensions for the data they share.',
  url: process.env.NEXT_PUBLIC_SITE_URL ?? 'https://eunomiaupm.github.io/eunomia-deployment',
  website: 'https://eunomia.dit.upm.es',
  github: 'https://github.com/EunomiaUPM',
  repo: 'https://github.com/EunomiaUPM/eunomia-deployment',
  codespaces: 'https://codespaces.new/EunomiaUPM/eunomia-deployment',
  license: 'GPL-3.0',
  contact: 'gi.internetng@upm.es',
  address: [
    'E.T.S. de Ingenieros de Telecomunicación, Building B',
    'Av. Complutense, 30',
    '28040 Madrid, Spain',
  ],
};

export const components = [
  {
    name: 'DS-Agent',
    repo: 'https://github.com/EunomiaUPM/ds-agent',
    docs: '/docs/components/ds-agent',
    role: 'Dataspace agent',
    summary:
      'What every participant runs, all alike: a DCAT 3 catalog to publish, ODRL contract negotiation and transfers with any other agent over the Dataspace Protocol, and the data plane that moves the bytes.',
  },
  {
    name: 'Heimdall',
    repo: 'https://github.com/EunomiaUPM/heimdall',
    docs: '/docs/components/heimdall',
    role: 'Authority',
    summary:
      'Onboards participants and issues their verifiable credentials over OID4VCI, verifies presentations over OID4VP and guards access with GNAP. Gaia-X legal and label credentials included.',
  },
  {
    name: 'Fafnir',
    repo: 'https://github.com/EunomiaUPM/fafnir-wallet',
    docs: '/docs/components/fafnir',
    role: 'Wallet',
    summary:
      'A sidecar SSI wallet next to every node: keys, DIDs and credentials, JWT signing and the holder side of OID4VCI and OID4VP. Pure Rust crypto, no external wallet service.',
  },
  {
    name: 'Ymir',
    repo: 'https://github.com/EunomiaUPM/ymir',
    docs: '/docs/components/ymir',
    role: 'Shared core',
    summary:
      'The crate every node is built on: the GNAP and SSI type system, the wallet abstraction, DID resolution, HTTP message signatures and the data model.',
  },
];

export const standards = [
  'Dataspace Protocol 2025-1',
  'DCAT 3',
  'ODRL',
  'GNAP',
  'OID4VCI',
  'OID4VP',
  'W3C Verifiable Credentials',
  'did:jwk',
  'did:web',
  'Gaia-X',
  'HTTP Message Signatures',
  'Rust',
  'PostgreSQL',
  'Docker',
];
