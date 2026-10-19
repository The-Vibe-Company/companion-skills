# Skill Refinery

Skill Refinery improves an existing Agent Skill and proves whether its real outputs became better.

It does not accept a rewrite because the prompt looks cleaner or because one model assigns it a higher style score. It snapshots the current skill, establishes a behavioral baseline, makes a bounded candidate edit, evaluates held-out cases, rejects ties and regressions, and presents the winning candidate for approval.

## Why it is different

- Outcome quality is the objective; structural quality is a gate.
- The baseline is the current best skill, not merely an agent with no skill.
- Tuning cases guide edits while held-out cases decide acceptance.
- Candidate authors do not see held-out prompts.
- Independent or blind judging is used when the host supports it.
- The installed target is never changed during experiments.
- Hosts without subagents get an honest sanity check, not a fake benchmark.

## The method

The loop is inspired by [Karpathy's Autoresearch](https://github.com/karpathy/autoresearch): establish a baseline, modify one trainable asset, run a fixed experiment, log the result, and keep or discard the change. It also builds on [Darwin Skill](https://github.com/alchaincyf/darwin-skill) and [Microsoft SkillOpt](https://github.com/microsoft/SkillOpt).

Skill Refinery adapts the idea for a harder setting. Agent Skills rarely have one trustworthy scalar metric, so it uses a frozen outcome contract and a lexicographic result vector: critical gates, held-out task success, regressions, consistency, cost, and complexity.

## Install

Copy the `refine-skill-tools` directory into any Agent Skills-compatible skill root, or install it with the package mechanism supported by your agent host.

The only required file is `SKILL.md`. The bundled Python helpers are optional and use only the standard library.

## Use

Ask naturally:

```text
Improve this skill and make its results more reliable.
Optimize the writing quality produced by this SKILL.md.
This skill looks fine but its reports are generic—make it better and prove it.
Continue the last Skill Refinery run.
```

Optional helpers:

```bash
python scripts/prepare_run.py /path/to/skill --output-root .skill-refinery/runs
python scripts/inspect_skill.py /path/to/skill
python scripts/compare_candidate.py /path/to/baseline /path/to/candidate
python scripts/record_experiment.py /path/to/run --help
```

## Safety model

Refinement happens on snapshots. Replacing the original skill, committing changes, pushing code, or publishing a package requires explicit approval.

## License

MIT
