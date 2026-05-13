# Java SDK → Python SDK Mapping Report

The Java SDK (`/Users/omar/IdeaProjects/dexpace/java-sdk`) has moved substantially
ahead since the Python port forked from it. This report catalogs what's new on
the Java side and recommends what should map back into the Python SDK.

## What landed in the Java SDK after the Python fork

| Theme | What's new |
|---|---|
| **Pipeline organization** | `Stage` enum + `StagedSteps` + pillar enforcement + surgical edits (`insertAfter<T>`, `replace<T>`, `remove<T>`) on the builder |
| **New built-in steps** | `RedirectStep` / `DefaultRedirectStep` (3xx loop with credential stripping), `SetDateStep`, `InstrumentationStep` consolidated as a pillar |
| **Auth** | `DigestChallengeHandler` (MD5 / SHA-256, RFC 7616), `BasicChallengeHandler`, `CompositeChallengeHandler`, RFC 7235 challenge parser, sealed `Credential` hierarchy |
| **Utilities** | `Clock` abstraction (sleep + monotonic + now), `Configuration` (layered env + sysprop + override), `ProxyOptions`, `DateTimeRfc1123`, `Uuids` |
| **Module split** | 6 modules: `sdk-core`, `sdk-io-okio3`, plus four async adapter modules (coroutines, reactor, netty, virtualthreads) |
| **Coverage** | 97%+ line coverage via Kover; ~1,400 tests |

---

## Recommendations — sorted by ROI

### 🟢 High value, straightforward port

#### 1. `RedirectStep` / `RedirectPolicy` — biggest gap

Python has no redirect handling at all. This is a real production feature:
301/302/303/307/308 follow with `Location` resolution, credential stripping
(security-critical — server-supplied redirect targets must not receive caller
credentials), loop detection, max-hops cap, and the 307/308 + non-replayable
body invariant.

- Belongs as a new `RedirectPolicy` in `pipeline/policies/`.
- Sketch: ~150 lines + tests.
- Direct port — Python's `urllib.parse.urljoin` handles `Location` resolution,
  and the `Url` type already exists.
- Surface: `RedirectPolicy(max_hops=10, follow_303=True, strip_authorization=True)`.

#### 2. `Clock` abstraction

Python uses `time.monotonic()` and `time.sleep()` directly in
`RetryPolicy._sleep_bounded` and `AccessTokenInfo.needs_refresh` — which makes
timing-dependent tests rely on real sleeps or `monkeypatch`. A `Clock` protocol
with `now() / monotonic() / sleep()` lets tests use a `FakeClock` that advances
time deterministically.

Wins:
- Retry-policy tests stop calling `sleep=lambda _: None`
- Token-expiry tests get a real clock to advance
- ~30 lines + a small fake in `tests/conftest.py`

Sketch:

```python
class Clock(Protocol):
    def now(self) -> float: ...        # wall clock (seconds since epoch)
    def monotonic(self) -> float: ...  # monotonic for elapsed measurement
    def sleep(self, duration: float) -> None: ...

class _SystemClock:
    def now(self) -> float: return time.time()
    def monotonic(self) -> float: return time.monotonic()
    def sleep(self, duration: float) -> None: time.sleep(duration)

SYSTEM_CLOCK: Clock = _SystemClock()
```

Async variant: `AsyncClock` with `async def sleep(self, duration: float) -> None`.

#### 3. `Configuration` (layered env + override)

