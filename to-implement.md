# Python SDK — Implementation Plan

Snapshot of work remaining after the initial scaffolding (commits up to
`9601f3f`). Organised into milestones; items within a milestone are roughly
independent and can be parallelised.

The shipping surface today is **contracts + a default in-memory I/O provider**.
What's listed below is what turns it from "scaffolding" into "SDK you'd actually
build a client library on top of".

---

## Open design questions

Resolve these before starting M3 onward — they shape multiple files.

| Question | Default position |
|----------|------------------|
| **Sync vs async API surface.** Two parallel hierarchies (`Source` / `AsyncSource`) or one unified hierarchy that returns `Awaitable` for async transports? | **Two parallel hierarchies.** Mirrors `httpx.Client` / `httpx.AsyncClient`. Lets the sync path stay allocation-cheap and the async path stay non-blocking. The in-memory `Buffer` can be shared (in-memory ops never suspend). |
| **Lint / format toolchain.** ruff-only, or ruff + black? | **ruff + ruff format**, no black. Single tool, fewer config files. Pin ruff in `[project.optional-dependencies].dev`. |
| **Type-checking strictness.** `mypy --strict` from day one? | Yes. The contract surface is small enough to keep strict-clean. Looser settings invite drift. |
| **Minimum Python.** Stay on 3.8, or bump to 3.9? | **Stay on 3.8 through M3**, re-evaluate after async lands. 3.8 EOL was 2024-10; 3.9 is still supported. The cost of staying is mostly cosmetic (`Dict[...]` vs `dict[...]`). |
| **Test framework.** pytest, or stdlib `unittest`? | **pytest.** Lower-friction fixtures + parametrisation; widely understood. `unittest`-style assertions still work inside pytest tests. |

---

## M1 — Foundation hardening

Lock the existing surface in with tests, CI, and the small body shapes that
the Java SDK ships but the Python SDK omits.

- [ ] **pytest test suite** covering every contract under `tests/`:
  - `tests/io/` — `DefaultBuffer` round-trips (write_bytes → read_bytes,
    write_utf8 → read_utf8, peek non-consuming, slice, copy_to range checks,
    read_utf8_line CRLF/LF/no-terminator), `Io.install_provider` conflict /
    idempotent paths, `Io.with_provider` restoration.
  - `tests/http/` — `Headers` case-insensitive lookup, multi-value semantics,
    `with_added` / `with_set` / `without` / `with_merged` immutability;
    `MediaType.parse` (incl. `boundary=abc=def`), `MediaType.includes`
    wildcards, charset accessor; `Method` / `Status` / `Protocol` round-trip.
  - `tests/context/` — promotion chain registers in `ContextStore`,
    `close()` evicts, `ContextStore.put` rejects duplicate trace ids.
  - `tests/pipeline/` — `PipelineStep` runtime `isinstance` check against a
    plain callable, `RetryConfig` defaults.
- [ ] **GitHub Actions CI** — `ci.yml` matrix of Python 3.8 / 3.9 / 3.10 / 3.11
      / 3.12 / 3.13 running `ruff check`, `ruff format --check`, `mypy --strict`,
      `pytest --cov`. Coverage gate at 90% for `src/dexpace/sdk/core/`.
- [ ] **`pyproject.toml` dev extras** — add `[project.optional-dependencies].dev`
      with `pytest`, `pytest-cov`, `ruff`, `mypy`. Add `[tool.ruff]`,
      `[tool.mypy]`, `[tool.pytest.ini_options]` sections.
- [ ] **`LoggableRequestBody`** in `http/request/loggable_request_body.py` —
      wraps a `RequestBody`, uses the existing `TeeSink` to mirror bytes into
      an internal `Buffer` during `write_to`, exposes `snapshot()` for log
      preview. Mirrors `java-sdk`'s `LoggableRequestBody.kt`.
- [ ] **`LoggableResponseBody`** in `http/response/loggable_response_body.py` —
      wraps a `ResponseBody`, eagerly drains the underlying source into an
      internal `Buffer` on first access, returns `peek()`-backed sources for
      repeatable reads. Both `LoggableRequestBody` and `LoggableResponseBody`
      use `Buffer.MAX_BYTE_ARRAY_SIZE` as the cap before raising.
