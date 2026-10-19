# Skill System Architecture

Use this reference when the task is broader than editing one `SKILL.md`: audits, trigger fixes, overlap cleanup, public-surface refactors, legacy owner migration, workflow mining, Companion readiness, or SkillOpt-light iterations.

## Core Principle

Treat the skill system as a product surface. Every recurring kind of work should have exactly one obvious owner, and reusable narrow abilities should be capabilities that owner skills can call.

Prefer:
- one owner per user intent
- a small public surface
- clear trigger descriptions
- reversible refactors
- evidence from real prompts or transcripts

Avoid:
- multiple public skills claiming the same workflow
- folder names that reveal private context
- duplicating local policies inside shareable packages
- deleting useful skills without a snapshot
- broad rewrites when a trigger fix would solve the problem

## Owner And Capability Pattern

Use this model for medium or large skill collections:

- **Owner skill**: owns a complete user workflow end to end, including decisions, artifacts, evals, and final output.
- **Capability skill**: performs one reusable action that can be used by several owners.
- **Private reference/script**: supports an owner but should not appear as a standalone public entrypoint.

Default decision rule:
- If users naturally ask for it as a complete outcome, it is probably an owner.
- If it is a reusable step inside several outcomes, it is probably a capability.
- If it is only implementation detail, keep it as a script, reference, or local project rule.

## Standard Run Directory

For system-level work, create a run directory:

`plans/skill-creator/runs/<YYYYMMDD-HHMMSS>-<slug>/`

Use the current repository or workspace root. If the host is read-only, use a temp workspace and report the path.

Common artifacts:
- `inventory.md`: current skill surface, public owners, capabilities, and notable metadata
- `usage-evidence.md`: bounded conversation evidence from Codex/Claude histories
- `frictions.md`: observed trigger failures, overlaps, dormant skills, confusing names, and evidence
- `proposal.md`: recommended changes and patch order
- `patch-report.md`: what changed, what was intentionally left alone, and why
- `eval-report.md`: validation prompts, results, and residual risk
- `skillopt-report.md`: hypothesis, baseline, candidate, evidence, and decision
- `rejected-edits.jsonl`: rejected candidate edits and lessons

Only create the artifacts that are useful for the requested scope. Do not generate paperwork for a one-line trigger fix.

## Audit Mode

Use audit mode when the user asks for a broad pass on skills.

Prefer `scripts/audit_skill_system.py` for the first inventory pass:

```bash
python scripts/audit_skill_system.py --skill-root <path-to-skills> --out <run-dir>
```

Steps:
1. Inventory skill roots and list `SKILL.md` files.
2. Parse `name`, `description`, optional package metadata, references, scripts, and evals.
3. Identify owners, capabilities, private helpers, duplicates, gaps, and dormant surfaces.
4. Look for description collisions: two skills that would trigger for the same prompt.
5. Check portability: local paths, private organizations, secrets, host-only fields, and unconfigured dependencies.
6. Write `inventory.md`, `frictions.md`, and `proposal.md`.

Default `proposal.md` structure:

```md
## Recommendation
## Current Public Surface
## What To Simplify Now
## What Not To Merge Now
## Suggested Patch Order
## Bottom Line
```

Do not recommend merges based only on similar folder names. Require evidence from descriptions, real user prompts, transcripts, or repeated workflow shape.

## Fix Mode

Use fix mode when the user reports one concrete skill problem.

Steps:
1. Restate the problem as a trigger failure, behavior failure, artifact-contract failure, dependency failure, or ownership failure.
2. Identify the smallest likely target skill and file.
3. Gather evidence from the skill text, references, evals, and available recent conversation context.
4. Write a scoped `proposal.md` if the fix is non-trivial.
5. Apply the smallest coherent patch after approval when approval is required.
6. Run the workspace setup/install command if the local project requires it.
7. Record verification in `patch-report.md` or `eval-report.md`.

Prefer:
- frontmatter `description` edits for trigger mismatches
- explicit protected invariants for repeated architecture drift
- artifact-contract edits for output shape drift
- scripts for deterministic repeated steps

Avoid:
- broad rewrites for narrow trigger problems
- moving ownership without evidence
- silently adding non-portable dependencies

## Refactor Mode

Use refactor mode for merges, splits, retirements, renames, public/private surface changes, or legacy owner migration.

Steps:
1. Build the current inventory.
2. Propose the new public surface and the owner/capability split.
3. Explain what each retired or merged skill becomes: owner, capability, reference, script, or archive.
4. Snapshot retired skills under `plans/skill-creator/legacy/<skill-name>-<timestamp>/`.
5. Apply the approved patch.
6. Run the workspace setup/install command if present.
7. Record the resulting surface and residual risks.

