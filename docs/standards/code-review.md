# Code Review Standards

Guidelines for reviewing code in roxabi-memory.

## Review Checklist

- [ ] Code follows project patterns (see [backend-patterns](backend-patterns.md))
- [ ] Tests added/updated for changes
- [ ] No security vulnerabilities introduced (SQL injection, unsafe deserialization)
- [ ] Documentation updated if public API changed
- [ ] All SQL uses parameterized queries (`?` placeholders)
- [ ] FTS queries go through `_safe_query()` sanitization
- [ ] Database connections use context managers
- [ ] No new required dependencies added to core (keep core lightweight)
- [ ] Migrations are additive and idempotent
- [ ] Commit messages follow Conventional Commits

## What to Look For

### Security

- SQL injection: any string interpolation in SQL queries
- Metadata injection: unsanitized JSON stored in metadata column
- Path traversal: user-controlled database paths in CLI

### Correctness

- FTS index stays in sync (triggers handle INSERT/UPDATE/DELETE)
- Namespace scoping is applied consistently (vault always included in searches)
- Migration version numbers are sequential and never reused

### Performance

- FTS queries use the `rank` column for BM25 ordering
- Result limits are applied at the SQL level, not in Python
- WAL mode is set on every connection

## AI Quick Reference

<!-- Compressed imperative rules for dev-core agents. Keep under 10 lines. -->

- REJECT any SQL that interpolates user input — must use `?` params
- REJECT changes that break FTS trigger sync
- REJECT new core dependencies — use optional extras for non-essential features
- VERIFY migrations are additive (no DROP, no column removal)
- VERIFY namespace scoping includes `vault` in search queries
- CHECK that tests use in-memory databases, not file-based
