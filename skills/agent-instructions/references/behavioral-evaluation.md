# Behavioral evaluation

Use behavioral evaluation for high-impact repositories, large migrations, disputed rules, or when the user asks whether the new context is actually better.

## Why

Shorter files are easier to maintain, but line-count reduction does not prove better task performance. Published studies disagree on correctness and efficiency effects, and effects can differ by agent and task.

## Conditions

Compare at least:

- **A — no context:** remove repository instruction files from the isolated evaluation workspace;
- **B — current:** use the current instruction stack exactly as loaded;
- **C — proposed:** use the candidate stack and topology.

Keep the repository commit, task, environment, tool permissions, and evaluation oracle constant. Prevent external writes such as pushes, deployments, messages, or production mutations.

## Tasks

Prefer real merged issues or representative tasks with hidden or independently defined checks. Include tasks that exercise claimed rules:

- an architecture-boundary change;
- a validation-command choice;
- a subtree-specific change;
- a security or privacy invariant;
- a normal task for which persistent context should stay out of the way.

Avoid evaluating only easy tasks that every condition passes or impossible tasks that every condition fails. The informative range may differ between agent models.

## Measures

Measure:

- correctness against tests or a golden oracle;
- adherence to non-functional invariants;
- unnecessary file reads and tool calls;
- targeted versus wasteful test execution;
- wall-clock duration;
- input/output tokens or cost when available;
- files changed outside the requested scope;
- unsupported claims in the final report.

Repeat important cells when the agent is stochastic. Report sample size and limitations.

For review or instruction rules, also grade:

- **coverage** — known violating changes are found or avoided;
- **restraint** — safe changes and valid exceptions do not trigger noise;
- **retention** — unrelated ordinary defects are still detected;
- **actionability** — the output identifies the invariant, evidence, location, and safe path.

For every proposed nested scope include one violating task, one safe task, one unrelated defect, and one cross-subtree task. Reject the scope if it does not outperform the smaller topology on a consequential measure.

## Decision rule

Adopt the proposal when it protects a concrete invariant or improves a useful process metric without a material correctness regression. If the proposal only looks cleaner, reduce it further or keep the current state until real-use evidence exists.

Do not use a broad repository overview as the intervention unless the overview itself is the hypothesis being tested.
