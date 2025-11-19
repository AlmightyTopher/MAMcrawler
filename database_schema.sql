-- ============================================================================
-- AUDIOBOOK AUTOMATION SYSTEM - PostgreSQL DATABASE SCHEMA
-- ============================================================================
-- Purpose: Central database for orchestrating all audiobook automation tasks
-- Retention: 1-month active history, permanent failed-attempt tally
-- Version: 1.0
-- Created: 2025-11-16
-- ============================================================================

-- Create extension for UUID support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE: books
-- Purpose: All discovered/imported books with metadata completeness tracking
-- ============================================================================
CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    abs_id VARCHAR(255) UNIQUE,                    -- Audiobookshelf internal ID
    title VARCHAR(500) NOT NULL,
    author VARCHAR(500),
    series VARCHAR(500),
    series_number VARCHAR(50),                    -- Position in series (e.g., "3" or "3.5")
    isbn VARCHAR(50),
    asin VARCHAR(50),
    publisher VARCHAR(500),
    published_year INT,
    duration_minutes INT,                         -- Audiobook duration
    description TEXT,

    -- Metadata completeness tracking
    metadata_completeness_percent INT DEFAULT 0,
    last_metadata_update TIMESTAMP,
    metadata_source JSONB DEFAULT '{}',           -- Field → source mapping: {"title": "GoogleBooks", "author": "Goodreads", ...}

    -- Import tracking
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    import_source VARCHAR(100),                   -- "user_import", "mam_scraper", "series_completion", "author_discovery"

    -- Status tracking
    status VARCHAR(50) DEFAULT 'active',          -- active, duplicate, archived

    INDEX idx_abs_id (abs_id),
    INDEX idx_title (title),
    INDEX idx_author (author),
    INDEX idx_series (series),
    INDEX idx_date_added (date_added)
);

-- ============================================================================
-- TABLE: series
-- Purpose: Track all series in library + completion status
-- ============================================================================
CREATE TABLE series (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL UNIQUE,
    author VARCHAR(500),
    goodreads_id VARCHAR(255),
    total_books_in_series INT,                    -- Per Goodreads

    -- Completion tracking
    books_owned INT DEFAULT 0,
    books_missing INT DEFAULT 0,
    completion_percentage INT DEFAULT 0,

    -- Series scanning
    last_completion_check TIMESTAMP,
    completion_status VARCHAR(100),               -- complete, partial, incomplete

    date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_name (name),
    INDEX idx_goodreads_id (goodreads_id),
    INDEX idx_completion_status (completion_status)
);

-- ============================================================================
-- TABLE: authors
-- Purpose: Track all authors in library + external audiobook discovery
-- ============================================================================
CREATE TABLE authors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL UNIQUE,

    -- External IDs for cross-platform searching
    goodreads_id VARCHAR(255),
    google_books_id VARCHAR(255),
    mam_author_id VARCHAR(255),

    -- Audiobook counts
    total_audiobooks_external INT,                -- Found in external sources
    audiobooks_owned INT DEFAULT 0,
    audiobooks_missing INT DEFAULT 0,

    -- Author scanning
    last_completion_check TIMESTAMP,
    completion_status VARCHAR(100),               -- complete, partial, incomplete

    date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_name (name),
    INDEX idx_goodreads_id (goodreads_id),
    INDEX idx_last_check (last_completion_check)
);

-- ============================================================================
-- TABLE: missing_books
-- Purpose: Identified gaps in series/author completeness
-- ============================================================================
CREATE TABLE missing_books (
    id SERIAL PRIMARY KEY,
    book_id INT REFERENCES books(id) ON DELETE SET NULL,
    series_id INT REFERENCES series(id) ON DELETE CASCADE,
    author_id INT REFERENCES authors(id) ON DELETE CASCADE,

    title VARCHAR(500) NOT NULL,
    author_name VARCHAR(500),
    series_name VARCHAR(500),
    series_number VARCHAR(50),

    -- Why it's missing
    reason_missing VARCHAR(100) NOT NULL,         -- series_gap, author_gap

    -- External source info
    isbn VARCHAR(50),
    asin VARCHAR(50),
    goodreads_id VARCHAR(255),

    -- Status tracking
    identified_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    download_status VARCHAR(100) DEFAULT 'identified',  -- identified, queued, downloading, completed, failed
    download_id INT REFERENCES downloads(id) ON DELETE SET NULL,

    priority INT DEFAULT 1,                       -- 1 = high, 2 = medium, 3 = low

    INDEX idx_series_id (series_id),
    INDEX idx_author_id (author_id),
    INDEX idx_download_status (download_status),
    INDEX idx_identified_date (identified_date)
);

