# Host Adapters

Use this when running skill evals or packaging in a host that lacks subagents, browser access, write access, or a specific local CLI.

## Generic Fallbacks

- If subagents are available, use paired isolated runs for candidate and baseline.
- If subagents are unavailable, run the test prompts manually and label the result as a sanity check, not a benchmark.
- If a browser is unavailable, generate static HTML artifacts or present outputs inline.
- If a filesystem path is read-only, copy the skill to a temporary writable directory and package from the copy.
- If timing or token usage is unavailable, record that gap clearly and keep the benchmark structure.

## Claude.ai-Style Hosts

The core loop remains draft, test, review, improve, repeat.

Adaptations:
- Run test cases manually one at a time.
- Skip paired baseline benchmarks unless the host provides isolated agent runs.
- Present results directly in conversation or as downloadable files.
- Focus on qualitative feedback when quantitative grading is impractical.
- Skip description optimization scripts if the required local CLI is unavailable.
- Preserve the original skill name and directory name when updating an existing skill.

## Cowork-Style Hosts

Cowork-style hosts usually have subagents but may not have browser/display access.

Adaptations:
- Use subagents for paired with-skill and baseline runs.
- Generate the eval viewer as a static HTML file when no browser server is available.
- Ask the user to review the static viewer and provide or export feedback.
- Use `scripts/package_skill.py` from a writable staging directory when packaging.

## Packaging Without Presentation Tools

If a direct file presentation tool is unavailable, still package the skill:

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

Report the resulting `.skill` path and any validation warnings.
