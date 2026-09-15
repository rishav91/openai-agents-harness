# PRD — Equity Research Harness

See [README.md](README.md) for the spine. Contracts and ADRs live in [ARCHITECTURE.md](ARCHITECTURE.md).

## 1. Problem

Screening an unfamiliar exchange still means tab-hopping (listings, filings, news) and then inventing a split of cash by gut. Chat UIs do not isolate per-name research, do not keep a shared workspace of structured findings, and do not stop when spend blows up.

**Wedge:** one local command that (1) refuses to start until the brief is complete, (2) fans out **independent** ticker research via the Agents API, (3) allocates with code, not prose, (4) cancels the turn at a configured USD ceiling.

This is a hands-on Agents API project for a single operator. It is not a product for other people to log into.

## 2. Goals and non-goals

**Goals (outcomes)**

- G1. Operator can produce one educational allocation memo from a complete brief without writing orchestration code by hand each run.
- G2. Missing brief fields never result in invented country, exchange, N, K, or budget.
- G3. A turn that hits `COST_BOUND_USD` stops; partial files are not presented as a recommendation.
- G4. Dollar amounts in the book are reproducible from saved JSON + the allocation spec.
- G5. After the container is gone, a completed or cancelled run still has a host snapshot sufficient to replay G4 or inspect a non-recommendation (`FR-5.*`). P1, not P0.

**Deferred (not v1)**

| Item | Why |
|---|---|
| Local web UI | CLI proves the harness; UI is presentation |
| Brokerage / paper trade | Execution is a different product |
| Live market-data APIs | Subagents inherit web search only; quotes can wait |
| Multi-session resume UX | One turn per brief is enough to learn the API |
| Sandbox providers (E2B, Modal, …) | Locked to Docker on this machine |
| Run database, search, tags, compare-runs UI | Persistence is a snapshot, not a product (`ADR-006`) |

**Excluded**

| Item | Why |
|---|---|
| Defaulting missing brief fields | Violates **Gate** |
| Licensed / personalized investment advice | Legal and product posture |
| Automatic order placement | Violates **Ground** (action from untrusted model) |
| Softening cost cancel (buffer UI, “let it finish”) | Violates **Kill** |
| OpenAI-hosted sandbox as the v1 environment | Locked to self-hosted Docker (`ADR-001`) |
| Aggregator subagent | Coordinator aggregates (`ADR-002`) |
| OpenAI session as system of record for workspace files | Self-hosted files are not published artifacts (`ADR-006`) |
| Showing a cost-cancelled archive as a recommendation | Violates **Kill** / `FR-4.2` |

**Failure even if it “ships”:** a run that starts on a partial brief; an allocation that does not match the spec given the JSON; a turn that keeps working after the cost bound.

## 3. Personas

| Persona | Scope | Primary need | AuthZ |
|---|---|---|---|
| Operator (you) | Entire machine, one process | Learn Agents API + get a sourced memo | None. Single user, localhost, no accounts |

No buyer/admin split. No multi-tenant isolation.

## 4. Core use case

**UC-1 — One-shot research and allocate**

1. Operator starts the CLI.
2. CLI asks, one field at a time if needed, for: **country**, **exchange**, **research count**, **portfolio count**, **USD budget**. Accepts full name or ISO/code for country and exchange if unambiguous. Does not guess.
3. CLI validates (`FR-1.*`). On failure, asks again. Does **not** create session work.
4. CLI creates an Agents API session (`self_hosted`), starts Docker + `codex exec-server`, waits until the environment is connected.
5. CLI sends **one** user message containing the complete brief and instructions (universe → N subagents → wait → write files).
6. Coordinator writes `universe.json`, spawns one subagent per ticker (≤ N, ≤ cap 12), each writes only `research/{TICKER}.*`.
7. Cost guard samples turn usage. If estimate ≥ `COST_BOUND_USD`, CLI cancels the turn (`FR-4.1`) and reports last estimate. Stop.
8. If the turn completes, CLI runs the allocator on disk JSON (`FR-3.*`) and writes host-visible `outputs/allocation.json` + `outputs/recommendation.md` (memo may be model-written **narrative around** the computed book, not a second set of weights).
9. CLI prints the book, disclaimer, and spend estimate. Does not place trades.
10. **P1:** CLI writes an immutable host archive (`FR-5.*`) on every terminal outcome, then tears down Docker. OpenAI session delete remains optional.

No other v1 use cases. Archive is teardown of UC-1, not a second product surface.

## 5. Scope / governing rule applied