-- ============================================================================
-- TABLE: downloads
-- Purpose: Track all download attempts (queued, in-progress, completed, failed)
-- ============================================================================
CREATE TABLE downloads (
    id SERIAL PRIMARY KEY,
    book_id INT REFERENCES books(id) ON DELETE CASCADE,
    missing_book_id INT REFERENCES missing_books(id) ON DELETE CASCADE,

    title VARCHAR(500) NOT NULL,
    author VARCHAR(500),

    -- Source & link
    source VARCHAR(100) NOT NULL,                 -- MAM, GoogleBooks, Goodreads, Manual
    magnet_link TEXT,
    torrent_url TEXT,

    -- qBittorrent tracking
    qbittorrent_hash VARCHAR(255),
    qbittorrent_status VARCHAR(100),              -- downloading, seeding, completed

    -- Retry logic
    status VARCHAR(100) NOT NULL DEFAULT 'queued', -- queued, downloading, completed, failed, abandoned
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    last_attempt TIMESTAMP,
    next_retry TIMESTAMP,

    -- Audiobookshelf import
    abs_import_status VARCHAR(100),               -- pending, imported, import_failed
    abs_import_error TEXT,

    date_queued TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_completed TIMESTAMP,

    INDEX idx_book_id (book_id),
    INDEX idx_status (status),
    INDEX idx_source (source),
    INDEX idx_qbittorrent_hash (qbittorrent_hash),
    INDEX idx_date_queued (date_queued),
    INDEX idx_next_retry (next_retry)
);

-- ============================================================================
-- TABLE: tasks
-- Purpose: Execution history of all scheduled jobs
-- ============================================================================
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,              -- MAM, TOP10, METADATA_FULL, METADATA_NEW, SERIES, AUTHOR

    -- Scheduling
    scheduled_time TIMESTAMP,
    actual_start TIMESTAMP,
    actual_end TIMESTAMP,
    duration_seconds INT,

    -- Status
    status VARCHAR(100) NOT NULL,                 -- scheduled, running, completed, failed

    -- Results
    items_processed INT DEFAULT 0,
    items_succeeded INT DEFAULT 0,
    items_failed INT DEFAULT 0,

    -- Logging
    log_output TEXT,
    error_message TEXT,

    -- Details for context
    metadata JSONB DEFAULT '{}',                  -- Task-specific metadata

    date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_task_name (task_name),
    INDEX idx_status (status),
    INDEX idx_scheduled_time (scheduled_time),
    INDEX idx_date_created (date_created)
);

-- ============================================================================
-- TABLE: failed_attempts
-- Purpose: PERMANENT tally of all failures (never deleted) for analytics
-- ============================================================================
CREATE TABLE failed_attempts (
    id SERIAL PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,              -- MAM, TOP10, METADATA_FULL, METADATA_NEW, SERIES, AUTHOR, DOWNLOAD

    -- What failed
    item_id INT,                                  -- book_id or other relevant ID
    item_name VARCHAR(500),

    -- Why it failed
    reason VARCHAR(500) NOT NULL,
    error_code VARCHAR(100),
    error_details TEXT,

    -- Tracking
    first_attempt TIMESTAMP,
    last_attempt TIMESTAMP NOT NULL,
    attempt_count INT DEFAULT 1,

    -- Metadata for analysis
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_task_name (task_name),
    INDEX idx_item_id (item_id),
    INDEX idx_last_attempt (last_attempt),
    INDEX idx_created_at (created_at),
    INDEX idx_attempt_count (attempt_count)
);

-- ============================================================================
-- TABLE: metadata_corrections
-- Purpose: History of all metadata changes (1-month retention)
-- ============================================================================
CREATE TABLE metadata_corrections (
    id SERIAL PRIMARY KEY,
    book_id INT NOT NULL REFERENCES books(id) ON DELETE CASCADE,

    field_name VARCHAR(100) NOT NULL,             -- title, author, series, etc.
    old_value TEXT,
    new_value TEXT,

    -- Source of correction
    source VARCHAR(100) NOT NULL,                 -- GoogleBooks, Goodreads, Manual, Auto-corrected

    -- Reason
    reason VARCHAR(255),

    correction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    corrected_by VARCHAR(100) DEFAULT 'system',   -- Username or 'system'

    INDEX idx_book_id (book_id),
    INDEX idx_field_name (field_name),
    INDEX idx_source (source),
    INDEX idx_correction_date (correction_date)
);

-- ============================================================================
-- TABLE: genre_settings
-- Purpose: Configurable genres for weekly top-10 feature
-- ============================================================================
CREATE TABLE genre_settings (
    id SERIAL PRIMARY KEY,
    genre_name VARCHAR(100) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    include_in_top10 BOOLEAN DEFAULT TRUE,

    last_top10_run TIMESTAMP,
    top10_count INT DEFAULT 10,                   -- Can override per genre

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_genre_name (genre_name),
    INDEX idx_enabled (enabled)
);

