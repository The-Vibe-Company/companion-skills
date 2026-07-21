# Granite Host Adapters

Use this reference when connecting or repairing Granite MCP registrations.

## Canonical MCP Command

Prefer stdio for local agent hosts:

```text
<absolute-granite-binary> mcp --vault <absolute-vault-path>
```

Absolute paths avoid shell and version-manager PATH differences between an interactive terminal and an agent host.

The configured MCP is not just a transport. It is Granite's required knowledge interface: its intention-first tools carry the type registry, validation, provenance fields, recommendations, and lifecycle rules. After connection, agents must use MCP tools for all knowledge operations. Do not give the agent Granite CLI knowledge commands as an alternative.

Do not add another Granite server when one already exists under a different scope or transport. Inspect, explain, then replace only after approval.

## Claude Code

Canonical user-scope registration:

```bash
claude mcp add --scope user granite -- \
  /absolute/path/to/granite mcp --vault /absolute/path/to/.granite
```

Inspection:

```bash
claude mcp get granite
claude mcp list
```

Run project/local-scope inspection, removal, and registration with the selected project as the current working directory. Otherwise Claude may inspect or mutate the local scope of whichever directory launched the installer.

Claude Code can have the same server name in local, project, and user scopes. `claude mcp list` may report “Conflicting scopes.” When replacing an approved conflict, remove the Granite entry from each relevant scope, then add one canonical user-scope entry:

```bash
claude mcp remove granite --scope local
claude mcp remove granite --scope project
claude mcp remove granite --scope user
```

Ignore “not found” only for scopes that genuinely do not contain Granite.

## Codex

Canonical registration:

```bash
codex mcp add granite -- \
  /absolute/path/to/granite mcp --vault /absolute/path/to/.granite
```

Inspection and removal:

```bash
codex mcp get granite
codex mcp remove granite
```

Codex stores MCP configuration in its own user config. Prefer the CLI over directly rewriting the TOML so unrelated configuration and comments remain intact.

## Cursor

Cursor commonly reads:

```text
~/.cursor/mcp.json
```

Canonical entry:

```json
{
  "mcpServers": {
    "granite": {
      "command": "/absolute/path/to/granite",
      "args": ["mcp", "--vault", "/absolute/path/to/.granite"]
    }
  }
}
```

Parse and merge the JSON. Preserve every unrelated server and field. If the file is invalid JSON, stop rather than overwriting it.

## HTTP Or Daemon Mode

Use HTTP only when the user deliberately wants a persistent local service or a remote client:

```bash
granite daemon start --vault ~/.granite
```

The local default is stdio because it has fewer lifecycle and port-conflict concerns. Do not convert an intentional authenticated HTTP setup to stdio without understanding why HTTP was chosen.

## Verification

Configuration written to disk is not enough. After the host reloads:

1. confirm the server appears connected;
2. call the MCP tool `granite_wakeup`;
3. read the MCP resource `granite://vault/types`;
4. call `granite_research_topic`, `granite_query`, or `granite_compile_context`;
5. report the exact connected vault.

Do not substitute `granite wakeup`, `granite search`, or another CLI knowledge command for these checks. CLI status/doctor commands may diagnose the local process, but only an MCP call proves the harness is using Granite's business-logic surface.
