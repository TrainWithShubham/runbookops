# Contributing

Start with a small issue explaining the observed behavior, expected result, and a reproducible example. Check existing issues first. For a security issue, follow [SECURITY.md](SECURITY.md).

## Set up

Use Python 3.11–3.13, uv, and Node.js 26 or newer for the JavaScript tests. The browser app itself needs no Node.js installation.

```bash
uv sync --frozen --extra aws
npm ci
make check
```

Work on a focused branch. Keep commits short. Explain what changed and how you checked it. Include screenshots when behavior or presentation changes. Keep credentials, local state, Terraform plans, and model responses containing private data out of Git.

## Tests and documentation

Keep the 100% application coverage gates. Add tests for meaningful behavior rather than copying the implementation into assertions. Check permission filtering, exact-change approval, cancellation, concurrency, persistence, and idempotency when changing those boundaries.

Offline tests must not use real provider credentials, create AWS resources, or silently switch to a paid model. Live checks require explicit opt-in and separate evidence. Document their cost and scope.

Update the relevant docs and [DECISIONS.md](DECISIONS.md) when changing architecture or operational behavior. Run `make check` and the affected container/infrastructure checks before submitting.

## New tools

Expose a narrow capability with a validated schema, bounded inputs/results, a timeout, and explicit permissions. Bind the caller and incident on the server. Models must not choose their own identity or approve their own proposals. Operational writes require an exact reviewed proposal and an idempotent executor; do not add a generic shell tool.

By submitting a contribution, you agree to license it under the repository's Apache-2.0 license. Preserve existing third-party notices.
