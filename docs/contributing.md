# Contributing

How to set up, develop, and contribute to roxabi-vault.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)

## Getting Started

```bash
# Clone the repository
git clone <repo-url>
cd roxabi-vault

# Install dependencies (including dev tools)
uv sync

# Install pre-commit hooks
uv run pre-commit install

# Verify everything works
uv run pytest
```

## Development Workflow

### Branch Strategy

- `main` — stable, release-ready code
- `staging` — integration branch, merges go here first
- `feat/<issue>-<slug>` — feature branches off staging

### Making Changes

1. Create a feature branch from `staging`: `git checkout -b feat/<issue>-<slug> staging`
2. Make your changes
3. Run the checks (see below)
4. Open a PR targeting `staging`

### Running Checks

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .
```

### Commit Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(scope): add new feature
fix(scope): fix a bug
chore(scope): maintenance task
docs(scope): documentation update
```

### PR Process

1. PRs target `staging` (not `main`)
2. All checks must pass (lint, test)
3. PRs are reviewed before merge
4. Staging is promoted to main for releases

## Project Structure

```
roxabi-vault/
├── roxabi_vault/        # Library source
│   ├── __init__.py       # Public API exports
│   ├── schema.py         # DDL + migrations
│   ├── db.py             # Sync MemoryDB
│   ├── async_db.py       # Async AsyncMemoryDB
│   ├── fts.py            # FTS5 search logic
│   ├── namespace.py      # Namespaced wrappers
│   └── cli.py            # vault CLI
├── tests/                # Test suite
├── docs/                 # Documentation
├── artifacts/            # Frames, specs, plans
├── tools/                # Utility scripts
├── pyproject.toml        # Project config
└── uv.lock               # Locked dependencies
```

## Adding a New Feature

1. **Frame** the problem in `artifacts/frames/`
2. **Spec** the solution in `artifacts/specs/`
3. **Plan** the implementation in `artifacts/plans/`
4. **Implement** on a feature branch
5. **Test** — add tests in `tests/`
6. **Document** — update relevant docs
