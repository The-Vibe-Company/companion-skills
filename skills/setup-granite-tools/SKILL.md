---
name: setup-granite-tools
description: Install, update, configure, repair, and onboard Granite as an
  MCP-first, LLM-operated knowledge system. Use whenever someone asks to install
  or upgrade Granite, set up a Granite vault, make the web UI available
  persistently on port 4321, check or restart a broken Granite dashboard,
  connect Granite MCP to Claude Code, Codex, or Cursor, force agents to use MCP
  instead of Granite CLI knowledge commands, add Granite rules to AGENTS.md or
  CLAUDE.md, fix duplicate/conflicting Granite MCP or daemon entries, migrate an
  existing installation, decide what initial knowledge to ingest, or asks
  whether they should upload files directly. This skill owns the complete
  zero-to-useful setup and maintenance path; it should leave the user with a
  working vault, healthy persistent web interface, connected MCP harness, an
  enforced no-CLI knowledge contract, a clear no-dump ingestion model, and a
  reviewed first-ingestion plan.
metadata: {}
---

# Granite Setup

Take a user from no Granite installation to a working, useful, agent-connected vault.

The successful outcome is not merely “the MCP responds.” The user should have:

- Granite installed at a known version;
- one existing or newly initialized vault;
- a persistent local web interface at `http://127.0.0.1:4321`;
- the right MCP registration for each selected agent host;
- short, managed Granite instructions in the project rule files;
- a strict MCP-only interface for all retrieval and knowledge mutations;
- a clear understanding that Granite is operated by the LLM harness and is not a file dump;
- a reviewed plan for the first useful knowledge to ingest;
- a successful wakeup, status check, and real retrieval test.

## Protected Invariants

1. Preserve existing vaults. Never run `granite init` over a vault with `granite.yml`.
2. Inspect before changing. Detect installed binaries, vaults, MCP entries, instruction files, symlinks, and existing managed blocks first.
3. Stay idempotent. A second run should report “already configured” instead of adding duplicate MCP servers or instruction text.
4. Show the mutation plan before applying it. Installation and setup are expected, but replacing a conflicting MCP entry or importing user data requires explicit approval.
5. Never scan broad personal storage, cloud accounts, mailboxes, or home directories without the user choosing exact sources or roots.
6. Import agent-written knowledge as drafts, preserve provenance, and search before creating.
7. Keep the wakeup rule conditional: call `granite_wakeup` once before Granite-backed work, not blindly for every unrelated conversation.
8. Do not install an embedded model, vector store, scheduler, or background agent. Granite is deterministic local knowledge infrastructure; the connected agent provides intelligence.
9. Treat the web UI as unauthenticated. Granite currently reports a loopback URL but may listen on more interfaces depending on its runtime, so warn the user, keep the machine/network trusted, and never expose port 4321 to the public internet.
10. Granite is an LLM-operated knowledge compiler, not a dump. The configured harness must use Granite for retrieval and ingestion. Do not recommend uploading, copying, or dragging files directly into the vault as a substitute for LLM analysis, deduplication, structure, and provenance.
11. All knowledge operations must use Granite MCP. Its intention-first surface enforces type contracts, validation, provenance, recommendations, and editorial lifecycle. Never use Granite CLI knowledge commands or direct Markdown edits as a shortcut.

## Reference Routing

- Read `references/host-adapters.md` when configuring or repairing MCP connections.
- Read `references/initial-ingestion.md` after the technical setup works and the user wants to decide what Granite should know first.
- Use `scripts/setup_granite.py` for deterministic detection, installation, vault initialization, MCP configuration, and managed instruction blocks.

## Workflow

### 1. Establish The Setup Target

Infer what you can, then confirm only decisions that materially change the setup:

- project root whose `AGENTS.md` / `CLAUDE.md` should carry Granite guidance;
- agent hosts to connect: Claude Code, Codex, Cursor, or every detected host;
- existing vault path, normally `~/.granite`;
- new-vault template: `founder-os` for personal/company memory, minimal only when the user explicitly wants the four core knowledge types;
- whether the user wants a fresh setup, repair, or migration.

Do not ask the user for facts the script can detect.

### 2. Inspect In Dry-Run Mode

Run:

```bash
python3 scripts/setup_granite.py \
  --project-root "<project-root>" \
  --hosts auto \
  --json
```

The script defaults to read-only planning. Review:

- Granite and npm availability;
- vault status;
- selected/detected hosts;
- matching, absent, or conflicting MCP entries;
- instruction files and symlink relationships;
- actions that would be applied;
- blockers requiring a decision.

If an existing Granite MCP definition points to another binary, vault, transport, or scope, explain the conflict. Do not silently stack another definition.

