# Equity Research Harness

A local, single-operator CLI that runs the OpenAI **Agents API** (managed Codex harness) against a **Docker sandbox on this machine**. The operator supplies a complete investment brief; the coordinator screens a universe, one subagent researches each ticker, and a **deterministic allocator** turns on-disk research JSON into a one-shot USD book. Output is an educational memo, not licensed advice.

**Scope decision:** In = gated brief → self-hosted session → parallel per-ticker research → grounded allocation, with a hard per-turn cost kill-switch. P1 = immutable **host folder** per run (brief + research JSON + meta; allocation only on success). Deferred = web UI, brokerage, live quotes, auth, run search/DB. Excluded = defaulting missing brief fields, treating model prose as trusted dollars, continuing a turn after `COST_BOUND_USD`.

## Governing principle

**Gate, ground, then kill.**

| Rule | Meaning |
|---|---|
| **Gate** | No harness input that starts universe search or subagents until country, exchange, research count, portfolio count, and USD budget are all present and valid. |
| **Ground** | Dollar weights come from a deterministic function over research JSON + budget + caps. Unsourced figures are `unknown`; they lower confidence or drop the name. |
| **Kill** | When estimated turn cost ≥ `COST_BOUND_USD`, send `agent.session.input.cancel` immediately. No coordinator wrap-up. |

A feature that skips a gate, trusts an LLM number as money, or softens the kill-switch is out.

## Locked stack

- OpenAI Agents API (`client.beta.agents`, header `OpenAI-Beta: agents=v1`)
- Environment: `self_hosted`, Docker on this Mac, `codex exec-server`
- App `OPENAI_API_KEY` stays **outside** the container; restricted environment key is `CODEX_API_KEY` inside
- Tools: hosted `web_search`, `multi_agent`; subagents do **not** get function tools
- Budget and cost bound: USD; cost bound is env-only (`COST_BOUND_USD`), cancel at 100% of estimate
- Data residency: Agents API US-only; not ZDR-eligible
- Observability: OpenTelemetry traces from the CLI; **Jaeger** UI to inspect them (`ADR-007`). Optional; no-op if OTLP endpoint unset. Prometheus scrape of the CLI is out (short-lived process)
- *Assumption:* P0 surface is CLI; Python 3 + official OpenAI SDK; `AGENT_MODEL` env; `research_count` hard cap **12**; per-name allocation cap **35%**; P1 archives under `runs/<id>/` on the host (not OpenAI, not a database)

## Document map

| Doc | Purpose |
|---|---|
| [README.md](README.md) | Spine, stack, reading order |
| [PRD.md](PRD.md) | Problem, scope, requirements, risks, phases |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Runtime, flows, contracts, cost guard, run archive, observability, ADRs |

## Reading order

1. This file  
2. [PRD.md](PRD.md)  
3. [ARCHITECTURE.md](ARCHITECTURE.md)

## Conventions

- Requirements: `FR-x.y`, `NFR-x.y` (P0 = MVP). Decisions: `ADR-00N`.
- Home of a fact is one doc; others link.
- *Assumption:* marks a default that is not a user-confirmed number or product fact.

**Next:** [PRD.md](PRD.md)