- [ ] **`FileRequestBody`** in `http/request/file_request_body.py` — replayable
      body backed by a `pathlib.Path`. Transports can `isinstance`-check this
      to dispatch zero-copy `os.sendfile(2)` via `socket.sendfile`. Add
      `RequestBody.from_file(path, media_type=None, offset=0, count=-1)` factory.
- [ ] **`HttpHeaderName` typed constants** in `http/common/http_header_name.py`
      — frozen-dataclass wrapper carrying `(value, canonical_name)`; ships
      ~50 IANA-registered names (Content-Type, Authorization, ETag, Set-Cookie,
      …). `Headers.get` / `Headers.with_added` / `Headers.with_set` accept both
      `str` and `HttpHeaderName`. Saves the `.lower().strip()` step on the hot
      path.
- [ ] **URL helpers** in `http/common/url.py` — `Url(scheme, host, port, path,
      query, fragment)` frozen dataclass with `parse(str)` and `__str__`;
      `QueryParams` immutable multi-dict mirroring the `Headers` shape.
      Pulls the `urllib.parse` interop into one place rather than scattering
      `urlsplit`/`urlencode` across consuming code.
- [ ] **`http.common.etag.ETag`** — frozen dataclass with `weak: bool` flag and
      `parse` / `__str__`. Used by If-Match / If-None-Match request conditions.
- [ ] **`http.common.http_range.HttpRange`** — frozen dataclass for byte-range
      headers (`Range`, `Content-Range`).
- [ ] **`http.common.request_conditions.RequestConditions`** — bundle of
      If-Match / If-None-Match / If-Modified-Since / If-Unmodified-Since, with
      a `.apply_to(request) -> Request` helper that fans out into headers.

**Definition of done**: every existing public symbol has at least one test;
CI green on the matrix; `mypy --strict` clean.

---

## M2 — Composition & resilience

The `PipelineStep` Protocol exists but there is no engine yet that runs a
chain. This milestone adds the executor, retry orchestration, and the
diagnostic plumbing (logger + redactor) that hangs off it.

- [ ] **`RequestPipeline`** class in `pipeline/request_pipeline.py` — holds an
      ordered tuple of `PipelineStep[Request, Request]` and exposes
      `apply(request, context) -> Request`. Steps run in declaration order; a
      step that returns `None` aborts the chain with `PipelineAbortedError`.
- [ ] **`ResponsePipeline`** class — same shape for `Response` → `Response`.
- [ ] **`ExecutionPipeline`** class — composes a `RequestPipeline`, an
      `HttpClient`, and a `ResponsePipeline` into a single
      `execute(request) -> Response` callable. This is the public entry point
      most consumers will use.
- [ ] **Retry executor** in `pipeline/retry.py` — drives a `RetryableStep`
      against a `RetryConfig`. Computes per-attempt delay (`initial_backoff_ms`,
      `multiplier`, `max_backoff_ms`), respects `retry_on` allow-list, threads
      `ExchangeContext` for attempt counting. Sync via `time.sleep`; an async
      twin lands in M3.
- [ ] **`ClientLogger`** in `instrumentation/client_logger.py` — thin facade
      over stdlib `logging` that emits structured key=value pairs and respects
      the SDK's `LogLevel`. One logger per consuming module; trace-id is
      pulled from the active `CallContext` and added as a structured field.
- [ ] **`UrlRedactor`** in `instrumentation/url_redactor.py` — strips userinfo
      and configurable query-param values from a URL string for safe log
      emission. Default allow-list mirrors `java-sdk`'s. Returns a `str`, not
      a `Url`, so callers can format directly.
- [ ] **Default JSON `Serde`** in `serde/json_serde.py` — concrete
      implementation of the `Serde` / `Serializer` / `Deserializer` Protocols
      backed by stdlib `json`. Ships an `int`-key option, ISO-8601 datetime
      encoder, and pluggable `default` / `object_hook`. Module-level
      `JSON_SERDE` singleton for the common case.
- [ ] **`PipelineAbortedError`** in `pipeline/__init__.py` — typed exception
      raised when a step short-circuits a chain.

**Definition of done**: an `ExecutionPipeline` composed of a logging step, a
retry-wrapping step, and a stub transport completes a happy-path request in
a test; retries fire on the configured exception types.

---

## M3 — Reference transport & async stack

