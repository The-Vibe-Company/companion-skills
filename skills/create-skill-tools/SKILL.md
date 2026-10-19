---
name: create-skill-tools
description: Create, modify, audit, refactor, package, publish, and optimize
  agent skills. Use when users want to create a skill from scratch, edit or
  optimize an existing skill, run evals, benchmark skill performance, analyze
  Codex or Claude conversation history for real skill usage, optimize a skill
  description, fix skill triggers, merge or split overlapping skills, enforce
  MECE skill ownership, design skill file formats, migrate legacy skill-system
  owners, prepare Companion-compatible skill packages, or build a SkillOpt-style
  improvement loop.
metadata: {}
---

<!-- skillpack:usage:start -->
## Skillpack runtime

Usage is observed locally by skillpack-runtime when installed through Skillpack. Package: da943979-69aa-4031-841f-a629d25233f6@1.1.1, origin: https://thecompanion.sh.
Do not send activation reports, run tracking commands, or install hooks during this skill's execution. Setup and updates belong to Skillpack. Continue the task when collection is unavailable. SKILLPACK_TELEMETRY=0 disables collection for this session.
<!-- skillpack:usage:end -->

# Skill Creator

Mega skill for creating, improving, auditing, refactoring, evaluating, packaging, and publishing portable agent skills.

This skill owns skill-system work end to end. When the user asks to audit skills, fix triggers, merge or split skills, codify recurring workflows, optimize a skill loop, reason about skill file format, or make the local skill surface cleaner, stay here.

Read `references/skill-system-architecture.md` when the task involves a broad skill audit, one concrete skill friction, MECE ownership, public-surface refactors, legacy-skill migration, workflow mining, Companion readiness, or a bounded SkillOpt-light loop.

Default loop:
- Capture the intended workflow, trigger surface, output contract, dependencies, and success criteria.
- Draft or revise the skill with a compact public contract and deeper references/scripts only when useful.
- Build realistic eval prompts, run the skill against a baseline, and draft measurable expectations while runs execute.
- Show the user qualitative outputs plus benchmark data through `eval-viewer/generate_review.py`.
- Apply bounded revisions from user feedback and benchmark failures, then repeat or expand the suite.
- After the behavior is stable, optimize the frontmatter description as the router.

Figure out where the user is in this loop and continue from there. If they already have a draft, go straight to eval/iterate. If they explicitly want a light pass, keep the loop lightweight but still preserve the durable lessons in the skill.

## Skill system ownership

Use this skill as the single owner for:
- new skill creation
- existing skill improvement
- trigger and routing fixes
- skill file format decisions
- skill audits and inventory
- MECE ownership and overlap cleanup
- public-surface refactors
- Companion package readiness
- SkillOpt light and deep eval loops
- workflow mining and usage-history analysis from repeated user requests or Codex/Claude conversations

If the user is migrating from a legacy local skill-system owner, fold the durable logic into this skill and retire the duplicate owner after explicit approval. Keep local workspace conventions in that workspace's own docs or private references, not in the shareable core package.

## Portability rules

This skill must be shareable with anyone.

- Do not hard-code personal paths, organization names, accounts, secrets, private URLs, or one user's skill surface in `SKILL.md`.
- Put host-specific behavior in clearly labeled sections, references, or scripts with safe defaults.
- Prefer relative paths inside the skill folder and configurable CLI flags for workspace roots.
- Keep dependencies and publishing metadata in `companion.json`, not in ad hoc frontmatter fields.
- When importing useful patterns from a private skill, generalize the pattern and leave behind private names.
- If a local project has its own rules, read that project's `AGENTS.md`, `CLAUDE.md`, or equivalent, then apply them as local overlay rules for that run only.

Non-negotiable shareability checks:
- A public skill package must make sense outside the creator's machine, company, repository, and account.
- The universal path is `SKILL.md` plus optional `references/`, `scripts/`, `assets/`, `evals/`, and `companion.json`. Anything else must be optional or documented.
- Private operating rules belong in local project docs, private references excluded from the package, or user-specific companion metadata.
- If a rule mentions a specific person, org, repo, vault, inbox, database, or internal tool, either generalize it or label it as a local overlay that should not be published.
- Scripts must accept explicit input/output paths and must not assume one home directory, one repo layout, one agent host, or one installed CLI unless the dependency is declared.
- Evals should use realistic but sanitized examples. Do not ship private transcripts, customer names, internal URLs, tokens, or production data as fixtures.
- Before publishing, scan `SKILL.md`, `references/`, `scripts/`, `evals/`, and `companion.json` for absolute paths, private names, secret-like strings, and host-only assumptions.
- If portability conflicts with local convenience, keep the portable package clean and document the local convenience as an overlay outside the shared skill.

