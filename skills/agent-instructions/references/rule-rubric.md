# Rule admission and placement rubric

## Admission test

Retain a persistent instruction only when all relevant questions have concrete answers:

1. What precise mistake becomes more likely if the rule is absent?
2. Is the information difficult to infer before the agent reaches the relevant decision point?
3. Is the rule relevant often enough within its scope to justify always-on context?
4. What exact source proves it is currently true?
5. Is it stable enough to version with the repository?
6. Is prose the correct enforcement mechanism?
7. Can a task or check demonstrate that the rule changes useful behavior?

If the omission risk is vague, reject the rule.

### Decision-point and anti-convention test

“Discoverable somewhere in the repository” is not the same as “reliably inferred before acting.” Admit a compact rule when all of these are true:

1. a common framework or tooling convention suggests a specific action;
2. this repository intentionally does something different;
3. taking the conventional action first would create a competing owner, bypass a required wrapper, or cause another concrete failure; and
4. the agent is not guaranteed to inspect the disambiguating source before that action.

Example: if a route-group layout already owns the document shell and a conventional root layout would compete with it, say not to create the root layout. Do not expand that warning into a route-tree overview.

### Authority-pointer test

A short conditional pointer to ordinary documentation is justified when all of these are true:

1. the repository explicitly designates the document as the authority or source of truth;
2. a recognizable class of changes must conform to it;
3. agents are not guaranteed to open it before making those changes; and
4. drift would be plausible if the pointer were absent.

Write only the condition and pointer, for example: “When changing the public UI, follow `DESIGN.md` as the visual source of truth.” Keep the actual design rules in `DESIGN.md`.

## Destination matrix

| Information | Preferred destination |
|---|---|
| Shared, stable, non-obvious repository constraint | Root `AGENTS.md` or canonical host file |
| Constraint for one subtree | Nearest nested instruction file or supported path rule |
| Long or occasional procedure | Skill |
| Deterministic requirement | Script, hook, test, linter, CI, or settings |
| Architecture/product knowledge | README, docs, ADR, schema, or code |
| Volatile inventory | Runtime discovery or generated artifact |
| Personal/private routing | Ignored local overlay or private system |
| Fact obvious before the decision point from manifests or source | Nothing |

## Failure-severity ordering

When several candidates compete for a small context budget, prefer them in this order:

1. trust, authorization, secret, and destructive-operation boundaries;
2. canonical-source versus generated-output boundaries;
3. wrappers or validation paths whose bypass changes behavior;
4. anti-convention architecture traps;
5. conditional pointers to declared authorities;
6. generic tooling or repository facts, which are normally rejected.

This is an ordering, not a quota. Retain every candidate that passes the admission test, but do not let an obvious stack reminder displace a rule whose omission can destroy or silently overwrite work.

## Writing form

Prefer one condition, one action, and one reason:

> When changing database authorization, run the disposable-database integration suite because unit tests do not exercise row-level isolation.

Avoid:

- vague roles or personas;
- universal `always` rules that apply only occasionally;
- repeated project summaries;
- large code-style examples when a formatter or neighboring code is authoritative;
- copying numeric limits that a validator already enforces;
- duplicated rules for emphasis.

## Removal test

For every final bullet, complete this sentence:

> Removing this rule would likely cause an agent to ___ because the repository does not otherwise reveal ___ before the decision point.

If the sentence cannot be completed without speculation, remove or relocate the rule.