The contracts are transport-agnostic — until something implements `HttpClient`,
nothing actually talks HTTP. This milestone ships a no-deps sync transport, the
full async hierarchy, and an async transport so the public API is usable from
both worlds.

- [ ] **`UrllibHttpClient`** in `client/urllib_http_client.py` — synchronous
      reference transport over `urllib.request`. Honours `RequestBody.write_to`
      (via a custom `Request.data` handler that pipes through a `BufferedSink`),
      surfaces response status / headers / body as a `BufferedSource`. Not for
      production traffic — it's the test / example transport.
- [ ] **`AsyncSource` / `AsyncSink`** in `io/async_source.py` /
      `io/async_sink.py` — `async def read(...)`, `async def write(...)`,
      `async def close()`. Implement `__aenter__` / `__aexit__`.
- [ ] **`AsyncBufferedSource`** / **`AsyncBufferedSink`** — typed-read /
      typed-write surfaces with `async def read_bytes`, `async def read_utf8`,
      `async def write_bytes`, `async def write_all` etc.
- [ ] **`AsyncBuffer`** — same in-memory contract as `Buffer`; can extend
      `Buffer` directly since in-memory ops never suspend (the async wrappers
      just `return` immediately). Decide whether to expose this directly or
      hide it behind the AsyncIoProvider.
- [ ] **`AsyncIoProvider`** in `io/async_io_provider.py` — async twin of
      `IoProvider`; factory methods return the async-surface types.
- [ ] **`AsyncIo`** registry — `asyncio.Lock`-guarded twin of `Io`.
- [ ] **`AsyncHttpClient`** Protocol in `client/async_http_client.py` —
      `async def execute(request) -> Response`.
- [ ] **`AsyncResponseBody`** — `async def bytes()`, `async def string()`,
      `async def source() -> AsyncBufferedSource`. Implements `__aenter__` /
      `__aexit__`.
- [ ] **`AsyncioHttpClient`** in `client/asyncio_http_client.py` — async
      reference transport built on `asyncio.open_connection` (raw sockets, no
      third-party deps). Production-quality async transports should still
      come from adapters — this is the reference.
- [ ] **`AsyncRetryExecutor`** — async twin of the M2 retry executor, using
      `asyncio.sleep`.

**Definition of done**: sync and async test transports both round-trip a
request against a `socketserver`-based fixture; async test suite runs cleanly
under `pytest-asyncio`.

---

## M4 — Auth & advanced HTTP

- [ ] **Credential types** in `http/auth/`:
  - `KeyCredential(value: str)` — frozen, redacts under `repr`.
  - `BearerTokenCredential(token: str)`.
  - `BasicAuthCredential(username: str, password: str)`.
  - `TokenCredential` Protocol — `get_token(scopes: Sequence[str]) -> AccessToken`
    for OAuth2-style flows; sync and async variants.
- [ ] **`AccessToken`** frozen dataclass — `token: str`, `expires_at: datetime`,
      `is_expired(now=...) -> bool`.
- [ ] **`KeyCredentialPipelineStep`** / **`BearerTokenPipelineStep`** /
      **`BasicAuthPipelineStep`** — concrete `RequestPipelineStep`s that read
      a credential and stamp the right header onto the outgoing request.
- [ ] **Token cache** in `http/auth/token_cache.py` — pluggable cache (in-mem
      default, swap-out for Redis / file-backed) keyed by `(scopes, audience)`.
- [ ] **`http.common.pagination`** — `Page[T]` / `Pager[T]` iterators (sync)
      and `AsyncPage[T]` / `AsyncPager[T]` (async). Drive page advancement via
      a caller-supplied `next_link` extractor.

---

## M5 — Streaming & ergonomics

- [ ] **`http.sse.SseEvent`** frozen dataclass + `SseParser` over a
      `BufferedSource`. Handles `data:` / `event:` / `id:` / `retry:` fields
      and multi-line `data` reassembly per the WHATWG SSE spec. Async twin
      reads from `AsyncBufferedSource`.
- [ ] **Streaming JSON deserialization** helper — drains a `BufferedSource` in
      chunks into the default JSON `Serde`. Useful for newline-delimited JSON
      (`application/jsonl`) and SSE payloads.
- [ ] **Multipart form-data builder** — `RequestBody.from_multipart(parts)`
      factory producing a replayable `multipart/form-data` body with a
      generated boundary.
