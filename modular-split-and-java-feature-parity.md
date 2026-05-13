# Multi-Package Split + Java-SDK Feature Parity — Implementation Plan

## Context

This plan executes two coupled initiatives on `dexpace-sdk-core` (Python):

1. **Restructure into a multi-package workspace** so transports ship as
   separate packages — B2B clients pick transports per their dependency
   constraints (httpx vs aiohttp vs stdlib vs requests).
2. **Port high-value features that landed in the Java SDK** after the Python
   fork: redirect policy, stage-based pipeline organization, `Clock`,
   `Configuration`, `ProxyOptions`, `SetDatePolicy`, `DigestChallengeHandler`.

API-breaking changes are in scope — project is pre-1.0 (`Development Status ::
3 - Alpha`, version `0.1.0`).

Methodology mirrors the previous remediation plan
(`i-want-you-to-velvety-wigderson.md`): TDD-first per task, wave-based parallel
execution where files are disjoint, in-orchestrator runs for cross-cutting
refactors, full verification gate between waves.

## Severity Summary

| Theme | Tasks | Wave count |
|---|---|---|
| **Phase 0 — Workspace split** | 5 | 2 waves (1 solo + 1 parallel) |
| **Phase 1 — Foundation utilities** | 4 | 1 wave (parallel) |
| **Phase 2 — Stage-based pipeline** | 5 | 3 waves (2 solo + 1 parallel) |
| **Phase 3 — New policies** | 5 | 1 wave (parallel) |
| **Phase 4 — ProxyOptions** | 2 | 1 wave (parallel) |
| **Phase 5 — Optional transport packages** | 3 | 1 wave (parallel) |
| **Total** | 24 | 9 waves |

---

## Phase 0 — Workspace split

Lay the foundation: move existing code into a multi-package layout, set up the
build tooling, ensure all existing tests still pass against the new structure.

### Goals

- Two packages exist: `dexpace-sdk-core` (toolkit) and `dexpace-sdk-http-stdlib`
  (current `UrllibHttpClient` + `AsyncioHttpClient`).
- Workspace managed by `uv` (modern, fast, the direction of the Python
  ecosystem). PDM is the alternative — pick `uv` unless the user specifies
  otherwise during execution.
- PEP 420 implicit namespace packages keep `dexpace.sdk.*` shared across
  distributions.
- All 400 existing tests pass against the new layout.

### Target directory shape

```
python-sdk/
├── packages/
│   ├── dexpace-sdk-core/
│   │   ├── pyproject.toml
│   │   ├── src/dexpace/sdk/core/...      # ← all current src/dexpace/sdk/core/ minus client/
│   │   ├── tests/
│   │   └── README.md
│   └── dexpace-sdk-http-stdlib/
│       ├── pyproject.toml
│       ├── src/dexpace/sdk/http/stdlib/
│       │   ├── __init__.py               # re-exports UrllibHttpClient, AsyncioHttpClient
│       │   ├── urllib_http_client.py     # moved from sdk/core/client/
│       │   └── asyncio_http_client.py
│       ├── tests/
│       └── README.md
├── pyproject.toml                        # workspace root
├── uv.lock                               # generated
├── README.md
├── CLAUDE.md
├── docs/                                 # shared cross-package docs
└── ...
```

**Key decisions:**

- **No `__init__.py`** at `src/dexpace/`, `src/dexpace/sdk/`, or
  `src/dexpace/sdk/http/` — PEP 420 namespace packages so packages share the
  prefix without shadowing.
- **`dexpace-sdk-http-stdlib` depends on `dexpace-sdk-core>=0.1,<0.2`** — pin
  to minor while pre-1.0.
- **Version-locked extras at workspace root** for testing: workspace
  `pyproject.toml` declares `[tool.uv.sources]` pointing each package to its
  local path.
- **Single test runner:** `uv run pytest` from workspace root walks both
  packages.

### Task 0.1 — Workspace skeleton (solo, in-orchestrator)

**Files (new):**
- `pyproject.toml` (workspace root — replaces current)
- `packages/dexpace-sdk-core/pyproject.toml`
- `packages/dexpace-sdk-http-stdlib/pyproject.toml`

**Steps:**
- [ ] Read the current `pyproject.toml` to capture authors, license, classifiers,
      ruff config, mypy config — these all stay on `dexpace-sdk-core`'s
      `pyproject.toml`.
- [ ] Write the workspace-root `pyproject.toml`:
  ```toml
  [project]
  name = "dexpace-sdk-workspace"
  version = "0.0.0"  # never published
  requires-python = ">=3.12"

  [tool.uv.workspace]
  members = ["packages/*"]

  [tool.uv.sources]
  dexpace-sdk-core = { workspace = true }
  dexpace-sdk-http-stdlib = { workspace = true }
  ```
- [ ] Write `packages/dexpace-sdk-core/pyproject.toml` — carries the bulk of
      the current `pyproject.toml`:
  ```toml
  [project]
  name = "dexpace-sdk-core"
  version = "0.1.0"
  description = "Zero-dependency Python toolkit for HTTP client libraries"
  requires-python = ">=3.12"
  classifiers = [...]  # carry over from current pyproject

  [build-system]
  requires = ["hatchling"]
  build-backend = "hatchling.build"

  [tool.hatch.build.targets.wheel]
  packages = ["src/dexpace"]

  [tool.mypy]
  strict = true
  python_version = "3.12"

  [tool.ruff]
  # ... carry over current rule set
  ```
- [ ] Write `packages/dexpace-sdk-http-stdlib/pyproject.toml`:
  ```toml
  [project]
  name = "dexpace-sdk-http-stdlib"
  version = "0.1.0"
  description = "Reference stdlib transports for dexpace-sdk-core (urllib + asyncio)"
  requires-python = ">=3.12"
  dependencies = ["dexpace-sdk-core>=0.1,<0.2"]
  ```
- [ ] `uv sync` in workspace root — confirm both packages install in editable mode.
- [ ] No tests run yet — files haven't moved.

**Commit:** `chore: scaffold uv workspace with dexpace-sdk-core and dexpace-sdk-http-stdlib`

### Task 0.2 — Move sdk-core sources (solo, in-orchestrator)