Default run directory for skill-system work:

`plans/skill-creator/runs/<YYYYMMDD-HHMMSS>-<slug>/`

Create only the artifacts that match the task size, but prefer these names for consistency:
- `inventory.md`
- `frictions.md`
- `proposal.md`
- `patch-report.md`
- `eval-report.md`
- `skillopt-report.md`
- `rejected-edits.jsonl`

For broad refactors, deletions, merges, or de-publicizing skills, present the proposal first and wait for explicit approval unless the user already clearly gave that approval in the current request.

## SkillOpt iteration discipline

When improving an existing skill, default to SkillOpt-style iteration unless the user explicitly asks for a broad rewrite.

Read `references/skillopt.md` when the work involves optimization, repeated evals, self-improvement, benchmark deltas, trigger tuning, or turning user feedback into durable skill changes.

Core rules:
- edit one target file per iteration when possible
- keep edits bounded, usually 4-8 bullets/paragraphs or a small script patch
- protect stable invariants from fast feedback
- compare against a baseline snapshot, not only against no skill
- accept only strict improvements on held-out or previously unused eval prompts
- reject ties and log rejected edits as future negative feedback
- keep deployed skills compact; move fast-changing examples and logs to references or workspaces
- test the frontmatter `description` as a routing surface, not only the body after activation

## Communicating with the user

People using this skill range from non-technical operators to experienced engineers. Match the user's vocabulary and explain terms briefly when the context suggests they may not know them.

- "evaluation" and "benchmark" are borderline, but OK
- for "JSON" and "expectation" you want to see serious cues from the user that they know what those things are before using them without explaining them

When in doubt, define the term in one short phrase and keep moving.

---

## Creating a skill

### Capture Intent

Start by understanding the user's intent. The current conversation might already contain a workflow the user wants to capture (e.g., they say "turn this into a skill"). If so, extract answers from the conversation history first — the tools used, the sequence of steps, corrections the user made, input/output formats observed. The user may need to fill the gaps, and should confirm before proceeding to the next step.

1. What should this skill enable Claude to do?
2. When should this skill trigger? (what user phrases/contexts)
3. What's the expected output format?
4. Should we set up test cases to verify the skill works? Skills with objectively verifiable outputs (file transforms, data extraction, code generation, fixed workflow steps) benefit from test cases. Skills with subjective outputs (writing style, art) often don't need them. Suggest the appropriate default based on the skill type, but let the user decide.

### Interview and Research

Proactively ask questions about edge cases, input/output formats, example files, success criteria, and dependencies. Wait to write test prompts until you've got this part ironed out.

Check available MCPs - if useful for research (searching docs, finding similar skills, looking up best practices), research in parallel via subagents if available, otherwise inline. Come prepared with context to reduce burden on the user.

### Write the SKILL.md

Based on the user interview, fill in these components:

- **name**: Skill identifier
- **description**: When to trigger, what it does. This is the primary triggering mechanism - include both what the skill does AND specific contexts for when to use it. All "when to use" info goes here, not in the body. Note: currently Claude has a tendency to "undertrigger" skills -- to not use them when they'd be useful. To combat this, please make the skill descriptions a little bit "pushy". So for instance, instead of "How to build a simple fast dashboard to display internal Anthropic data.", you might write "How to build a simple fast dashboard to display internal Anthropic data. Make sure to use this skill whenever the user mentions dashboards, data visualization, internal metrics, or wants to display any kind of company data, even if they don't explicitly ask for a 'dashboard.'"
- **compatibility**: Required tools, dependencies (optional, rarely needed)
- **the rest of the skill :)**

### Skill Writing Guide

#### Anatomy of a Skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

#### Shareable Skill Package Format

