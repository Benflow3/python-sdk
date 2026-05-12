# Dexpace Python SDK

> [!CAUTION]
> **PROPRIETARY & CONFIDENTIAL SOFTWARE**
>
> **NO RIGHTS ARE GRANTED.**
>
> Any use, copying, modification, or distribution without
> explicit written consent from **Omar Aljarrah / dexpace**
> constitutes copyright infringement.

A zero-dependency, production-grade SDK core for building and maintaining Python HTTP
client libraries. Pure standard library, targeting **Python 3.8+**, with a pluggable
I/O seam, immutable HTTP models, and a composable pipeline architecture — the Python
counterpart to [`dexpace/java-sdk`](https://github.com/dexpace/java-sdk).

## Highlights

- **Zero runtime dependencies** — standard library only
- **Pluggable I/O** via `IoProvider` — contracts ship in `core`; a default in-memory
  adapter built on `bytearray` and `BinaryIO` ships out of the box (`DefaultIoProvider`)
- **Immutable HTTP models** with fluent builders (`Request`, `Response`, `Headers`,
  `MediaType`, `Protocol`)
- **Pipeline architecture** for composable request/response processing
- **Context promotion chain** `DispatchContext` → `RequestContext` → `ExchangeContext`,
  each carrying an `InstrumentationContext` for tracing correlation
- **Thread-safe registries** — `Io` and `ContextStore` are safe for concurrent use
- **PEP 8 / type-annotated** — `from __future__ import annotations` everywhere,
  `typing` only for static checkers

## Project Structure

```
python-sdk/
  src/
    dexpace/sdk/core/        Single package — all SDK core code
      io/                    I/O contracts + default adapter
      http/                  Request, Response, Headers, MediaType, Protocol, contexts
      pipeline/              PipelineStep, traits
      client/                HttpClient transport SPI
      serde/                 Serde, Serializer, Deserializer
      instrumentation/       InstrumentationContext, Span, TracingScope (noops included)
      generics.py            Builder protocol
      util/                  Annotations and tiny helpers
  pyproject.toml
```

### Subpackages (`dexpace.sdk.core`)

| Package                                                                     | Description                                                                   |
|-----------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`io`](src/dexpace/sdk/core/io)                                             | `Source`, `Sink`, `BufferedSource`, `BufferedSink`, `Buffer`, `IoProvider`, `Io`, `TeeSink`, `DefaultIoProvider` |
| [`http.request`](src/dexpace/sdk/core/http/request)                         | Immutable `Request`, `RequestBody`, `Method`                                  |
| [`http.response`](src/dexpace/sdk/core/http/response)                       | Immutable `Response`, `ResponseBody`, `Status`                                |
| [`http.common`](src/dexpace/sdk/core/http/common)                           | `Headers`, `MediaType`, `Protocol`, `CommonMediaTypes`                        |
| [`http.context`](src/dexpace/sdk/core/http/context)                         | `CallContext`, `DispatchContext`, `RequestContext`, `ExchangeContext`, `ContextStore` |
| [`pipeline`](src/dexpace/sdk/core/pipeline)                                 | `PipelineStep`, `RequestPipelineStep`, `ResponsePipelineStep`, step traits    |
| [`client`](src/dexpace/sdk/core/client)                                     | `HttpClient` Protocol                                                         |
| [`serde`](src/dexpace/sdk/core/serde)                                       | `Serde`, `Serializer`, `Deserializer`                                         |
| [`instrumentation`](src/dexpace/sdk/core/instrumentation)                   | `InstrumentationContext`, `Span`, `TracingScope`, noops                       |
| [`generics`](src/dexpace/sdk/core/generics.py)                              | `Builder[T]` protocol                                                         |

## Quick Start

### Install the I/O provider

A provider must be installed once before any I/O call:

```python
from dexpace.sdk.core.io import Io
from dexpace.sdk.core.io.default import DefaultIoProvider

Io.install_provider(DefaultIoProvider())
```

### Making a request

```python
from dexpace.sdk.core.http.request import Method, Request, RequestBody
from dexpace.sdk.core.http.common import CommonMediaTypes

request = (
    Request.builder()
        .url("https://api.example.com/v1/resource")
        .method(Method.POST)
        .add_header("Content-Type", "application/json")
        .body(RequestBody.from_string('{"key": "value"}', CommonMediaTypes.APPLICATION_JSON))
        .build()
)

with http_client.execute(request) as response:
    if response.status.is_success:
        body = response.body.bytes()  # consumes the body
```

### Using the I/O layer

```python
from dexpace.sdk.core.io import Io

buffer = Io.provider.buffer()
buffer.write_utf8("Hello, world!")
text = buffer.read_utf8()           # "Hello, world!"
```

## Architecture

The SDK is an **HTTP-client toolkit, not an HTTP client**. It provides abstractions,
models, and pipelines; consuming libraries plug in a concrete transport via the
`HttpClient` Protocol and a concrete I/O implementation via the `IoProvider` ABC.

Layered, bottom-up:

1. **`io/` contracts** — `Source` / `Sink` (primitive byte channels), `BufferedSource` /
   `BufferedSink` (typed reads/writes: byte strings, UTF-8 strings, lines, peek, BinaryIO
   bridges), `Buffer` (both source and sink + `snapshot()` for body logging). All
   interfaces; `core` ships exactly one default implementation (`DefaultIoProvider`)
   built on `bytearray` and `BinaryIO`. `IoProvider` is the single factory seam;
   `Io.install_provider(provider)` wires it once at startup and `Io.provider` resolves
   it everywhere.
2. **`http.request` / `http.response` / `http.common`** — immutable models built with
   private constructors + `Builder` + `new_builder()`. `RequestBody` exposes
   `is_replayable()` and `to_replayable(provider)`; factories cover bytes, strings,
   in-memory `Buffer`s, `BufferedSource`s, and form-encoded payloads.
3. **`http.context`** — context promotion chain: `DispatchContext` → `RequestContext`
   → `ExchangeContext`, all carrying an `InstrumentationContext` for tracing
   correlation, registered in the thread-safe `ContextStore` by trace id.
4. **`pipeline/`** — composable request/response processing. `PipelineStep[T, V]` is
   the building block; `RequestPipelineStep` / `ResponsePipelineStep` are typed aliases
   for the request/response sides.
5. **`client/HttpClient`** — single-method Protocol (`execute(request) -> Response`).
   Transport is **not** provided by `core`.

## Conventions

- **Python 3.8 compatible.** No `match`, no `X | Y` annotations in runtime contexts,
  no `Self`, no `TypeAlias`. `from __future__ import annotations` everywhere.
- **Immutable data + builder.** Models use `@dataclass(frozen=True)` and expose a
  matching `Builder` class implementing `Builder[T]`.
- **Thread-safety where it matters.** `Io` and `ContextStore` are safe under
  concurrent calls; individual buffers / sources / sinks are not.
- **No runtime dependencies.** Add nothing to `pyproject.toml` beyond stdlib.

## Tech Stack

| Component   | Version       |
|-------------|---------------|
| Python      | 3.8+          |
| Dependencies| None (stdlib) |
