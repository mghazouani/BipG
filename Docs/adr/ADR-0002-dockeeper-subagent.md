# ADR-0002-dockeeper-subagent

## Context

The project uses structured “builder/reviewer” prompt documents to guide AI-assisted implementation. As the POC grows across FastAPI, Odoo, and Flutter, we need consistent, reliable documentation updates and change tracking that can be used for PR descriptions and team communication.

## Decision

Introduce a dedicated documentation/change-tracking subagent: **DocKeeper**.

DocKeeper:

- Summarizes changes (what/why/impact) from provided diffs or file lists.
- Updates documentation under `docs/` (changelog, architecture, ADRs, runbooks).
- Produces PR-ready release notes without inventing test results.
- Does not modify production code or run commands.

The canonical prompt/spec lives at `.cursor/agents/dockeeper.md`.

## Alternatives considered

- **Manual documentation only**: works, but is easy to miss and inconsistent across teams.
- **Have implementation agents also update docs**: increases coupling and risk of non-minimal diffs in production code tasks.
- **External wiki**: adds drift risk and reduces “docs-as-code” benefits.

## Consequences

- Documentation updates become a first-class deliverable alongside code changes.
- A clear boundary is established: DocKeeper edits docs only, never production code.
- Teams get consistent PR-ready summaries and changelog entries.

## Follow-ups

- Adopt a lightweight review step that checks `docs/CHANGELOG.md` and (when relevant) adds/updates ADRs.
- When a significant architectural decision is implemented, ensure an ADR is created/updated.