**Files moved:**
- `src/dexpace/sdk/core/**` → `packages/dexpace-sdk-core/src/dexpace/sdk/core/**`
  (excluding `client/urllib_http_client.py`, `client/asyncio_http_client.py`)
- `tests/**` (excluding `tests/client/test_urllib_http_client.py`,
  `tests/client/test_asyncio_http_client.py`) →
  `packages/dexpace-sdk-core/tests/**`
- `py.typed`, `__init__.py` files preserved.

**Steps:**
- [ ] Use `git mv` to preserve history:
  ```bash
  mkdir -p packages/dexpace-sdk-core/src/dexpace/sdk
  git mv src/dexpace/sdk/core packages/dexpace-sdk-core/src/dexpace/sdk/core
  ```
- [ ] Move tests excluding client transport tests.
- [ ] **Remove** `__init__.py` files at `packages/dexpace-sdk-core/src/dexpace/`
      and `packages/dexpace-sdk-core/src/dexpace/sdk/` — they must not exist
      so the namespace package works.
- [ ] Remove the now-empty `client/urllib_http_client.py` and
      `client/asyncio_http_client.py` from `dexpace-sdk-core` (they move to
      `-http-stdlib` next task) — but the `client/http_client.py` Protocol +
      `client/async_http_client.py` Protocol stay in `-core`.
- [ ] Run from workspace root:
      `uv run pytest packages/dexpace-sdk-core/tests -q`
      Expect: all tests pass that don't reference the stdlib transports
      (those will move next task).
- [ ] Run `uv run mypy --strict packages/dexpace-sdk-core/src packages/dexpace-sdk-core/tests` — clean.
- [ ] Run `uv run ruff check packages/dexpace-sdk-core` — clean.

**Commit:** `chore: relocate sdk-core sources into packages/dexpace-sdk-core`

### Task 0.3 — Move stdlib transports (solo, in-orchestrator)

**Files moved:**
- `urllib_http_client.py` → `packages/dexpace-sdk-http-stdlib/src/dexpace/sdk/http/stdlib/urllib_http_client.py`
- `asyncio_http_client.py` → `packages/dexpace-sdk-http-stdlib/src/dexpace/sdk/http/stdlib/asyncio_http_client.py`
- `tests/client/test_urllib_http_client.py` →
  `packages/dexpace-sdk-http-stdlib/tests/test_urllib_http_client.py`
- `tests/client/test_asyncio_http_client.py` →
  `packages/dexpace-sdk-http-stdlib/tests/test_asyncio_http_client.py`

**Steps:**
- [ ] `git mv` source files. Create `packages/dexpace-sdk-http-stdlib/src/dexpace/sdk/http/stdlib/__init__.py`:
  ```python
  """Reference stdlib transports for dexpace-sdk-core."""
  from .urllib_http_client import UrllibHttpClient
  from .asyncio_http_client import AsyncioHttpClient

  __all__ = ["UrllibHttpClient", "AsyncioHttpClient"]
  ```
- [ ] **Do not** create `__init__.py` at `packages/dexpace-sdk-http-stdlib/src/dexpace/`,
      `.../sdk/`, or `.../sdk/http/` — namespace packages only.
- [ ] Update imports inside the moved files: change relative imports
      (`from ..http.common.headers import Headers`) to absolute
      (`from dexpace.sdk.core.http.common.headers import Headers`). The
      transports live in a different package now and can't use relative imports
      to reach `-core`.
- [ ] Update test imports analogously.
- [ ] Add `tests/conftest.py` to the stdlib package if needed (echo-server fixtures,
      etc. — check what the moved test files reference).
- [ ] Update `packages/dexpace-sdk-core/src/dexpace/sdk/core/client/__init__.py`
      to no longer re-export `UrllibHttpClient` / `AsyncioHttpClient` (only the
      `HttpClient` / `AsyncHttpClient` Protocols stay).
- [ ] Run from workspace root:
      `uv run pytest -q`
      Expect: all 400 tests pass (both packages).
- [ ] Run `uv run mypy --strict packages/dexpace-sdk-core packages/dexpace-sdk-http-stdlib`.
- [ ] Run `uv run ruff check packages/`.

**Commit:** `chore: extract stdlib transports into dexpace-sdk-http-stdlib package`

### Task 0.4 — Workspace-wide CI + tooling (parallel with 0.5)

**Files:**
- `.github/workflows/test.yml` (or whatever CI config exists — verify first)
- Root `CLAUDE.md` — update to reflect new layout
- Root `README.md` — point at packages, document `uv sync` flow
- `pyproject.toml` (root) — add a `[tool.uv]` section with dev dependencies
  (pytest, mypy, ruff) so `uv sync --dev` populates the workspace tools

**Steps:**
- [ ] If `.github/workflows/*` exists, update to use `uv sync` + `uv run pytest`
      + `uv run mypy` + `uv run ruff` from the workspace root.
- [ ] Update `CLAUDE.md`'s "Repository Layout" section to reflect the new tree.
- [ ] Update root `README.md` with a "Quick start" that shows
      `uv sync` and a basic usage example pulling from both packages.
- [ ] No source changes; verification is just that the workspace `uv sync &&
      uv run pytest -q && uv run mypy --strict && uv run ruff check` is green.

**Commit:** `docs+ci: workspace-wide tooling and documentation refresh`

### Task 0.5 — Per-package READMEs + initial publishing metadata (parallel with 0.4)

**Files:**
- `packages/dexpace-sdk-core/README.md`
- `packages/dexpace-sdk-http-stdlib/README.md`

**Steps:**
- [ ] Write a short `README.md` per package describing its purpose,
      installation snippet, and a minimal usage example.
- [ ] Confirm each package's `pyproject.toml` has all the metadata needed for
      PyPI publishing (authors, license, project URLs, classifiers, keywords).
- [ ] No tests; the verification is `uv build` succeeds in each package dir and
      produces a valid wheel.

**Commit:** `docs: per-package READMEs and PyPI metadata polish`

---

## Phase 1 — Foundation utilities (in `dexpace-sdk-core`)

Two infrastructure pieces that several Phase-2 and Phase-3 tasks depend on.

### Task 1.1 — `Clock` abstraction

**Files:**
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/util/__init__.py` (new subpackage)
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/util/clock.py`
- New: `packages/dexpace-sdk-core/tests/util/test_clock.py`

