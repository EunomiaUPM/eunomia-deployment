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
  title: 'EUNOMIA: open-source data spaces',
  tagline: 'A secure data space.',
  description:
    'EUNOMIA drives a secure data economy in Europe, supporting Gaia-X ISBL and DSBA. We develop open-source solutions and open standards for secure and trusted data sharing.',
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
  group: 'GING, Next Generation Internet Group · Department of Telematic Engineering (DIT), Universidad Politécnica de Madrid',
  funding:
    'Funded by INCIBE through the call “Solutions for sovereignty, trust and security in data spaces” (ETD202300196), co-financed by the European Union Recovery and Resilience Facility.',
};

export const components = [
  {
    name: 'DS-Agent',
    repo: 'https://github.com/EunomiaUPM/ds-agent',
    docs: '/docs/components/ds-agent',
    role: 'Dataspace agent',
    summary:
      'Provider and consumer in one Rust binary: DCAT 3 catalog, ODRL contract negotiation and transfers over the Dataspace Protocol, plus the data plane that moves the bytes.',
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

export const team = [
  { name: 'Joaquín Salvachúa', role: 'Principal Investigator' },
  { name: 'Pedro Reviriego', role: 'Professor' },
  { name: 'Gabriel Huecas', role: 'Professor' },
  { name: 'Santiago Pavón', role: 'Professor' },
  { name: 'Enrique Barra', role: 'Associate Professor' },
  { name: 'Álvaro Alonso', role: 'Associate Professor' },
  { name: 'Aldo Gordillo', role: 'Associate Professor' },
  { name: 'Jose Andrés Muñoz', role: 'Assistant Professor' },
  { name: 'Alejandro Pozo', role: 'Assistant Professor' },
  { name: 'Javier Conde', role: 'Assistant Professor' },
  { name: 'Carlos Aparicio', role: 'PhD candidate' },
  { name: 'Carlos Arriaga', role: 'PhD candidate' },
  { name: 'Rodrigo Menéndez', role: 'Intern' },
  { name: 'Irene Plaza', role: 'Intern' },
];
