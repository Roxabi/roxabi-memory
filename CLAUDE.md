@.claude/stack.yml

# roxabi-vault

## TL;DR

- **Project:** roxabi-vault
- **Before work:** Use `/dev #N` as the single entry point — it determines tier (S / F-lite / F-full) and drives the full lifecycle
- **Decisions:** summarize context → numbered options + recommendation → wait for reply (see [Decision Protocol](#decision-protocol))
- **Never** commit without asking, push without request, or use `--force`/`--hard`/`--amend`
- **Always** use appropriate skill even without slash command

### Decision Protocol

For all decisions, choices (≥2 options), approach proposals:

1. **Summarize** — why / root cause / current behavior / target / path to reach it
2. **Propose** — numbered options, one marked as recommended
3. **Explain** — why the recommended option is recommended

Then wait for reply.

### Git

Format: `<type>(<scope>): <desc>` + `Co-Authored-By: Claude <model> <noreply@anthropic.com>`
Types: feat|fix|refactor|docs|style|test|chore|ci|perf
Never push without request. Never force/hard/amend. Hook fail → fix + NEW commit.

### Dev Process

**Entry point: `/dev #N`** — single command that scans artifacts, shows progress, and delegates to the right phase skill.

| Tier | Criteria | Phases |
|------|----------|--------|
| **S** | ≤3 files, no arch, no risk | triage → implement → pr → validate → review → fix* → cleanup* |
| **F-lite** | Clear scope, single domain | Frame → spec → plan → implement → verify → ship |
| **F-full** | New arch, unclear reqs, >2 domains | Frame → analyze → spec → plan → implement → verify → ship |

`*` = conditional (runs only if applicable)

Phases: **Frame** (problem) → **Shape** (spec) → **Build** (code) → **Verify** (review) → **Ship** (release).

### Artifact Model

Artifacts are the state markers `/dev` uses for progress detection and resumption.

| Type | Directory | Question answered |
|------|-----------|-------------------|
| **Frame** | `artifacts/frames/` | What's the problem? |
| **Analysis** | `artifacts/analyses/` | How deep is it? |
| **Spec** | `artifacts/specs/` | What will we build? |
| **Plan** | `artifacts/plans/` | How do we build it? |

### Coding Standards

| Context | Read |
|---------|------|
| Tests | [testing](docs/standards/testing.md) |

## Gotchas

<!-- Add project-specific gotchas here -->
