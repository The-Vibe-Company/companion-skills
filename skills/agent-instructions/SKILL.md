---
name: agent-instructions
description: Make a repository agent-ready or improve an existing agent harness.
  Create, audit, rebuild, migrate, and validate AGENTS.md, CLAUDE.md, nested
  instructions, DESIGN.md and architecture/product/security/testing authorities,
  reproducible workflows, deterministic guardrails, and review feedback loops.
  Use whenever a user mentions agent readiness, coding-agent onboarding,
  repository instructions, context debt, AGENTS.md, CLAUDE.md, DESIGN.md,
  architecture docs, nested agent guidance, review rules, or improving how
  coding agents understand and validate a codebase—even if they only ask to
  "write a good AGENTS.md" or "clean up Claude's instructions."
metadata: {}
compatibility: Requires read access to the target repository and Python 3.
  Writes only to an isolated run directory until the user approves applying the
  proposal.
---

# Agent-Ready Repositories

Build the smallest evidence-backed repository harness that lets an unfamiliar coding agent find the right authority before acting, use the supported workflow, respect important boundaries, verify the result, and improve the system after repeated failures. Treat persistent context as a scarce routing layer, not as a second README.

## Protected invariants

- Start from repository evidence. Do not use a generic template as the source of truth.
- Judge readiness by behavior and evidence, never by the presence or number of recommended filenames.
- In Rebuild mode, complete the cold inventory and cold candidate before reading the bodies of existing instruction files. Existing files are forensic evidence, not authority.
- Admit a rule only when its omission creates a specific plausible mistake that is difficult to infer before the relevant decision point, or when a familiar convention actively points agents toward the wrong choice.
- Allow the correct result to be an empty or nearly empty instruction system.
- Keep deterministic requirements in scripts, hooks, tests, CI, or configuration; keep long knowledge in normal documentation; keep occasional procedures in skills.
- Give every durable fact exactly one authority. Instruction files may route to that authority but must not summarize it again.
- Treat `DESIGN.md` as a versioned design and taste authority when the product needs one, not as a second instruction file or a mandatory deliverable.
- Create a nested instruction scope only when a consequential subtree-only rule passes violation, safe, unrelated, and cross-scope evaluation.
- Never overwrite an existing instruction file, replace a symlink, or alter nested scope without showing the proposal and migration plan first.
- Keep private identifiers, personal routing, secrets, customer context, and machine-specific paths out of a shareable result.

## Choose the mode

Use **Create mode** when no substantive repository instruction system exists. A trivial adapter such as a one-line `@AGENTS.md` import does not count as substantive.

Use **Rebuild mode** when substantive instructions already exist, when files overlap or conflict, or when the user asks to audit, clean, reduce, restructure, migrate, or recreate them.

Use **Audit-only delivery** when the user asks for analysis but not changes. Follow Rebuild mode through the proposal and stop before applying it.

Within any mode, distinguish a **narrow instruction request** from a **full agent-readiness request**. For a narrow request, inspect adjacent authorities and guardrails for conflicts but keep the deliverable focused. For a full readiness request, evaluate every readiness dimension and propose improvements outside instruction files when justified.

Read:

- [`references/create-mode.md`](references/create-mode.md) for Create mode.
- [`references/rebuild-mode.md`](references/rebuild-mode.md) for Rebuild or audit-only mode.
- [`references/platform-semantics.md`](references/platform-semantics.md) before choosing canonical files, imports, symlinks, overrides, or nested scopes.
- [`references/agent-readiness.md`](references/agent-readiness.md) for knowledge authorities, `DESIGN.md`, readiness dimensions, nested-scope admission, and the improvement loop.
- [`references/rule-rubric.md`](references/rule-rubric.md) while admitting and placing rules.
- [`references/behavioral-evaluation.md`](references/behavioral-evaluation.md) when the change is important enough to compare behavior, cost, or correctness.
- [`references/research.md`](references/research.md) when the user asks why the workflow is intentionally minimal or requests current source support. Treat its verification date as an expiry signal.

## Common workflow

### 1. Establish scope and safety

Identify the repository root, requested agent hosts, intended output, and whether the user authorized applying changes or only asked for a proposal.

Record the current branch, commit, worktree state, instruction-file symlinks, imports, and nested scopes. Preserve unrelated user changes. If applying a proposal would collide with a dirty file, stop before the write and report the collision.

Create an isolated run directory, preferably:

`plans/agent-instructions/runs/<timestamp>-<slug>/`

If the repository does not allow local run artifacts, use a temporary directory and report it.

### 2. Capture repository evidence

Run the bundled inventory without reading instruction bodies:

```bash
python3 <skill-dir>/scripts/cold_inventory.py \
  --repo <repository-root> \
  --out <run-dir>/inventory.json \
  --markdown <run-dir>/inventory.md
```

Inspect the listed manifests, CI, scripts, tests, architecture docs, security boundaries, contributor docs, and source layout. Build `evidence-ledger.md` with one row per candidate fact:

| Candidate fact | Exact source | Scope | Stability | Mistake if omitted | Destination |
|---|---|---|---|---|---|

Do not turn every fact into a rule.

For a full agent-readiness request, also run:

```bash
python3 <skill-dir>/scripts/audit_agent_readiness.py \
  --repo <repository-root> \
  --out <run-dir>/agent-readiness-report.json \
  --markdown <run-dir>/agent-readiness-report.md
```

Treat its findings as heuristics to verify, not a score or a file-generation checklist. Build `authority-map.md` naming the single owner, consumers, executable proof, and re-review trigger for each durable knowledge class that actually exists.

### 3. Design the instruction topology

Default to a shared root `AGENTS.md` plus a minimal `CLAUDE.md` containing `@AGENTS.md` when multiple agent hosts matter. If the repository explicitly targets only Claude Code, a canonical `CLAUDE.md` may be simpler.