| Tier | In |
|---|---|
| P0 (MVP) | `FR-1.*`–`FR-4.*`, Docker executor, web search, multi-agent, deterministic allocator, cost cancel, CLI |
| P1 | Host run archive (`FR-5.*`); OTel traces + Jaeger UI (`FR-6.*`); event-richer TTY; optional follow-up turn **only** if the brief is unchanged and cost guard still applies |
| P2 | Web UI, live quotes on the **coordinator** only, Prometheus via OTel collector |

## 6. Requirements

P0 = MVP. Acceptance is in the ID row.

### Brief (Gate)

| ID | Pri | Requirement | Acceptance |
|---|---|---|---|
| FR-1.1 | P0 | Collect country, exchange, research count, portfolio count, USD budget. Ask clearly if absent. | A run with any field missing never sends research input to the session |
| FR-1.2 | P0 | Country and exchange: full name or code; reject if empty or contradictory (e.g. two venues named) | Invalid → re-ask; no inference of exchange from country |
| FR-1.3 | P0 | `research_count` integer ≥ 1 and ≤ `MAX_RESEARCH_COUNT` (12) | Out of range → re-ask |
| FR-1.4 | P0 | `portfolio_count` integer ≥ 1 and ≤ `research_count` | Else re-ask |
| FR-1.5 | P0 | Budget: positive USD amount (cents allowed) | Else re-ask |
| FR-1.6 | P0 | `COST_BOUND_USD` is env-only; never prompted | Process refuses to start if unset or ≤ 0 |

### Session (harness)

| ID | Pri | Requirement | Acceptance |
|---|---|---|---|
| FR-2.1 | P0 | Session: `environment.type=self_hosted`, Docker workspace, `codex exec-server` | Research files appear under the mounted workspace |
| FR-2.2 | P0 | `web_search` + `multi_agent.enabled`; `max_concurrent_subagents` ≥ research count (subject to cap) | Subagents run; they do not receive function tools |
| FR-2.3 | P0 | Coordinator alone builds universe and writes `/workspace/universe.json` before spawning | No subagent starts without a ticker assignment from that file |
| FR-2.4 | P0 | One subagent per ticker; each writes only its own `research/{TICKER}.json` (+ optional `.md`) | No two agents edit the same path |
| FR-2.5 | P0 | Coordinator waits, then stops; it does **not** invent allocation weights | Weights exist only after `FR-3.1` |

### Allocation (Ground)

| ID | Pri | Requirement | Acceptance |
|---|---|---|---|
| FR-3.1 | P0 | Allocator is code: inputs = valid research JSON + budget + caps; output = `allocation.json` | Re-running the function on the same files yields the same cents |
| FR-3.2 | P0 | Select up to `portfolio_count` names; drop missing/invalid JSON and `unknown`-heavy rows per [ARCHITECTURE.md](ARCHITECTURE.md) § Allocation | Dropped names never receive dollars |
| FR-3.3 | P0 | Per-name weight cap 35%; leftover cash allowed | Sum of invested + cash = budget (cents) |
| FR-3.4 | P0 | User-facing memo states educational disclaimer and that weights are computed | No “buy” / broker CTA |

### Cost (Kill)

| ID | Pri | Requirement | Acceptance |
|---|---|---|---|
| FR-4.1 | P0 | While a turn is in progress, estimate USD from recorded turn usage (root + subagents). At estimate ≥ `COST_BOUND_USD`, send `agent.session.input.cancel` immediately | No further user input; CLI labels outcome `cancelled_cost_bound` |
| FR-4.2 | P0 | Cancelled or failed turns must not present `allocation.json` as the result | Explicit error; partial research may be listed as incomplete |
| FR-4.3 | P0 | Missing/`null` usage is not treated as $0 | Guard keeps polling; if a turn completes with unknown usage, still run allocator but flag `usage_unknown` — *except* if last known estimate already ≥ bound (then cancel path) |

### Run archive (P1)

Self-hosted workspace dies with the container. OpenAI keeps session *items*, not `/workspace` files. Archive is a host folder so **Ground** can be replayed after teardown. Not a database.

| ID | Pri | Requirement | Acceptance |
|---|---|---|---|
| FR-5.1 | P1 | After every terminal outcome (completed, `cancelled_cost_bound`, failed), copy an immutable `runs/<run_id>/` on the host | Folder exists before Docker teardown; re-running the CLI does not mutate a prior folder |
| FR-5.2 | P1 | Archive always contains `brief.json` and `meta.json`. Include `universe.json` and `research/*.json` when present | `meta.json` has session id, outcome, cost estimate, `AGENT_MODEL`, `COST_BOUND_USD`, `allocation_spec` version |
| FR-5.3 | P1 | `outputs/allocation.json` and success memo only if the allocator ran as success | Cost-cancel and failed archives: `outcome` is not `success`; those files are omitted |
| FR-5.4 | P1 | Allocator replay from an archived success folder matches original cents (`FR-3.1`) | Same function + same JSON + same spec version |