### 3. Apply The Approved Technical Setup

When the plan is accepted, run:

```bash
python3 scripts/setup_granite.py \
  --project-root "<project-root>" \
  --hosts "<confirmed-hosts>" \
  --apply \
  --json
```

Add `--replace-mcp` only when the user approved replacing conflicting Granite entries.

The script:

- installs `granite-mem` with npm when the `granite` binary is absent;
- initializes `~/.granite` only when no vault exists;
- registers a stdio Granite MCP using the absolute Granite binary and vault paths;
- starts `granite daemon` persistently, with the normal local URL `http://127.0.0.1:4321` and HTTP MCP on port `3321`;
- refuses to replace an unrelated service occupying either port, and requires `--replace-daemon` before restarting a conflicting Granite daemon;
- rereads the MCP registration and rolls configuration files back when the host does not retain the canonical entry;
- writes or updates marked Granite blocks in `AGENTS.md` and `CLAUDE.md`;
- avoids duplicate writes when those files resolve to the same target;
- runs Granite verification commands when setup succeeds.

Every setup or repair run also checks the daemon status and requests the web URL. If the daemon already targets the expected vault and ports but `http://127.0.0.1:4321` does not respond, the apply run restarts that daemon and verifies both status and HTTP before reporting success. A daemon using a different vault or port remains a conflict and still requires `--replace-daemon`.

Explain the operating model during every installation or onboarding:

- the user works through an LLM/agent harness connected to Granite;
- the harness loads relevant vault context, searches existing knowledge, and writes structured notes;
- a raw file is input material, not finished knowledge;
- for files, the harness reads or extracts the content, analyzes it, deduplicates it, and creates the appropriate `source`, `note`, or `synthesis` entries with provenance;
- attach or preserve the original file only when the artifact itself is useful evidence.

The interface boundary is strict:

- MCP is mandatory for orientation, research, queries, context compilation, extraction, capture, import, revision, and disposal;
- use the MCP resource `granite://vault/types` for the active type contracts;
- the CLI is allowed only for installation, `init`, daemon lifecycle, and diagnostics while repairing MCP;
- do not use `granite wakeup`, `search`, `list`, `show`, `new`, `add`, `edit`, `extract`, or `import` as the agent's knowledge interface;
- never edit vault Markdown files directly from the harness.
- never declare the knowledge runtime verified until the host succeeds with both `granite_wakeup` and a real MCP retrieval against the intended vault.

Do not present the web UI's upload or file operations as the recommended ingestion workflow. `granite_extract_document` and `granite_import_document` must be called through MCP so the workflow stays inside Granite's business-logic boundary.

If a selected host requires restart or reload before it can see the new MCP, say so clearly and stop MCP-tool verification until the host reloads.

The persistent web UI is enabled by default. Use `--skip-web` only when the user explicitly does not want a background service. Use `--web-port` for a user-requested alternative; keep 4321 as the normal setup target. Always surface the no-authentication/network-exposure warning from the setup report.

Include the operating commands in the handoff:

```bash
GRANITE_VAULT=~/.granite granite daemon status
GRANITE_VAULT=~/.granite granite daemon logs
GRANITE_VAULT=~/.granite granite daemon stop
```

Use `GRANITE_VAULT` for daemon subcommands. Granite 0.1.12 may ignore a `--vault` flag placed on `daemon status` or `daemon stop`, which can target the default vault unexpectedly.

### 4. Update Granite And Recover The Dashboard

Use the npm package registry as the update source. Do not reinstall blindly. First inspect the plan:

```bash
python3 scripts/setup_granite.py \
  --project-root "<project-root>" \
  --update-granite \
  --skip-mcp \
  --skip-guidance \
  --json
```

The script reads the installed version with `granite --version`, reads the current release with `npm view granite-mem@latest version --json`, and plans `npm install -g granite-mem@latest` only when npm has a newer semantic version. It never downgrades an installation that is ahead of the registry. On a fresh machine, the planned install already targets `@latest`, so no separate update check tries to execute the not-yet-created binary. Review the plan, then apply it:

```bash
python3 scripts/setup_granite.py \
  --project-root "<project-root>" \
  --update-granite \
  --skip-mcp \
  --skip-guidance \
  --apply \
  --json
```

After an actual update, the script automatically restarts the matching persistent daemon so it loads the new Granite version. It then verifies that the daemon retained the requested vault, MCP port `3321`, and web port `4321`, and that the dashboard returns an HTTP response. If Granite is already current, it does not restart a healthy daemon.

`--skip-mcp --skip-guidance` makes this a maintenance-only run: it does not inspect or rewrite agent MCP registrations or project instruction files. It does not authorize knowledge work through CLI; the existing MCP remains the mandatory knowledge interface.