Use nested instructions only for rules that apply to a genuine subtree. Calculate the complete instruction chain for representative paths; a small root plus several repetitive nested files can still be large and contradictory.

Trace representative root, subtree, and cross-subtree launch paths with `trace_instruction_chain.py`. Do not assume that Codex, Claude Code, and every Copilot surface discover nested instructions at the same time or with the same precedence. In a portable multi-host repository, each accepted nested shared `AGENTS.md` normally needs a sibling `CLAUDE.md` adapter; an empty pair is debt, not compatibility.

Design the broader authority system at the same time. Prefer a short root instruction map pointing conditionally to existing product, architecture, design, security, reliability, and testing sources. If two documents have ambiguous roles—especially `DESIGN.md` and `docs/design.md`—clarify or rename their authorities instead of explaining the collision forever in `AGENTS.md`.

### 4. Compose rules

Prefer conditional, operational wording:

> When changing `<scope>`, run or preserve `<action>` because `<specific failure>`.

Do not copy stack descriptions, file tours, API documentation, obvious style rules, or volatile inventories. However, do not reject a rule merely because the truth becomes visible after opening the right file: retain a concise anti-convention warning when agents are likely to make the wrong structural choice before discovering that file. Link to an authority only when the pointer prevents a likely mistake; never summarize the authority again in the instruction file.

Before finalizing, compare the proposal against the evidence ledger by failure severity. Prefer trust and security boundaries, source-versus-generated ownership, required wrappers, anti-convention traps, and authoritative pointers over generic tooling reminders. A visible package-manager lockfile rarely needs a rule; a generated directory that looks editable usually does.

#### Reconcile semantic retention in Rebuild mode

After classifying legacy content, reconcile the semantic diff against the evidence ledger and proposal before finalizing:

1. Split a mixed legacy section into separate decision-point rules before assigning dispositions. Do not let a concise operational selector inherit the `move` or `delete` classification of its surrounding implementation tour.
2. For every `move`, record the concrete destination, the affected task class and decision point, and evidence that an agent will discover that destination before acting. A file or command being present somewhere in the repository is not proof of before-decision discovery.
3. When manifests or documentation expose multiple supported commands or launchers but the correct choice depends on the environment, host, or workflow, retain one conditional selector in the narrowest instruction scope if the conventional default would choose a competing or unsafe path. Move the detailed mechanics to their ordinary authority instead of copying the tour.

Add any newly separated candidate to `evidence-ledger.md`, and make its final instruction, destination, or rejection rationale explicit in `semantic-diff.md`.

For each proposed nested scope or consequential review rule, define four cases before admitting it:

- a violating change it must catch or prevent;
- a safe change or valid exception it must leave alone;
- an unrelated defect ordinary review must still catch;
- a cross-subtree change that reveals whether placement and loading are correct.

Write candidates under `<run-dir>/proposed/`, not into the repository.

### 5. Validate statically

Run:

```bash
python3 <skill-dir>/scripts/lint_instruction_stack.py \
  --repo <repository-root> \
  --instructions <run-dir>/proposed \
  --out <run-dir>/static-validation.json
```

Resolve every error. Review warnings for duplicate rules, broken imports, missing paths, unknown package scripts, suspicious private data, oversized files, and an excessive aggregate context budget. A warning may be accepted only with a written reason.

### 6. Present before applying

Show:

- the proposed topology and files;
- the evidence ledger;
- static validation;
- information intentionally excluded or moved;
- unresolved human decisions;
- for Rebuild mode, the semantic diff and migration plan.
- for full readiness, the readiness report, authority map, executable-guardrail gaps, and review/improvement plan.

Apply only after the user has authorized the concrete proposal. Preserve file modes and symlink intent. Update setup scripts that would otherwise recreate the old topology.

### 7. Verify after applying

Run the repository's relevant checks. Re-run the instruction linter against the applied files. Report what was verified and what remains unverified.

For high-impact repositories or material migrations, compare no context, current context, and proposed context using representative tasks. Do not claim improvement from line-count reduction alone.

Grade consequential rules on coverage, restraint, retention, and actionability. Route repeated findings to exactly one durable owner: executable check, knowledge authority, scoped instruction, on-demand skill/runbook, private overlay, or no codification.

## Output contract

Every run produces:

- `inventory.md` and `inventory.json`;
- `evidence-ledger.md`;
- `proposed/` instruction files;
- `static-validation.json`;
- `decision-report.md` explaining inclusions, exclusions, uncertainties, and whether applying is recommended.

Full agent-readiness runs additionally produce:

- `agent-readiness-report.md` and `.json`, with evidence-backed `strong`, `partial`, `missing`, or `not-applicable` dimensions and no aggregate score;
- `authority-map.md`, including ambiguous or overlapping authorities;
- `review-plan.md`, including static, drift, behavioral, and garbage-collection checks;
- proposals for docs, scripts, hooks, tests, or CI only where the evidence justifies them.

Rebuild and audit-only runs additionally produce:

- `current-stack.json`;
- `debt-report.md`;
- `semantic-diff.md` classifying old rules as keep, move, automate, private, confirm, or delete;
- `migration-plan.md`, including symlink/import/setup changes and rollback;
- behavioral comparison artifacts when requested or proportionate to the risk.

## Ownership boundary

This skill owns end-to-end repository agent readiness: instruction topology, knowledge-authority routing, cold reconstruction, reproducible agent workflows, deterministic guardrail gaps, review quality, migration, and maintenance design.

Incremental promotion of one lesson from a bug, review, or incident into an existing instruction system belongs to the repository's learning-loop workflow when one exists. A full rebuild may consume those lessons as evidence, but should not become an append-only learning log.
