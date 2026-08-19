# Platform semantics

Last verified: 2026-08-04

Read the current vendor documentation again when behavior is safety-critical or the verification date is old.

## OpenAI Codex

Source: [OpenAI — Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

- Codex discovers project instructions from the project root toward the current working directory.
- At each level it checks the supported override, regular, and configured fallback names.
- Instructions are concatenated from broad to specific; closer guidance appears later and therefore has precedence.
- The aggregate project-document budget is configurable and defaults to 32 KiB.
- Put repository-wide rules at root and specialized rules near the relevant subtree.
- The regular project chain is resolved once at run start from repository root to the startup working directory. Do not assume that merely editing a deeper file injects that directory's `AGENTS.md` into an already-started root workflow.

When auditing a path, evaluate the complete loaded chain rather than the nearest file in isolation.

## Anthropic Claude Code

Sources: [Memory](https://code.claude.com/docs/en/memory), [Best practices](https://code.claude.com/docs/en/best-practices), [Features overview](https://code.claude.com/docs/en/features-overview)

- Project `CLAUDE.md` files provide context, not deterministic enforcement.
- Claude Code supports imports such as `@AGENTS.md`.
- Ancestor project instructions load at launch; child `CLAUDE.md` files are discovered on demand when Claude reads files in that subtree.
- Child instructions may need to be rediscovered after context compaction. Use the `InstructionsLoaded` hook or `/context` when exact loading matters.
- Imports resolve relative to the importing file and may recurse up to four hops. Imports organize content but do not save context; nested files and path-scoped `.claude/rules/` provide selective loading.
- Anthropic recommends concise, specific content and uses roughly 200 lines as a maintenance warning, not a target.
- Skills are better for on-demand procedures; hooks and settings are better for deterministic behavior.
- Conflicting instructions are unsafe even when both are individually reasonable.

For a multi-host repository, prefer a shared `AGENTS.md` with a thin `CLAUDE.md` adapter unless the repository has real Claude-only instructions. A symlink is acceptable when host behavior and repository tooling preserve it, but imports make the direction explicit and leave room for a small host-specific overlay.

## GitHub Copilot and the open convention

Sources: [GitHub Copilot CLI custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions), [GitHub support matrix](https://docs.github.com/en/copilot/reference/custom-instructions-support), [AGENTS.md convention](https://agents.md/)

- GitHub tools support repository-wide, path-specific, and agent instruction files in different combinations.
- Copilot CLI may discover root, current, intermediate, and worked-file-path instruction files, including `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`.
- GitHub does not define one general precedence order across all supported instruction families. Avoid conflicts instead of depending on an assumed winner.
- Path-specific `.github/instructions/*.instructions.md` files can use `applyTo` globs.
- Support varies by GitHub surface and IDE, so do not promise one identical loading model everywhere.

## Topology defaults

### Multiple coding-agent hosts

```text
AGENTS.md       canonical shared constraints
CLAUDE.md       @AGENTS.md plus genuine Claude-only notes, usually nothing else
subtree/
  AGENTS.md     only rules unique to this subtree
  CLAUDE.md     @AGENTS.md when Claude must receive the subtree rule
```

### Claude-only repository

```text
CLAUDE.md       canonical concise constraints
.claude/rules/  path-specific Claude rules when useful
```

### No persistent context justified

Create no file. Record the decision and rely on executable repository sources.

## Migration checks

- Resolve symlinks before writing and detect loops or broken targets.
- Search setup, install, bootstrap, and CI scripts for code that recreates instruction files.
- Search all instruction variants, not only root `AGENTS.md` and `CLAUDE.md`.
- Confirm import paths relative to the importing file.
- Test representative working directories so the loaded chain matches the intended scope.
- For Claude, observe child loading with `InstructionsLoaded` or `/context` when the scope is consequential.
- For Copilot, verify the exact target surface against the current support matrix.