Use this layout when a skill should travel across Codex, Claude Code, Companion, or another agent host:

```
skill-name/
├── SKILL.md
├── companion.json        # Optional, publishing metadata and dependencies
├── evals/evals.json      # Optional, realistic prompts and expectations
├── scripts/              # Optional, deterministic helpers with CLI flags
├── references/           # Optional, longer playbooks loaded on demand
└── assets/               # Optional, templates or static inputs
```

Keep `SKILL.md` as the stable public contract:
- `name` and `description` are the only universally required frontmatter fields.
- `description` is the router. It should say when to use the skill, competing contexts where it should win, and common user phrasings.
- The body should contain the core workflow, protected invariants, approval gates, and pointers to deeper references.
- Long examples, local policies, private conventions, eval logs, and volatile research belong outside `SKILL.md`.

#### Clean Skill Structure

For a polished skill, use this spine unless the domain calls for something simpler:
- **frontmatter**: pushy trigger description plus scope boundaries such as "For X, see Y"
- **context intake**: read one shared context source when a family of skills needs the same product, project, or user background
- **workflow**: ordered steps, decision points, approval gates, and deterministic scripts
- **output contract**: exact sections, fields, file names, or artifacts the user should receive
- **quality guardrails**: common mistakes, self-checks, safety rules, and no-fabrication rules
- **related skills**: explicit handoffs so neighboring skills do not overlap silently
- **evals**: realistic happy-path, casual-phrasing, edge-case, and wrong-owner prompts in `evals/evals.json`

Use `companion.json` for distribution concerns:
- package title, version, notes, changelog, dependencies, environment variables, secrets metadata, and command summaries
- no secret values
- no local absolute paths
- dependencies declared by package or skill name, with clear notes when optional

Use scripts when a step is deterministic, repetitive, or easy to get subtly wrong. Scripts should accept paths as arguments, write outputs under a caller-provided directory, and avoid assuming a specific username, home directory, repository, or organization.

Use references when instructions are too long for the entrypoint. The `SKILL.md` must tell the agent exactly when to read each reference so progressive disclosure still works.

#### Progressive Disclosure

Skills use a three-level loading system:
1. **Metadata** (name + description) - Always in context (~100 words)
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** - As needed (unlimited, scripts can execute without loading)

These word counts are approximate and you can feel free to go longer if needed.

**Key patterns:**
- Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional layer of hierarchy along with clear pointers about where the model using the skill should go next to follow up.
- Reference files clearly from SKILL.md with guidance on when to read them
- For large reference files (>300 lines), include a table of contents

**Domain organization**: When a skill supports multiple domains/frameworks, organize by variant:
```
cloud-deploy/
├── SKILL.md (workflow + selection)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```
Claude reads only the relevant reference file.

#### Principle of Lack of Surprise

This goes without saying, but skills must not contain malware, exploit code, or any content that could compromise system security. A skill's contents should not surprise the user in their intent if described. Don't go along with requests to create misleading skills or skills designed to facilitate unauthorized access, data exfiltration, or other malicious activities. Things like a "roleplay as an XYZ" are OK though.

#### Writing Patterns

Prefer using the imperative form in instructions.

**Defining output formats** - You can do it like this:
```markdown
## Report structure
ALWAYS use this exact template:
# [Title]
## Executive summary
## Key findings
## Recommendations
```

**Examples pattern** - It's useful to include examples. You can format them like this (but if "Input" and "Output" are in the examples you might want to deviate a little):
```markdown
## Commit message format
**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

### Writing Style

Try to explain to the model why things are important in lieu of heavy-handed musty MUSTs. Use theory of mind and try to make the skill general and not super-narrow to specific examples. Start by writing a draft and then look at it with fresh eyes and improve it.

### Protected invariants

For skills that are likely to be iterated, add a short protected-invariants section. This section should capture non-negotiable decisions such as ownership boundaries, safety rules, artifact contracts, and approved public surfaces.

Do not let routine edits remove these invariants. If an invariant is wrong, change it deliberately and record why.

### Test Cases

After writing the skill draft, come up with realistic test prompts — the kind of thing a real user would actually say. Use 2-3 for a small/private skill and 5-7 for a public owner skill or a skill with nearby competitors.

Include a balanced eval set:
- one canonical happy path
- one casual or underspecified phrasing that should still trigger
- one edge case or domain-specific constraint
- one wrong-owner prompt that should defer to a related skill instead of doing the work
- one stateful/resume, file-input, or "make it quick" pressure test when relevant

Share them with the user: [you don't have to use this exact language] "Here are a few test cases I'd like to try. Do these look right, or do you want to add more?" Then run them.

Save test cases to `evals/evals.json`. Use `expected_output` as a prose success contract. Don't write expectations yet unless the suite already has them — you'll draft or refine expectations in the next step while the runs are in progress.

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": []
    }
  ]
}
```

