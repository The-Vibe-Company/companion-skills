# Rebuild mode

Use this mode when substantive root or nested instructions already exist, or when the user asks to audit, reduce, restructure, migrate, or recreate them.

## Isolation rule

Do not read the bodies of existing instruction files until the cold candidate exists. File names, sizes, hashes, symlink targets, import edges, and nesting locations may be recorded during the cold pass.

If the agent already saw the old content earlier in the conversation, disclose that the cold pass is contaminated. Continue, but label the limitation in the decision report.

## Procedure

1. Snapshot metadata and content hashes with `snapshot_instruction_stack.py`.
2. Run the cold inventory with instruction-body reads disabled.
3. Build the evidence ledger from the repository and draft the cold candidate.
4. Save the candidate before opening legacy instruction bodies.
5. Read the complete current instruction chain, including imports, symlinks, overrides, path-specific rules, and setup scripts that recreate them.
6. Split old text into individual rules and classify each one:
   - **keep** — verified, non-obvious, correctly scoped, and worth persistent context;
   - **move** — useful but belongs in a nested file, skill, normal doc, or private overlay;
   - **automate** — should become a hook, test, script, linter, CI gate, or configuration;
   - **private** — contains personal, customer, account, database, secret, or machine-specific context;
   - **confirm** — plausible human intent that current repository evidence cannot verify;
   - **delete** — stale, duplicated, generic, contradictory, inferrable, or without a concrete omission risk.
7. Merge only verified `keep` rules into the cold candidate. Do not preserve text merely to minimize the diff.
8. Write the semantic diff and migration plan.
9. Run static validation on the final candidate.
10. Present the candidate and unresolved `confirm` decisions before applying.

## Migration plan requirements

Include:

- exact files created, replaced, moved, or removed;
- symlink and import direction before and after;
- nested-scope impact for representative paths;
- setup or installer scripts that must change with the topology;
- dirty-worktree collisions;
- commands to validate the migration;
- a rollback path that restores the previous stack.

## Debt report smells

Look for repeated sections, generic style advice, product summaries, file tours, stale commands, nonexistent paths, append-only incident rules, private identifiers, personal tool routing, copied documentation, contradictions between hosts, root rules that affect only one subtree, and deterministic requirements that are not enforced.

