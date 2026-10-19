# SkillOpt Discipline

Use this when improving an existing skill or building a skill that will be iterated over time.

## Core Idea

Treat `SKILL.md` and its reference files as trainable external state for a frozen agent. The goal is not to write a perfect long prompt once. The goal is to make small, validated edits that survive realistic tasks.

## Operating Rules

1. **One target file per iteration.** Pick `SKILL.md` or one reference/script. Do not rewrite the whole skill unless it is unusable.
2. **Bound the edit.** Prefer 4-8 bullets, paragraphs, or small code paths changed per pass.
3. **Protect invariants.** Keep a short protected section for decisions that should not be overwritten by fast edits.
4. **Use held-out evals.** Accept an edit only when it improves a held-out or previously unused test. Reject ties.
5. **Log rejected edits.** Keep the reason an edit was rejected; it becomes negative feedback for the next pass.
6. **Keep deployment compact.** Move bulky examples and fast-changing data to references, artifacts, or eval workspaces.
7. **Separate router from body.** Test that the frontmatter `description` triggers the skill, not only that the body is good after activation.

## Fast And Slow State

Slow state:
- protected invariants
- stable workflow
- role boundaries
- artifact contracts
- safety rules

Fast state:
- examples
- recent user feedback
- failed edits
- benchmark outputs
- source corpora

Do not bloat the deployed skill with fast-state logs. Keep them in the workspace, evals, or references that are loaded only when useful.

## Acceptance Gate

Before accepting a skill edit, record:
- hypothesis
- target file
- exact diff summary
- eval prompts used
- baseline behavior
- candidate behavior
- accepted or rejected
- why

Accept only when the candidate is strictly better on the validation gate or fixes a correctness/safety bug that the gate did not yet cover. If the result is merely different or equally good, reject and keep the baseline.

## Practical Defaults

For a normal skill improvement:
- snapshot the baseline
- edit one file
- run 2-3 realistic prompts
- compare against the baseline, not against no skill
- update evals if the failure mode was not measured
- run setup/install scripts required by the host workspace

For subjective skills such as writing, design, or strategy:
- combine structured checks with human review
- score specificity, artifact completeness, and avoided failure modes
- do not pretend style quality is fully captured by expectations