**Spec:**

```python
# clock.py
from typing import Protocol, runtime_checkable
import asyncio
import time

@runtime_checkable
class Clock(Protocol):
    """Source of wall-clock time, monotonic time, and blocking sleep.

    Injected into time-dependent components (retry backoff, bearer-token
    expiry) so tests can drive time deterministically without real sleeps.
    """
    def now(self) -> float: ...
    def monotonic(self) -> float: ...
    def sleep(self, duration: float) -> None: ...

@runtime_checkable
class AsyncClock(Protocol):
    """Async twin of `Clock`."""
    def now(self) -> float: ...
    def monotonic(self) -> float: ...
    async def sleep(self, duration: float) -> None: ...

class _SystemClock:
    def now(self) -> float: return time.time()
    def monotonic(self) -> float: return time.monotonic()
    def sleep(self, duration: float) -> None:
        if duration > 0: time.sleep(duration)

class _AsyncSystemClock:
    def now(self) -> float: return time.time()
    def monotonic(self) -> float: return time.monotonic()
    async def sleep(self, duration: float) -> None:
        if duration > 0: await asyncio.sleep(duration)

SYSTEM_CLOCK: Clock = _SystemClock()
ASYNC_SYSTEM_CLOCK: AsyncClock = _AsyncSystemClock()
```

**Steps:**
- [ ] Write failing tests in `test_clock.py`:
  - `test_system_clock_now_advances`
  - `test_system_clock_monotonic_non_decreasing`
  - `test_system_clock_sleep_zero_is_noop`
  - `test_system_clock_sleep_negative_is_noop` (or raises? — pick noop, matches Java)
  - `test_async_system_clock_sleep` (using pytest-asyncio)
  - `test_clock_protocol_satisfied_by_system_clock` (`isinstance(SYSTEM_CLOCK, Clock)`)
- [ ] Implement.
- [ ] Add `clock`, `Clock`, `AsyncClock`, `SYSTEM_CLOCK`, `ASYNC_SYSTEM_CLOCK` to
      a top-level `util/__init__.py` and verify `from dexpace.sdk.core.util import Clock` works.
- [ ] Add a `FakeClock` to `tests/conftest.py` for use by other tests:
  ```python
  class FakeClock:
      def __init__(self, start: float = 0.0):
          self._t = start
      def now(self) -> float: return self._t
      def monotonic(self) -> float: return self._t
      def sleep(self, d: float) -> None: self._t += max(0, d)
      def advance(self, d: float) -> None: self._t += d
  ```
- [ ] Full verification gate.
- [ ] Commit: `feat: add Clock and AsyncClock abstractions for testable time`

### Task 1.2 — `Configuration` (layered env + override)

**Files:**
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/config/__init__.py`
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/config/configuration.py`
- New: `packages/dexpace-sdk-core/tests/config/test_configuration.py`

**Spec:**

```python
# configuration.py
from dataclasses import dataclass, field
from typing import Final
import os

@dataclass(frozen=True, slots=True)
class Configuration:
    """Layered runtime configuration: explicit override -> env var -> default.

    Typed accessors return the default on parse failure. Configuration
    issues never throw at the lookup site.
    """
    overrides: dict[str, str] = field(default_factory=dict)
    _env: Callable[[str], str | None] = field(default=os.environ.get, repr=False)

    def get(self, name: str, default: str | None = None) -> str | None: ...
    def get_int(self, name: str, default: int) -> int: ...
    def get_bool(self, name: str, default: bool) -> bool: ...  # strict: "true"/"false" only
    def get_duration(self, name: str, default: float) -> float: ...  # seconds; supports "500ms", "5s", "1m"

    # Well-known keys (mirror Java's well-knowns where relevant)
    MAX_RETRY_ATTEMPTS: Final[str] = "MAX_RETRY_ATTEMPTS"
    REQUEST_RETRY_DEFAULT_TIMEOUT: Final[str] = "REQUEST_RETRY_DEFAULT_TIMEOUT"
    HTTPS_PROXY: Final[str] = "HTTPS_PROXY"
    HTTP_PROXY: Final[str] = "HTTP_PROXY"
    NO_PROXY: Final[str] = "NO_PROXY"
```

Builder pattern: `ConfigurationBuilder().put("KEY", "value").build()`.

**Steps:**
- [ ] Write failing tests:
  - get/get_int/get_bool/get_duration happy paths
  - parse-failure-returns-default for each typed accessor
  - override beats env, env beats default
  - empty env value treated as absent (matches Java)
  - duration parsing for `500ms`, `5s`, `1m`, `2h`, bare number → seconds
- [ ] Implement.
- [ ] Full verification gate.
- [ ] Commit: `feat: add Configuration with layered env-var + override lookup`

### Task 1.3 — Migrate `RetryPolicy` to use `Clock`

**Files:**
- `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/policies/retry.py`
- `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/policies/async_retry.py`
- `packages/dexpace-sdk-core/tests/pipeline/test_retry.py`
- `packages/dexpace-sdk-core/tests/pipeline/test_async_pipeline.py`

**Goal:** Replace `time.monotonic()` and the `sleep` callable parameter with a
`Clock` injection. The existing `sleep: Callable[[float], None]` parameter
becomes a backwards-incompatible kwarg removal — pre-1.0, breaking is OK. Tests
migrate to `FakeClock`.

**Steps:**
- [ ] Update `RetryPolicy.__init__` to accept `clock: Clock = SYSTEM_CLOCK`
      (replaces the `sleep` callable).
- [ ] Replace `time.monotonic()` calls with `self._clock.monotonic()`.
- [ ] Replace `self._sleep(duration)` with `self._clock.sleep(duration)`.
- [ ] Same for `AsyncRetryPolicy` with `AsyncClock`.
- [ ] Update every existing test in `test_retry.py` / `test_async_pipeline.py`
      that built a `RetryPolicy(sleep=_no_sleep)` to use a `FakeClock` instead.
- [ ] Add new tests demonstrating deterministic backoff progression:
  - `test_retry_advances_clock_by_backoff_seconds`
  - `test_retry_clock_jitter_seeded` (verify jitter reproducible with seeded rand)
