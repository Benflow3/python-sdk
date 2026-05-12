# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository

The Python counterpart to [`dexpace/java-sdk`](https://github.com/dexpace/java-sdk).
The architecture follows the same shape (pluggable I/O, immutable HTTP models,
pipeline steps, context promotion chain) but the public API uses Python idioms
— dataclasses instead of builder objects, Protocols instead of interfaces with
implementation modules, context managers instead of explicit close pairs.

## Conventions (enforced — match these when adding code)

- **Python 3.8 syntax.** No `match` (3.10+), no `X | Y` runtime unions, no `Self`
  (3.11+), no `TypeAlias` (3.10+), no PEP 695 syntax. Use
  `from __future__ import annotations` at the top of every module so forward refs
  and PEP 604 unions in annotations work without runtime cost.
- **No runtime dependencies.** `core` ships against the standard library only. If
  you reach for a third-party package, stop — model it as an adapter behind
  `IoProvider` / `HttpClient` / `Serde`.
- **Immutable data, no builders.** Models are `@dataclass(frozen=True)`; mutate via
  `dataclasses.replace` or the `with_*` helpers. Builders are a Java idiom —
  Python's keyword and default arguments make them redundant noise.
- **Protocol for SPIs, ABC for shared behaviour.** Structural duck-typed seams
  (`HttpClient`, `Serde`, `PipelineStep`) are `typing.Protocol`. Types that ship
  default methods (`Source`, `Sink`, `Span`, `CallContext`) are `abc.ABC`.
- **Context managers for resources.** `Source`, `Sink`, `Response`, `ResponseBody`,
  `CallContext`, and `TracingScope` all implement `__enter__` / `__exit__` so
  callers can `with ...:` and rely on deterministic cleanup.
- **Thread-safety where stated.** `Io` and `ContextStore` are safe under
  concurrent use; individual buffers / sources / sinks are not. `Io.install_provider`
  uses a `threading.Lock`; per-context lookups rely on CPython's GIL for the
  atomic dict ops and use the lock only for check-and-set sequences.
- **Public API is narrow.** Helpers and concrete adapter classes are module-private
  (leading underscore). The public surface for each subpackage is what its
  `__init__.py` re-exports.
- **No logging package dependency.** Use stdlib `logging` when needed; do not add
  `loguru` or similar.
- **Commit style:** `chore:` for refactors/cleanup; `feat:` for new features;
  `fix:` for bug fixes.

## Repository Layout

```
python-sdk/
├── LICENSE.md
├── README.md
├── pyproject.toml
└── src/dexpace/sdk/core/
    ├── generics.py              # Builder[T] Protocol (optional; not used by core models)
    ├── io/                      # Source/Sink/BufferedSource/BufferedSink/Buffer/IoProvider/Io
    │   ├── source.py, sink.py
    │   ├── buffered_source.py, buffered_sink.py
    │   ├── buffer.py, io_provider.py, io.py
    │   ├── tee_sink.py          # mirror-write helper for body logging
    │   └── default.py           # DefaultIoProvider — bytearray + BinaryIO
    ├── http/
    │   ├── common/              # Headers, MediaType, common_media_types, Protocol
    │   ├── request/             # Request, RequestBody, Method
    │   ├── response/            # Response, ResponseBody, Status
    │   └── context/             # CallContext, DispatchContext, RequestContext, ExchangeContext, ContextStore
    ├── pipeline/
    │   └── step/                # PipelineStep, RetryableStep, StepMetadata, RetryConfig
    ├── client/                  # HttpClient Protocol
    ├── serde/                   # Serde, Serializer, Deserializer Protocols
    └── instrumentation/         # InstrumentationContext, Span, Tracer, TracingScope, noops
```

## Architecture — Big Picture

The SDK is an **HTTP-client toolkit, not an HTTP client**. It provides abstractions,
models, and pipelines; consuming libraries plug in a concrete transport via the
`HttpClient` Protocol and a concrete I/O implementation via the `IoProvider` ABC.

Layered, bottom-up:

1. **`io/` contracts** — `Source` / `Sink` (primitive byte channels), `BufferedSource`
   / `BufferedSink` (typed reads/writes), `Buffer` (both + `snapshot()` for body
   logging). `IoProvider` is the single factory seam; `Io.install_provider(provider)`
   wires it once. Missing provider raises `RuntimeError` with the install
   instruction. `DefaultIoProvider` ships a working implementation backed by
   `bytearray` and `BinaryIO`.
2. **`http.request` / `http.response` / `http.common`** — immutable frozen-dataclass
   models. Non-destructive mutation via `dataclasses.replace` or `with_*` helpers.
   `RequestBody` exposes `is_replayable()` and `to_replayable(provider)`; classmethod
   factories (`from_bytes`, `from_string`, `from_form`, `from_buffer`,
   `from_source`) cover the common shapes.
3. **`http.context`** — promotion chain `DispatchContext` → `RequestContext` →
   `ExchangeContext`, all carrying an `InstrumentationContext` for tracing
   correlation. The thread-safe `ContextStore` is keyed by trace id; entries
   evict on `CallContext.close()`.
4. **`pipeline/step/PipelineStep`** — a `Protocol` with signature
   `(input, context) -> output`. Steps compose into chains; `RetryableStep` adds
   a retry hook. `StepMetadata` and `RetryConfig` provide optional configuration.
5. **`client/HttpClient`** — single-method `Protocol` (`execute(request) -> Response`).
   Transport is **not** provided by `core`.

## Things That Will Bite You

- `Io.install_provider(...)` must run before any code that calls `Io.provider`.
  Tests that touch buffers should install `DefaultIoProvider` in their setup.
- The HTTP request/response models are frozen — mutate via `dataclasses.replace`
  or the `with_*` helpers, not by reassigning fields.
- The default `Buffer` is in-memory and unbounded. Don't drain a multi-GB response
  body into a single buffer; stream via `BufferedSource.input_stream()` or read
  in chunks.
- `ResponseBody` is single-use — once `.bytes()` / `.string()` / `.source().read_*`
  consumes the underlying source, the bytes are gone. Wrap with a logging body
  if you need repeatable reads.
- `Headers` is case-insensitive but case-preserving on the wire form. Lookups
  (`get`, `__contains__`) compare names case-insensitively; iteration yields
  the lower-cased canonical form.
