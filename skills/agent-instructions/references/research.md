# Research basis

Last verified: 2026-08-04

This reference explains the design choices behind the skill. It is not a universal template, and observational frequency is not evidence that a category improves agent performance.

## Official guidance

- [OpenAI Codex AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md): hierarchical discovery, root-to-working-directory composition at run start, closer-scope precedence, and a default aggregate project-document limit of 32 KiB.
- [Anthropic Claude Code memory](https://code.claude.com/docs/en/memory): `CLAUDE.md` as context, import support, scoped rules, and guidance to keep files concise and specific.
- [Anthropic Claude Code best practices](https://code.claude.com/docs/en/best-practices): include commands, nonstandard conventions, testing expectations, and known gotchas; exclude information the agent can infer and long tutorials.
- [GitHub Copilot CLI custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions) and [support matrix](https://docs.github.com/en/copilot/reference/custom-instructions-support): repository-wide, path-specific, and agent instruction surfaces with host-dependent discovery and no general precedence across every family.
- [AGENTS.md convention](https://agents.md/): open cross-agent format.
- [OpenAI custom Code Review rules](https://learn.chatgpt.com/blog/custom-code-review-rules-for-codex): root versus nested placement and behavioral evaluation across coverage, restraint, retention, and actionability.

The practical synthesis is progressive scope: shared constraints at root, specialized constraints near their subtree, procedures in skills, and deterministic enforcement in executable mechanisms.

## Descriptive studies: context debt is real

[Agent READMEs: An Empirical Study of Context Files for Agentic Coding](https://arxiv.org/abs/2511.12884) studied 2,303 files from 1,925 repositories. It found that these files are often long and difficult to read, usually use a shallow hierarchy, and are commonly changed through small additions with few deletions. The paper names the resulting maintenance problem “context debt.”

[Context Engineering for AI Agents in Open-Source Software](https://arxiv.org/abs/2510.21413) examined adoption and evolution across open-source repositories. It found no stable universal content structure and identified descriptive, prescriptive, prohibitive, explanatory, and conditional writing styles. These observations describe current practice; they do not prove which categories improve task outcomes.

[GitHub's analysis of more than 2,500 agent files](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/) favors executable commands, explicit boundaries, concrete examples, and iterative growth. Its examples focus heavily on specialized GitHub agents, so do not turn its suggested sections into a mandatory repository template.

## Effect studies: results conflict

[On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents](https://arxiv.org/abs/2601.20404) compared Codex runs across 124 pull requests in 10 repositories. It associated `AGENTS.md` presence with lower median runtime and fewer output tokens while reporting comparable task-completion behavior. The study focused on efficiency, one agent family, and relatively small changes.

[Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?](https://arxiv.org/abs/2602.11988) found no general success-rate improvement and more than 20 percent higher inference cost in its settings. Developer-written files modestly outperformed generated files, while generated files often added redundant overviews. Agents followed the context but explored and tested more without reliably solving more tasks.

[Do Context Files Help Coding Agents? A Two-Agent Ablation Study on Real Repositories](https://arxiv.org/abs/2607.27250) compared no context, always-on context, and selective context across 288 evaluated runs, 17 tasks, three Python repositories, Claude Code, and Codex. It found no measurable correctness effect, but did find a narrow process benefit where a warning about a very slow test suite reduced blind full-suite runs. Its limited repository and task sample prevents universal conclusions.

## Other relevant evidence

- [IHEval](https://aclanthology.org/2025.naacl-long.425/) shows that conflicting instructions sharply reduce reliable hierarchy following.
- [Lost in the Middle](https://arxiv.org/abs/2307.03172) shows that models can underuse relevant information buried in long context.
- [OpenAI harness engineering](https://openai.com/index/harness-engineering/) argues for a short map into structured, mechanically maintained repository knowledge instead of an always-loaded manual.

## Derived principles

1. Minimal nonstandard requirements are a stronger default than exhaustive repository context.
2. Generated overviews should be rejected unless they prevent a demonstrated navigation error.
3. A rule about an expensive command or hidden trust boundary can be valuable even when generic context is not.
4. Conflicts and duplicates deserve active removal.
5. Existing human-authored rules should be preserved only after verification, not automatically discarded or automatically trusted.
6. Effectiveness must be evaluated on representative tasks; file length is only a maintenance signal.
7. Research and host semantics are versioned dependencies. Keep a verification date and refresh them before major package releases.
8. Repository readiness depends on discoverable authorities, executable guardrails, and feedback loops—not the existence of a prescribed set of Markdown files.
