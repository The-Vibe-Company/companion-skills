# Create mode

Use this mode when the repository has no substantive instruction system.

## Goal

Produce the smallest useful topology from current repository evidence. Do not invent a comprehensive onboarding manual and do not create files merely because the skill was invoked.

## Procedure

1. Run the cold inventory and inspect executable sources: manifests, CI, scripts, tests, contributor docs, security policies, architecture decisions, and source boundaries.
2. Build the evidence ledger before drafting instructions.
3. Identify costly or dangerous choices an agent cannot reliably infer before acting, such as a nonstandard validation wrapper, an unusual generated-file boundary, a security invariant, or a known architecture trap.
4. Reject facts already obvious at the decision point from manifests, standard tooling, or the files an agent will necessarily inspect. Do not reject an anti-convention trap just because the correct topology becomes obvious after opening a file the agent may never know to inspect.
5. Treat a repository document that explicitly declares itself the source of truth as a candidate pointer when agents are not guaranteed to inspect it before the affected class of change. Link to it conditionally; do not copy or summarize it.
6. Check the evidence ledger explicitly for trust/security boundaries, source-versus-generated ownership, required wrappers, anti-convention traps, and authoritative pointers. Record an admission or rejection reason for every discovered item in those classes.
7. Prefer those concrete failure boundaries over generic reminders. A package manager shown by a root lockfile and manifest is normally obvious; an output directory that looks editable but is regenerated from canonical sources is not.
8. Choose the topology based on requested hosts and scope.
9. Draft candidates under the run directory, then cross-check that every admitted ledger row appears exactly once in the proposed instruction chain.
10. Run the static linter and resolve errors.
11. Present the proposal, including the option to create no file.
12. Apply only after approval, then run repository checks.

## Create-mode decision report

Explain:

- why persistent context is or is not justified;
- the exact mistake each retained rule prevents;
- why each rule belongs at root or in a subtree;
- what was deliberately left to code, docs, CI, hooks, or skills;
- how the proposal will be evaluated after real use.

## Common failure

A generated repository overview often looks useful while adding facts the agent could discover itself. Treat overview text as rejected by default. A short pointer is justified only when it directs the agent away from a known wrong authority or expensive path.

Framework conventions need special care. If the conventional location or workflow is intentionally absent and following the convention would create a competing owner, duplicate configuration, or bypass a wrapper, a one-line prohibition can be justified even though repository exploration could eventually reveal the design.
