# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository

The Python counterpart to [`dexpace/java-sdk`](https://github.com/dexpace/java-sdk).
Mirrors the java-sdk's architecture (pluggable I/O, immutable HTTP models, pipeline
steps, context promotion chain) in idiomatic Python.

## Conventions (enforced — match these when adding code)

- **Python 3.8 bytecode/syntax.** No `match` (3.10+), no `X | Y` annotations in runtime
  contexts, no `Self` (3.11+), no `TypeAlias` (3.10+), no PEP 695 syntax. Use
  `from __future__ import annotations` at the top of every module so forward refs and
  PEP 604 unions in annotations work without runtime cost.
- **No runtime dependencies.** `core` ships against the standard library only. If you
  reach for a third-party package, stop — model it as an adapter behind `IoProvider` /
  `HttpClient` / `Serde`.
- **Immutable data + builder.** Models use `@dataclass(frozen=True)` with a nested
  `Builder` class that implements `Builder[T]`. The data class private-constructor
  contract is enforced by convention (do not call the constructor directly — use
  `Model.builder()` or `instance.new_builder()`).
- **Thread-safety where stated.** `Io` and `ContextStore` are safe under concurrent
  use; individual buffers / sources / sinks are not. `Io.install_provider` uses a
  `threading.Lock`; per-context lookups use `ConcurrentMap`-equivalent stdlib
  primitives (`dict` + `threading.Lock` for the few mutation paths).
- **Public API is narrow.** Helpers and concrete adapter classes are kept module-private
  (leading underscore). The public surface for each subpackage is the set of names
  re-exported from its `__init__.py`.
- **No logging package dependency.** Use `logging` from the stdlib when needed; do not
  add `loguru` or similar.
- **Commit style:** `chore:` for refactors/cleanup; `feat:` for new features; `fix:`
  for bug fixes.

## Repository Layout

```
python-sdk/
├── LICENSE.md
├── README.md
├── pyproject.toml
└── src/dexpace/sdk/core/
    ├── generics.py              # Builder[T] Protocol
    ├── io/                      # Source/Sink/BufferedSource/BufferedSink/Buffer/IoProvider/Io
    │   ├── source.py, sink.py
    │   ├── buffered_source.py, buffered_sink.py
    │   ├── buffer.py, io_provider.py, io.py
    │   ├── tee_sink.py          # mirror-write helper for body logging
    │   └── default.py           # DefaultIoProvider — bytearray + BinaryIO
    ├── http/
    │   ├── common/              # Headers, MediaType, CommonMediaTypes, Protocol
    │   ├── request/             # Request, RequestBody, Method
    │   ├── response/            # Response, ResponseBody, Status
    │   └── context/             # CallContext, DispatchContext, RequestContext, ExchangeContext, ContextStore
    ├── pipeline/
    │   └── step/                # PipelineStep, RequestPipelineStep, ResponsePipelineStep, traits
    ├── client/                  # HttpClient Protocol
    ├── serde/                   # Serde, Serializer, Deserializer
    ├── instrumentation/         # InstrumentationContext, Span, TracingScope, noops
    └── util/                    # annotations and tiny helpers
```

## Architecture — Big Picture

The SDK is an **HTTP-client toolkit, not an HTTP client**. It provides abstractions,
models, and pipelines; consuming libraries plug in a concrete transport via the
`HttpClient` Protocol and a concrete I/O implementation via the `IoProvider` ABC.

Layered, bottom-up:

1. **`io/` contracts** — `Source` / `Sink` (primitive byte channels), `BufferedSource` /
   `BufferedSink` (typed reads/writes), `Buffer` (both + `snapshot()` for body logging).
   `IoProvider` is the single factory seam; `Io.install_provider(provider)` wires it
   once. Missing provider throws `RuntimeError` with the install instruction.
2. **`http.request` / `http.response` / `http.common`** — immutable models built with
   builders implementing `Builder[T]`. `RequestBody` exposes `is_replayable()` and
   `to_replayable(provider)`; built-in factories cover bytes, strings, in-memory
   `Buffer`s, `BufferedSource`s, and form-encoded payloads.
3. **`http.context`** — promotion chain `DispatchContext` → `RequestContext` →
   `ExchangeContext`, all carrying an `InstrumentationContext` for tracing
   correlation. The thread-safe `ContextStore` is keyed by trace id.
4. **`pipeline/step/PipelineStep`** — a callable `(input, context) -> output`. Steps
   compose into chains; traits (`PipelineStepMetadataTrait`, `PipelineStepRetryConfigTrait`)
   layer optional configuration onto a step without coupling unrelated callers.
5. **`client/HttpClient`** — single-method Protocol (`execute(request) -> Response`).
   Transport is **not** provided by `core`.

## Things That Will Bite You

- `Io.install_provider(...)` must run before any code that calls `Io.provider`. Tests
  that touch buffers should install `DefaultIoProvider` in their setup.
- The HTTP request/response models are frozen dataclasses — mutate via
  `instance.new_builder().<set>().build()`, not by reassigning fields.
- The default `Buffer` is in-memory only and unbounded. Don't drain a multi-GB
  response body into a single buffer; stream via `BufferedSource.input_stream()`.
- `ResponseBody` is single-use — wrap with a logging body if you need repeatable reads.
