# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository

The Python counterpart to [`dexpace/java-sdk`](https://github.com/dexpace/java-sdk).
The architecture follows the same shape (immutable HTTP models, pipeline steps,
context promotion chain) but the public API uses Python idioms — dataclasses
instead of builder objects, Protocols instead of interfaces with implementation
modules, context managers instead of explicit close pairs. The pluggable I/O
seam that exists in the Java SDK was removed in this port: Python's `bytes` /
`bytearray` / `memoryview` / `BinaryIO` cover the same surface natively, so
bodies are modelled as typed Pythonic abstractions instead.

## Conventions (enforced — match these when adding code)

- **Python 3.12+.** Modern union syntax (`X | None`), built-in generics
  (`list[X]`, `dict[X, Y]`, `tuple[X, ...]`), `Self` for fluent returns, PEP
  695 type parameters (`def f[T](x: T) -> T`) and `type` statement aliases
  where they fit. `from __future__ import annotations` at the top of every
  module so forward refs evaluate lazily.
- **`mypy --strict` clean.** Every public signature is typed; no `Any` in
  public API; no unused `# type: ignore` comments.
- **`ruff` and `ruff format` clean** (rule set in `pyproject.toml`).
- **No runtime dependencies.** `core` ships against the standard library only.
  If you reach for a third-party package, stop — model it as an adapter
  behind `HttpClient` or `Serde`.
- **Immutable data with slots.** Models are
  `@dataclass(frozen=True, slots=True)`; mutate via `dataclasses.replace` or
  the `with_*` helpers. Builders are a Java idiom — Python's keyword and
  default arguments make them redundant noise.
- **Protocol for SPIs, ABC for shared behaviour.** Structural duck-typed
  seams (`HttpClient`, `Serde`, `PipelineStep`) are `typing.Protocol`. Types
  that ship default methods (`RequestBody`, `ResponseBody`, `Span`,
  `CallContext`) are `abc.ABC`.
- **Context managers for resources.** `Response`, `ResponseBody`,
  `CallContext`, and `TracingScope` all implement `__enter__` / `__exit__`
  so callers can `with …:` and rely on deterministic cleanup.
- **Bodies are Pythonic.** `RequestBody` produces bytes via
  `iter_bytes(chunk_size)`; factories cover `from_bytes` / `from_string` /
  `from_form` / `from_stream` / `from_iter` / `from_file`. `ResponseBody`
  exposes `iter_bytes` / `bytes` / `string`. Single-use bodies (stream /
  iter) raise `RuntimeError` on second consumption — call `to_replayable()`
  before the first send if retries are needed.
- **Body capture for logging uses `BytesIO`.** `LoggableRequestBody` mirrors
  writes into a `BytesIO` tap; `LoggableResponseBody` caches drained bytes
  for repeatable reads. Both honour a configurable byte cap.
- **Thread-safety where stated.** `ContextStore` is safe under concurrent
  use; individual bodies and streams are not. Per-context lookups rely on
  CPython's GIL for atomic dict ops and use a lock only for check-and-set.
- **Public API is narrow.** Helpers and concrete adapter classes are
  module-private (leading underscore). The public surface for each subpackage
  is what its `__init__.py` re-exports.
- **`__all__` declares the surface** on every module that exports anything;
  keep it accurate as new symbols land.
- **`py.typed`** ships with the package (PEP 561) so downstream type-checkers
  consume our annotations.
- **No logging package dependency.** Use stdlib `logging` when needed; do
  not add `loguru` or similar.
- **Google-style docstrings.** One-line summary, blank line, then details
  with `Args:` / `Returns:` / `Raises:` / `Yields:` sections. Plain backticks
  for code/type references — no Sphinx `:class:` / `:meth:` cross-references.
- **Function-size cap: 50 lines.** Aim 10–25. Refactor when you push past.
- **Commit style:** `chore:` for refactors/cleanup; `feat:` for new features;
  `fix:` for bug fixes; `docs:` for documentation-only changes.

## Repository Layout

The repo is a `uv`-managed workspace. Each member under `packages/` is its own
distribution; PEP 420 namespace packages let them share the `dexpace.sdk.*`
prefix. Commands run from the workspace root via `uv run …` — `uv sync`
provisions the virtualenv with both packages installed in editable mode.

```
python-sdk/
├── LICENSE.md
├── README.md
├── CLAUDE.md
├── pyproject.toml                          # workspace root (uv workspace, dev deps,
│                                           # ruff/mypy/pytest config)
├── uv.lock
├── .github/workflows/ci.yml                # pytest + mypy + ruff on 3.12 and 3.13
├── docs/                                   # cross-package documentation
└── packages/
    ├── dexpace-sdk-core/                   # zero-dependency toolkit (no transports)
    │   ├── pyproject.toml
    │   ├── README.md
    │   ├── src/dexpace/sdk/core/
    │   │   ├── http/
    │   │   │   ├── common/                 # Headers, HttpHeaderName, MediaType,
    │   │   │   │                           # Protocol, Url, QueryParams, ETag,
    │   │   │   │                           # HttpRange, RequestConditions,
    │   │   │   │                           # common_media_types
    │   │   │   ├── request/                # Request, RequestBody, FileRequestBody,
    │   │   │   │                           # LoggableRequestBody, Method
    │   │   │   ├── response/               # Response, ResponseBody,
    │   │   │   │                           # LoggableResponseBody, Status
    │   │   │   ├── context/                # CallContext, DispatchContext,
    │   │   │   │                           # RequestContext, ExchangeContext,
    │   │   │   │                           # ContextStore
    │   │   │   └── auth/                   # Credential, BearerTokenPolicy,
    │   │   │                               # BasicAuthPolicy, KeyCredentialPolicy
    │   │   ├── pipeline/                   # Pipeline, Policy ABC, RetryPolicy,
    │   │   │                               # LoggingPolicy, TracingPolicy, async twins
    │   │   ├── client/                     # HttpClient + AsyncHttpClient Protocols
    │   │   ├── serde/                      # Serde, Serializer, Deserializer Protocols
    │   │   ├── errors/                     # SDK-level exception hierarchy
    │   │   └── instrumentation/            # InstrumentationContext, Span, Tracer,
    │   │                                   # TracingScope, noops
    │   └── tests/                          # pytest suite — http/, context/,
    │                                       # pipeline/, auth/, serde/, sse/, errors/,
    │                                       # instrumentation/
    └── dexpace-sdk-http-stdlib/            # reference stdlib transports
        ├── pyproject.toml                  # depends on dexpace-sdk-core
        ├── README.md
        ├── src/dexpace/sdk/http/stdlib/
        │   ├── urllib_http_client.py       # UrllibHttpClient (sync, blocking)
        │   └── asyncio_http_client.py      # AsyncioHttpClient (async, stdlib only)
        └── tests/
```

Planned follow-up packages (not yet present): `dexpace-sdk-http-httpx`,
`dexpace-sdk-http-aiohttp`, `dexpace-sdk-http-requests`. Each will live under
`packages/` as a separate distribution, depend on `dexpace-sdk-core`, and
adapt its third-party HTTP library to the `HttpClient` / `AsyncHttpClient`
Protocols. Namespace packaging (no `__init__.py` at `src/dexpace/`,
`src/dexpace/sdk/`, or `src/dexpace/sdk/http/`) is mandatory for every
package so the `dexpace.sdk` prefix stays shared.

### Common commands (run from the workspace root)

```bash
uv sync                          # install workspace + dev tools
uv run pytest -q                 # walk both packages' test suites
uv run mypy --strict             # type-check everything in `files = [...]`
uv run ruff check                # lint
uv run ruff format --check       # formatting gate
```

## Architecture — Big Picture

The SDK is an **HTTP-client toolkit, not an HTTP client**. It provides
abstractions, models, and pipelines; consuming libraries plug in a concrete
transport via the `HttpClient` Protocol.

Layered, bottom-up:

1. **Bodies (`http.request.RequestBody` / `http.response.ResponseBody`)** —
   typed abstractions for outgoing/incoming payloads. `iter_bytes(chunk_size)`
   is the primary streaming surface; `bytes()` / `string()` for full reads.
   Bytes- and file-backed variants are replayable; stream- and iter-backed
   variants are single-use. `Loggable*` decorators wrap either side for
   diagnostic capture with a configurable cap.
2. **`http.request` / `http.response` / `http.common`** — immutable
   `@dataclass(frozen=True, slots=True)` models. Non-destructive mutation
   via `dataclasses.replace` or the `with_*` helpers. The HTTP value layer
   includes `Headers`, `HttpHeaderName` (typed constants for IANA names),
   `MediaType`, `Url` / `QueryParams`, `ETag`, `HttpRange`,
   `RequestConditions`.
3. **`http.context`** — promotion chain `DispatchContext` → `RequestContext`
   → `ExchangeContext`, all carrying an `InstrumentationContext` for tracing
   correlation. The thread-safe `ContextStore` is keyed by trace id; entries
   evict on `CallContext.close()`.
4. **`pipeline/step/PipelineStep`** — a Protocol with signature
   `(input, context) -> output`. Steps compose into chains; the provisional
   `RetryableStep` adds a retry hook (M2 replaces it with a `Policy` ABC
   that wraps the downstream chain — see `to-implement.md`). `StepMetadata`
   and `RetryConfig` provide optional configuration.
5. **`client/HttpClient`** — single-method Protocol
   (`execute(request) -> Response`). Transport is **not** provided by `core`.

## Things That Will Bite You

- The HTTP request/response models are frozen — mutate via
  `dataclasses.replace` or the `with_*` helpers, not by reassigning fields.
  Trying to assign raises `dataclasses.FrozenInstanceError`.
- `RequestBody.from_stream` and `from_iter` are **single-use**. The second
  `iter_bytes` call raises `RuntimeError`. Call `to_replayable()` before the
  first send if you need retries.
- `ResponseBody.bytes()` / `.string()` consume and close the body. Wrap with
  `LoggableResponseBody` if repeatable reads are needed.
- `LoggableRequestBody.snapshot()` / `LoggableResponseBody.snapshot()` are
  capped at `max_capture_bytes` (default = CPython's effective `bytes`
  ceiling, ~2 GiB). The primary write path still receives the full payload;
  only the tap is truncated.
- `Headers` is case-insensitive but stores names in lower-case canonical
  form. Lookups (`get`, `__contains__`) compare names case-insensitively;
  iteration yields the lower-cased name. Pass `HttpHeaderName` instances
  directly to skip the `.lower()` step on the hot path.
- The Java SDK's `Io`/`IoProvider` seam intentionally does NOT exist here.
  Python's stdlib (`bytes`, `bytearray`, `memoryview`, `BytesIO`,
  `BinaryIO`) is the contract. Don't reintroduce an Okio-style layer.
- `mypy` is invoked as `uv run mypy --strict` from the workspace root (config
  in the root `pyproject.toml`). `python_version = "3.12"` because mypy 2.x
  requires it; the source still runs on whatever interpreter ≥ 3.12. Don't
  lower the floor.