Approval is required before:
- deleting a live skill
- merging two public owners
- de-publicizing a skill
- changing a skill name used by other tools or manifests
- publishing or replacing a package in a shared registry

## Workflow Mining Mode

Use workflow mining when the user asks what should become a skill.

Look for repeated manual work across conversations, scripts, or recent project history. A workflow is a good skill candidate when it has:
- repeated user intent
- a clear input shape
- a clear output shape
- a reusable process
- identifiable dependencies
- objective or human-reviewable success criteria

Before creating a new public skill, check whether an existing owner should simply be extended. If no owner exists, create the smallest owner skill that covers the recurring workflow.

## Usage History Mode

Use usage history mode when the user asks how a skill has actually behaved in Codex or Claude conversations, why it failed, whether it triggered correctly, or how to update the skill from real usage.

Prefer `scripts/analyze_usage_history.py` for the evidence pass:

```bash
python scripts/analyze_usage_history.py \
  --skill <skill-name> \
  --days 30 \
  --out <run-dir>
```

The script reads local Codex and Claude history only, then writes:
- `usage-evidence.md`: matched sessions, bounded snippets, and signal counts
- `frictions.md`: likely trigger, behavior, correction, or packaging issues
- `proposal.md`: evidence-backed patch ideas and validation plan
- `usage-summary.json`: machine-readable counts

Default flow:
1. Run the usage analysis for one target skill at a time.
2. Read `usage-evidence.md` and ignore snippets that are merely adjacent keyword matches.
3. Treat user corrections as higher-quality evidence than assistant self-assessments.
4. Convert repeated failures into one narrow hypothesis.
5. Patch only one target file with a bounded SkillOpt-light edit.
6. Turn representative snippets into sanitized eval prompts.
7. Keep at least one matched snippet held out for acceptance.

Do not paste private transcripts into a shared skill package. Generalize the lesson, sanitize examples, and keep raw evidence in the local run directory.

## SkillOpt Light Mode

Use this mode when a skill should improve through evidence but a full automated optimizer is heavier than needed.

Required loop:
1. Pick one target skill.
2. Pick one target file.
3. Snapshot the current file before editing under `baseline/<target-skill>/<target-file-relative-to-skill-dir>`.
4. State one hypothesis.
5. Write 2-4 tuning prompts and 1-3 held-out prompts.
6. Apply a bounded candidate patch.
7. Compare the candidate against the baseline.
8. Accept only strict held-out improvement.
9. Reject ties.
10. If rejected, tied, or incomparable, restore the target file from the baseline snapshot.
11. Log rejected edits in `rejected-edits.jsonl`.
12. Write `skillopt-report.md`.

Allowed in one iteration:
- 4-8 bullet or paragraph changes
- one new example
- one sharper artifact contract
- one eval improvement
- one small deterministic script patch

Avoid in one iteration:
- full rewrites
- simultaneous frontmatter, body, references, evals, and scripts changes
- adding multiple new modes at once
- optimizing subjective taste without human review

Rejected edit JSONL fields:
- `timestamp`
- `target_skill`
- `target_file`
- `hypothesis`
- `patch_summary`
- `held_out_prompt`
- `failure_reason`
- `lesson`

If no candidate is rejected, write one no-op record with `failure_reason: "none"` so the artifact remains checkable.

## Deep Validation Mode

Use the full eval workflow in the main `SKILL.md` when the change matters enough that "looks better" is not a sufficient standard:
- trigger fixes affecting an owner skill
- changes to public skill ownership
- changes to artifact contracts or approval gates
- refactors where the old version may still look plausible

Minimum validation:
1. State the hypothesis.
2. Snapshot the baseline.
3. Write realistic prompts close to how the user actually asks.
4. Run paired isolated agent/subagent runs for candidate and baseline when available.
5. Keep outputs isolated.
6. Strengthen expectations while runs execute.
7. Grade each run.
8. Aggregate `benchmark.json`, `benchmark.md`, and a human review artifact.
9. Do an analyst pass before deciding the next patch.
10. Rerun after the smallest real fix.

If the host lacks subagents, run the prompts manually and label the result as a sanity check rather than a benchmark.

## Companion Readiness

Before publishing a skill package:
- Ensure `SKILL.md` has portable frontmatter and no secrets.
- Ensure `companion.json` contains title, version, notes, changelog, dependencies, environment metadata, and command summaries when appropriate.
- Keep secret values out of the package.
- Check that dependencies refer to package names or skill names, not local absolute paths.
- Run local validation scripts if present.
- Confirm whether the user wants personal, organization, or public scope.
- Publish only after explicit approval.

## Output Format

For system-level changes, report:
- what changed
- what was removed, merged, archived, or left alone
- where any legacy snapshot lives
- whether the setup/install refresh ran
- what was validated
- remaining risks or follow-up evals
