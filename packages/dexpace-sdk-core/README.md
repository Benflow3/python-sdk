# dexpace-sdk-core

Zero-dependency Python toolkit for building HTTP client libraries.

`dexpace-sdk-core` ships abstractions, models, the request/response pipeline,
authentication primitives, observability hooks, and serde Protocols — but
**not transports**. Pair with a transport package
(`dexpace-sdk-http-stdlib`, `dexpace-sdk-http-httpx`, etc.) or roll your own
`HttpClient` adapter.

See the workspace root README for installation and quickstart.
