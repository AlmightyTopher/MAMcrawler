# Database Migrations

This directory contains Alembic database migrations for the MAMcrawler project.

## Setup

Install Alembic:
```bash
pip install alembic
```

## Common Commands

### Check Current Version
```bash
alembic current
```

### Generate New Migration
```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "description of changes"

# Create empty migration for manual edits
alembic revision -m "description of changes"
```

### Apply Migrations
```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade <revision_id>

# Upgrade by steps
alembic upgrade +1
```

### Rollback Migrations
```bash
# Downgrade by one step
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade <revision_id>

# Downgrade to base (empty database)
alembic downgrade base
```

### View Migration History
```bash
# Show all revisions
alembic history

# Show current to head
alembic history --verbose
```

### Generate SQL Script
```bash
# Generate SQL for offline migration
alembic upgrade head --sql > migration.sql
```

## Best Practices

1. **Always review auto-generated migrations** - Alembic's autogenerate is helpful but not perfect
2. **Test migrations locally** before deploying to production
3. **Keep migrations small** - One logical change per migration
4. **Write both upgrade and downgrade** - Ensure migrations are reversible
5. **Use descriptive messages** - Help future developers understand the change
6. **Back up before migrating** - Especially in production

## Migration Workflow

1. Make changes to SQLAlchemy models in `backend/models/`
2. Generate migration: `alembic revision --autogenerate -m "add user_preferences table"`
3. Review the generated migration in `backend/migrations/versions/`
4. Test upgrade: `alembic upgrade head`
5. Test downgrade: `alembic downgrade -1`
6. Commit the migration file

## Troubleshooting

### "Target database is not up to date"
```bash
alembic stamp head  # Mark current state as up to date
```

### Multiple heads (branched migrations)
```bash
alembic heads  # Show all heads
alembic merge <rev1> <rev2> -m "merge branches"
```

### Import errors
Ensure you're running from the project root directory with proper PYTHONPATH:
```bash
PYTHONPATH=. alembic upgrade head
```