Python has nothing here. Right now policies/clients hardcode reading config
(the bearer policy doesn't even consult env vars). A `Configuration` class with
`.get_int / .get_bool / .get_duration` and a normalizer (env
`MAX_RETRY_ATTEMPTS` ↔ overrides-dict equivalent — Python doesn't have
sysprops) means `RetryPolicy.from_config()`, `ProxyOptions.from_config()`, etc.

- Defers to defaults on parse failure (never throws at lookup site).
- ~80 lines.
- Surface mirrors Java's: explicit override → env var → default.

#### 4. `DigestChallengeHandler`

Currently the Python SDK has `BasicAuthPolicy` and `BearerTokenPolicy` but no
Digest. RFC 7616 (MD5 / MD5-sess / SHA-256 / SHA-256-sess, `qop=auth`) is
mechanical to port.

- ~120 lines + the challenge parser and `AuthenticateChallenge` data class.
- Skip `auth-int` and mutual-auth, same as Java.
- Standard library has everything needed: `hashlib`, `secrets.token_hex` for cnonce.

#### 5. `ProxyOptions` + env-var parsing

Python has no proxy support. Java's `ProxyOptions` carries:
- Glob patterns (compiled once at construction)
- Userinfo masking in `__repr__` / `__str__`
- A `from_configuration` factory reading `HTTPS_PROXY` / `HTTP_PROXY` /
  `NO_PROXY` env vars

Direct port — only the actual proxy use (CONNECT tunneling in the transport)
is hard, but `ProxyOptions` as a value type with `bypasses_proxy(host)` is
easy and lets future transports consume it.

#### 6. `SetDatePolicy`

A 50-line policy that stamps `Date: <RFC 1123>` after retry. Useful for
AWS/Azure-style request signing where the date is part of the signature and
must be re-stamped per attempt. Python has `email.utils.format_datetime` for
RFC 5322 dates (close enough to RFC 1123 to use directly).

Goes inside the retry loop (after retry, before auth) so each attempt gets a
fresh stamp.

---

### 🟡 Worth considering — architectural shifts

#### 7. `Stage` enum + pillar pipeline organization

This is the biggest design shift in the Java SDK. Instead of "pipeline is a
list of policies in user-specified order," each policy declares a `Stage`
(REDIRECT, RETRY, PRE_AUTH, AUTH, LOGGING, etc.), and the builder sorts them.
Pillar stages allow exactly one step (one retry, one auth, one redirect);
non-pillar stages stack.

**Pros:**
- Users can't accidentally put retry before redirect or auth after logging — the
  stage ordering is correctness, not convention.
- Surgical edits (`replace<T>`, `insertBefore<T>`) make adapting a pre-built
  pipeline trivial.
- Pillar replacement emits a warning, catching footguns.

**Cons / Python-specific concerns:**
- Python's current `Pipeline(client, policies=[...])` is dead simple; Stage
  adds machinery.
- The "first one wins" / "last one wins" semantic for pillars in Java relies on
  Kotlin's `reified T : HttpStep`. Python's runtime `isinstance` works fine
  for `replace_first(StepType, new_step)` but doesn't get the same
  compile-time guarantees.
- The pillar invariant means library authors have to declare a Stage on every
  Policy; some natural composites (e.g., a single "default" policy that
  handles retry+logging together) become awkward.

**Recommendation:** Worth it if you expect users to compose non-trivial
pipelines or pass pipelines around for modification. If most users just build
once and run, the cost outweighs the benefit.

#### 8. Module split (`sdk-core` + adapter modules)

Java's 6-module layout is driven by Java's distinct concurrency primitives
(CompletableFuture, coroutines, Reactor, Netty Future, virtual threads).
Python has *one* async story: `asyncio`. So there's no analog of
`sdk-async-reactor` or `sdk-async-netty`.

The Java split that maps cleanly:
- `dexpace-sdk-core` (current) — abstractions, models, pipeline
- `dexpace-sdk-http-httpx` — `HttpClient` adapter on `httpx` (currently we ship
  `UrllibHttpClient` + `AsyncioHttpClient` inside core)
- `dexpace-sdk-http-aiohttp` — async adapter on `aiohttp`

This is purely a **packaging** question (do we ship one wheel or three?). Most
consumers will want one install + extras:

```
pip install dexpace-sdk-core[httpx]
```

via `pyproject.toml` optional-dependencies.

**Recommendation:** keep one wheel; expose `httpx` / `aiohttp` adapters as
extras rather than separate distributions until there's actual demand.

---

### 🟠 Skip / not applicable

#### 9. `IoProvider` / Okio pluggability

Java's pluggable I/O is for `Source` / `Sink` / `Buffer` because Java's stdlib
I/O is poor. Python's `bytes` / `BinaryIO` / `BytesIO` is the native contract —
CLAUDE.md explicitly says "Don't reintroduce an Okio-style layer." No-op.

#### 10. Async adapter modules (`sdk-async-coroutines`, etc.)

Python has one async story. No-op.

#### 11. `Builder<T>` generic builder interface

Python uses keyword args + dataclasses; builders are noise. No-op (and we
already dropped `Builder[T]` per commit `9601f3f`).

#### 12. Embedded Jackson / Aalto XML / OTel adapters in legacy compat tree

These are Java-ecosystem-specific. No-op.

---

## Suggested ordering if you want to act on this

1. **Clock + Configuration** (one PR, ~150 LOC + tests) — these are
   infrastructure for the next two.
2. **RedirectPolicy** — biggest user-visible gap.
3. **DigestChallengeHandler + challenge parser** — completes the auth pillar.
4. **ProxyOptions** (value type only, no transport plumbing) — preps for
   proxy-aware transports later.
5. **SetDatePolicy** — small, easy win.
6. *(Defer)* Stage-based pipeline organization — only if you commit to it as
   an architectural direction; it's a bigger change that affects every
   existing test that builds a `Pipeline(client, policies=[...])`.

Total scope for items 1–5: roughly 600–800 lines of source + tests, fits in
3–4 sessions of the wave-based execution pattern.

---

## File references in the Java SDK

For anyone implementing the ports, the canonical Java sources live at:

| Feature | Java source path |
|---|---|
| Stage enum | `sdk-core/src/main/kotlin/.../http/pipeline/Stage.kt` |
| StagedSteps | `sdk-core/src/main/kotlin/.../http/pipeline/StagedSteps.kt` |
| HttpPipelineBuilder (surgical edits) | `sdk-core/src/main/kotlin/.../http/pipeline/HttpPipelineBuilder.kt` |
| DefaultRedirectStep | `sdk-core/src/main/kotlin/.../http/pipeline/steps/DefaultRedirectStep.kt` |
| SetDateStep | `sdk-core/src/main/kotlin/.../http/pipeline/steps/SetDateStep.kt` |
| DigestChallengeHandler | `sdk-core/src/main/kotlin/.../http/auth/DigestChallengeHandler.kt` |
| Clock | `sdk-core/src/main/kotlin/.../util/Clock.kt` |
| Configuration | `sdk-core/src/main/kotlin/.../config/Configuration.kt` |
| ProxyOptions | `sdk-core/src/main/kotlin/.../util/ProxyOptions.kt` |
| PagedIterable | `sdk-core/src/main/kotlin/.../http/paging/PagedIterable.kt` |
