# System architecture

This file is the authority for runtime and domain architecture.

The API owns authorization and tenant-scoped data access. The worker receives opaque tenant and job identifiers, claims jobs with a renewable lease, and must make recovery idempotent. The web client never talks directly to the database.

