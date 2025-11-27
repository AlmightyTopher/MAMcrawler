# Database Migrations Guide
## Alembic Configuration for MAMcrawler

This guide explains how to use Alembic for database schema versioning and migrations.

---

## Overview

**Alembic** is a lightweight database migration tool for SQLAlchemy. It allows us to:
- Version control database schema changes
- Track migration history
- Safely upgrade and downgrade databases
- Ensure consistency across environments (dev, staging, production)

---

## Setup

### Installation

Alembic is already listed in `backend/requirements.txt`:

```bash
pip install alembic
```

### Configuration Files

The migration system includes:

```
alembic/
├── __init__.py              # Package initialization
├── env.py                   # Migration environment config
├── script.py.mako           # Migration template
└── versions/
    ├── __init__.py
    └── 001_initial_schema.py  # Initial migration

alembic.ini                 # Alembic configuration
```

---

## Common Commands

### Initialize Database with Migrations

```bash
# Upgrade to latest migration
alembic upgrade head

# This applies all pending migrations to the database
```

### Create a New Migration

After modifying a SQLAlchemy model:

```bash
# Auto-detect changes and generate migration
alembic revision --autogenerate -m "Description of changes"

# Example:
alembic revision --autogenerate -m "Add series completion tracking"

# This creates a new file in alembic/versions/ with the DDL changes
```

### Check Migration Status

```bash
# Show current database revision
alembic current

# Show all migrations and their status
alembic history

# Show migrations not yet applied
alembic status
```

### Apply Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply one specific migration
alembic upgrade +1

# Apply to a specific revision
alembic upgrade abc123
```

### Revert Migrations

```bash
# Revert last migration
alembic downgrade -1

# Revert to specific revision
alembic downgrade abc123

# Revert to initial state (before any migrations)
alembic downgrade base
```

---

## Workflow: Adding a New Database Table

### Step 1: Define SQLAlchemy Model

Add your model to `backend/models/`:

```python
# backend/models/my_new_model.py
from sqlalchemy import Column, Integer, String, DateTime
from backend.database import Base

class MyNewModel(Base):
    __tablename__ = "my_new_models"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Step 2: Import Model in __init__.py

```python
# backend/models/__init__.py
from backend.models.my_new_model import MyNewModel
```

### Step 3: Generate Migration

```bash
cd C:\Users\dogma\Projects\MAMcrawler
alembic revision --autogenerate -m "Add MyNewModel table"
```

This creates: `alembic/versions/002_add_mynewmodel_table.py`

### Step 4: Review Generated Migration

```python
# alembic/versions/002_add_mynewmodel_table.py

def upgrade():
    # SQL statements to create table
    op.create_table(
        'my_new_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        # ... other columns
    )

def downgrade():
    # SQL statements to drop table
    op.drop_table('my_new_models')
```

### Step 5: Apply Migration

```bash
alembic upgrade head
```

### Step 6: Verify

```bash
alembic current  # Should show your new migration revision
```

---

## Workflow: Modifying an Existing Column

### Step 1: Modify SQLAlchemy Model

```python
# Before:
name = Column(String(255), nullable=False)

# After:
name = Column(String(512), nullable=False)  # Increased length
```

### Step 2: Generate Migration

```bash
alembic revision --autogenerate -m "Increase name column length"
```

### Step 3: Review and Apply

```bash
alembic upgrade head
```

---

## Best Practices

### 1. Always Generate Migrations for Schema Changes

**❌ WRONG:**
```python
# Don't manually modify database
# ALTER TABLE books MODIFY COLUMN title VARCHAR(512);
```

**✅ RIGHT:**
```bash
# Generate migration through Alembic
alembic revision --autogenerate -m "Increase title column length"
```

### 2. Test Migrations Before Production

```bash
# In development database
alembic upgrade head
# Test application
alembic downgrade -1
alembic upgrade head
# Verify downgrade and upgrade work
```

### 3. Review Generated Migrations

Always review the generated SQL before applying:

```bash
# View SQL without executing
alembic upgrade head --sql
```

### 4. Use Descriptive Migration Messages

**❌ BAD:**
```bash
alembic revision --autogenerate -m "Update"
```

**✅ GOOD:**
```bash
alembic revision --autogenerate -m "Add book_quality field for narrator matching"
```

### 5. Don't Edit Revision IDs

Migration files are named by revision ID. Don't rename them after creation.

### 6. Commit Migrations to Git

```bash
git add alembic/versions/
git commit -m "Add database migration for X feature"
```

---

## Production Deployment

### Pre-Deployment Checklist

```bash
# 1. Check pending migrations
alembic status

# 2. Preview SQL changes
alembic upgrade head --sql > migration_preview.sql

# 3. Backup production database (done separately)

# 4. Apply migrations
alembic upgrade head

# 5. Verify migration success
alembic current
```

### Rolling Back in Production

```bash
# If migration causes issues:
alembic downgrade -1

# Investigate the problem, fix migration file, then reapply
alembic upgrade head
```

---

## Troubleshooting

### Issue: "sqlalchemy.exc.ProgrammingError" During Migration

**Cause:** Migration targets a table/column that doesn't exist

**Solution:**
```bash
# Downgrade problematic migration
alembic downgrade -1

# Review and fix migration file
vim alembic/versions/XXX_migration.py

# Reapply
alembic upgrade head
```

### Issue: "alembic.util.exc.CommandError: Can't find identifier"

**Cause:** Revision ID doesn't exist

**Solution:**
```bash
# Check available revisions
alembic history

# Use correct revision
alembic downgrade 002
```

### Issue: "sqlalchemy.exc.ArgumentError: Could not locate a declarative base"

**Cause:** SQLAlchemy models not properly imported in env.py

**Solution:**
Ensure all models are imported:
```python
# In backend/models/__init__.py
from backend.models.book import Book
from backend.models.author import Author
# ... import all models
```

### Issue: Models Not Detected in Autogenerate

**Cause:** Models not imported in `backend/database.py`

**Solution:**
```python
# backend/database.py
from backend.models import *  # Ensure all models imported
```

---

## Migration File Structure

Each migration file has this structure:

```python
"""Description of what this migration does

Revision ID: 002
Revises: 001
Create Date: 2025-11-25 12:34:56.789012

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply this migration to the database"""
    # SQL/DDL statements to upgrade schema
    op.create_table(...)
    op.add_column(...)
    # etc.


def downgrade() -> None:
    """Revert this migration from the database"""
    # SQL/DDL statements to downgrade schema
    op.drop_table(...)
    op.drop_column(...)
    # etc.
```

---

## Environment-Specific Migrations

### Development Database

```bash
cd C:\Users\dogma\Projects\MAMcrawler
# Create migrations as needed
alembic revision --autogenerate -m "New feature"
alembic upgrade head
```

### Production Database

```bash
# Use same migrations, different database URL (from .env)
alembic upgrade head
```

The `DATABASE_URL` from `.env` determines which database gets upgraded.

---

## Continuous Integration

### GitHub Actions Example

```yaml
- name: Run database migrations
  run: |
    alembic upgrade head
  env:
    DATABASE_URL: postgresql://user:pass@localhost/testdb
```

---

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Database Migration Best Practices](https://blog.logrocket.com/handling-database-migrations-in-python/)

---

## Next Steps

1. Review the initial migration: `alembic/versions/001_initial_schema.py`
2. Test upgrade: `alembic upgrade head`
3. Test downgrade: `alembic downgrade -1`
4. Commit to git: `git add alembic/`
5. Add to deployment procedures

---

*Last Updated: 2025-11-25*
*Alembic Version: 1.12.1*