See `references/schemas.md` for the full schema, including the `expectations` field.

## Running and evaluating test cases

This section is one continuous sequence — don't stop partway through. Do NOT use `/skill-test` or any other testing skill.

Put results in `<skill-name>-workspace/` as a sibling to the skill directory. Within the workspace, organize results by iteration (`iteration-1/`, `iteration-2/`, etc.) and within that, each test case gets a directory (`eval-0/`, `eval-1/`, etc.). Don't create all of this upfront — just create directories as you go.

### Step 1: Spawn all runs (with-skill AND baseline) in the same turn

For each test case, spawn two subagents in the same turn — one with the skill, one without. This is important: don't spawn the with-skill runs first and then come back for baselines later. Launch everything at once so it all finishes around the same time.

**With-skill run:**

```
Execute this task:
- Skill path: <path-to-skill>
- Task: <eval prompt>
- Input files: <eval files if any, or "none">
- Save outputs to: <workspace>/iteration-<N>/eval-<ID>/with_skill/outputs/
- Outputs to save: <what the user cares about — e.g., "the .docx file", "the final CSV">
```

**Baseline run** (same prompt, but the baseline depends on context):
- **Creating a new skill**: no skill at all. Same prompt, no skill path, save to `without_skill/outputs/`.
- **Improving an existing skill**: the old version. Before editing, snapshot the skill (`cp -r <skill-path> <workspace>/skill-snapshot/`), then point the baseline subagent at the snapshot. Save to `old_skill/outputs/`.

Write an `eval_metadata.json` for each test case (expectations can be empty for now). Give each eval a descriptive name based on what it's testing — not just "eval-0". Use this name for the directory too. If this iteration uses new or modified eval prompts, create these files for each new eval directory — don't assume they carry over from previous iterations.

```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name-here",
  "prompt": "The user's task prompt",
  "expectations": []
}
```

### Step 2: While runs are in progress, draft expectations

Don't just wait for the runs to finish — you can use this time productively. Draft quantitative expectations for each test case and explain them to the user. If expectations already exist in `evals/evals.json`, review them and explain what they check.

Good expectations are objectively verifiable and have descriptive names — they should read clearly in the benchmark viewer so someone glancing at the results immediately understands what each one checks. Subjective skills (writing style, design quality) are better evaluated qualitatively — don't force expectations onto things that need human judgment.

Update the `eval_metadata.json` files and `evals/evals.json` with the expectations once drafted. Also explain to the user what they'll see in the viewer — both the qualitative outputs and the quantitative benchmark.

### Step 3: As runs complete, capture timing data

When each subagent task completes, you receive a notification containing `total_tokens` and `duration_ms`. Save this data immediately to `timing.json` in the run directory:

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

This is the only opportunity to capture this data — it comes through the task notification and isn't persisted elsewhere. Process each notification as it arrives rather than trying to batch them.

### Step 4: Grade, aggregate, and launch the viewer

Once all runs are done:

1. **Grade each run** — spawn a grader subagent (or grade inline) that reads `agents/grader.md` and evaluates each expectation against the outputs. Save results to `grading.json` in each run directory. The grading.json expectations array must use the fields `text`, `passed`, and `evidence` (not `name`/`met`/`details` or other variants) — the viewer depends on these exact field names. For expectations that can be checked programmatically, write and run a script rather than eyeballing it — scripts are faster, more reliable, and can be reused across iterations.

2. **Aggregate into benchmark** — run the aggregation script from the skill-creator directory:
   ```bash
   python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
   ```
   This produces `benchmark.json` and `benchmark.md` with pass_rate, time, and tokens for each configuration, with mean ± stddev and the delta. If generating benchmark.json manually, see `references/schemas.md` for the exact schema the viewer expects.
