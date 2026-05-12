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
- **Immutable HTTP models** — `Request`, `Response`, `Headers`, `MediaType`, `Protocol`
  are frozen `dataclass`es; non-destructive mutation via `dataclasses.replace` and
  `with_*` helpers
- **Pipeline architecture** — `PipelineStep[T, V]` as a `Protocol`, composable into
  request / response chains
- **Context promotion chain** `DispatchContext` → `RequestContext` → `ExchangeContext`,
  each carrying an `InstrumentationContext` for tracing correlation
- **Thread-safe registries** — `Io` and `ContextStore` are safe for concurrent use
- **`Protocol`-first SPI** — `HttpClient`, `Serde`, `Serializer`, `Deserializer` are
  structural; any callable / object with the right shape qualifies

## Project Structure

```
python-sdk/
  src/
    dexpace/sdk/core/        Single package — all SDK core code
      io/                    I/O contracts + default adapter
      http/                  Request, Response, Headers, MediaType, Protocol, contexts
      pipeline/              PipelineStep + step config
      client/                HttpClient Protocol
      serde/                 Serde, Serializer, Deserializer
      instrumentation/       InstrumentationContext, Span, TracingScope (noops included)
  pyproject.toml
```

### Subpackages (`dexpace.sdk.core`)

| Package                                                                     | Description                                                                   |
|-----------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`io`](src/dexpace/sdk/core/io)                                             | `Source`, `Sink`, `BufferedSource`, `BufferedSink`, `Buffer`, `IoProvider`, `Io`, `TeeSink`, `DefaultIoProvider` |
| [`http.request`](src/dexpace/sdk/core/http/request)                         | Immutable `Request`, `RequestBody`, `Method`                                  |
| [`http.response`](src/dexpace/sdk/core/http/response)                       | Immutable `Response`, `ResponseBody`, `Status`                                |
| [`http.common`](src/dexpace/sdk/core/http/common)                           | `Headers`, `MediaType`, `Protocol`, `common_media_types`                      |
| [`http.context`](src/dexpace/sdk/core/http/context)                         | `CallContext`, `DispatchContext`, `RequestContext`, `ExchangeContext`, `ContextStore` |
| [`pipeline`](src/dexpace/sdk/core/pipeline)                                 | `PipelineStep`, `RequestPipelineStep`, `ResponsePipelineStep`, `StepMetadata`, `RetryConfig` |
| [`client`](src/dexpace/sdk/core/client)                                     | `HttpClient` Protocol                                                         |
| [`serde`](src/dexpace/sdk/core/serde)                                       | `Serde`, `Serializer`, `Deserializer` Protocols                               |
| [`instrumentation`](src/dexpace/sdk/core/instrumentation)                   | `InstrumentationContext`, `Span`, `Tracer`, `TracingScope`, noop singletons   |

## Quick Start

### Install the I/O provider

A provider must be installed once before any I/O call:

```python
from dexpace.sdk.core.io import Io
from dexpace.sdk.core.io.default import DefaultIoProvider

Io.install_provider(DefaultIoProvider())
```

### Building a request

Models are frozen dataclasses — construct directly and mutate via `with_*` helpers
or `dataclasses.replace`:

```python
from dexpace.sdk.core.http.common import Headers, common_media_types
from dexpace.sdk.core.http.request import Method, Request, RequestBody

request = Request(
    method=Method.POST,
    url="https://api.example.com/v1/resource",
    headers=Headers({"Content-Type": "application/json"}),
    body=RequestBody.from_string(
        '{"key": "value"}',
        media_type=common_media_types.APPLICATION_JSON,
    ),
)

# Non-destructive updates return a new Request:
retried = request.with_added_header("X-Retry-Count", "1")
```

### Consuming a response

`Response` and `ResponseBody` are context managers — use `with` to release the
transport handle deterministically:

```python
with http_client.execute(request) as response:
    if response.is_success:
        text = response.body.string()         # decodes per media-type charset
        # … or `.bytes()` for raw bytes, or `.source()` for streaming reads
```

### Using the I/O layer

```python
from dexpace.sdk.core.io import Io

buffer = Io.provider.buffer()
buffer.write_utf8("Hello, world!")
text = buffer.read_utf8()            # "Hello, world!"
```

### Writing a pipeline step

`PipelineStep[T_in, T_out]` is a `Protocol` — any callable with the matching shape
qualifies, including plain functions and lambdas:

```python
from dexpace.sdk.core.http.context import DispatchContext
from dexpace.sdk.core.http.request import Request
from dexpace.sdk.core.pipeline import PipelineStep

def add_user_agent(request: Request, context: DispatchContext) -> Request:
    return request.with_header("User-Agent", "my-app/1.0")

step: PipelineStep[Request, Request] = add_user_agent
```

## Architecture

The SDK is an **HTTP-client toolkit, not an HTTP client**. It provides abstractions,
models, and pipelines; consuming libraries plug in a concrete transport via the
`HttpClient` Protocol and a concrete I/O implementation via the `IoProvider` ABC.

Layered, bottom-up:

1. **`io/` contracts** — `Source` / `Sink` (primitive byte channels), `BufferedSource` /
   `BufferedSink` (typed reads/writes: byte strings, UTF-8 strings, lines, peek,
   `BinaryIO` bridges), `Buffer` (both source and sink + `snapshot()` for body
   logging). `IoProvider` is the single factory seam; `Io.install_provider(provider)`
   wires it once at startup. `DefaultIoProvider` ships a working in-memory implementation.
2. **`http.request` / `http.response` / `http.common`** — immutable frozen-dataclass
   models. Non-destructive mutation via `dataclasses.replace` or the `with_*` helpers.
   `RequestBody` exposes `is_replayable()` and `to_replayable(provider)`; classmethod
   factories (`from_bytes`, `from_string`, `from_form`, `from_buffer`, `from_source`)
   cover the common shapes.
3. **`http.context`** — promotion chain `DispatchContext` → `RequestContext` →
   `ExchangeContext`, all carrying an `InstrumentationContext` for tracing
   correlation, registered in the thread-safe `ContextStore` by trace id.
4. **`pipeline/`** — `PipelineStep[T_in, T_out]` Protocol is the building block;
   `RetryableStep` adds a retry hook. `StepMetadata` and `RetryConfig` provide
   optional configuration objects.
5. **`client/HttpClient`** — single-method Protocol (`execute(request) -> Response`).
   Transport is **not** provided by `core`.

## Conventions

- **Python 3.8 compatible.** No `match`, no `|` runtime unions, no `Self`, no
  `TypeAlias`. `from __future__ import annotations` everywhere.
- **Immutable data, no builders.** Models are `@dataclass(frozen=True)`; mutate via
  `dataclasses.replace` or the `with_*` helpers. Builders are a Java idiom — Python's
  keyword/default arguments make them redundant.
- **Thread-safety where stated.** `Io` and `ContextStore` are safe under concurrent
  calls; individual buffers / sources / sinks are not.
- **`Protocol` for SPIs, `ABC` for shared behaviour.** `HttpClient`, `Serde`, and
  `PipelineStep` are structural Protocols. `Source`, `Sink`, `Buffer`, `Span` are
  ABCs because they ship default methods (e.g. context-manager support).
- **No runtime dependencies.** Add nothing to `pyproject.toml` beyond stdlib.

## Tech Stack

| Component   | Version       |
|-------------|---------------|
| Python      | 3.8+          |
| Dependencies| None (stdlib) |