- [ ] **Chunked transfer-encoding writer** — `BufferedSink` decorator that
      wraps each `write_bytes` in HTTP/1.1 chunk framing.

---

## M6 — Observability integrations

These are *optional* extras; the core stays no-deps.

- [ ] **`dexpace-sdk-otel`** sibling package — implements `Tracer` / `Span` /
      `TracingScope` over OpenTelemetry's Python API. Provides an
      `OpenTelemetryTracer.install()` shortcut.
- [ ] **Metrics interface** in `instrumentation/metrics/` — `Counter` /
      `Histogram` / `Gauge` ABCs plus a `MetricsContext` factory analogous to
      `InstrumentationContext`. Ship noop singletons; real implementations in
      `dexpace-sdk-otel`.
- [ ] **Built-in `LoggingPipelineStep`** — `RequestPipelineStep` that emits a
      structured log line per request using `ClientLogger` + `UrlRedactor`.
- [ ] **Built-in `TracingPipelineStep`** — `RequestPipelineStep` that opens a
      span around the downstream chain via the installed `Tracer`.

---

## M7 — Documentation

- [ ] `docs/architecture.md` — high-level design, package map, data flow.
- [ ] `docs/io.md` — `Source` / `Sink` / `Buffer` contracts, the `IoProvider`
      seam, the `DefaultIoProvider`'s bytearray-backed implementation, async
      twins.
- [ ] `docs/http.md` — request/response models, headers, media types, context
      promotion chain, `HttpClient` Protocol.
- [ ] `docs/pipelines.md` — pipeline composition, retry semantics, the step
      Protocols, common built-in steps.
- [ ] `docs/body-logging.md` — `LoggableRequestBody` / `LoggableResponseBody`
      mechanics, snapshot caps, concurrency model.
- [ ] `docs/auth.md` — credential types, token caching, integration with
      pipelines.
- [ ] Sphinx-generated API reference under `docs/api/` (autodoc + intersphinx
      to stdlib). Optional; only worth it once the surface stabilises.

---

## Cross-cutting items (do alongside any milestone)

- [ ] **`__all__` audits** — every `__init__.py` and every public module
      already declares `__all__`; keep it accurate as new symbols land.
- [ ] **`py.typed` marker** — `src/dexpace/sdk/core/py.typed` (PEP 561) so
      downstream type-checkers consume our annotations.
- [ ] **Versioning policy** — pre-1.0 follows zerover: `0.MINOR.PATCH`, breaking
      changes only on minor bumps. Document in `CONTRIBUTING.md` once the
      project takes external contributors.

---

## Known carry-overs from the initial scaffolding

Items that landed in the first commits but want a second pass.

- [ ] **`TeeSink.output_stream`** — currently returns a duck-typed object that
      isn't actually a `BinaryIO` subclass; the `# type: ignore[return-value]`
      hides it. Wrap properly in an `io.RawIOBase` mirror like the other
      stream adapters in `io/default.py`.
- [ ] **`DefaultBuffer.read_utf8_line`** edge case — when the line is exactly
      `\r` with no following `\n`, the `\r` is returned in the result. Match
      the documented "consume CRLF or LF terminator" semantics by stripping
      a lone trailing `\r` only when followed by `\n`.
- [ ] **`Headers.__repr__`** — currently shows the raw tuple-of-tuples;
      `Headers({{Content-Type: [application/json]}})` would be friendlier.
- [ ] **`Status.from_code`** — Java's SDK exposes a `fromCodeOrNull` /
      `fromCode` pair. Python `IntEnum(code)` already does the first;
      consider an explicit classmethod for symmetry with the Java SDK so
      docs and examples stay parallel.

---

## How to pick this up in a new session

1. Read this file end-to-end, then `CLAUDE.md`, then `README.md`.
2. Pick a milestone — start at the top of M1 unless told otherwise.
3. Skim the `dexpace/java-sdk` counterpart for the item you're working on if
   one exists; use it for shape, not for syntax. Python idioms (dataclasses
   over builders, Protocols over interfaces with adapter modules, context
   managers over `Closeable`+`close`) take precedence.
4. Land tests in the same PR as the code; CI must stay green.
5. Update this file as items move from `[ ]` to `[x]` and add follow-ups you
   discover at the bottom of the relevant milestone.
