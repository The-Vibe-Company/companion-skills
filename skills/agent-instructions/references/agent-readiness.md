# Agent readiness

Use this reference when the request is broader than writing one instruction file, when repository knowledge is fragmented, or when nested instructions, `DESIGN.md`, architecture docs, review rules, or ongoing improvement are in scope.

## Definition

A repository is agent-ready when an unfamiliar coding agent can:

1. discover the right authority before making a consequential decision;
2. install, run, and validate the project without guessing or touching production;
3. stay inside architectural, security, privacy, reliability, and generated-source boundaries;
4. receive high-signal review with a safe path for fixing violations;
5. turn repeated failures into the right durable artifact without growing an append-only prompt.

Do not use a numeric readiness score. Rate each dimension `strong`, `partial`, `missing`, or `not-applicable`, cite exact evidence, and identify blockers separately.

| Dimension | Strong evidence |
|---|---|
| Entry and reproducibility | Checked setup/start/build/test commands, environment contract, safe fixtures or sandboxes, and CI parity |
| Context routing | A concise entry map, justified scopes, working host adapters, and traced instruction chains without conflicts |
| Knowledge authorities | Product, architecture, design, security, reliability, and testing knowledge each have one discoverable owner where needed |
| Deterministic guardrails | Mechanical invariants live in tests, schemas, linters, hooks, configuration, or CI rather than prose alone |
| Review quality | Consequential rules pass coverage, restraint, retention, and actionability evaluation |
| Feedback and maintenance | Evidence has re-review triggers; repeated findings are promoted deliberately; stale rules and docs are garbage-collected |

One unresolved high-consequence trust or safety boundary can block readiness even when the other dimensions are strong.

## Authority map

Use roles, not a mandatory filename template:

| Role | Common artifact | Boundary |
|---|---|---|
| Entry map | `AGENTS.md` | Short conditional routes and cross-repository invariants |
| Claude adapter | `CLAUDE.md` | `@AGENTS.md` plus genuine Claude-only behavior |
| Architecture | `ARCHITECTURE.md` or `docs/architecture/` | Domains, dependency direction, runtime boundaries, links to decisions |
| Product | Product brief, PRD, or `docs/product/` | Users, jobs, non-goals, product invariants |
| Design | `DESIGN.md` or `docs/design/` | Human taste, interaction principles, accessibility, examples, and verification |
| Security/reliability/testing | Existing named authorities | Trust boundaries, operating promises, and verification strategy |
| Decisions and plans | ADR/design-doc index and execution plans | Why durable choices exist and how large work evolves |

Create or split an authority only when durable knowledge exists that code and checks cannot express clearly and a recognizable task class needs to consult it. Each fact gets one owner; other documents link rather than restate it.

For every authority record:

- purpose and exact path;
- task classes that must consult it;
- executable proof or validation command, if any;
- source files or decisions it explains;
- changes that trigger re-review;
- status: authoritative, transitional, historical, generated, or private.

## `DESIGN.md` contract

`DESIGN.md` is a versioned design and taste authority, not another `AGENTS.md`. It is also not necessarily a token dump.

For a product UI it may own:

- intent and core beliefs;
- interaction and information-hierarchy principles;
- visual tokens, or a link to their executable source;
- accessibility and responsive behavior;
- representative approved examples and explicit anti-examples;
- screenshot, browser-flow, visual-regression, or design-lint verification;
- the changes that require design review.

Keep volatile component inventories and facts inferable from code out of it. Put machine-checkable tokens and invariants in code or a linter, with `DESIGN.md` explaining the human decision.

Use `ARCHITECTURE.md` or a design-doc index for system structure. If `DESIGN.md` means UI design while `docs/design.md` means system architecture, disambiguate them with an authority index or a reversible rename. Do not make agents memorize an unexplained naming collision.

The instruction layer should use a conditional pointer, for example:

> When changing the public UI, follow `DESIGN.md` and run the affected visual and accessibility checks.

Do not copy colors, component catalogs, or long design prose into instruction files.

## Nested instruction admission

Create a nested scope only when all are true:

1. the subtree has a high-consequence, non-obvious rule irrelevant outside it;
2. placing the rule at root would add noise or create false positives;
3. the host loading path is understood for representative workflows;
4. the local file does not substantially repeat root instructions or an authority document;
5. the scope passes behavioral evaluation.

For portable multi-host support:

```text
AGENTS.md
CLAUDE.md                  # @AGENTS.md
apps/api/
  AGENTS.md
  CLAUDE.md                # @AGENTS.md
```

Do not mirror every package. For Claude-only glob ownership, `.claude/rules/` with `paths` may be more precise. For Copilot path-specific behavior, use `.github/instructions/*.instructions.md` with `applyTo` after verifying the target surface.

Trace at least root, each accepted subtree, and one cross-subtree workflow. Remember that Codex builds its regular project chain from repository root to startup working directory, while Claude discovers child `CLAUDE.md` files when it reads that subtree. Imports organize content but do not make it selective.

Evaluate every consequential nested rule with:

- **violation:** the rule must catch or prevent it;
- **safe:** a valid exception must remain allowed;
- **unrelated:** ordinary defects must still be reviewed;
- **cross-scope:** placement and host loading must work across boundaries.

Reject the nested scope if it improves none of these compared with the smaller topology.

## Review system

### Static topology

Enumerate instructions, imports, symlinks, overrides, path rules, and setup scripts that recreate them. Trace representative loaded chains. Detect contradictions, semantic duplicates, broken links/imports, private data, context budgets, and empty adapters. Distinguish a legitimate adapter from physical duplication.

### Authority and drift

Map each admitted rule to exact evidence and one authority or executable check. Detect overlapping owners, unlinked authorities, stale paths and commands, and ambiguous names. Record re-review triggers; do not rewrite documents automatically from heuristics.

### Behavioral review

For each consequential rule grade:

- **coverage** — known violations are caught;
- **restraint** — safe changes and exceptions are left alone;
- **retention** — ordinary defects are still found;
- **actionability** — findings name the invariant, evidence, location, and safe path.

For material migrations compare no context, current context, and proposed context with the same repository commit, tasks, permissions, and oracle. Repeat important stochastic cells and report sample size.

### Promotion routing

Route a repeated review comment, incident, or agent failure to exactly one destination:

- deterministic invariant → test, linter, schema, hook, configuration, or CI;
- durable explanation → product, architecture, design, security, reliability, or testing authority;
- decision-point warning → the narrowest justified instruction scope and host adapter;
- occasional procedure → skill or runbook;
- personal or customer context → ignored private overlay;
- weak or one-off signal → no codification yet.

### Garbage collection

Periodically rerun static and behavioral review. Remove rules that no longer change behavior, narrow rules that produce noise, update authority links when evidence changes, and retain rejected candidates only as local evaluation feedback—not shipped context.
