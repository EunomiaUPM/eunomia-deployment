// Generate the API reference pages from the OpenAPI specs:
//   npm run generate:api
import { rm, writeFile } from 'node:fs/promises';
import { generateFiles } from 'fumadocs-openapi';
import { createOpenAPI } from 'fumadocs-openapi/server';

const out = process.argv[2] ?? './content/docs/api';

// Tag names split letter by letter by the generator, and the untagged group.
const titles = {
  'D S P Protocol': 'DSP Protocol',
  'D S P R P C': 'DSP RPC',
  'O D R L Policies': 'ODRL Policies',
  'O I D C4 V P': 'OIDC4VP',
  'R P C': 'RPC',
  'V C Requester': 'VC Requester',
  'Gate Keeper': 'Gatekeeper',
  'Well Known': 'Well-known',
  Unknown: 'Other',
};

const sections = {
  agent: { title: 'Agent', description: 'DS-Agent: the provider and consumer API.' },
  authority: { title: 'Authority', description: 'Heimdall: the authority API.' },
  'demo-factory': { title: 'Demo factory', description: 'The demo backend: robots, measures and subscriptions.' },
};

const inputs = {
  agent: '../static/specs/agent/openapi/merged_openapi.json',
  authority: '../static/specs/heimdall/openapi/openapi.json',
  'demo-factory': '../extensions/demo/service/specs/openapi/robots.yaml',
};

for (const [id, path] of Object.entries(inputs)) {
  await rm(`${out}/${id}`, { recursive: true, force: true });
  await generateFiles({
    input: createOpenAPI({ input: { [id]: path } }),
    output: `${out}/${id}`,
    per: 'tag',
    includeDescription: true,
    beforeWrite(files) {
      for (const file of files) {
        file.path = file.path.replace(/unknown\.mdx$/, 'other.mdx');
        file.content = file.content.replace(/^title: (.+)$/m, (line, title) => `title: ${titles[title] ?? title}`);
      }
    },
  });
  await writeFile(`${out}/${id}/meta.json`, JSON.stringify({ ...sections[id], pages: ['...'] }, null, 2) + '\n');
}