- [ ] Full verification gate.
- [ ] Commit: `refactor!: retry policy now takes a Clock; replaces sleep callable`

### Task 1.4 — Migrate `BearerTokenPolicy` / `AccessTokenInfo` to use `Clock`

**Files:**
- `packages/dexpace-sdk-core/src/dexpace/sdk/core/http/auth/access_token.py`
- `packages/dexpace-sdk-core/src/dexpace/sdk/core/http/auth/policies.py`
- `packages/dexpace-sdk-core/tests/auth/test_policies.py`
- `packages/dexpace-sdk-core/tests/auth/test_credentials.py`

**Goal:** Inject a `Clock` into `BearerTokenPolicy` /
`AsyncBearerTokenPolicy`. `AccessTokenInfo.needs_refresh()` takes an optional
`clock` parameter so it can be tested deterministically.

**Steps:**
- [ ] `AccessTokenInfo.needs_refresh(*, leeway_seconds: int = 300, clock: Clock | None = None)` —
      default to `SYSTEM_CLOCK` when None. Mostly a parameter addition.
- [ ] `BearerTokenPolicy.__init__` and async twin accept `clock: Clock | None = None`.
- [ ] Forward clock into all needs_refresh calls.
- [ ] Update token-expiry tests to use `FakeClock.advance()` instead of
      constructing tokens with `expires_on = time.time() + 3600`.
- [ ] Full verification gate.
- [ ] Commit: `refactor: BearerTokenPolicy accepts injectable Clock for testability`

---

## Phase 2 — Stage-based pipeline organization

Add the Java-style `Stage` enum and a parallel `StagedPipelineBuilder`
alongside the existing `Pipeline(client, policies=[...])` constructor. The list
constructor stays as the "I know my order" escape hatch.

### Task 2.1 — `Stage` enum + `__init_subclass__` enforcement (solo, in-orchestrator)

**Files:**
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/stage.py`
- `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/policy.py` (add
  `STAGE` ClassVar requirement via `__init_subclass__`)
- `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/async_policy.py` (same)
- `packages/dexpace-sdk-core/tests/pipeline/test_stage.py` (new)

**Spec:**

```python
# stage.py
from enum import IntEnum

class Stage(IntEnum):
    """Pipeline stage. Lower value runs first (closer to caller entry).

    Pillar stages admit at most one policy; non-pillar stages stack.
    Sparse 100-apart values leave room to insert new stages later.
    """
    # Wrapping (re-invoke downstream)
    REDIRECT = 100      # pillar
    POST_REDIRECT = 150
    RETRY = 200         # pillar
    POST_RETRY = 250

    # Auth
    PRE_AUTH = 300
    AUTH = 400          # pillar
    POST_AUTH = 500

    # Instrumentation
    PRE_LOGGING = 600
    LOGGING = 700       # pillar
    POST_LOGGING = 800

    # Serde / send
    PRE_SERDE = 900
    SERDE = 1000        # pillar (reserved)
    POST_SERDE = 1100
    PRE_SEND = 1200
    SEND = 1300         # terminal — never user-extensible

    @property
    def is_pillar(self) -> bool:
        return self in _PILLARS

_PILLARS = frozenset({Stage.REDIRECT, Stage.RETRY, Stage.AUTH, Stage.LOGGING,
                      Stage.SERDE, Stage.SEND})
```

Then in `policy.py`:

```python
class Policy(ABC):
    STAGE: ClassVar[Stage]

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        # Allow intermediate abstract bases to skip STAGE; concrete classes must declare.
        if not getattr(cls, "__abstractmethods__", None) and not hasattr(cls, "STAGE"):
            raise TypeError(
                f"{cls.__name__} must declare STAGE: ClassVar[Stage]. "
                f"See dexpace.sdk.core.pipeline.Stage for choices."
            )
```

**Steps:**
- [ ] Write failing tests:
  - `test_stage_pillar_check` (REDIRECT.is_pillar == True; POST_REDIRECT.is_pillar == False)
  - `test_concrete_policy_without_STAGE_raises` (define a subclass missing STAGE; expect TypeError at class-creation)
  - `test_concrete_policy_with_STAGE_succeeds`
  - `test_abstract_intermediate_policy_can_skip_STAGE`
- [ ] Implement `stage.py` and the `__init_subclass__` hook.
- [ ] Set `STAGE` on every existing concrete policy: `RetryPolicy.STAGE = Stage.RETRY`,
      `BearerTokenPolicy.STAGE = Stage.AUTH`, `BasicAuthPolicy.STAGE = Stage.AUTH`,
      `KeyCredentialPolicy.STAGE = Stage.AUTH`, `LoggingPolicy.STAGE = Stage.LOGGING`,
      `TracingPolicy.STAGE = Stage.LOGGING` (debatable — could be POST_LOGGING; pick one).
- [ ] Same for async twins.
- [ ] Full verification gate.
- [ ] Commit: `feat: introduce Stage enum and STAGE ClassVar enforcement on Policy`

### Task 2.2 — `StagedPipelineBuilder` (solo, in-orchestrator)

**Files:**
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/staged_builder.py`
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/async_staged_builder.py`
- `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/__init__.py` (re-export)
- New: `packages/dexpace-sdk-core/tests/pipeline/test_staged_builder.py`
- New: `packages/dexpace-sdk-core/tests/pipeline/test_async_staged_builder.py`

**Spec:**

```python
class StagedPipelineBuilder:
    """Build a Pipeline by stage rather than by user-specified order.

    Each Policy declares its STAGE; the builder slots them into stage buckets
    and flattens to a list at build() time. Pillar stages raise on second
    insertion — use replace() to swap.

    Pillar replacement: raises by default (safer than Java's warning).
    Use `.replace(StepType, new_step)` to swap explicitly.
    """
    def __init__(self, client: HttpClient) -> None: ...

    def append(self, policy: Policy) -> Self: ...        # add to tail of policy.STAGE bucket
    def prepend(self, policy: Policy) -> Self: ...       # add to head
    def replace(self, target: type[Policy], new: Policy) -> Self: ...
    def insert_after(self, target: type[Policy], new: Policy) -> Self: ...
    def insert_before(self, target: type[Policy], new: Policy) -> Self: ...
    def remove(self, target: type[Policy]) -> Self: ...

    def build(self) -> Pipeline: ...                     # walks stages in order, skips SEND
