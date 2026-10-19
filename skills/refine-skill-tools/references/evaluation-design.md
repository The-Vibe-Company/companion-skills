# Evaluation design

Read this before creating, repairing, or selecting evals for a refinement run.

## Objective

Measure whether a candidate skill helps an agent produce better results on the skill's actual job. Do not optimize for a generic rubric when the user cares about a concrete artifact or decision.

## Build the outcome contract

Extract five kinds of criteria:

1. **Task success** — what must be accomplished.
2. **Artifact completeness** — required files, fields, sections, or actions.
3. **Correctness** — facts, calculations, syntax, or domain rules that can be checked.
4. **Failure avoidance** — hallucination, unsafe action, scope drift, or missing approval.
5. **Efficiency constraints** — time, tokens, external calls, or package complexity when material.

Separate hard gates from preferences. A critical safety violation cannot be averaged away by attractive prose.

## Tuning and held-out suites

Use tuning cases to understand failures and shape hypotheses. Use held-out cases only to decide whether a candidate is accepted.

Held-out cases should:

- exercise the same capability without copying tuning wording;
- contain realistic variation in inputs and constraints;
- include at least one regression check for protected invariants;
- stay hidden from the candidate author and candidate-generation context;
- be replaced or expanded if they leak into candidate instructions.

For small skills, start with 3 tuning and 2 held-out cases. For high-risk or variable work, use more cases and repeated runs.

## Expectations

Write expectations as observable statements:

Good:

- "The generated CSV contains exactly the required seven columns."
- "No external message is sent before user approval."
- "Every recommendation cites a source present in the input ledger."

Weak:

- "The output is high quality."
- "The agent behaves professionally."
- "The skill is comprehensive."

If a dimension is subjective, define anchors instead of pretending it is deterministic:

```text
5 — immediately usable, specific, coherent, and faithful to the brief
3 — usable after moderate editing; one material weakness
1 — generic, incomplete, or misaligned with the brief
```

## Baseline choice

For refinement, the baseline is the current best version of the target skill—not an agent with no skill. A no-skill run may reveal whether the skill adds value, but it must not replace regression comparison against the installed version.

## Matched execution

Keep model, tools, input files, budgets, and system conditions as similar as the host permits. Run versions in isolated contexts and randomize output labels for blind comparison.

If the task is stochastic:

- repeat high-impact cases;
- report distributions or win counts rather than one score;
- treat small or inconsistent deltas as inconclusive;
- avoid changing the benchmark after seeing a candidate result unless both versions are rerun.

## Decision rule

Use a lexicographic gate:

1. critical invariants;
2. held-out task success;
3. regression-free segment results;
4. consistency;
5. efficiency and simplicity.

Reject ties. Do not combine unrelated dimensions into a single average that hides a critical regression.

## Eval health checks

Before trusting a benchmark, look for:

- expectations that every version passes;
- expectations that reward formatting but not correctness;
- judge decisions unsupported by evidence;
- cases copied into the candidate instructions;
- only happy-path prompts;
- a candidate that exploits a metric without improving usefulness;
- a subjective judge that knows which output is the candidate;
- large variance hidden behind one run.

Repair the benchmark and rerun both versions when any of these occur.
