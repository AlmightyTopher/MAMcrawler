# SQLAlchemy ORM Models - Audiobook Automation System

This directory contains all SQLAlchemy ORM models for the FastAPI audiobook automation system. These models match the PostgreSQL schema defined in `database_schema.sql`.

## Model Overview

### Core Content Models

1. **Book** (`book.py`)
   - Represents all discovered/imported audiobooks
   - Tracks metadata completeness and sources
   - Primary table for library content

2. **Series** (`series.py`)
   - Tracks book series and completion status
   - Monitors series gaps for automatic discovery

3. **Author** (`author.py`)
   - Tracks authors and their audiobook collections
   - Monitors author completeness across platforms

### Gap Identification & Downloads

4. **MissingBook** (`missing_book.py`)
   - Identified gaps in series/author completeness
   - Links to series or author that has the gap
   - Tracks download status and priority

5. **Download** (`download.py`)
   - All download attempts (queued, active, completed, failed)
   - Tracks qBittorrent integration and retry logic
   - Handles Audiobookshelf import status

### Task Tracking & Analytics

6. **Task** (`task.py`)
   - Execution history of scheduled jobs
   - Tracks performance metrics and logs
   - **1-month retention policy**

7. **FailedAttempt** (`failed_attempt.py`)
   - Permanent record of all failures
   - Used for analytics and pattern detection
   - **NEVER deleted - permanent retention**

8. **MetadataCorrection** (`metadata_correction.py`)
   - History of metadata changes
   - Tracks source and reason for corrections
   - **1-month retention policy**

## Model Relationships

```
Book
├── downloads (One-to-Many → Download)
├── missing_book_entries (One-to-Many → MissingBook)
└── metadata_corrections (One-to-Many → MetadataCorrection)

Series
└── missing_books (One-to-Many → MissingBook)

Author
└── missing_books (One-to-Many → MissingBook)

MissingBook
├── book (Many-to-One → Book)
├── series (Many-to-One → Series)
├── author (Many-to-One → Author)
└── download (One-to-One → Download)

Download
├── book (Many-to-One → Book)
└── missing_book (One-to-One → MissingBook)

MetadataCorrection
└── book (Many-to-One → Book)

Task
└── (No relationships - standalone logging table)

FailedAttempt
└── (No relationships - standalone analytics table)
```

## Usage Examples

### Import Models

```python
from backend.models import (
    Book, Series, Author, MissingBook,
    Download, Task, FailedAttempt, MetadataCorrection
)
```

### Create a Book

```python
from backend.database import get_db
from backend.models import Book

with get_db() as db:
    book = Book(
        title="The Name of the Wind",
        author="Patrick Rothfuss",
        series="The Kingkiller Chronicle",
        series_number="1",
        isbn="9780756404079",
        metadata_completeness_percent=85
    )
    db.add(book)
    db.commit()
    db.refresh(book)
```

### Query Missing Books

```python
from backend.database import get_db
from backend.models import MissingBook

with get_db() as db:
    # Get all high-priority missing books
    missing = db.query(MissingBook).filter(
        MissingBook.priority == 1,
        MissingBook.download_status == 'identified'
    ).all()

    for book in missing:
        print(f"{book.title} - {book.reason_missing}")
```

### Track Task Execution

```python
from backend.database import get_db
from backend.models import Task
from datetime import datetime

with get_db() as db:
    task = Task(
        task_name="SERIES",
        scheduled_time=datetime.now(),
        actual_start=datetime.now(),
        status="running"
    )
    db.add(task)
    db.commit()

    # Later, update task
    task.status = "completed"
    task.actual_end = datetime.now()
    task.items_processed = 50
    task.items_succeeded = 48
    task.items_failed = 2
    db.commit()
```

### Record Failed Attempt

```python
from backend.database import get_db
from backend.models import FailedAttempt
from datetime import datetime

with get_db() as db:
    failure = FailedAttempt(
        task_name="DOWNLOAD",
        item_id=123,
        item_name="The Wise Man's Fear",
        reason="Torrent not found on MAM",
        error_code="TORRENT_404",
        last_attempt=datetime.now(),
        metadata={"source": "MAM", "search_terms": "wise man's fear rothfuss"}
    )
    db.add(failure)
    db.commit()
```

## Database Initialization

To create all tables in the database:

```python
from backend.database import init_db

# This will create all tables based on the models
init_db()
```

## Key Design Patterns

### Timestamps
- All models use `func.now()` for default timestamps
- Automatic `onupdate=func.now()` for `date_updated` fields

### Foreign Keys
- Use `ondelete="CASCADE"` for dependent relationships
- Use `ondelete="SET NULL"` for optional references

### Indexes
- Primary keys automatically indexed
- Foreign keys indexed for join performance
- Status/date fields indexed for filtering
- Unique constraints on natural keys (names, IDs)

### JSON Fields
- Use `JSON` type for flexible metadata storage
- Default to empty dict `{}`
- Useful for task-specific data and analytics

### Relationships
- Use `back_populates` for bidirectional relationships
- Lazy loading by default (can be optimized per query)
- Foreign key constraints enforce referential integrity

## Data Retention

### 1-Month Retention
- `tasks` - Scheduled cleanup of records > 30 days old
- `metadata_corrections` - Scheduled cleanup of records > 30 days old

### Permanent Retention
- `failed_attempts` - NEVER deleted, used for long-term analytics

### Active Data
- All other tables retain data indefinitely until explicitly deleted

## Notes

- All string lengths match PostgreSQL schema exactly
- Column types chosen for PostgreSQL compatibility
- Models include comprehensive docstrings for IDE support
- Relationship definitions enable SQLAlchemy's lazy loading and eager loading
- All models inherit from `backend.database.Base`