Put each with_skill version before its baseline counterpart.

3. **Do an analyst pass** — read the benchmark data and surface patterns the aggregate stats might hide. See `agents/analyzer.md` (the "Analyzing Benchmark Results" section) for what to look for — things like expectations that always pass regardless of skill (non-discriminating), high-variance evals (possibly flaky), and time/token tradeoffs.

4. **Launch the viewer** with both qualitative outputs and quantitative data:
   ```bash
   nohup python <skill-creator-path>/eval-viewer/generate_review.py \
     <workspace>/iteration-N \
     --skill-name "my-skill" \
     --benchmark <workspace>/iteration-N/benchmark.json \
     > /dev/null 2>&1 &
   VIEWER_PID=$!
   ```
   For iteration 2+, also pass `--previous-workspace <workspace>/iteration-<N-1>`.

   **Cowork / headless environments:** If `webbrowser.open()` is not available or the environment has no display, use `--static <output_path>` to write a standalone HTML file instead of starting a server. Feedback will be downloaded as a `feedback.json` file when the user clicks "Submit All Reviews". After download, copy `feedback.json` into the workspace directory for the next iteration to pick up.

Note: please use generate_review.py to create the viewer; there's no need to write custom HTML.

5. **Tell the user** something like: "I've opened the results in your browser. There are two tabs — 'Outputs' lets you click through each test case and leave feedback, 'Benchmark' shows the quantitative comparison. When you're done, come back here and let me know."

### What the user sees in the viewer

The "Outputs" tab shows one test case at a time:
- **Prompt**: the task that was given
- **Output**: the files the skill produced, rendered inline where possible
- **Previous Output** (iteration 2+): collapsed section showing last iteration's output
- **Formal Grades** (if grading was run): collapsed section showing expectation pass/fail
- **Feedback**: a textbox that auto-saves as they type
- **Previous Feedback** (iteration 2+): their comments from last time, shown below the textbox

The "Benchmark" tab shows the stats summary: pass rates, timing, and token usage for each configuration, with per-eval breakdowns and analyst observations.

Navigation is via prev/next buttons or arrow keys. When done, they click "Submit All Reviews" which saves all feedback to `feedback.json`.

### Step 5: Read the feedback

When the user tells you they're done, read `feedback.json`:

```json
{
  "reviews": [
    {"run_id": "eval-0-with_skill", "feedback": "the chart is missing axis labels", "timestamp": "..."},
    {"run_id": "eval-1-with_skill", "feedback": "", "timestamp": "..."},
    {"run_id": "eval-2-with_skill", "feedback": "perfect, love this", "timestamp": "..."}
  ],
  "status": "complete"
}
```

Empty feedback means the user thought it was fine. Focus your improvements on the test cases where the user had specific complaints.

Kill the viewer server when you're done with it:

```bash
kill $VIEWER_PID 2>/dev/null
```

---

## Improving the skill

This is the heart of the loop. You've run the test cases, the user has reviewed the results, and now you need to make the skill better based on their feedback.

### How to think about improvements

1. **Generalize from the feedback.** The big picture thing that's happening here is that we're trying to create skills that can be used a million times (maybe literally, maybe even more who knows) across many different prompts. Here you and the user are iterating on only a few examples over and over again because it helps move faster. The user knows these examples in and out and it's quick for them to assess new outputs. But if the skill you and the user are codeveloping works only for those examples, it's useless. Rather than put in fiddly overfitty changes, or oppressively constrictive MUSTs, if there's some stubborn issue, you might try branching out and using different metaphors, or recommending different patterns of working. It's relatively cheap to try and maybe you'll land on something great.

2. **Keep the prompt lean.** Remove things that aren't pulling their weight. Make sure to read the transcripts, not just the final outputs — if it looks like the skill is making the model waste a bunch of time doing things that are unproductive, you can try getting rid of the parts of the skill that are making it do that and seeing what happens.

