# Contributing

Run `pnpm verify:change` after changes. Exit code 2 means fast checks passed but the printed environment-backed checks remain.

Changes to tenant boundaries, personal resources, secrets, or row-level security require `pnpm test:integration` against a disposable migrated Postgres database.

Frontend behavior changes require a running stack plus `pnpm browser:smoke` and a real browser inspection.

Use Conventional Commit titles for commits and pull requests.

