import { createOpenAPI } from 'fumadocs-openapi/server';

/**
 * The specs the API reference is generated from, by document id. They live
 * next to the services they describe, outside this site.
 */
export const openapiInputs = {
  agent: '../static/specs/agent/openapi/merged_openapi.json',
  authority: '../static/specs/heimdall/openapi/openapi.json',
  'demo-factory': '../extensions/demo/service/specs/openapi/robots.yaml',
};

export const openapi = createOpenAPI({
  input: openapiInputs,
});