```

**Steps:**
- [ ] Write failing tests covering:
  - append + build → stage-ordered pipeline
  - pillar slotted exactly once; second append raises ValueError
  - .replace() swaps the pillar OK
  - non-pillar deque accepts multiple appends
  - insert_after / insert_before with type-based target
  - remove() drops all instances of a type
- [ ] Implement using a `dict[Stage, list[Policy]]` for non-pillars and
      `dict[Stage, Policy]` for pillars. Flatten by walking `Stage` in
      enum-value order.
- [ ] Same for async builder.
- [ ] Full verification gate.
- [ ] Commit: `feat: add StagedPipelineBuilder with type-based surgical edits`

### Task 2.3 — `StagedPipelineBuilder.from_pipeline(p)` factory (parallel with 2.4 + 2.5)

**Files:**
- `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/staged_builder.py`
- `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/async_staged_builder.py`
- `packages/dexpace-sdk-core/tests/pipeline/test_staged_builder.py`
- `packages/dexpace-sdk-core/tests/pipeline/test_async_staged_builder.py`

**Goal:** Given a `Pipeline` already built via the list constructor, produce a
`StagedPipelineBuilder` seeded with its policies. Enables "build a default
pipeline, then surgically swap one piece" workflows.

**Steps:**
- [ ] `StagedPipelineBuilder.from_pipeline(p: Pipeline) -> Self` classmethod.
- [ ] Test: round-trip (pipeline → builder → pipeline) preserves policy order
      and identity.
- [ ] Test: round-trip surfaces ordering violations — if the input pipeline has
      RETRY before REDIRECT, `from_pipeline` raises ValueError (with hint to
      use the list constructor).
- [ ] Commit: `feat: StagedPipelineBuilder.from_pipeline reconstructs from list-form`

### Task 2.4 — `default_pipeline()` convenience factory (parallel with 2.3 + 2.5)

**Files:**
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/defaults.py`
- New: `packages/dexpace-sdk-core/tests/pipeline/test_defaults.py`

**Spec:** A convenience function that returns a `StagedPipelineBuilder`
pre-loaded with the canonical stack: SetDate → Retry → Auth → Logging. Mirrors
Java's `DefaultHttpPipeline` shape.

```python
def default_pipeline(
    client: HttpClient,
    *,
    credential: Credential | None = None,
    retry: RetryPolicy | None = None,
    redirect: RedirectPolicy | None = None,
    logging: LoggingPolicy | None = None,
) -> StagedPipelineBuilder: ...
```

**Steps:**
- [ ] Write tests covering each combination of opt-in components.
- [ ] Implement — wires the supplied (or default) policies into a builder.
- [ ] Commit: `feat: add default_pipeline() factory wiring canonical policies`

### Task 2.5 — Pillar-replacement raise behavior + `force=True` opt-in (parallel with 2.3 + 2.4)

**Files:**
- `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/staged_builder.py`
- `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/async_staged_builder.py`
- `packages/dexpace-sdk-core/tests/pipeline/test_staged_builder.py`

**Goal:** The default behavior (raise on pillar replacement) is the right
default but rare valid use cases (test fixtures swapping pillars) need an
escape. Add `force: bool = False` to `append` / `prepend`.

**Steps:**
- [ ] Write tests:
  - second `append` of a pillar without `force=True` raises
  - `append(policy, force=True)` replaces silently
  - `replace()` always succeeds (no force needed — explicit intent)
- [ ] Implement.
- [ ] Commit: `feat: pillar replacement guard with explicit force=True escape`

---

## Phase 3 — New policies

All four are file-disjoint with each other and with Phase-2 internals.
Dispatched as a single parallel wave.

### Task 3.1 — `RedirectPolicy`

**Files:**
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/policies/redirect.py`
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/policies/async_redirect.py`
- New: `packages/dexpace-sdk-core/tests/pipeline/test_redirect.py`
- New: `packages/dexpace-sdk-core/tests/pipeline/test_async_redirect.py`