### Observability (P1)

App-side traces of **our** loop. Not a replacement for `runs/` or for **Kill**. OpenAI Agents dashboard traces are not the SoR.

| ID | Pri | Requirement | Acceptance |
|---|---|---|---|
| FR-6.1 | P1 | If `OTEL_EXPORTER_OTLP_ENDPOINT` is set, export one trace per CLI invocation over OTLP | Jaeger (or any OTLP backend) shows a root span `harness.run` after a run; unset endpoint → no exporter, process still runs |
| FR-6.2 | P1 | Spans cover intake, session/docker connect, and later research/cost/allocator/archive | Child spans named in [ARCHITECTURE.md](ARCHITECTURE.md) § Observability; `outcome` on the root span |
| FR-6.3 | P1 | Local **Jaeger** UI to inspect traces | `docker compose` in `observability/` serves the UI; no API keys on span attributes |
| FR-6.4 | P2 | Prometheus metrics via OTel collector (not scrape of the CLI) | Deferred; CLI remains a job, not a scrape target |

### Non-functionals

| ID | Pri | Requirement |
|---|---|---|
| NFR-1.1 | P0 | Scale: **1** concurrent session per CLI process |
| NFR-1.2 | P0 | `research_count` ≤ **12** |
| NFR-2.1 | P0 | Cost: cancel at **100%** of `COST_BOUND_USD` using the estimate in [ARCHITECTURE.md](ARCHITECTURE.md) § Cost guard. *Assumption:* recorded usage can lag; a small overshoot after cancel is accepted and documented |
| NFR-2.2 | P0 | Secrets: `OPENAI_API_KEY` never passed into the container; executor uses environment key only |
| NFR-3.1 | P0 | Threat model: untrusted web/tool text in the sandbox; no extra credentials in the workspace; output is not an order |
| NFR-3.2 | P1 | Span attributes must not include `OPENAI_API_KEY`, `OPENAI_EXECUTOR_API_KEY`, or `CODEX_API_KEY` |
| NFR-4.1 | P1 | *Assumption:* no p95 latency SLO for a learning CLI; operator waits on the turn |

## 7. Success metrics

| Kind | Metric | Target |
|---|---|---|
| Product | Complete-brief → memo without skipped gates | 100% of UC-1 happy paths in manual test |
| Product | Partial brief starts research | **0** occurrences |
| Technical | Allocator replay | Identical `allocation.json` bytes for same inputs |
| Technical | Cost guard | Fixture where estimate ≥ bound → cancel event observed; no allocation presented |
| Technical | Spend | Operator-set `COST_BOUND_USD`; no product target beyond “never ignore it” |
| Technical (P1) | Archive | After teardown, success run still replays allocator; cancelled run has meta + any partial JSON and no presented book |

## 8. Risks

| Risk | Mitigation |
|---|---|
| Web search stale/wrong figures | Schema requires sources; unsourced → `unknown` (`ADR-003`) |
| Usage lag overshoots bound | Document overshoot; still cancel at 100% of **reported** estimate (`ADR-004`) |
| Subagents collide on files | Path-per-ticker contract (`FR-2.4`) |
| `codex exec-server` / Docker flaky | Fail the run on `environment.failed`; do not send work |
| Model writes its own weights | CLI **overwrites** weights from allocator; model memo must quote `allocation.json` |
| Regulatory misread as advice | Disclaimer on every memo; excluded from goals |
| Container teardown wipes grounded JSON | P1 host snapshot (`ADR-006`); P0 still reads the live mount only |
| Archive mistaken for a saved “portfolio” | `outcome` in meta; no allocation file on cancel (`FR-5.3`) |
| Observability mistaken for Ground | Traces are inspect-only; dollars still from allocator + archive |

## 9. Phases

| Phase | Ships | Unlocks |
|---|---|---|
| 0 | CLI intake + env checks + session create + Docker executor connect (no research message) | Proves self-hosted loop |
| 1 | Brief → universe → subagents → files → allocator → memo; cost guard | P0 complete |
| 2 | Host run archive (`FR-5.*`); OTel + Jaeger (`FR-6.*`); richer event log; optional same-brief follow-up | Operability; inspect runs without scraping the CLI |

Sequencing: environment before agents (`ADR-001`); cost guard in the same phase as the first research send so an unbounded turn never exists. Archive after P0 so a cancelled turn is not blocked on disk I/O design, but **before** treating Docker teardown as safe.

**Next:** [ARCHITECTURE.md](ARCHITECTURE.md)
