# Demo factory

The data backend the demo provider shares: a factory with robots (pull), their yearly measures, and the events the robots emit (push), behind a Keycloak. A Go service with its own Postgres.

`./eunomia up` starts it; `./eunomia up demo --build` rebuilds it after a change.

The guide is [The demo factory](https://eunomiaupm.github.io/eunomia-deployment/docs/components/demo-factory). The API is in [specs/openapi/robots.yaml](specs/openapi/robots.yaml) and at <http://127.0.0.1:1210/docs> once it runs.