**Spec (mirrors Java's `DefaultRedirectStep`):**

```python
class RedirectPolicy(Policy):
    STAGE: ClassVar[Literal[Stage.REDIRECT]] = Stage.REDIRECT

    def __init__(
        self,
        *,
        max_hops: int = 10,
        follow_303: bool = True,
        allowed_methods: frozenset[Method] = frozenset({Method.GET, Method.HEAD}),
        strip_authorization: bool = True,
        should_redirect: Callable[[RedirectDecision], bool] | None = None,
    ) -> None: ...

    def send(self, request: Request, ctx: PipelineContext) -> Response: ...
```

Status-code matrix:
- 301, 302: follow with original method if in `allowed_methods`
- 303: if `follow_303`, reissue as GET and drop body + `Content-*` headers
- 307, 308: follow with original method **and body**; body must be replayable
- Anything else: don't follow

Security:
- `Authorization` header stripped before every redirect reissue (when
  `strip_authorization=True`)
- `userinfo` in the `Location` URI is dropped before reissue

Loop detection:
- `LinkedHashSet`-equivalent (Python: `dict.fromkeys(visited)`) of visited
  URIs; if next URI is already visited, return current response without throwing

Errors:
- 307/308 with non-replayable body raises `RuntimeError` (body cannot be safely
  re-sent)

**Steps:**
- [ ] Write tests for each row of the status-code matrix (~12 tests).
- [ ] Write security tests: `Authorization` stripped, `userinfo` dropped.
- [ ] Loop detection test.
- [ ] Max-hops cap test.
- [ ] 307 + single-use body raises test.
- [ ] Implement sync; async is a near-mechanical port.
- [ ] Update `docs/pipelines.md` with a redirect section.
- [ ] Commit: `feat: add RedirectPolicy / AsyncRedirectPolicy with credential stripping`

### Task 3.2 — `SetDatePolicy`

**Files:**
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/pipeline/policies/set_date.py`
- New: `packages/dexpace-sdk-core/tests/pipeline/test_set_date.py`

**Spec:**

```python
class SetDatePolicy(Policy):
    """Stamps outgoing request with `Date` header in RFC 7231 (HTTP-date) format.

    Placed at POST_RETRY so each retry attempt receives a fresh timestamp;
    placing it earlier would cache the time across attempts and risk false
    signatures on services that bind the date into request signing.
    """
    STAGE: ClassVar[Literal[Stage.POST_RETRY]] = Stage.POST_RETRY

    def __init__(self, *, clock: Clock = SYSTEM_CLOCK) -> None: ...

    def send(self, request: Request, ctx: PipelineContext) -> Response: ...
```

Use `email.utils.formatdate(usegmt=True)` from stdlib for the RFC 7231 form
(`Sun, 06 Nov 1994 08:49:37 GMT`).

**Steps:**
- [ ] Write tests:
  - stamps `Date` header on outgoing request
  - format matches RFC 7231 (`r'^[A-Z][a-z]{2}, \d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2} GMT$'`)
  - re-stamps on each retry (use FakeClock + advance between attempts)
  - does not overwrite a caller-supplied `Date` header? Decision: yes, overwrite (matches Java)
- [ ] Async variant `AsyncSetDatePolicy`.
- [ ] Commit: `feat: add SetDatePolicy for per-attempt RFC 7231 timestamps`

### Task 3.3 — `DigestChallengeHandler` + auth challenge parser

**Files:**
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/http/auth/challenge.py` (AuthenticateChallenge dataclass + parser)
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/http/auth/challenge_handler.py` (ChallengeHandler Protocol + BasicChallengeHandler + CompositeChallengeHandler)
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/http/auth/digest.py` (DigestChallengeHandler)
- New: `packages/dexpace-sdk-core/tests/auth/test_challenge_parser.py`
- New: `packages/dexpace-sdk-core/tests/auth/test_digest.py`

**Spec:**

```python
@dataclass(frozen=True, slots=True)
class AuthenticateChallenge:
    scheme: str                 # "Basic", "Digest", "Bearer", ...
    parameters: dict[str, str]  # case-insensitive keys per RFC 7235

def parse_challenges(header_value: str) -> list[AuthenticateChallenge]:
    """Parse a `WWW-Authenticate` or `Proxy-Authenticate` header per RFC 7235."""

class ChallengeHandler(Protocol):
    def can_handle(self, challenges: list[AuthenticateChallenge]) -> bool: ...
    def handle(
        self,
        method: Method,
        url: Url,
        challenges: list[AuthenticateChallenge],
        *,
        is_proxy: bool,
    ) -> tuple[str, str] | None:  # (header_name, header_value)
        ...

class DigestChallengeHandler:
    def __init__(
        self,
        username: str,
        password: str,
        *,
        preferred_algorithms: tuple[DigestAlgorithm, ...] = DEFAULT_PREFERENCE,
    ) -> None: ...
```

Algorithms: `MD5`, `MD5-sess`, `SHA-256`, `SHA-256-sess`. Skip `auth-int` and
mutual-auth (matches Java v1 scope).

Concurrency: nonce counter via `itertools.count()` wrapped in a `Lock` (CPython
`int` is not atomic; the lock is cheap).

**Steps:**
- [ ] Write tests for the challenge parser:
  - quoted-string params with escapes
  - multiple comma-separated challenges (`Basic realm="r1", Digest realm="r2"`)
  - case-insensitive scheme + param-name comparison
  - rejects malformed headers cleanly
- [ ] Write tests for DigestChallengeHandler:
  - MD5 / SHA-256 happy paths (known test vectors from RFC 7616 §3.9.1)
  - prefers SHA-256 over MD5 when both are offered
  - nonce counter increments per request
  - returns `Proxy-Authorization` when `is_proxy=True`
- [ ] Implement parser using a small state machine (don't reach for `pyparsing`).
- [ ] Implement DigestChallengeHandler using `hashlib` + `secrets.token_hex(16)`
      for cnonce.
- [ ] Commit: `feat: add Digest auth + WWW-Authenticate challenge parser`

### Task 3.4 — `ChallengeHandler` integration with `BearerTokenPolicy` (parallel with 3.1-3.3)

**Files:**
- `packages/dexpace-sdk-core/src/dexpace/sdk/core/http/auth/policies.py`
- `packages/dexpace-sdk-core/tests/auth/test_policies.py`

**Goal:** Wire the new ChallengeHandler Protocol into BearerTokenPolicy's
`on_challenge` hook so subclasses can use a handler instead of overriding the
method. Largely additive — existing on_challenge override path still works.

**Steps:**
- [ ] Add optional `challenge_handler: ChallengeHandler | None = None` parameter.
- [ ] When set, on 401/407 the policy parses `WWW-Authenticate` / `Proxy-Authenticate`
      and delegates to the handler.
- [ ] Test that DigestChallengeHandler wired into BearerTokenPolicy successfully
      negotiates a Digest challenge.
- [ ] Commit: `feat: BearerTokenPolicy can delegate challenges to a ChallengeHandler`

---

## Phase 4 — ProxyOptions

Value type only. Actual proxy use (CONNECT tunneling) is a transport concern —
not in scope here.

### Task 4.1 — `ProxyOptions` dataclass (parallel with 4.2)

**Files:**
- New: `packages/dexpace-sdk-core/src/dexpace/sdk/core/util/proxy.py`
- New: `packages/dexpace-sdk-core/tests/util/test_proxy.py`

**Spec:**

```python
@dataclass(frozen=True, slots=True)
class ProxyOptions:
    type: ProxyType                  # HTTP / SOCKS4 / SOCKS5
    host: str
    port: int
    non_proxy_hosts: tuple[str, ...] = ()
    username: str | None = None
    password: str | None = None

    def bypasses_proxy(self, host: str) -> bool: ...

    def __repr__(self) -> str:
        # mask credentials
```

`bypasses_proxy` compiles `non_proxy_hosts` glob patterns once at construction
(use `re.compile(fnmatch.translate(pattern), re.IGNORECASE)`).

**Steps:**
- [ ] Write tests:
  - `bypasses_proxy("api.internal.example.com")` matches `*.internal.example.com`
  - case-insensitive matching
  - `__repr__` masks credentials
  - validation: port in 0..65535, non-empty host
- [ ] Implement.
- [ ] Commit: `feat: add ProxyOptions value type with bypass-glob matching`

### Task 4.2 — `ProxyOptions.from_configuration()` (parallel with 4.1)

**Files:**
- `packages/dexpace-sdk-core/src/dexpace/sdk/core/util/proxy.py`
- `packages/dexpace-sdk-core/tests/util/test_proxy.py`

**Goal:** Factory that reads `HTTPS_PROXY` / `HTTP_PROXY` / `NO_PROXY` env vars
via `Configuration`. Returns `None` when no proxy is configured.

`NO_PROXY=*` → return None (bypass everything).
`HTTPS_PROXY=http://user:pass@proxy.corp:8080` → full parse.

**Steps:**
- [ ] Write tests covering: HTTPS_PROXY wins over HTTP_PROXY, NO_PROXY=*
      bypasses, malformed URL returns None (with a warning log), invalid port
      returns None.
- [ ] Implement using `urllib.parse.urlsplit`.
- [ ] Commit: `feat: ProxyOptions.from_configuration reads HTTP(S)_PROXY env vars`

---

## Phase 5 — Optional transport packages

Three new packages, each a thin adapter to a popular Python HTTP library.
File-disjoint with each other and with `dexpace-sdk-http-stdlib`. Run in
parallel.

### Task 5.1 — `dexpace-sdk-http-httpx`

**Files:**
- New: `packages/dexpace-sdk-http-httpx/pyproject.toml`
- New: `packages/dexpace-sdk-http-httpx/src/dexpace/sdk/http/httpx/__init__.py`
- New: `packages/dexpace-sdk-http-httpx/src/dexpace/sdk/http/httpx/sync.py` (`HttpxHttpClient`)
- New: `packages/dexpace-sdk-http-httpx/src/dexpace/sdk/http/httpx/async_.py` (`AsyncHttpxHttpClient`)
- New: `packages/dexpace-sdk-http-httpx/tests/test_httpx_client.py`
- New: `packages/dexpace-sdk-http-httpx/README.md`

**Spec:** `HttpxHttpClient` implements the `HttpClient` Protocol from `-core`,
delegating to `httpx.Client`. Supports streaming uploads/downloads (unlike
urllib), per-phase timeouts (connect / read / write / pool), `ProxyOptions`.

**Steps:**
- [ ] Write integration tests using `httpx.MockTransport` (no real network).
- [ ] Implement sync + async clients.
- [ ] Workspace `pyproject.toml` gets `dexpace-sdk-http-httpx = { workspace = true }`.
- [ ] Commit: `feat: add dexpace-sdk-http-httpx package`

### Task 5.2 — `dexpace-sdk-http-aiohttp`

**Files:**
- New: `packages/dexpace-sdk-http-aiohttp/pyproject.toml`
- New: `packages/dexpace-sdk-http-aiohttp/src/dexpace/sdk/http/aiohttp/__init__.py`
- New: `packages/dexpace-sdk-http-aiohttp/src/dexpace/sdk/http/aiohttp/client.py` (async only)
- New: `packages/dexpace-sdk-http-aiohttp/tests/test_aiohttp_client.py`
- New: `packages/dexpace-sdk-http-aiohttp/README.md`

**Spec:** `AiohttpHttpClient` implements `AsyncHttpClient` over
`aiohttp.ClientSession`. Streaming uploads via async iterables.

**Steps:**
- [ ] Tests against `aiohttp.test_utils.AioHTTPTestCase` or a local server fixture.
- [ ] Implement.
- [ ] Commit: `feat: add dexpace-sdk-http-aiohttp package`

### Task 5.3 — `dexpace-sdk-http-requests`

**Files:**
- New: `packages/dexpace-sdk-http-requests/pyproject.toml`
- New: `packages/dexpace-sdk-http-requests/src/dexpace/sdk/http/requests/__init__.py`
- New: `packages/dexpace-sdk-http-requests/src/dexpace/sdk/http/requests/client.py` (sync only)
- New: `packages/dexpace-sdk-http-requests/tests/test_requests_client.py`
- New: `packages/dexpace-sdk-http-requests/README.md`

**Spec:** `RequestsHttpClient` over `requests.Session`. Streaming downloads via
`Response.iter_content`; uploads use `requests`'s file-like body support.

**Steps:**
- [ ] Tests using `responses` or `requests_mock`.
- [ ] Implement.
- [ ] Commit: `feat: add dexpace-sdk-http-requests package`

---

## Subagent Execution Waves

### File-collision matrix

| Task | Files modified (selected) |
|---|---|
| 0.1 | root + 2 new pyprojects |
| 0.2 | massive git mv — solo |
| 0.3 | massive git mv — solo |
| 0.4 | CI + READMEs |
| 0.5 | per-package READMEs (disjoint with 0.4) |
| 1.1 | new util/clock.py + tests |
| 1.2 | new config/configuration.py + tests |
| 1.3 | retry.py + tests |
| 1.4 | auth/policies.py + access_token.py + tests |
| 2.1 | new stage.py + policy.py + async_policy.py + every existing policy file (STAGE add) |
| 2.2 | new staged_builder.py + tests |
| 2.3 | staged_builder.py + tests |
| 2.4 | new defaults.py |
| 2.5 | staged_builder.py + tests |
| 3.1 | new redirect.py + tests |
| 3.2 | new set_date.py + tests |
| 3.3 | new auth/challenge.py + digest.py + tests |
| 3.4 | auth/policies.py + tests |
| 4.1 | new util/proxy.py + tests |
| 4.2 | util/proxy.py + tests (sequential after 4.1) |
| 5.1 / 5.2 / 5.3 | three brand-new packages (fully disjoint) |

### Wave plan

| Wave | Mode | Tasks | Notes |
|---|---|---|---|
| **1** | solo | 0.1 | Scaffold workspace |
| **2** | solo | 0.2 | Move sdk-core sources |
| **3** | solo | 0.3 | Move stdlib transports |
| **4** | parallel | 0.4, 0.5 | CI + READMEs |
| — | gate | full pytest + mypy + ruff against the new workspace | |
| **5** | parallel | 1.1, 1.2 | Clock + Configuration (file-disjoint) |
| — | gate | | |
| **6** | parallel | 1.3, 1.4 | Migrate retry + bearer to Clock (file-disjoint) |
| — | gate | | |
| **7** | solo | 2.1 | Stage enum + STAGE on every policy (cross-cutting) |
| — | gate | | |
| **8** | solo | 2.2 | StagedPipelineBuilder (new files, but builds on 2.1) |
| — | gate | | |
| **9** | parallel | 2.3, 2.4, 2.5 | Builder polish (different files within staged_builder area — verify on dispatch) |
| — | gate | | |
| **10** | parallel | 3.1, 3.2, 3.3, 3.4 | All four new policies (disjoint files) |
| — | gate | | |
| **11** | sequential | 4.1 → 4.2 | ProxyOptions then its factory (same file) |
| — | gate | | |
| **12** | parallel | 5.1, 5.2, 5.3 | Three new transport packages (fully disjoint) |
| — | gate | | |

### Verification gate between waves

After every wave, before the next dispatch, run:

```bash
uv run pytest -q
uv run mypy --strict packages/
uv run ruff check packages/
uv run ruff format --check packages/
```

Any failure halts the wave roll-forward. The orchestrator either fixes
in-place (cheap) or re-dispatches the offending task with the failure output
appended to its prompt.

### Subagent prompt template

Each subagent task gets a self-contained prompt of this shape:

```
You are implementing Task <ID> from
/Users/omar/.claude/plans/modular-split-and-java-feature-parity.md. Read that
section now (search for "Task <ID>:" in the file).

You will modify ONLY these files:
  - <file 1>
  - <file 2>
  ...

Workspace is uv-managed. Run commands from /Users/omar/PycharmProjects/python-sdk:
  uv run pytest -q
  uv run mypy --strict packages/
  uv run ruff check packages/
  uv run ruff format --check packages/

Workflow per the task:
1. Write the failing test(s) in the listed test file(s).
2. Run the package's pytest: <exact command>. Confirm it fails.
3. Implement in the listed source file(s).
4. Re-run pytest: confirm pass.
5. Run the full verification gate.
6. Commit with the message shown in the task.
7. Report: commit hash + one-line summary.

Read "Notes for the implementing agent" in the plan file before starting.
```

---

## Notes for the implementing agent

- **Namespace packages are non-negotiable.** `__init__.py` MUST NOT exist at
  `packages/<pkg>/src/dexpace/`, `packages/<pkg>/src/dexpace/sdk/`, or
  intermediate levels above the leaf package. Tests for namespace-package
  setup live in `packages/dexpace-sdk-core/tests/test_namespace_imports.py` —
  add this in Task 0.2.

- **Use `uv run` for everything.** Don't activate venvs manually. Don't fall
  back to `python3 -m pytest` after the workspace split — `uv run pytest`
  ensures the editable install is used.

- **`Clock` injection is API-breaking on RetryPolicy.** The old
  `sleep: Callable[[float], None]` parameter is removed in Task 1.3. Update
  every existing test that constructs `RetryPolicy(sleep=...)`. The FakeClock
  from `conftest.py` is the new way.

- **`Stage` `__init_subclass__` enforcement triggers at class-creation time.**
  Make sure every concrete Policy subclass in the codebase declares `STAGE`
  before Task 2.1's commit lands, or imports will start raising on the next
  test run. The plan handles this within Task 2.1 (single commit lands STAGE
  on every existing policy).

- **`StagedPipelineBuilder` is additive.** The existing `Pipeline(client,
  policies=[...])` constructor stays. Don't migrate existing tests to use the
  staged builder — both APIs are first-class.

- **`packages/dexpace-sdk-http-stdlib` imports `dexpace.sdk.core.*`
  absolutely**, never relatively, because it lives in a separate distribution.

- **Each transport adapter package (`-httpx`, `-aiohttp`, `-requests`) must
  satisfy `HttpClient`/`AsyncHttpClient` from `-core`** but is otherwise free
  to use third-party deps. Pin to a minor version range of the third-party lib
  for predictability.

- **Pre-existing breaking changes are OK.** `Response.message → reason`,
  `Request.url: str → Url`, `RetryPolicy(sleep=...)` removal are all
  acceptable. Update tests as needed in the same commit.

- **No new sysprop layer.** Python doesn't have system properties; the layered
  lookup is just `overrides → env → default`. The Java SDK's three-layer
  design (override → env → sysprop → default) collapses to two layers.

- **Don't reach for third-party utilities.** The plan stays within stdlib for
  `-core`. `httpx`, `aiohttp`, `requests` enter only in their respective
  transport packages.

---

## Verification

**Per-task:** Each task has its own pytest + mypy + ruff invocation noted.

**Per-wave:** Run the full gate (`uv run pytest -q && uv run mypy --strict
packages/ && uv run ruff check packages/ && uv run ruff format --check
packages/`) before proceeding to the next wave.

**End-to-end after Phase 5:**
- `uv build` succeeds in every package directory, producing valid wheels.
- `pip install dist/dexpace_sdk_core-*.whl dist/dexpace_sdk_http_httpx-*.whl`
  into a fresh venv works.
- A scratch integration test importing across packages confirms namespace
  packaging is correct.

---

## Out of scope (intentionally deferred)

- **CONNECT proxy tunneling** in any transport. `ProxyOptions` is a value
  type; consuming it for actual proxy use is a follow-up.

- **`PagedIterable` rework.** Python's `ItemPaged` / `Pager` already cover the
  Java `PagedIterable` shape; no port needed.

- **Tracing instrumentation expansions.** `TracingPolicy` exists and covers
  the basics. OpenTelemetry adapter modules are out of scope.

- **Metrics emission wiring.** The `Meter` / `LongCounter` /
  `DoubleHistogram` surface from Java's `instrumentation.metrics` is not
  ported; the `instrumentation/metrics.py` stub on the Python side can wait
  for a dedicated milestone.

- **Generated-client compat layer.** Java's `src/main/java` legacy tree
  (Azure-style annotations, embedded Jackson Core, Aalto XML, OTel adapters)
  is intentionally not part of the Kotlin surface and has no Python analog.

- **`Builder<T>` generic interface.** Already dropped (commit `9601f3f`); the
  Java port of this idiom is intentionally absent from the Python API.

- **Process-wide global `Configuration` slot.** Java has a `@Volatile` global
  for last-write-wins lookups; Python applications can pass `Configuration`
  explicitly or use a module-level singleton — no built-in global needed.