3. **Explain the why.** Try hard to explain the **why** behind everything you're asking the model to do. Today's LLMs are *smart*. They have good theory of mind and when given a good harness can go beyond rote instructions and really make things happen. Even if the feedback from the user is terse or frustrated, try to actually understand the task and why the user is writing what they wrote, and what they actually wrote, and then transmit this understanding into the instructions. If you find yourself writing ALWAYS or NEVER in all caps, or using super rigid structures, that's a yellow flag — if possible, reframe and explain the reasoning so that the model understands why the thing you're asking for is important. That's a more humane, powerful, and effective approach.

4. **Look for repeated work across test cases.** Read the transcripts from the test runs and notice if the subagents all independently wrote similar helper scripts or took the same multi-step approach to something. If all 3 test cases resulted in the subagent writing a `create_docx.py` or a `build_chart.py`, that's a strong signal the skill should bundle that script. Write it once, put it in `scripts/`, and tell the skill to use it. This saves every future invocation from reinventing the wheel.

This task is pretty important (we are trying to create billions a year in economic value here!) and your thinking time is not the blocker; take your time and really mull things over. I'd suggest writing a draft revision and then looking at it anew and making improvements. Really do your best to get into the head of the user and understand what they want and need.

### The iteration loop

After improving the skill:

1. Apply your improvements to the skill
2. Rerun all test cases into a new `iteration-<N+1>/` directory, including baseline runs. If you're creating a new skill, the baseline is always `without_skill` (no skill) — that stays the same across iterations. If you're improving an existing skill, use your judgment on what makes sense as the baseline: the original version the user came in with, or the previous iteration.
3. Launch the reviewer with `--previous-workspace` pointing at the previous iteration
4. Wait for the user to review and tell you they're done
5. Read the new feedback, improve again, repeat

Keep going until:
- The user says they're happy
- The feedback is all empty (everything looks good)
- You're not making meaningful progress

---

## Advanced: Blind comparison

For situations where you want a more rigorous comparison between two versions of a skill (e.g., the user asks "is the new version actually better?"), there's a blind comparison system. Read `agents/comparator.md` and `agents/analyzer.md` for the details. The basic idea is: give two outputs to an independent agent without telling it which is which, and let it judge quality. Then analyze why the winner won.

This is optional, requires subagents, and most users won't need it. The human review loop is usually sufficient.

---

## Description Optimization

The description field in `SKILL.md` frontmatter is the primary routing surface. After creating or improving a skill, offer to optimize the description for better triggering accuracy.

Read `references/trigger-description-optimization.md` before generating trigger evals, running `scripts/run_loop.py`, or manually improving a skill description.

---

## Host Adapters And Packaging

Read `references/host-adapters.md` when the current host lacks subagents, browser access, write access, a local CLI, or direct file presentation tools. Use `scripts/package_skill.py` when packaging a shareable `.skill` bundle.

---

## Reference files

The agents/ directory contains instructions for specialized subagents. Read them when you need to spawn the relevant subagent.

- `agents/grader.md` — How to evaluate expectations against outputs
- `agents/comparator.md` — How to do blind A/B comparison between two outputs
- `agents/analyzer.md` — How to analyze why one version beat another

The references/ directory has additional documentation:
- `references/schemas.md` — JSON structures for evals.json, grading.json, etc.
- `references/skillopt.md` — Bounded improvement discipline for existing skills.
- `references/skill-system-architecture.md` — Audits, MECE ownership, refactors, workflow mining, Codex/Claude usage-history analysis, Companion readiness, and SkillOpt-light loops.
- `references/trigger-description-optimization.md` — Router description evals and optimization workflow.
- `references/host-adapters.md` — Fallbacks for hosts without subagents, browser access, write access, or direct file presentation.

---

Repeating one more time the core loop here for emphasis:

- Figure out what the skill is about
- Draft or edit the skill
- Run isolated agent-with-skill tests against baseline prompts
- With the user, evaluate the outputs:
  - Create benchmark.json and run `eval-viewer/generate_review.py` to help the user review them
  - Run quantitative evals
- Repeat until you and the user are satisfied
- Package the final skill and return it to the user.

Please add steps to your TodoList, if you have such a thing, to make sure you don't forget. If you're in Cowork, please specifically put "Create evals JSON and run `eval-viewer/generate_review.py` so human can review test cases" in your TodoList to make sure it happens.

Good luck!
