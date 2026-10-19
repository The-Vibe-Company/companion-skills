# Autoresearch method for skills

Read this before the first refinement experiment.

## Origin

Karpathy's Autoresearch reduces autonomous research to a controlled loop:

1. establish a baseline;
2. modify one trainable file;
3. run a fixed evaluation under a fixed budget;
4. log the result;
5. keep an improvement or discard a failure;
6. repeat from the best known state.

Darwin Skill applied this ratchet to Agent Skills by combining structural inspection with actual test-prompt execution, independent judges, keep/revert decisions, human checkpoints, and early stopping. Microsoft SkillOpt formalized a related approach with rollout evidence, bounded textual updates, held-out validation, rejected-edit memory, and a compact best-skill artifact.

Skill Refinery adopts the shared experimental discipline while changing the objective from "maximize a generic skill score" to "improve the target skill's real job without violating its constraints."

## Mapping

| Autoresearch | Skill Refinery |
|---|---|
| `program.md` | `refine-skill-tools/SKILL.md`, the research policy |
| `train.py` | one selected file in the candidate skill |
| fixed `prepare.py` evaluator | frozen contract, held-out cases, judge rules, and execution budget |
| `val_bpb` | outcome vector: critical gates, task success, regressions, consistency, cost, complexity |
| five-minute run | matched per-case time/token/tool budget |
| `results.tsv` | append-only `results.tsv` plus `decisions.jsonl` |
| advance branch | promote accepted candidate to current best inside the run workspace |
| reset failed commit | discard candidate snapshot and retain current best |

## Experimental constitution

Freeze these before comparing a candidate:

- target skill intent;
- critical invariants;
- held-out cases;
- expectation definitions and subjective anchors;
- target model class and tool access when controllable;
- per-case time or token budget;
- acceptance rule.

Do not edit the evaluation harness after seeing a disappointing candidate and then grade only the candidate. If a legitimate benchmark flaw is found, version the harness and rerun both sides.

## Single mutable asset

Default to one primary target file per experiment. This keeps the causal story reviewable:

```text
hypothesis -> bounded edit -> matched rollout -> decision
```

An atomic cross-file change is allowed only when one file cannot express the hypothesis—for example, adding a small deterministic validator and one instruction that invokes it. Record the exception and gate the combined delta as one experiment.

Do not mix trigger tuning, workflow redesign, new scripts, new evals, and package cleanup in the same candidate.

## Fixed budget

Matched conditions matter more than a universal duration. Choose a budget suitable for the target job and keep it fixed across the pair:

- maximum wall time;
- maximum model or tool calls when available;
- allowed tools and network access;
- input and reference availability;
- number of stochastic repetitions.

A candidate that times out or crashes is a failed experiment unless the failure is demonstrably caused by the harness itself.

## Ratchet

Use these statuses:

- `keep` — strict objective improvement with no critical regression;
- `discard` — worse, tied, overfit, too complex, or violates a gate;
- `crash` — candidate cannot complete under the fixed budget;
- `inconclusive` — noise, missing isolation, judge disagreement, or insufficient evidence.

The current best moves only on `keep`. Never delete failed hypotheses from the ledger; they are optimizer memory.

Equal task outputs plus a materially simpler skill can count as a strict improvement only when simplicity was declared in the contract before evaluation. This is not a post-hoc exception for a candidate that failed to improve results.

## Result vector, not vanity score

Autoresearch has one trustworthy scalar metric. General Agent Skills usually do not. Decide lexicographically:

1. critical safety, correctness, scope, and approval gates;
2. held-out task success;
3. segment regressions and consistency;
4. cost and latency;
5. package simplicity and maintainability.

Do not average a critical failure together with cosmetic strengths. A 90/100 score does not rescue a skill that sends a message without approval or fabricates a source.

## Early stopping

Default stop conditions:

- two consecutive `discard` or `inconclusive` experiments;
- no material failure remains;
- remaining gains are smaller than their complexity or cost;
- the next idea changes the intended job;
- three experiments have completed in the current run.

The user may explicitly request a larger or unattended budget. Even then, maintain the fixed harness, artifact isolation, and ratchet.

## Anti-patterns

Reject these moves:

1. the same context authors and judges its own candidate;
2. the optimizer sees held-out cases before authoring;
3. the evaluation harness changes for only one side;
4. multiple unrelated dimensions change in one experiment;
5. structural rubric gains substitute for worse task outputs;
6. dry runs are presented as benchmarks;
7. prompt length grows merely to impress a judge;
8. rejected ideas disappear from history;
9. a tiny gain introduces disproportionate runtime or complexity;
10. an unattended loop performs external or destructive actions outside the isolated run.

## What not to copy literally

Autoresearch can run indefinitely because its metric and sandbox are unusually clear. Skill optimization may involve subjective judgments, private data, external tools, approval gates, and costly actions. Therefore Skill Refinery defaults to bounded runs, snapshot isolation, independent judgment, and final human approval rather than "never stop."
