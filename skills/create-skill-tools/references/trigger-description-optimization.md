# Trigger Description Optimization

Use this when a skill is functionally good but does not trigger reliably, triggers in the wrong contexts, or competes with adjacent skills.

## Step 1: Generate Trigger Eval Queries

Create 20 eval queries as JSON, mixing should-trigger and should-not-trigger cases:

```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "another prompt", "should_trigger": false}
]
```

The queries must be realistic and concrete. Include files, backstory, expected output shape, competing skills, typos, casual phrasing, and near misses. Avoid abstract prompts like `"Format this data"` or obviously irrelevant negative cases.

For should-trigger queries, cover different phrasings of the same intent and cases where the user does not explicitly name the skill.

For should-not-trigger queries, focus on tricky adjacent tasks that share keywords but need another skill or no skill.

## Step 2: Review With The User

Present the eval set for review using `assets/eval_review.html`:

1. Read the template.
2. Replace `__EVAL_DATA_PLACEHOLDER__` with the JSON array.
3. Replace `__SKILL_NAME_PLACEHOLDER__` with the skill name.
4. Replace `__SKILL_DESCRIPTION_PLACEHOLDER__` with the current description.
5. Open the generated HTML or write a static file the user can open.
6. Use the exported `eval_set.json` for the optimization loop.

This review matters because poor eval queries produce poor router descriptions.

## Step 3: Run The Optimization Loop

If the host has the required local CLI for `scripts/run_loop.py`, run:

```bash
python -m scripts.run_loop \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <model-id-powering-this-session> \
  --max-iterations 5 \
  --verbose
```

Use the model powering the current session when possible so the triggering test matches the user's real environment.

The loop splits the eval set into train and held-out test, evaluates the current description multiple times, proposes improvements, and returns the best description by held-out score.

If the host cannot run the script, do a manual version:
1. Score the current description against the eval queries.
2. Identify false positives and false negatives.
3. Rewrite the description to clarify when the skill should and should not trigger.
4. Re-score on held-out queries.
5. Apply only if the new description is strictly better or fixes an important routing bug.

## How Skill Triggering Works

Skill metadata is the router. The `description` should describe:
- user intents that should trigger the skill
- contexts where this skill should win over adjacent skills
- common casual phrasing
- important negative boundaries

Good eval queries are substantive enough that the agent would benefit from using a skill. Very small one-step prompts often do not trigger a skill even when keywords match.

## Step 4: Apply The Result

Update the `description` field in `SKILL.md` frontmatter. Show the before/after and report the scores or manual evidence.
