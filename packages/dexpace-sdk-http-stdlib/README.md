# dexpace-sdk-http-stdlib

Reference HTTP transports for `dexpace-sdk-core`, built on the Python stdlib
(`urllib.request` and `asyncio`). Zero third-party dependencies.

Intended for tests, examples, and demonstrating the pipeline shape — production
deployments should plug in an adapter built on a real HTTP library (`httpx`,
`requests`, `aiohttp`) via the dedicated transport packages.