To check or repair only the dashboard, run the same dry-run and apply commands without `--update-granite`. A matching but non-responsive daemon is planned for restart and repaired during `--apply`. Never use `--replace-daemon` merely to repair the expected daemon; reserve it for a reviewed daemon conflict involving another vault or ports. If a non-Granite process occupies port `4321` or `3321`, stop and ask the user what to do.

An explicit `--granite-bin` is not updated automatically because the script cannot safely infer its package manager. Report the available npm version and ask the user to update that executable through its owning installation method.

This maintenance workflow does not relax the interface boundary: npm and Granite CLI are used only for package and daemon administration. Wakeup, retrieval, extraction, capture, import, revision, and every other knowledge operation still go through Granite MCP.

### 5. Verify The Connection

After the host reloads:

1. Call the MCP tool `granite_wakeup` once.
2. Read the MCP resource `granite://vault/types` if the vault is new or unfamiliar.
3. Call `granite_research_topic`, `granite_query`, or `granite_compile_context` for a real retrieval.
4. Use CLI only to inspect administrative health with `granite status` or `granite daemon status`.
5. Confirm the daemon reports the selected vault and `http://127.0.0.1:4321`.
6. Open or request the local URL and confirm the UI responds.
7. Confirm the MCP is connected to the intended vault and its retrieval result has provenance.

Do not claim knowledge-runtime success solely because a config file was written or a CLI command succeeded. A real MCP tool call is required.

### 6. Run The Initial Knowledge Interview

Read `references/initial-ingestion.md`.

Ask the user what Granite should help them remember or answer. Offer concrete source categories:

- profile, working style, preferences, and recurring rules;
- active projects and current decisions;
- important people, clients, organizations, and relationships;
- meeting notes or transcripts;
- Markdown/Obsidian folders;
- documents, PDFs, exports, or reference material;
- URLs, articles, repositories, or research sources.

Let the user choose exact sources. Inspect selected sources read-only, then present an ingestion plan with estimated note types, deduplication keys, provenance, and exclusions.

Say explicitly: “Granite is not a dump. Give the selected material to the connected LLM harness; it will analyze and structure the useful knowledge before writing to the vault.”

### 7. Ingest A Bounded First Batch

Prototype with 3–10 representative items before attempting a large migration.

For every proposed note:

- research Granite through MCP first;
- update a matching note rather than creating a duplicate;
- use the vault’s configured type contract;
- mark agent-created knowledge as draft;
- attach provenance or `derived_from` where relevant;
- avoid dumping raw transcripts or entire folders into durable notes;
- preserve original files when the file itself matters.

Never count a copied or attached file as successful ingestion on its own. Success means the harness produced useful, searchable, typed knowledge from it and retained a traceable link to the source.

Perform the batch through MCP tools. Do not fall back to CLI capture/import commands when MCP is unavailable; repair or reload the MCP first.

Show the result of the first batch and ask whether the structure feels right before scaling the import.

### 8. Prove The Vault Is Useful

End onboarding with a real user question, such as:

- “What are my active projects and unresolved decisions?”
- “Who are the important people around this client?”
- “What did we decide about this product?”
- “What sources support this idea?”

Use Granite to answer it. If retrieval is weak, improve titles, types, links, or starter coverage before declaring onboarding complete.

## Output Contract

Return a concise setup report:

```markdown
# Granite Setup Report

## Installed
- Granite version:
- Vault:
- Template/types:

## Connected
- Claude Code:
- Codex:
- Cursor:

## Project Instructions
- AGENTS.md:
- CLAUDE.md:

## Usage Model
- LLM harness connected:
- Knowledge interface: MCP
- CLI knowledge operations disabled:
- No-dump guidance explained:
- File ingestion path:

## Verification
- Wakeup:
- MCP retrieval:
- Status:
- Web UI:
- Persistent daemon:
- Retrieval test:

## Initial Ingestion
- Selected sources:
- First batch:
- Created/updated:
- Deferred or excluded:

## Remaining Action
<restart, conflict approval, source selection, or "None">
```

## Boundaries And Handoffs

- This skill owns installation, repair, host connection, setup instructions, and the initial onboarding corpus.
- The bundled setup script requires Python 3.10+; installing Granite requires Node.js/npm. It is tested on macOS and Linux, with Windows path handling provided on a best-effort basis.
- After onboarding, ordinary conversational capture belongs to the vault’s normal capture workflow.
- Large recurring source ingestion should use the user’s existing source-ingestion owner when one exists; do not create a parallel public workflow.
- Vault gardening, compilation, and audience-specific outputs are downstream work, not reasons to rerun setup.
