# Architecture

This document is authoritative for architecture and trust boundaries.

- Personal resources are creator-private; administrators have no override.
- Tenant-owned data is scoped by `org_id` with row-level security as defense in depth.
- Secret plaintext is write-only and must never be persisted, logged, audited, or returned.
- Untrusted user code executes only in sandboxed provider workloads, never in the control plane.
- `packages/core` remains framework-free so API and worker share the same service behavior.

