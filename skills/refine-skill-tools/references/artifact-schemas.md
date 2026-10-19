# Artifact schemas

Use these minimal portable schemas. Hosts may add fields but should preserve the required ones.

## `run.json`

```json
{
  "schema_version": 1,
  "run_id": "20260720T140000Z-example-skill",
  "created_at": "2026-07-20T14:00:00Z",
  "source_skill": "/local/path/to/example-skill",
  "baseline_snapshot": "baseline/skill",
  "candidate_snapshot": "candidate/skill",
  "current_best": "baseline",
  "iteration": 0,
  "evaluation_mode": "benchmark"
}
```

`evaluation_mode` is one of `benchmark`, `sanity_check`, or `static_only`.

## `contract.json`

```json
{
  "intent": "Produce an implementation-ready feature specification",
  "non_goals": ["Implement the feature"],
  "critical_invariants": ["Never invent repository facts"],
  "expectations": [
    {
      "id": "acceptance-criteria",
      "kind": "objective",
      "critical": true,
      "text": "Every acceptance criterion is testable"
    }
  ],
  "subjective_dimensions": [
    {
      "id": "usability",
      "anchors": {"1": "not usable", "3": "needs editing", "5": "ready to use"}
    }
  ],
  "constraints": {"max_cost_delta_percent": 25}
}
```

## Eval case

```json
{
  "id": "ambiguous-request",
  "suite": "held_out",
  "prompt": "Turn these rough notes into a feature spec",
  "files": [],
  "expectation_ids": ["acceptance-criteria"]
}
```

Do not place private inputs directly in a case file when paths or sanitized fixtures are sufficient.

## Execution result

```json
{
  "case_id": "ambiguous-request",
  "version": "candidate-1",
  "output_paths": ["outputs/candidate-1/ambiguous-request/spec.md"],
  "duration_seconds": 42.1,
  "tokens": null,
  "errors": [],
  "notes": []
}
```

Use `null` for unavailable metrics.

## Judge result

```json
{
  "case_id": "ambiguous-request",
  "labels": {"A": "hidden", "B": "hidden"},
  "expectations": [
    {"id": "acceptance-criteria", "passed_a": true, "passed_b": false, "evidence": "..."}
  ],
  "subjective_scores": {
    "usability": {"a": 5, "b": 3, "evidence": "..."}
  },
  "winner": "A",
  "critical_regressions": [],
  "confidence": 0.86
}
```

Store the A/B version mapping separately until judging is complete.

## `decisions.jsonl`

One JSON object per experiment:

```json
{"iteration":1,"hypothesis":"Add a checkable completion gate","target_file":"SKILL.md","patch_summary":"Added a three-item artifact gate","held_out_result":"won 2, tied 0, lost 0","decision":"accepted","promoted_snapshot":"best/candidate-1","reason":"Strict improvement with no critical regression"}
{"iteration":2,"hypothesis":"Add a mandatory second reviewer","target_file":"SKILL.md","patch_summary":"Added unconditional review pass","held_out_result":"tied 2","decision":"rejected","reason":"No output gain; cost increased"}
```

Allowed decisions: `accepted`, `rejected`, `inconclusive`, `blocked`.

## `results.tsv`

Keep a human-scannable append-only experiment ledger alongside `decisions.jsonl`:

```text
timestamp\titeration\tstatus\ttarget_file\tbaseline_result\tcandidate_result\tevaluation_mode\thypothesis\treason
2026-07-20T14:10:00Z\t1\tkeep\tSKILL.md\t3/5\t5/5\tbenchmark\tAdd artifact gate\tStrict held-out improvement
```

Allowed statuses are `keep`, `discard`, `crash`, and `inconclusive`. Do not edit prior rows to hide failed experiments.

## `report.md`

```markdown
# Refinement result

Verdict: IMPROVED

## Result quality
## Skill quality
## Accepted change
## Rejected experiments
## Evidence and regressions
## Winning candidate
## Remaining risks
## Approval required
```
