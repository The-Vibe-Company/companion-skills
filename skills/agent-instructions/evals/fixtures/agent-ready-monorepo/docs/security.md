# Security

Every API request resolves the authenticated tenant on the server. Repository methods require a tenant identifier and enforce tenant predicates. Browser-supplied tenant identifiers are untrusted.

