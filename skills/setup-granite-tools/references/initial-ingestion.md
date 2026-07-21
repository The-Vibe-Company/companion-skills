# Initial Granite Ingestion

Use this reference after Granite is technically working.

## Goal

Create a small, high-signal starter vault that can already answer a real question for the user.

Do not treat onboarding as a bulk backup job. Granite is not a dump: it is a knowledge compiler operated by an LLM harness. The first ingestion establishes information architecture, note quality, and trust.

## Required Operating Model

Teach this before asking for sources:

1. The user gives selected material to the connected LLM/agent harness.
2. The harness reads or extracts the source material through `granite_extract_document` on MCP.
3. The LLM analyzes meaning, entities, decisions, claims, and relationships.
4. The harness uses `granite_research_topic`, `granite_query`, or `granite_resolve` on MCP to deduplicate.
5. The harness writes structured, typed knowledge through `granite_capture_knowledge`, `granite_import_document`, or `granite_revise_note` on MCP.
6. The MCP applies type validation, provenance, recommendations, and lifecycle rules.
7. The original file is attached only through MCP and only when it is useful evidence or a durable artifact.

Uploading, copying, or dragging a file into the vault is not complete ingestion. Do not use the Granite CLI or direct Markdown edits for knowledge operations. If MCP is unavailable, stop ingestion and repair the connection rather than bypassing Granite's business logic.

## Interview

Start with outcomes:

- What should Granite help you remember?
- What questions should your agent answer without asking you to repeat context?
- Which parts of your work or life are safe and useful to place in this vault?
- What should never be ingested?

Then offer source categories:

| Category | Examples | Likely Granite types |
| --- | --- | --- |
| User context | profile, preferences, working style, recurring rules | note, learning |
| Projects | goals, status, decisions, open questions | note, synthesis, organization |
| Relationships | people, clients, partners, teams | person, organization |
| Meetings | notes, transcripts, decisions, action items | meeting, note |
| Existing knowledge | Markdown, Obsidian, docs, wikis | source, note |
| Documents | PDF, DOCX, reports, contracts, research | source, note |
| External sources | URLs, articles, posts, repositories | source, learning |

Use only types actually declared by the target vault.

## Permission Ladder

1. Ask which source categories matter.
2. Ask for exact paths, files, URLs, or connected sources.
3. Inspect selected sources read-only.
4. Report what was found, including private or risky material.
5. Present the proposed import plan.
6. Obtain approval for the first batch.
7. Write 3–10 drafts.
8. Review structure and content with the user.
9. Scale only after approval.

Never recursively scan a home directory, mailbox, drive, calendar, or cloud account because it happens to be available.

## Ingestion Plan

Show:

```markdown
## Sources Selected
- <source and scope>

## Proposed Notes
| Input | Proposed type | Title/entity | Provenance | Dedupe key |
| --- | --- | --- | --- | --- |

## Excluded
- <secret, low-signal, duplicate, or out-of-scope material>

## First Batch
- <3–10 representative items>
```

Choose a batch that samples different shapes instead of importing ten nearly identical documents.

## Quality Rules

- Search exact identifiers, URLs, file hashes, entity names, and close titles before creating.
- Prefer one durable idea or entity per note.
- Keep source material close to the original and distinguish it from interpretation.
- Do not turn guesses about the user into canonical facts.
- Mark agent-written starter notes as drafts.
- Use wikilinks for relationships, not decorative tags.
- Preserve original files when the artifact itself matters.
- Summarize large documents for the graph while keeping their source attachment or path.
- Avoid raw transcript dumps; extract decisions, facts, relationships, and durable insights.
- Do not count an attached file as an ingested knowledge item unless the harness also created useful structured knowledge from it.
- Require MCP tool results for the first batch and acceptance test; CLI output is not evidence of a valid agent ingestion path.

## Starter Sets

### Personal or founder setup

- one user/context note;
- two or three active project or organization notes;
- three to five important person notes;
- one current decision or open-question note;
- one synthesis connecting the active landscape.

### Team or company setup

- company or team identity;
- current priorities;
- active clients/projects;
- decision-making and communication rules;
- important people and ownership;
- recent source documents or meetings.

### Research setup

- research question and scope;
- three to five foundational sources;
- atomic learnings from those sources;
- one early synthesis with open questions.

## Acceptance Test

Ask the user for one question the vault should now answer. Retrieve from Granite and check:

- the correct entities appear;
- claims trace back to sources or user-provided facts;
- drafts are clearly marked;
- no private excluded material leaked into the answer;
- the answer is better than a generic response.

If the test fails, improve structure or coverage before importing more.