-- ============================================================================
-- TABLE: api_logs
-- Purpose: Optional logging of all API requests (1-month retention)
-- ============================================================================
CREATE TABLE api_logs (
    id SERIAL PRIMARY KEY,
    endpoint VARCHAR(255),
    method VARCHAR(10),
    request_body TEXT,
    response_code INT,
    response_time_ms INT,

    user_id INT,                                  -- For future multi-user support
    ip_address VARCHAR(45),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_endpoint (endpoint),
    INDEX idx_created_at (created_at),
    INDEX idx_user_id (user_id)
);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: Current series completion status
CREATE VIEW series_completion_summary AS
SELECT
    s.id,
    s.name,
    s.author,
    s.books_owned,
    s.books_missing,
    s.total_books_in_series,
    ROUND((s.books_owned::FLOAT / NULLIF(s.total_books_in_series, 0) * 100)::NUMERIC, 1) AS completion_percent,
    s.last_completion_check,
    s.completion_status
FROM series s
ORDER BY completion_percent ASC;

-- View: Current author completion status
CREATE VIEW author_completion_summary AS
SELECT
    a.id,
    a.name,
    a.audiobooks_owned,
    a.audiobooks_missing,
    a.total_audiobooks_external,
    ROUND((a.audiobooks_owned::FLOAT / NULLIF(a.total_audiobooks_external, 0) * 100)::NUMERIC, 1) AS completion_percent,
    a.last_completion_check,
    a.completion_status
FROM authors a
ORDER BY completion_percent ASC;

-- View: Recent failed downloads
CREATE VIEW recent_failed_downloads AS
SELECT
    d.id,
    d.title,
    d.author,
    d.source,
    d.status,
    d.retry_count,
    d.last_attempt,
    d.next_retry
FROM downloads d
WHERE d.status IN ('failed', 'abandoned')
  AND d.date_queued > CURRENT_TIMESTAMP - INTERVAL '30 days'
ORDER BY d.last_attempt DESC;

-- ============================================================================
-- INITIAL DATA: Insert genres from config
-- ============================================================================
INSERT INTO genre_settings (genre_name, enabled, include_in_top10)
VALUES
    ('Science Fiction', TRUE, TRUE),
    ('Fantasy', TRUE, TRUE),
    ('Mystery', TRUE, TRUE),
    ('Thriller', TRUE, TRUE),
    ('Romance', FALSE, FALSE),
    ('Erotica', FALSE, FALSE),
    ('Self-Help', FALSE, FALSE)
ON CONFLICT (genre_name) DO UPDATE
SET enabled = EXCLUDED.enabled, include_in_top10 = EXCLUDED.include_in_top10;

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================
-- Already created inline with table definitions
-- Key indexes:
--   - books(abs_id): Fast lookup by Audiobookshelf ID
--   - books(date_added): Timeline queries
--   - series(name, completion_status): Quick filtering
--   - authors(last_completion_check): Scheduling queries
--   - downloads(status, next_retry): Download scheduling
--   - tasks(task_name, status, date_created): Historical queries
--   - failed_attempts(task_name, last_attempt): Analytics

-- ============================================================================
-- DATA RETENTION POLICY
-- ============================================================================
-- The following tables are subject to 1-month history retention:
--   - tasks (delete older than 30 days)
--   - metadata_corrections (delete older than 30 days)
--   - api_logs (delete older than 30 days)
--
-- The following table has PERMANENT retention (never deleted):
--   - failed_attempts (keeps forever for analytics)
--
-- Implementation: Scheduled PostgreSQL CRON job to run nightly:
--   DELETE FROM tasks WHERE date_created < CURRENT_TIMESTAMP - INTERVAL '30 days';
--   DELETE FROM metadata_corrections WHERE correction_date < CURRENT_TIMESTAMP - INTERVAL '30 days';
--   DELETE FROM api_logs WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';

-- ============================================================================
-- TABLE: users
-- Purpose: Admin panel user accounts for authentication and authorization
-- ============================================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',        -- admin, moderator, viewer
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP,

    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_is_active (is_active)
);

-- ============================================================================
-- TABLE: audit_logs
-- Purpose: Audit trail for all admin actions (1-month retention)
-- ============================================================================
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,                      -- login, logout, create, update, delete, etc.
    resource VARCHAR(50) NOT NULL,                    -- user, config, system, etc.
    resource_id VARCHAR(50),                          -- ID of affected resource
    details TEXT,                                     -- JSON details of the action
    ip_address VARCHAR(45),                           -- IPv6 compatible
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_resource (resource),
    INDEX idx_timestamp (timestamp)
);

-- ============================================================================
-- INITIAL ADMIN USER
-- ============================================================================
-- Create default admin user (password: admin123 - CHANGE THIS IMMEDIATELY!)
INSERT INTO users (username, email, password_hash, role)
VALUES (
    'admin',
    'admin@mamcrawler.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPjYLC7TkWKq',  -- bcrypt hash of 'admin123'
    'admin'
);

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
